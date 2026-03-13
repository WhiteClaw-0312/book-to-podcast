"""
播客文案生成 Skill
将图书/文档内容转换为双人对话式播客文案
支持反复打磨优化 prompt
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel
from enum import Enum


class DialogueStyle(str, Enum):
    """对话风格"""
    HUMOROUS = "humorous"        # 幽默风趣
    SERIOUS = "serious"          # 严谨专业
    CASUAL = "casual"            # 轻松随意
    STORYTELLING = "storytelling" # 故事叙述


class PodcastConfig(BaseModel):
    """播客配置"""
    # 主持人配置
    host_a_name: str = "小北"
    host_a_style: str = "活泼好奇，喜欢提问和吐槽，偶尔用网络用语"
    host_b_name: str = "阿南"
    host_b_style: str = "沉稳博学，善于总结和引经据典"
    
    # 播客风格
    dialogue_style: DialogueStyle = DialogueStyle.HUMOROUS
    podcast_name: str = "枕边书"
    
    # 内容要求
    max_sentences_per_chapter: int = 50  # 每章最大对话数
    include_summary: bool = True          # 是否包含章节总结
    include_preview: bool = True          # 是否预告下期
    
    # 输出配置
    output_dir: str = "data/output/scripts"


# ==================== Prompt 模板 ====================
# 这些模板可以反复打磨优化

SYSTEM_PROMPT = """你是一位专业的播客文案编写专家。你的任务是将图书内容转换为生动有趣的双人对话式播客文案。

## 输出要求
1. 输出 JSON 格式，包含 dialogues 数组
2. 每条对话包含 speaker 和 content 字段
3. 两位主持人风格要有区分度
4. 对话要自然流畅，像真实聊天

## 输出格式示例
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

# 章节信息
- 书名: {book_title}
- 作者: {author}
- 章节编号: {chapter_number}
- 章节标题: {chapter_title}

# 章节内容
{chapter_content}

# 主持人设定
## {host_a_name}
- 风格: {host_a_style}

## {host_b_name}
- 风格: {host_b_style}

# 对话风格
{dialogue_style_instruction}

# 内容要求
1. 开场: 简短介绍本期主题
2. 核心: 用对话形式解读章节核心观点
   - 保留原文的重要论点和论据
   - 用生动的比喻和例子解释抽象概念
   - 主持人之间要有互动和碰撞
3. 结尾: 总结本章要点，预告下期内容

# 注意事项
1. 对话要自然，像朋友聊天
2. 可以适当加入幽默元素，但内容要严谨
3. 避免冗长的独白，多互动
4. 每句话控制在50字以内
5. 总对话数控制在{max_sentences}句左右

# 输出
直接输出 JSON，不要有其他内容。"""

DIALOGUE_STYLE_INSTRUCTIONS = {
    DialogueStyle.HUMOROUS: """- 幽默风趣，但不过分夸张
- 可以用网络用语和流行梗
- 适当吐槽和自嘲
- 让人边听边笑，同时学到东西""",

    DialogueStyle.SERIOUS: """- 严谨专业，但不要枯燥
- 引用原文和数据要准确
- 深入分析，层层递进
- 适合知识性强的内容""",

    DialogueStyle.CASUAL: """- 轻松随意，像朋友聊天
- 不要太正式，口语化
- 可以闲聊几句再切入正题
- 适合轻松的话题""",

    DialogueStyle.STORYTELLING: """- 故事叙述风格
