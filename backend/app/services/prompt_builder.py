"""
Prompt Builder 服务 v5.0
根据用户配置构建播客生成 Prompt
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PromptConfig:
    """Prompt 配置"""
    # 1. 风格
    style: str = "casual"
    
    # 2. 讲述人
    speaker_count: int = 2
    speakers: List[Dict] = None
    
    # 3. 长度
    dialogue_count: int = 65
    
    # 4. 高级选项
    interaction_level: str = "balanced"
    content_depth: str = "moderate"
    emotion_style: str = "natural"
    pace: str = "moderate"
    
    # 5. 特色功能
    enable_intro: bool = True
    enable_summary: bool = True
    keep_quotes: bool = False
    highlight_quotes: bool = False
    enable_qa: bool = False
    
    def __post_init__(self):
        if self.speakers is None:
            self.speakers = self._default_speakers()
    
    def _default_speakers(self):
        """默认讲述人配置"""
        default_configs = {
            1: [{"name": "讲述人", "gender": "neutral"}],
            2: [
                {"name": "小北", "gender": "female"},
                {"name": "阿南", "gender": "male"}
            ],
            3: [
                {"name": "小北", "gender": "female"},
                {"name": "阿南", "gender": "male"},
                {"name": "老王", "gender": "male"}
            ],
            4: [
                {"name": "小北", "gender": "female"},
                {"name": "阿南", "gender": "male"},
                {"name": "老王", "gender": "male"},
                {"name": "小李", "gender": "female"}
            ]
        }
        return default_configs.get(self.speaker_count, default_configs[2])


class PromptBuilder:
    """Prompt 构建器"""
    
    # 风格映射
    STYLE_PROMPTS = {
        "humorous": """对话风格：幽默风趣
- 使用轻松幽默的语言，可以适当穿插段子和网络流行语
- 让严肃的内容变得有趣，可以适度调侃增加趣味性
- 用词活泼，让人会心一笑""",
        
        "professional": """对话风格：严谨专业
- 使用专业、准确的语言，逻辑清晰，论证有力
- 避免过度口语化表达，保持学术严谨性
- 用词精准，表述规范""",
        
        "casual": """对话风格：日常聊天
- 像朋友聊天一样自然，使用口语化表达
- 可以用"诶~"、"哇"、"真的吗"等语气词增加互动感
- 轻松不刻板，让人感觉亲切""",
        
        "news": """对话风格：新闻播报
- 正式、客观的语调，像新闻报道一样陈述
- 语言简洁有力，避免过多情感色彩
- 结构清晰，信息密度高""",
        
        "storytelling": """对话风格：故事讲述
- 有故事性，引人入胜，适当设置悬念
- 用情节推动内容，让听众有代入感
- 娓娓道来，有画面感""",
        
        "educational": """对话风格：知识科普
