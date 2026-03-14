"""计费 API"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import APIKey, UsageLog
from ..schemas import APIKeyCreate, APIKeyResponse, BalanceResponse, UsageLogResponse

router = APIRouter(prefix="/api/keys", tags=["billing"])


@router.post("", response_model=APIKeyResponse)
async def create_api_key(
    data: APIKeyCreate,
    admin_key: str,
    db: Session = Depends(get_db)
):
    """创建 API Key（管理员）"""
    # TODO: 实现管理员验证
    if admin_key != "admin123":
        raise HTTPException(403, "管理员密钥错误")
    
    key = APIKey(
        name=data.name,
        balance=data.balance
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    
    return key


@router.get("/{api_key}/balance", response_model=BalanceResponse)
async def get_balance(api_key: str, db: Session = Depends(get_db)):
    """查询余额"""
    key = db.query(APIKey).filter(APIKey.key == api_key).first()
    
    if not key:
        raise HTTPException(404, "API Key 不存在")
    
    return BalanceResponse(
        key=key.key,
        balance=key.balance,
        total_used=key.total_used
    )


@router.post("/{api_key}/recharge")
async def recharge(
    api_key: str,
    amount: int,
    admin_key: str,
    db: Session = Depends(get_db)
):
    """充值（管理员）"""
    if admin_key != "admin123":
        raise HTTPException(403, "管理员密钥错误")
    
    key = db.query(APIKey).filter(APIKey.key == api_key).first()
    
    if not key:
        raise HTTPException(404, "API Key 不存在")
    
    key.balance += amount
    db.commit()
    
    return {"message": f"充值成功，当前余额: {key.balance}"}


@router.get("/{api_key}/usage", response_model=List[UsageLogResponse])
async def get_usage(
    api_key: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """查询用量日志"""
    from datetime import datetime, timedelta
    
    key = db.query(APIKey).filter(APIKey.key == api_key).first()
    if not key:
        raise HTTPException(404, "API Key 不存在")
    
    start_date = datetime.now() - timedelta(days=days)
    
    logs = db.query(UsageLog).filter(
        UsageLog.api_key == api_key,
        UsageLog.created_at >= start_date
    ).order_by(UsageLog.created_at.desc()).limit(100).all()
    
    return logs