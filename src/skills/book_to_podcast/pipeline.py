"""
图书转播客完整流程 Pipeline

流程：
PDF → Skill（skill-seekers）
    → 播客文稿（qwen3.5-plus，按章节）
    → 音频（qwen-tts + edge-tts 保底）
"""

import os
import json
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from .pdf_to_skill import PDFSkillExtractor, PDFSkillConfig, SkillOutput
from .podcast_writer import PodcastScriptGenerator, PodcastConfig, PodcastScript
from .audio_synthesizer import AudioSynthesizer, AudioConfig, AudioOutput


class PipelineConfig(BaseModel):
    """Pipeline 配置"""
    # API Keys
    qwen_api_key: str = ""          # Qwen3.5-plus（OCR + 文稿生成）
    qwen_tts_api_key: str = ""      # Qwen TTS
    
    # 输入输出
    input_pdf: str = ""             # 输入 PDF 路径
    output_base_dir: str = "data"   # 输出基础目录
    
    # 模块开关
    enable_skill_extraction: bool = True
    enable_script_generation: bool = True
    enable_audio_synthesis: bool = True
    
    # TTS 配置
    primary_tts_engine: str = "qwen"  # qwen 或 edge
    enable_tts_fallback: bool = True


class BookToPodcastPipeline:
    """
    图书转播客完整流程
    
    使用示例:
    ```python
    pipeline = BookToPodcastPipeline(
        qwen_api_key="sk-xxx",
        qwen_tts_api_key="sk-xxx"
    )
    
    result = pipeline.run("book.pdf")
    ```
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        
        # 设置输出目录
        self.base_dir = Path(self.config.output_base_dir)
        self.skill_dir = self.base_dir / "skills"
        self.script_dir = self.base_dir / "output" / "scripts"
        self.audio_dir = self.base_dir / "output" / "audio"
        
        # 创建目录
        for d in [self.skill_dir, self.script_dir, self.audio_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # 存储结果
        self.skill_output: Optional[SkillOutput] = None
        self.scripts: List[PodcastScript] = []
        self.audios: List[AudioOutput] = []
    
    def run(
        self,
        pdf_path: str,
        skill_name: str = None,
        skip_skill: bool = False,
        skip_script: bool = False,
        skip_audio: bool = False
    ) -> dict:
        """
        执行完整流程
        
        Args:
            pdf_path: PDF 文件路径
            skill_name: Skill 名称（默认使用文件名）
            skip_skill: 跳过 Skill 提取（使用已有的）
            skip_script: 跳过文稿生成
            skip_audio: 跳过音频合成
        
        Returns:
            结果字典
        """
        start_time = datetime.now()
        
        print("=" * 60)
        print("📚 图书转播客 Pipeline")
        print("=" * 60)
        
        if not skill_name:
            skill_name = Path(pdf_path).stem
        
        print(f"\n📖 书名: {skill_name}")
        print(f"📄 PDF: {pdf_path}")
        
        # Step 1: PDF → Skill
        if not skip_skill and self.config.enable_skill_extraction:
            print("\n" + "-" * 40)
            print("Step 1: PDF → Skill")
            print("-" * 40)
            
            skill_config = PDFSkillConfig(
                qwen_api_key=self.config.qwen_api_key,
                output_dir=str(self.skill_dir)
            )
            
            extractor = PDFSkillExtractor(skill_config)
            self.skill_output = extractor.extract(pdf_path, skill_name)
            
            print(f"✅ Skill 提取完成: {self.skill_output.skill_json_path}")
        
        # Step 2: Skill → 播客文稿
        if not skip_script and self.config.enable_script_generation:
            print("\n" + "-" * 40)
            print("Step 2: Skill → 播客文稿")
            print("-" * 40)
            
            # 加载 Skill（如果没有）
            if not self.skill_output:
                skill_json = self.skill_dir / f"{skill_name}_skill.json"
                if skill_json.exists():
                    with open(skill_json, "r", encoding="utf-8") as f:
                        skill_data = json.load(f)
                    self.skill_output = self._load_skill_from_json(skill_data, skill_json)
                else:
                    print("❌ 未找到 Skill 文件")
                    return {"success": False, "error": "Skill not found"}
            
            script_config = PodcastConfig(
                qwen_api_key=self.config.qwen_api_key,
                output_dir=str(self.script_dir)
            )
            
            generator = PodcastScriptGenerator(script_config)
            self.scripts = generator.generate_all_scripts(
                book_title=self.skill_output.metadata.get("title", skill_name),
                author=self.skill_output.metadata.get("author", "未知"),
                chapters=[{
                    "number": ch.number,
                    "title": ch.title,
                    "content": ch.content
                } for ch in self.skill_output.chapters]
            )
            
            print(f"✅ 文稿生成完成: {len(self.scripts)} 个章节")
        
        # Step 3: 文稿 → 音频
        if not skip_audio and self.config.enable_audio_synthesis:
            print("\n" + "-" * 40)
            print("Step 3: 文稿 → 音频")
            print("-" * 40)
            
            # 加载文稿（如果没有）
            if not self.scripts:
                for json_file in sorted(self.script_dir.glob("chapter_*.json")):
                    with open(json_file, "r", encoding="utf-8") as f:
                        script_data = json.load(f)
                        self.scripts.append(PodcastScript(
                            chapter_number=script_data["chapter_number"],
                            chapter_title=script_data["chapter_title"],
                            dialogues=script_data["dialogues"],
                            duration_estimate=script_data.get("duration_estimate", 0),
                            json_path=str(json_file),
                            txt_path=str(json_file).replace(".json", ".txt")
                        ))
            
            if not self.scripts:
                print("❌ 未找到文稿文件")
                return {"success": False, "error": "Scripts not found"}
            
            audio_config = AudioConfig(
                qwen_api_key=self.config.qwen_tts_api_key,
                output_dir=str(self.audio_dir),
                primary_engine=self.config.primary_tts_engine,
                fallback_enabled=self.config.enable_tts_fallback
            )
            
            synthesizer = AudioSynthesizer(audio_config)
            self.audios = synthesizer.synthesize_all_sync([
                {
                    "chapter_number": s.chapter_number,
                    "dialogues": s.dialogues
                }
                for s in self.scripts
            ])
            
            success_count = sum(1 for a in self.audios if a.success)
            print(f"✅ 音频合成完成: {success_count}/{len(self.audios)} 章")
        
        # 汇总
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("📊 执行汇总")
        print("=" * 60)
        
        result = {
            "success": True,
            "book_name": skill_name,
            "skill": {
                "path": self.skill_output.skill_json_path if self.skill_output else None,
                "chapters": len(self.skill_output.chapters) if self.skill_output else 0
            },
            "scripts": {
                "count": len(self.scripts),
                "total_dialogues": sum(len(s.dialogues) for s in self.scripts)
            },
            "audios": {
                "count": len(self.audios),
                "success": sum(1 for a in self.audios if a.success),
                "total_duration": sum(a.duration_seconds for a in self.audios if a.success)
            },
            "duration_seconds": duration
        }
        
        print(f"📚 章节: {result['skill']['chapters']}")
        print(f"📝 文稿: {result['scripts']['count']} 个, {result['scripts']['total_dialogues']} 句对话")
        print(f"🎵 音频: {result['audios']['success']}/{result['audios']['count']} 章")
        print(f"⏱️ 总时长: {result['audios']['total_duration']/60:.1f} 分钟")
        print(f"🕐 耗时: {duration:.1f} 秒")
        
        return result
    
    def _load_skill_from_json(self, data: dict, json_path: Path) -> SkillOutput:
        """从 JSON 加载 Skill"""
        from .pdf_to_skill import Chapter
        
        chapters = [
            Chapter(
                number=ch.get("number", i+1),
                title=ch.get("title", f"第{i+1}章"),
                content=ch.get("content", ""),
                word_count=ch.get("word_count", 0)
            )
            for i, ch in enumerate(data.get("chapters", []))
        ]
        
        md_path = Path(str(json_path).replace(".json", ".md"))
        
        return SkillOutput(
            metadata=data.get("metadata", {}),
            chapters=chapters,
            themes=data.get("themes", []),
            key_points=data.get("key_points", []),
            skill_md_path=str(md_path) if md_path.exists() else "",
            skill_json_path=str(json_path)
        )
    
    # ==================== 单独执行各步骤 ====================
    
    def extract_skill_only(self, pdf_path: str, skill_name: str = None) -> SkillOutput:
        """只执行 Skill 提取"""
        if not skill_name:
            skill_name = Path(pdf_path).stem
        
        config = PDFSkillConfig(
            qwen_api_key=self.config.qwen_api_key,
            output_dir=str(self.skill_dir)
        )
        
        extractor = PDFSkillExtractor(config)
        self.skill_output = extractor.extract(pdf_path, skill_name)
        return self.skill_output
    
    def generate_scripts_only(self, skill_json_path: str = None) -> List[PodcastScript]:
        """只执行文稿生成"""
        if skill_json_path:
            with open(skill_json_path, "r", encoding="utf-8") as f:
                skill_data = json.load(f)
            self.skill_output = self._load_skill_from_json(
                skill_data, Path(skill_json_path)
            )
        
        if not self.skill_output:
            raise ValueError("No skill loaded")
        
        config = PodcastConfig(
            qwen_api_key=self.config.qwen_api_key,
            output_dir=str(self.script_dir)
        )
        
        generator = PodcastScriptGenerator(config)
        self.scripts = generator.generate_all_scripts(
            book_title=self.skill_output.metadata.get("title", "未知"),
            author=self.skill_output.metadata.get("author", "未知"),
            chapters=[{
                "number": ch.number,
                "title": ch.title,
                "content": ch.content
            } for ch in self.skill_output.chapters]
        )
        
        return self.scripts
    
    def synthesize_audio_only(
        self,
        scripts_dir: str = None
    ) -> List[AudioOutput]:
        """只执行音频合成"""
        if scripts_dir:
            scripts_path = Path(scripts_dir)
            for json_file in sorted(scripts_path.glob("chapter_*.json")):
                with open(json_file, "r", encoding="utf-8") as f:
                    script_data = json.load(f)
                    self.scripts.append(PodcastScript(
                        chapter_number=script_data["chapter_number"],
                        chapter_title=script_data["chapter_title"],
                        dialogues=script_data["dialogues"],
                        duration_estimate=script_data.get("duration_estimate", 0),
                        json_path=str(json_file),
                        txt_path=str(json_file).replace(".json", ".txt")
                    ))
        
        if not self.scripts:
            raise ValueError("No scripts loaded")
        
        config = AudioConfig(
            qwen_api_key=self.config.qwen_tts_api_key,
            output_dir=str(self.audio_dir),
            primary_engine=self.config.primary_tts_engine,
            fallback_enabled=self.config.enable_tts_fallback
        )
        
        synthesizer = AudioSynthesizer(config)
        self.audios = synthesizer.synthesize_all_sync([
            {
                "chapter_number": s.chapter_number,
                "dialogues": s.dialogues
            }
            for s in self.scripts
        ])
        
        return self.audios


# ==================== 便捷函数 ====================

def convert_book_to_podcast(
    pdf_path: str,
    qwen_api_key: str,
    qwen_tts_api_key: str,
    output_dir: str = "data"
) -> dict:
    """
    一键转换图书为播客
    
    Args:
        pdf_path: PDF 文件路径
        qwen_api_key: Qwen API Key（用于 OCR + 文稿生成）
        qwen_tts_api_key: Qwen TTS API Key
        output_dir: 输出目录
    
    Returns:
        结果字典
    """
    config = PipelineConfig(
        qwen_api_key=qwen_api_key,
        qwen_tts_api_key=qwen_tts_api_key,
        output_base_dir=output_dir
    )
    
    pipeline = BookToPodcastPipeline(config)
    return pipeline.run(pdf_path)