- 深入浅出，通俗易懂，把复杂概念讲简单
- 多用类比和例子，面向小白用户
- 循序渐进，便于理解"""
    }
    
    # 互动程度映射
    INTERACTION_PROMPTS = {
        "high": "互动程度：高互动\n- 频繁的问答和插话，多用追问、反问\n- 增加讨论感，像是在激烈讨论",
        "balanced": "互动程度：平衡\n- 适度的问答互动，一问一答为主\n- 有来有往，节奏舒适",
        "low": "互动程度：低互动\n- 更多单人讲述，减少打断和插话\n- 更像是轮流演讲"
    }
    
    # 内容深度映射
    DEPTH_PROMPTS = {
        "simple": "内容深度：浅显易懂\n- 避免专业术语，用通俗语言解释\n- 面向入门读者，不假设背景知识",
        "moderate": "内容深度：适中\n- 平衡专业性和易读性，必要时解释术语\n- 面向一般读者",
        "deep": "内容深度：深度分析\n- 保留专业术语，深入分析原理\n- 面向专业读者，追求深度"
    }
    
    # 情感表达映射
    EMOTION_PROMPTS = {
        "enthusiastic": "情感表达：热情活泼\n- 充满激情，语气高昂\n- 积极正面，感染力强",
        "natural": "情感表达：平和自然\n- 舒适自然，不刻意煽情\n- 恰到好处的情感",
        "calm": "情感表达：冷静客观\n- 理性分析，不带情绪色彩\n- 像旁观者一样陈述"
    }
    
    # 节奏映射
    PACE_PROMPTS = {
        "fast": "节奏控制：快节奏\n- 信息密集，快速推进\n- 少留白，紧凑有力",
        "moderate": "节奏控制：适中\n- 张弛有度，信息和留白平衡\n- 舒适的节奏",
        "slow": "节奏控制：慢节奏\n- 舒缓放松，多留白\n- 让听众有时间思考和消化"
    }
    
    # 性别特征映射
    GENDER_TRAITS = {
        "humorous": {
            "female": "活泼可爱，喜欢用\"诶~\"、\"哇\"等语气词，反应快",
            "male": "幽默风趣，喜欢开玩笑和吐槽，接梗王",
            "neutral": "风趣幽默，善于活跃气氛"
        },
        "professional": {
            "female": "专业严谨，用词准确，思维缜密",
            "male": "学识渊博，逻辑清晰，论述有力",
            "neutral": "专业客观，条理清晰"
        },
        "casual": {
            "female": "活泼好奇，善于提问，反应快",
            "male": "沉稳博学，善于解释，条理好",
            "neutral": "自然随和，善于引导"
        },
        "news": {
            "female": "专业播音范儿，清晰流畅",
            "male": "新闻主播范儿，沉稳大气",
            "neutral": "客观中立，播报清晰"
        },
        "storytelling": {
            "female": "声音有感染力，善于渲染氛围",
            "male": "故事感强，善于设置悬念",
            "neutral": "娓娓道来，引人入胜"
        },
        "educational": {
            "female": "耐心细致，善于用类比",
            "male": "条理清晰，善于归纳总结",
            "neutral": "循序渐进，深入浅出"
        }
    }
    
    def build(
        self,
        config: PromptConfig,
        skill: Dict,
        chapter_info: Dict
    ) -> str:
        """构建完整 Prompt"""
        
        # 1. 系统角色定义
        system_prompt = self._build_system_prompt(config)
        
        # 2. 主持人设定
        speaker_prompt = self._build_speaker_prompt(config)
        
        # 3. 内容要求
        content_prompt = self._build_content_prompt(config, skill, chapter_info)
        
        # 4. 输出格式
        format_prompt = self._build_format_prompt(config)
        
        # 组合
        full_prompt = f"""{system_prompt}

{speaker_prompt}

{content_prompt}

{format_prompt}"""
        
        return full_prompt.strip()
    
    def _build_system_prompt(self, config: PromptConfig) -> str:
        """构建系统角色 Prompt"""
        style_prompt = self.STYLE_PROMPTS.get(config.style, self.STYLE_PROMPTS["casual"])
        interaction_prompt = self.INTERACTION_PROMPTS.get(config.interaction_level, "")
        depth_prompt = self.DEPTH_PROMPTS.get(config.content_depth, "")
        emotion_prompt = self.EMOTION_PROMPTS.get(config.emotion_style, "")
        pace_prompt = self.PACE_PROMPTS.get(config.pace, "")
        
        return f"""# 角色定义

你是一位专业的播客编剧，擅长将书籍内容转换为引人入胜的播客对话。

{style_prompt}

{interaction_prompt}

{depth_prompt}

{emotion_prompt}

{pace_prompt}"""
    
    def _build_speaker_prompt(self, config: PromptConfig) -> str:
        """构建主持人设定 Prompt"""
        speakers_desc = []
        for speaker in config.speakers:
            gender_desc = {"female": "女声", "male": "男声", "neutral": "中性"}.get(
                speaker["gender"], "中性"
            )
            speakers_desc.append(f'- {speaker["name"]}（{gender_desc}）')
        
        # 根据风格获取性格特点
        style_traits = self.GENDER_TRAITS.get(config.style, self.GENDER_TRAITS["casual"])
        speaker_traits = []
        for speaker in config.speakers:
            trait = style_traits.get(speaker["gender"], "善于讲述")
            speaker_traits.append(f'- {speaker["name"]}：{trait}')
        
        return f"""# 主持人设定

本播客有 {config.speaker_count} 位主持人：

{chr(10).join(speakers_desc)}

