"""
Prompt 配置 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from ..database import get_db
from ..models import PromptTemplate, User
from .auth import get_current_user

router = APIRouter(prefix="/api/prompt-configs", tags=["prompt-config"])


# ===== Pydantic Models =====

class SpeakerConfig(BaseModel):
    name: str
    gender: str  # female, male, neutral


class PromptConfigCreate(BaseModel):
    name: str
    description: Optional[str] = None
    
    # 配置项
    style: str = "casual"
    speaker_count: int = 2
    speakers: List[SpeakerConfig] = None
    dialogue_count: int = 65
    
    interaction_level: str = "balanced"
    content_depth: str = "moderate"
    emotion_style: str = "natural"
    pace: str = "moderate"
    
    enable_intro: bool = True
    enable_summary: bool = True
    keep_quotes: bool = False
    highlight_quotes: bool = False
    enable_qa: bool = False
    
    is_public: bool = False


class PromptConfigResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    
    style: str
    speaker_count: int
    speakers: Optional[List[dict]]
    dialogue_count: int
    
    interaction_level: str
    content_depth: str
    emotion_style: str
    pace: str
    
    enable_intro: bool
    enable_summary: bool
    keep_quotes: bool
    highlight_quotes: bool
    enable_qa: bool
    
    is_default: bool
    is_system: bool
    use_count: int
    
    class Config:
        from_attributes = True


# ===== API Endpoints =====

@router.get("/defaults")
async def get_default_options():
    """获取可选项列表"""
    return {
        "styles": [
            {"value": "humorous", "label": "🎭 幽默风趣", "desc": "轻松搞笑，穿插段子"},
            {"value": "professional", "label": "📚 严谨专业", "desc": "学术严谨，逻辑清晰"},
            {"value": "casual", "label": "☕ 日常聊天", "desc": "像朋友聊天，自然随性"},
            {"value": "news", "label": "🎙️ 新闻播报", "desc": "正式客观，新闻风格"},
            {"value": "storytelling", "label": "🌟 故事讲述", "desc": "引人入胜，有故事感"},
            {"value": "educational", "label": "💡 知识科普", "desc": "深入浅出，易懂"}
        ],
        "interaction_levels": [
            {"value": "high", "label": "🔥 高互动", "desc": "频繁问答、插话"},
            {"value": "balanced", "label": "⚖️ 平衡", "desc": "适度互动"},
            {"value": "low", "label": "📢 低互动", "desc": "更多讲述"}
        ],
        "content_depths": [
            {"value": "simple", "label": "🎈 浅显易懂", "desc": "面向小白"},
            {"value": "moderate", "label": "📊 适中深度", "desc": "平衡专业和易懂"},
            {"value": "deep", "label": "🔬 深度分析", "desc": "面向专业人士"}
        ],
        "emotion_styles": [
            {"value": "enthusiastic", "label": "🎉 热情活泼", "desc": "充满激情"},
            {"value": "natural", "label": "😌 平和自然", "desc": "舒适自然"},
            {"value": "calm", "label": "🧘 冷静客观", "desc": "理性分析"}
        ],
        "paces": [
            {"value": "fast", "label": "⚡ 快节奏", "desc": "信息密集"},
            {"value": "moderate", "label": "🎵 适中节奏", "desc": "张弛有度"},
            {"value": "slow", "label": "🐢 慢节奏", "desc": "舒缓放松"}
        ],
        "lengths": [
            {"value": 45, "label": "精简版", "desc": "5-8分钟，40-50句"},
            {"value": 65, "label": "标准版", "desc": "10-12分钟，60-70句"},
            {"value": 90, "label": "详细版", "desc": "15-20分钟，80-100句"}
        ],
        "default_speakers": {
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
    }


@router.get("/system")
async def get_system_configs(db: Session = Depends(get_db)):
    """获取系统预设配置"""
    configs = db.query(PromptTemplate).filter(
        PromptTemplate.is_system == True
    ).all()
    
    return configs


@router.get("/my-configs")
async def get_my_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的自定义配置"""
    configs = db.query(PromptTemplate).filter(
        PromptTemplate.user_id == current_user.id
    ).all()
    
    return configs


@router.post("/")
async def create_config(
    config: PromptConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建自定义配置"""
    template = PromptTemplate(
        user_id=current_user.id,
        name=config.name,
        description=config.description,
        
        style=config.style,
        speaker_count=config.speaker_count,
        speakers=[s.model_dump() for s in config.speakers] if config.speakers else None,
        dialogue_count=config.dialogue_count,
        
        interaction_level=config.interaction_level,
        content_depth=config.content_depth,
        emotion_style=config.emotion_style,
        pace=config.pace,
        
        enable_intro=config.enable_intro,
        enable_summary=config.enable_summary,
        keep_quotes=config.keep_quotes,
        highlight_quotes=config.highlight_quotes,
        enable_qa=config.enable_qa,
        
        is_public=config.is_public
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return {"success": True, "id": template.id}


@router.put("/{config_id}")
async def update_config(
    config_id: str,
    config: PromptConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新配置"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == config_id,
        PromptTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    template.name = config.name
    template.description = config.description
    template.style = config.style
    template.speaker_count = config.speaker_count
    template.speakers = [s.model_dump() for s in config.speakers] if config.speakers else None
    template.dialogue_count = config.dialogue_count
    template.interaction_level = config.interaction_level
    template.content_depth = config.content_depth
    template.emotion_style = config.emotion_style
    template.pace = config.pace
    template.enable_intro = config.enable_intro
    template.enable_summary = config.enable_summary
    template.keep_quotes = config.keep_quotes
    template.highlight_quotes = config.highlight_quotes
    template.enable_qa = config.enable_qa
    
    db.commit()
    
    return {"success": True}


@router.delete("/{config_id}")
async def delete_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除配置"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == config_id,
        PromptTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    if template.is_system:
        raise HTTPException(status_code=400, detail="系统配置不能删除")
    
    db.delete(template)
    db.commit()
    
    return {"success": True}


@router.put("/{config_id}/set-default")
async def set_as_default(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """设置默认配置"""
    # 先清除其他默认
    db.query(PromptTemplate).filter(
        PromptTemplate.user_id == current_user.id
    ).update({"is_default": False})
    
    # 设置新的默认
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == config_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    # 允许设置系统配置为默认
    template.is_default = True
    db.commit()
    
    return {"success": True}


@router.get("/{config_id}")
async def get_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """获取单个配置详情"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == config_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    return template