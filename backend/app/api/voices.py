"""音色配置 API"""
import os
import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import edge_tts

from ..database import get_db
from ..models import VoiceConfig

router = APIRouter(prefix="/api/voices", tags=["voices"])


class VoiceResponse(BaseModel):
    id: str
    speaker_name: str
    voice_id: str
    voice_name: str
    gender: str
    description: str | None
    preview_text: str | None

    class Config:
        from_attributes = True


# edge-tts 支持的中文音色
EDGE_TTS_VOICES = [
    # 女声
    {"speaker_name": "晓晓", "voice_id": "zh-CN-XiaoxiaoNeural", "voice_name": "晓晓 - 活泼女声", "gender": "female", "description": "声音活泼自然，适合日常对话", "preview_text": "大家好，欢迎来到今天的节目！"},
    {"speaker_name": "晓伊", "voice_id": "zh-CN-XiaoyiNeural", "voice_name": "晓伊 - 温柔女声", "gender": "female", "description": "温柔甜美，适合讲故事", "preview_text": "今天我要给大家讲一个有趣的故事。"},
    {"speaker_name": "晓涵", "voice_id": "zh-CN-XiaohanNeural", "voice_name": "晓涵 - 甜美女声", "gender": "female", "description": "声音甜美动听", "preview_text": "很高兴能和大家一起分享。"},
    {"speaker_name": "晓梦", "voice_id": "zh-CN-XiaomengNeural", "voice_name": "晓梦 - 少女音", "gender": "female", "description": "青春活力的少女音", "preview_text": "哇，这也太棒了吧！"},
    {"speaker_name": "晓萱", "voice_id": "zh-CN-XiaoxuanNeural", "voice_name": "晓萱 - 成熟女声", "gender": "female", "description": "知性优雅，适合正式场合", "preview_text": "让我们一起来探讨这个话题。"},
    {"speaker_name": "晓睿", "voice_id": "zh-CN-XiaoruiNeural", "voice_name": "晓睿 - 知性女声", "gender": "female", "description": "沉稳知性，适合科普内容", "preview_text": "这个问题值得我们深入思考。"},
    
    # 男声
    {"speaker_name": "云希", "voice_id": "zh-CN-YunxiNeural", "voice_name": "云希 - 阳光男声", "gender": "male", "description": "阳光开朗，适合轻松对话", "preview_text": "没错，我也这么认为！"},
    {"speaker_name": "云健", "voice_id": "zh-CN-YunjianNeural", "voice_name": "云健 - 磁性男声", "gender": "male", "description": "磁性低沉，适合讲故事", "preview_text": "让我来为大家详细介绍一下。"},
    {"speaker_name": "云夏", "voice_id": "zh-CN-YunxiaNeural", "voice_name": "云夏 - 少年音", "gender": "male", "description": "清澈少年音", "preview_text": "这个想法真的很有创意！"},
    {"speaker_name": "云扬", "voice_id": "zh-CN-YunyangNeural", "voice_name": "云扬 - 新闻播音", "gender": "male", "description": "专业播音腔，适合正式内容", "preview_text": "以下是今天的重点内容。"},
]


def init_voices(db: Session):
    """初始化音色配置"""
    existing = db.query(VoiceConfig).first()
    if existing:
        return
    
    for i, v in enumerate(EDGE_TTS_VOICES):
        voice = VoiceConfig(
            speaker_name=v["speaker_name"],
            voice_id=v["voice_id"],
            voice_name=v["voice_name"],
            gender=v["gender"],
            description=v.get("description"),
            preview_text=v.get("preview_text"),
            sort_order=i
        )
        db.add(voice)
    db.commit()


@router.get("", response_model=List[VoiceResponse])
async def list_voices(db: Session = Depends(get_db)):
    """获取可用音色列表"""
    init_voices(db)
    
    voices = db.query(VoiceConfig).filter(
        VoiceConfig.is_active == True
    ).order_by(VoiceConfig.gender, VoiceConfig.sort_order).all()
    
    return voices


