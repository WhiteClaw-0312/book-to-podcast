"""用户认证 API"""
import secrets
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from ..database import get_db
from ..models import User, APIKey

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

# 简单的token存储（生产环境应用Redis）
active_tokens = {}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    nickname: str
    api_key: str
    balance: int
    free_quota: int

    class Config:
        from_attributes = True


def generate_token():
    """生成认证token"""
    return secrets.token_hex(32)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录"
        )
    
    token = credentials.credentials
    user_id = active_tokens.get(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """获取可选用户（不强制登录）"""
    if not credentials:
        return None
    
    token = credentials.credentials
    user_id = active_tokens.get(token)
    
    if not user_id:
        return None
    
    return db.query(User).filter(User.id == user_id).first()


@router.post("/register")
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查邮箱是否已注册
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(400, "该邮箱已注册")
    
    # 创建API Key
    api_key = APIKey(
        name=f"用户 {data.email}",
        balance=0
    )
    db.add(api_key)
    db.flush()
    
    # 创建用户
    import hashlib
    password_hash = hashlib.sha256(data.password.encode()).hexdigest()
    
    user = User(
        email=data.email,
        password_hash=password_hash,
        api_key=api_key.key,
        nickname=data.nickname or data.email.split("@")[0],
        free_quota=3
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 生成token（与登录保持一致）
    token = generate_token()
    active_tokens[token] = user.id
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "api_key": user.api_key,
            "balance": api_key.balance,
            "free_quota": user.free_quota
        }
    }


@router.post("/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    import hashlib
    password_hash = hashlib.sha256(data.password.encode()).hexdigest()
    
    user = db.query(User).filter(
        User.email == data.email,
        User.password_hash == password_hash
    ).first()
    
    if not user:
        raise HTTPException(401, "邮箱或密码错误")
    
    if not user.is_active:
        raise HTTPException(403, "账户已被禁用")
    
    # 生成token
    token = generate_token()
    active_tokens[token] = user.id
    
    # 获取余额
    api_key = db.query(APIKey).filter(APIKey.key == user.api_key).first()
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "api_key": user.api_key,
            "balance": api_key.balance if api_key else 0,
            "free_quota": user.free_quota
        }
    }


@router.post("/logout")
async def logout(user: User = Depends(get_current_user)):
    """用户登出"""
    # 清除token
    tokens_to_remove = [k for k, v in active_tokens.items() if v == user.id]
    for t in tokens_to_remove:
        active_tokens.pop(t, None)
    
    return {"message": "已登出"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户信息"""
    api_key = db.query(APIKey).filter(APIKey.key == user.api_key).first()
    
    return UserResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        api_key=user.api_key,
        balance=api_key.balance if api_key else 0,
        free_quota=user.free_quota
    )