- 营造画面感和代入感
- 适当停顿和悬念
- 像讲评书一样引人入胜"""
}


class PodcastWriterSkill:
    """
    播客文案生成 Skill
    - 将图书内容转换为双人对话
    - 支持多种对话风格
    - 可反复打磨 prompt
    """
    
    def __init__(self, config: Optional[PodcastConfig] = None):
        self.config = config or PodcastConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return SYSTEM_PROMPT
    
    def get_chapter_prompt(
        self,
        book_title: str,
        author: str,
        chapter_number: int,
        chapter_title: str,
        chapter_content: str
    ) -> str:
        """
        生成章节转换提示词
        
        这个 prompt 可以反复打磨优化
        """
        style_instruction = DIALOGUE_STYLE_INSTRUCTIONS.get(
            self.config.dialogue_style,
            DIALOGUE_STYLE_INSTRUCTIONS[DialogueStyle.HUMOROUS]
        )
        
        return CHAPTER_PROMPT_TEMPLATE.format(
            book_title=book_title,
            author=author,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            chapter_content=chapter_content,
            host_a_name=self.config.host_a_name,
            host_a_style=self.config.host_a_style,
            host_b_name=self.config.host_b_name,
            host_b_style=self.config.host_b_style,
            dialogue_style_instruction=style_instruction,
            max_sentences=self.config.max_sentences_per_chapter
        )
    
    def build_messages(
        self,
        book_title: str,
        author: str,
        chapter_number: int,
        chapter_title: str,
        chapter_content: str
    ) -> List[Dict[str, str]]:
        """
        构建完整的消息列表（用于 LLM API 调用）
        
        Returns:
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        return [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": self.get_chapter_prompt(
                book_title=book_title,
                author=author,
                chapter_number=chapter_number,
                chapter_title=chapter_title,
                chapter_content=chapter_content
            )}
        ]
    
    def parse_response(self, response_text: str) -> Optional[Dict]:
        """
        解析 LLM 返回的 JSON
        
        Args:
            response_text: LLM 返回的文本
        
        Returns:
            解析后的字典，或 None（解析失败）
        """
        # 尝试提取 JSON
        try:
            # 直接解析
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 ```json ... ```
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end > start:
                try:
                    return json.loads(response_text[start:end].strip())
                except json.JSONDecodeError:
                    pass
        
        # 尝试提取 ``` ... ```
        if "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end > start:
                try:
                    return json.loads(response_text[start:end].strip())
                except json.JSONDecodeError:
                    pass
        
        return None
    
    def save_script(
        self,
        script_data: Dict,
        output_name: str = None
    ) -> str:
        """
        保存播客文案
        
        Args:
            script_data: 文案数据
            output_name: 输出文件名（不含扩展名）
        
        Returns:
            保存的文件路径
        """
        if not output_name:
            output_name = f"chapter_{script_data.get('chapter_number', 1):02d}"
        
        # 保存 JSON
        json_path = self.output_dir / f"{output_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)
        
        # 保存 TXT（人类可读）
        txt_path = self.output_dir / f"{output_name}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            for dialogue in script_data.get("dialogues", []):
                speaker = dialogue.get("speaker", "未知")
                content = dialogue.get("content", "")
                f.write(f"[{speaker}]: {content}\n\n")
        
        return str(json_path)


# ==================== 可复用的 Skill 定义 ====================
# 这个 Skill 本身也可以被其他 LLM 调用

SKILL_DEFINITION = """
# 播客文案生成 Skill

## 功能
将图书/文档内容转换为双人对话式播客文案。

## 输入
- book_title: 书名
- author: 作者
- chapter_number: 章节编号
- chapter_title: 章节标题
- chapter_content: 章节内容文本

## 输出
JSON格式的播客文案，包含：
- chapter_number: 章节编号
- chapter_title: 章节标题
- dialogues: 对话数组 [{"speaker": "小北", "content": "..."}]
- duration_estimate: 预估时长（秒）

## 使用方法
```python
from src.skills.podcast_writer import PodcastWriterSkill, PodcastConfig

config = PodcastConfig(
    host_a_name="小北",
    host_b_name="阿南",
    dialogue_style="humorous"
)

skill = PodcastWriterSkill(config)
messages = skill.build_messages(
    book_title="无语问上帝",
    author="菲利普·杨西",
    chapter_number=1,
    chapter_title="要命的错误",
    chapter_content="..."
)

# 调用 LLM API
response = call_llm(messages)

# 解析结果
script_data = skill.parse_response(response)
```

## 可调优参数
- 主持人风格描述（host_a_style, host_b_style）
- 对话风格（dialogue_style）
- 每章最大对话数（max_sentences_per_chapter）
"""