@router.get("/female", response_model=List[VoiceResponse])
async def list_female_voices(db: Session = Depends(get_db)):
    """获取女声音色"""
    init_voices(db)
    
    voices = db.query(VoiceConfig).filter(
        VoiceConfig.is_active == True,
        VoiceConfig.gender == "female"
    ).order_by(VoiceConfig.sort_order).all()
    
    return voices


@router.get("/male", response_model=List[VoiceResponse])
async def list_male_voices(db: Session = Depends(get_db)):
    """获取男声音色"""
    init_voices(db)
    
    voices = db.query(VoiceConfig).filter(
        VoiceConfig.is_active == True,
        VoiceConfig.gender == "male"
    ).order_by(VoiceConfig.sort_order).all()
    
    return voices


@router.get("/{voice_id}")
async def get_voice(voice_id: str, db: Session = Depends(get_db)):
    """获取音色详情"""
    init_voices(db)
    
    voice = db.query(VoiceConfig).filter(VoiceConfig.id == voice_id).first()
    if not voice:
        return {"error": "音色不存在"}
    
    return voice


@router.get("/{voice_id}/preview")
async def preview_voice(voice_id: str, db: Session = Depends(get_db)):
    """生成音色预览音频"""
    init_voices(db)
    
    voice = db.query(VoiceConfig).filter(VoiceConfig.id == voice_id).first()
    if not voice:
        raise HTTPException(404, "音色不存在")
    
    # 预览文本
    preview_text = voice.preview_text or "大家好，这是音色预览。"
    
    # 预览音频缓存目录
    preview_dir = "/tmp/voice_previews"
    os.makedirs(preview_dir, exist_ok=True)
    
    # 使用 voice_id 作为文件名
    preview_file = os.path.join(preview_dir, f"{voice.voice_id}.mp3")
    
    # 如果已存在且不超过1小时，直接返回
    if os.path.exists(preview_file):
        import time
        file_age = time.time() - os.path.getmtime(preview_file)
        if file_age < 3600:  # 1小时内
            return FileResponse(
                preview_file,
                media_type="audio/mpeg",
                filename=f"{voice.speaker_name}_preview.mp3"
            )
    
    # 生成预览音频
    try:
        communicate = edge_tts.Communicate(preview_text, voice.voice_id)
        await communicate.save(preview_file)
        
        return FileResponse(
            preview_file,
            media_type="audio/mpeg",
            filename=f"{voice.speaker_name}_preview.mp3"
        )
    except Exception as e:
        raise HTTPException(500, f"生成预览失败: {str(e)}")


@router.get("/edge-id/{edge_voice_id}/preview")
async def preview_voice_by_edge_id(edge_voice_id: str):
    """通过 edge-tts 音色ID直接生成预览（用于前端实时预览）"""
    # 预览文本
    preview_text = "大家好，这是音色预览。"
    
    # 预览音频缓存目录
    preview_dir = "/tmp/voice_previews"
    os.makedirs(preview_dir, exist_ok=True)
    
    preview_file = os.path.join(preview_dir, f"{edge_voice_id}.mp3")
    
    # 如果已存在且有效（非空且不超过1小时），直接返回
    if os.path.exists(preview_file):
        import time
        file_size = os.path.getsize(preview_file)
        file_age = time.time() - os.path.getmtime(preview_file)
        # 文件有效：大小>1000字节 且 时间<1小时
        if file_size > 1000 and file_age < 3600:
            return FileResponse(
                preview_file,
                media_type="audio/mpeg",
                filename=f"preview.mp3"
            )
        # 文件无效，删除重新生成
        try:
            os.remove(preview_file)
        except:
            pass
    
    # 生成预览音频
    try:
        communicate = edge_tts.Communicate(preview_text, edge_voice_id)
        await communicate.save(preview_file)
        
        # 验证生成的文件
        if not os.path.exists(preview_file) or os.path.getsize(preview_file) < 1000:
            raise Exception("音频生成失败或文件过小")
        
        return FileResponse(
            preview_file,
            media_type="audio/mpeg",
            filename=f"preview.mp3"
        )
    except Exception as e:
        # 清理可能存在的空文件
        if os.path.exists(preview_file):
            try:
                os.remove(preview_file)
            except:
                pass
        raise HTTPException(500, f"生成预览失败: {str(e)}")