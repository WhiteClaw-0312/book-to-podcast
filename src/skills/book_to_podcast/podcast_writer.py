"""
播客文稿生成模块
使用 Qwen3.5-plus 生成双人对话式播客文稿
按章节生成，一章一个文稿
"""

import os
import json
import openai
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel
from dataclasses import dataclass


class PodcastConfig(BaseModel):
    """播客配置"""
    # Qwen API 配置
    qwen_api_key: str = ""
    qwen_model: str = "qwen3.5-plus"
    base_url: str = "https://coding.dashscope.aliyuncs.com/v1"
    
    # 主持人配置
    host_a_name: str = "小北"
    host_a_style: str = "活泼好奇，喜欢提问和吐槽，偶尔用网络用语，语气轻松"
    host_b_name: str = "阿南"
    host_b_style: str = "沉稳博学，善于总结和引经据典，语气温和"
    
    # 播客设置
    podcast_name: str = "枕边书"
    max_sentences_per_chapter: int = 60  # 每章最大对话数
    
    # 输出配置
    output_dir: str = "data/output/scripts"


@dataclass
class PodcastScript:
    """播客文稿"""
    chapter_number: int
    chapter_title: str
    dialogues: List[Dict[str, str]]
    duration_estimate: int  # 预估时长（秒）
    json_path: str
    txt_path: str


# ==================== Prompt 模板 ====================
# 这些模板可以反复打磨优化

SYSTEM_PROMPT = """你是一位专业的播客文案编写专家。你的任务是将图书章节内容转换为生动有趣的双人对话式播客文案。

## 输出要求
1. 输出 JSON 格式，包含 chapter_number, chapter_title, dialogues, duration_estimate
2. dialogues 是数组，每条包含 speaker 和 content
3. 两位主持人风格要有明显区分
4. 对话要自然流畅，像真实聊天

## 输出格式
```json
{
  "chapter_number": 1,
  "chapter_title": "章节标题",
  "dialogues": [
    {"speaker": "小北", "content": "..."},
    {"speaker": "阿南", "content": "..."}
  ],
  "duration_estimate": 300
}
```"""

CHAPTER_PROMPT_TEMPLATE = """# 任务
将以下图书章节内容转换为双人对话式播客文案。

# 书籍信息
- 书名: {book_title}
- 作者: {author}
- 当前章节: 第 {chapter_number} 章 - {chapter_title}

# 章节内容
{chapter_content}

# 主持人设定

## {host_a_name}（主持人A）
- 风格: {host_a_style}
- 职责: 引出话题、提问、活跃气氛

## {host_b_name}（主持人B）
- 风格: {host_b_style}
- 职责: 解答问题、深入分析、总结要点

# 对话要求

1. **开场** (2-3句)
   - 简短介绍本期主题
   - 可以回顾上期内容（如果有多期）

2. **核心内容** (40-50句)
   - 用对话形式解读章节核心观点
   - 保留原文的重要论点和论据
   - 用生动的比喻和例子解释抽象概念
   - 主持人之间要有互动和思想碰撞
   - 可以适当加入幽默元素

3. **结尾** (3-5句)
   - 总结本章要点
   - 预告下期内容（如果是连载）
   - 引导订阅关注

# 风格要求

1. 对话要自然，像朋友聊天，不要像念稿子
2. 每句话控制在30-50字以内
3. 避免冗长的独白，要多互动
4. 内容要严谨，但形式可以活泼
5. 可以适当加入口语化表达，如"哎"、"哈哈"、"对吧"等

# 输出
直接输出 JSON，不要有其他内容。总对话数控制在 {max_sentences} 句左右。"""