主持人特点：
{chr(10).join(speaker_traits)}"""
    
    def _build_content_prompt(
        self,
        config: PromptConfig,
        skill: Dict,
        chapter_info: Dict
    ) -> str:
        """构建内容要求 Prompt"""
        
        # 长度要求
        length_requirement = f"对话数量：约 {config.dialogue_count} 句（上下浮动不超过10句）"
        
        # 特色功能
        features = []
        if config.enable_intro:
            features.append("- 开头要有章节引入，自然过渡到正题")
        if config.enable_summary:
            features.append("- 结尾要有内容总结，概括本章要点")
        if config.keep_quotes:
            features.append("- 保留书中的原话引用，用「」标注")
        if config.highlight_quotes:
            features.append("- 提炼并强调金句，用「」标注并解释其重要性")
        if config.enable_qa:
            features.append("- 结尾加入问答环节，解答读者可能的疑问")
        
        features_text = chr(10).join(features) if features else "- 无特殊要求"
        
        # 内容来源
        key_points = skill.get('key_points', [])
        important_details = skill.get('important_details', [])
        examples = skill.get('examples', [])
        
        content_source = f"""# 内容来源

书籍信息：
- 书名：《{chapter_info.get('book_title', '未知')}》
- 章节：第{chapter_info.get('number', 1)}章 - {chapter_info.get('title', '未知章节')}

## 📌 章节摘要

{skill.get('summary', '暂无摘要')}

## 💡 核心观点（必须全部覆盖）

{self._format_list(key_points)}

## 📝 重要细节（必须体现）

{self._format_list(important_details)}

## 🎯 重要示例（自然融入）

{self._format_list(examples)}"""
        
        return f"""# 内容要求

{length_requirement}

特色功能：
{features_text}

{content_source}

## 重要规则

1. **必须覆盖所有"核心观点"** - 一个都不能少
2. **"重要细节"必须体现在对话中** - 用自然的方式融入
3. **"重要示例"要自然融入** - 作为论据或说明
4. **不能遗漏任何关键内容** - 这是最重要的原则
5. **对话要自然流畅** - 像真人聊天一样"""
    
    def _build_format_prompt(self, config: PromptConfig) -> str:
        """构建输出格式 Prompt"""
        
        # 根据人数生成示例
        example_dialogues = []
        for i in range(min(4, config.speaker_count)):
            speaker = config.speakers[i % len(config.speakers)]
            example_dialogues.append(
                f'    {{"speaker": "{speaker["name"]}", "content": "..."}}'
            )
        
        return f"""# 输出格式

**只输出 JSON 格式，不要其他任何内容。**

```json
{{
  "chapter_number": {config.speaker_count},
  "chapter_title": "章节标题",
  "dialogue_count": {config.dialogue_count},
  "dialogues": [
{chr(10).join(example_dialogues)}
  ]
}}
```

注意：
- speaker 必须是设定的主持人名字之一
- content 是该主持人的台词
- 确保输出的是合法的 JSON 格式"""
    
    def _format_list(self, items: List[str]) -> str:
        """格式化列表"""
        if not items:
            return "（无）"
        return chr(10).join(f"- {item}" for item in items)


def build_prompt_from_model(prompt_model, skill: Dict, chapter_info: Dict) -> str:
    """从数据库模型构建 Prompt"""
    config = PromptConfig(
        style=prompt_model.style or "casual",
        speaker_count=prompt_model.speaker_count or 2,
        speakers=prompt_model.speakers,
        dialogue_count=prompt_model.dialogue_count or 65,
        interaction_level=prompt_model.interaction_level or "balanced",
        content_depth=prompt_model.content_depth or "moderate",
        emotion_style=prompt_model.emotion_style or "natural",
        pace=prompt_model.pace or "moderate",
        enable_intro=prompt_model.enable_intro if prompt_model.enable_intro is not None else True,
        enable_summary=prompt_model.enable_summary if prompt_model.enable_summary is not None else True,
        keep_quotes=prompt_model.keep_quotes or False,
        highlight_quotes=prompt_model.highlight_quotes or False,
        enable_qa=prompt_model.enable_qa or False
    )
    
    builder = PromptBuilder()
    return builder.build(config, skill, chapter_info)