"""Prompt模版 API"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models import PromptTemplate, User
from .auth import get_current_user, get_optional_user

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class PromptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    content: str
    is_public: bool = False


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_public: Optional[bool] = None


class PromptResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    content: str
    is_public: bool
    is_default: bool
    is_system: bool
    use_count: int
    user_id: Optional[str]

    class Config:
        from_attributes = True


# 默认系统Prompt
DEFAULT_PROMPT = """你是一位专业的播客编剧，擅长将图书内容转换为引人入胜的双人对话式播客。

主持人设定：
- 小北：活泼好奇，善于提问，用"诶~"、"哇"、"真的吗"等语气词增加互动感
- 阿南：沉稳博学，善于总结和解释，用"没错"、"其实"、"可以说"等连接词

对话风格：
1. 保持原文核心观点和精彩段落
2. 对话自然流畅，有互动感
3. 适当加入过渡和总结
4. 每章约 10-15 分钟时长（约 40-50 句对话）
5. 开头要有章节导入，结尾要有小结

输出要求：
- 只输出 JSON 格式，不要其他内容
- JSON 必须符合指定格式"""


def init_default_prompts(db: Session):
    """初始化默认Prompt模版"""
    existing = db.query(PromptTemplate).filter(PromptTemplate.is_system == True).first()
    if existing:
        return
    
    prompts = [
        PromptTemplate(
            name="标准播客风格",
            description="适用于大多数图书的标准双人对话播客风格",
            content=DEFAULT_PROMPT,
            is_system=True,
            is_default=True,
            is_public=True
        ),
        PromptTemplate(
            name="轻松访谈风格",
            description="更轻松活泼的访谈式对话",
            content=DEFAULT_PROMPT + "\n\n注意：对话更加轻松随意，像朋友聊天一样。",
            is_system=True,
            is_public=True
        ),
        PromptTemplate(
            name="深度解读风格",
            description="适合哲学、社科类书籍，深入解读内容",
            content=DEFAULT_PROMPT + "\n\n注意：对话更注重深度分析，每段对话更长。",
            is_system=True,
            is_public=True
        ),
    ]
    
    for p in prompts:
        db.add(p)
    db.commit()


@router.get("", response_model=List[PromptResponse])
async def list_prompts(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """获取Prompt模版列表"""
    # 初始化默认模版
    init_default_prompts(db)
    
    # 系统模版 + 公开模版 + 用户自己的模版
    query = db.query(PromptTemplate).filter(
        PromptTemplate.is_system == True
    )
    
    if user:
        # 也包含用户自己的模版
        query = db.query(PromptTemplate).filter(
            (PromptTemplate.is_system == True) |
            (PromptTemplate.is_public == True) |
            (PromptTemplate.user_id == user.id)
        )
    else:
        query = db.query(PromptTemplate).filter(
            (PromptTemplate.is_system == True) |
            (PromptTemplate.is_public == True)
        )
    
    return query.order_by(PromptTemplate.is_default.desc(), PromptTemplate.use_count.desc()).all()


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(prompt_id: str, db: Session = Depends(get_db)):
    """获取Prompt详情"""
    prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
    if not prompt:
        raise HTTPException(404, "Prompt模版不存在")
    return prompt


@router.post("", response_model=PromptResponse)
async def create_prompt(
    data: PromptCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建Prompt模版"""
    prompt = PromptTemplate(
        user_id=user.id,
        name=data.name,
        description=data.description,
        content=data.content,
        is_public=data.is_public
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    data: PromptUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新Prompt模版"""
    prompt = db.query(PromptTemplate).filter(
        PromptTemplate.id == prompt_id,
        PromptTemplate.user_id == user.id
    ).first()
    
    if not prompt:
        raise HTTPException(404, "Prompt模版不存在或无权修改")
    
    if data.name:
        prompt.name = data.name
    if data.description is not None:
        prompt.description = data.description
    if data.content:
        prompt.content = data.content
    if data.is_public is not None:
        prompt.is_public = data.is_public
    
    db.commit()
    db.refresh(prompt)
    return prompt


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除Prompt模版"""
    prompt = db.query(PromptTemplate).filter(
        PromptTemplate.id == prompt_id,
        PromptTemplate.user_id == user.id,
        PromptTemplate.is_system == False
    ).first()
    
    if not prompt:
        raise HTTPException(404, "Prompt模版不存在或无权删除")
    
    db.delete(prompt)
    db.commit()
    return {"message": "已删除"}