class PodcastScriptGenerator:
    """
    播客文稿生成器
    
    使用 Qwen3.5-plus 将章节内容转换为双人对话
    """
    
    def __init__(self, config: Optional[PodcastConfig] = None):
        self.config = config or PodcastConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 OpenAI 客户端
        self.client = openai.OpenAI(
            api_key=self.config.qwen_api_key,
            base_url=self.config.base_url
        )
    
    def generate_chapter_script(
        self,
        book_title: str,
        author: str,
        chapter_number: int,
        chapter_title: str,
        chapter_content: str
    ) -> PodcastScript:
        """
        生成单章播客文稿
        
        Args:
            book_title: 书名
            author: 作者
            chapter_number: 章节编号
            chapter_title: 章节标题
            chapter_content: 章节内容
        
        Returns:
            PodcastScript 对象
        """
        print(f"📝 生成第 {chapter_number} 章文稿: {chapter_title}")
        
        # 构建提示词
        prompt = CHAPTER_PROMPT_TEMPLATE.format(
            book_title=book_title,
            author=author,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            chapter_content=chapter_content[:8000],  # 限制长度
            host_a_name=self.config.host_a_name,
            host_a_style=self.config.host_a_style,
            host_b_name=self.config.host_b_name,
            host_b_style=self.config.host_b_style,
            max_sentences=self.config.max_sentences_per_chapter
        )
        
        # 调用 Qwen
        try:
            response = self.client.chat.completions.create(
                model=self.config.qwen_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content
            
            # 解析 JSON
            script_data = self._parse_response(result_text)
            
            if not script_data:
                print(f"⚠️ 解析失败，使用保底方案")
                script_data = self._create_fallback_script(
                    chapter_number, chapter_title, chapter_content
                )
            
        except Exception as e:
            print(f"❌ 生成失败: {e}")
            script_data = self._create_fallback_script(
                chapter_number, chapter_title, chapter_content
            )
        
        # 保存文稿
        return self._save_script(script_data)
    
    def generate_all_scripts(
        self,
        book_title: str,
        author: str,
        chapters: List[Dict]
    ) -> List[PodcastScript]:
        """
        生成所有章节的播客文稿
        
        Args:
            book_title: 书名
            author: 作者
            chapters: 章节列表 [{"number": 1, "title": "...", "content": "..."}]
        
        Returns:
            PodcastScript 列表
        """
        scripts = []
        total = len(chapters)
        
        for i, chapter in enumerate(chapters):
            print(f"\n📖 处理第 {i+1}/{total} 章")
            
            script = self.generate_chapter_script(
                book_title=book_title,
                author=author,
                chapter_number=chapter["number"],
                chapter_title=chapter["title"],
                chapter_content=chapter["content"]
            )
            
            scripts.append(script)
            
            print(f"✅ 第 {chapter['number']} 章完成: {len(script.dialogues)} 句对话")
        
        print(f"\n🎉 全部完成: {len(scripts)} 个文稿")
        return scripts
    
    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """解析 LLM 返回的 JSON"""
        import re
        
        # 尝试直接解析
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 ```json ... ```
        json_patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'\{[\s\S]*\}'
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response_text)
            if match:
                try:
                    json_str = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _create_fallback_script(
        self,
        chapter_number: int,
        chapter_title: str,
        chapter_content: str
    ) -> Dict:
        """创建保底文稿（当 LLM 失败时）"""
        return {
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "dialogues": [
                {
                    "speaker": self.config.host_a_name,
                    "content": f"大家好，欢迎收听{self.config.podcast_name}。今天我们继续读这本书。"
                },
                {
                    "speaker": self.config.host_b_name,
                    "content": f"这一章的标题是「{chapter_title}」，我们来聊聊这个话题。"
                },
                {
                    "speaker": self.config.host_a_name,
                    "content": chapter_content[:200] + "..."
                },
                {
                    "speaker": self.config.host_b_name,
                    "content": "这章内容很丰富，我们下期继续。"
                }
            ],
            "duration_estimate": 120
        }
    
    def _save_script(self, script_data: Dict) -> PodcastScript:
        """保存文稿到文件"""
        chapter_number = script_data.get("chapter_number", 1)
        chapter_title = script_data.get("chapter_title", "未知章节")
        dialogues = script_data.get("dialogues", [])
        duration = script_data.get("duration_estimate", 300)
        
        # 文件名
        output_name = f"chapter_{chapter_number:02d}"
        
        # 保存 JSON
        json_path = self.output_dir / f"{output_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)
        
        # 保存 TXT
        txt_path = self.output_dir / f"{output_name}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            for d in dialogues:
                f.write(f"[{d['speaker']}]: {d['content']}\n\n")
        
        return PodcastScript(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            dialogues=dialogues,
            duration_estimate=duration,
            json_path=str(json_path),
            txt_path=str(txt_path)
        )


# ==================== 便捷函数 ====================

def generate_podcast_scripts(
    skill_json_path: str,
    qwen_api_key: str = "",
    output_dir: str = "data/output/scripts"
) -> List[PodcastScript]:
    """
    从 Skill JSON 生成所有播客文稿
    
    Args:
        skill_json_path: Skill JSON 文件路径
        qwen_api_key: Qwen API Key
        output_dir: 输出目录
    
    Returns:
        PodcastScript 列表
    """
    # 加载 Skill
    with open(skill_json_path, "r", encoding="utf-8") as f:
        skill = json.load(f)
    
    # 配置
    config = PodcastConfig(
        qwen_api_key=qwen_api_key,
        output_dir=output_dir
    )
    
    # 生成
    generator = PodcastScriptGenerator(config)
    return generator.generate_all_scripts(
        book_title=skill["metadata"]["title"],
        author=skill["metadata"].get("author", "未知"),
        chapters=skill["chapters"]
    )