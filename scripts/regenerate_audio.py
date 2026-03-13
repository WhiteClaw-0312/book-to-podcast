#!/usr/bin/env python
"""重新生成失败的音频文件"""
import os
import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, '/home/admin/.openclaw/workspace/book-to-podcast')

AUDIO_DIR = Path('/home/admin/.openclaw/workspace/book-to-podcast/data/output/audio')
SCRIPTS_DIR = Path('/home/admin/.openclaw/workspace/book-to-podcast/data/output/scripts')

async def synthesize_with_edge(dialogues: list, output_path: str) -> bool:
    """使用 edge-tts 合成"""
    temp_files = []
    
    for i, d in enumerate(dialogues):
        speaker = d["speaker"]
        content = d["content"]
        
        voice = "zh-CN-XiaoxiaoNeural" if speaker == "小北" else "zh-CN-YunxiNeural"
        temp_path = str(AUDIO_DIR / f"regen_temp_{i}.mp3")
        
        cmd = ["edge-tts", "--voice", voice, "--text", content, "--write-media", temp_path]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        
        if Path(temp_path).exists() and Path(temp_path).stat().st_size > 0:
            temp_files.append(temp_path)
    
    if not temp_files:
        return False
    
    # 合并
    await merge_audio(temp_files, output_path)
    
    # 清理
    for f in temp_files:
        Path(f).unlink(missing_ok=True)
    
    return Path(output_path).exists() and Path(output_path).stat().st_size > 0

async def merge_audio(audio_files: list, output_path: str):
    """合并音频"""
    list_file = AUDIO_DIR / "regen_list.txt"
    with open(list_file, "w") as f:
        for af in audio_files:
            f.write(f"file '{Path(af).absolute()}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", output_path
    ]
    
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()
    
    list_file.unlink(missing_ok=True)

async def main():
    # 找出失败的章节
    failed = []
    for i in range(1, 41):
        audio_path = AUDIO_DIR / f"chapter_{i:02d}.mp3"
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            failed.append(i)
    
    print(f"需要重新生成 {len(failed)} 个章节: {failed}", flush=True)
    
    for chapter_num in failed:
        print(f"\n🎙️ 重新生成第 {chapter_num} 章...", flush=True)
        
        # 读取文稿
        script_path = SCRIPTS_DIR / f"chapter_{chapter_num:02d}.json"
        if not script_path.exists():
            print(f"  ⚠️ 文稿不存在，跳过", flush=True)
            continue
        
        with open(script_path, "r", encoding="utf-8") as f:
            script = json.load(f)
        
        dialogues = script.get("dialogues", [])
        if not dialogues:
            print(f"  ⚠️ 无对话内容，跳过", flush=True)
            continue
        
        # 合成
        output_path = str(AUDIO_DIR / f"chapter_{chapter_num:02d}.mp3")
        success = await synthesize_with_edge(dialogues, output_path)
        
        if success:
            size = Path(output_path).stat().st_size
            print(f"  ✅ 完成: {size/1024:.1f} KB", flush=True)
        else:
            print(f"  ❌ 失败", flush=True)
        
        await asyncio.sleep(0.5)
    
    print("\n✅ 全部完成!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())