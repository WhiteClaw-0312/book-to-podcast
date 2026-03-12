#!/usr/bin/env python3
"""图书转播客 - 主程序入口"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import track

from src.parser import PDFParser
from src.knowledge import KnowledgeBaseBuilder
from src.script import ScriptGenerator
from src.tts import PodcastTTS, TTSConfig, check_tts_available

console = Console()


@click.group()
def cli():
    """图书转播客 - 将图书内容转换为双人对话式播客音频"""
    pass


@cli.command()
@click.argument("book_path", type=click.Path(exists=True))
@click.option("--output", "-o", default="data/output", help="输出目录")
@click.option("--chapters", "-c", default=None, help="指定章节范围，如 1-3")
def convert(book_path: str, output: str, chapters: str):
    """转换图书为播客"""
    console.print(f"[bold green]开始转换: {book_path}[/bold green]")
    
    # 步骤 1: 解析图书
    console.print("\n[bold]步骤 1/4: 解析图书...[/bold]")
    with PDFParser(book_path) as parser:
        metadata = parser.extract_metadata()
        console.print(f"  书名: {metadata.get('title', '未知')}")
        console.print(f"  页数: {metadata.get('page_count', 0)}")
        
        book_data = {
            "metadata": metadata,
            "text": parser.extract_text(),
            "chapters": parser.detect_chapters(),
        }
    
    # 步骤 2: 构建知识库
    console.print("\n[bold]步骤 2/4: 构建知识库...[/bold]")
    builder = KnowledgeBaseBuilder(book_data)
    knowledge = builder.build()
    console.print(f"  章节数: {len(knowledge.chapters)}")
    console.print(f"  人物数: {len(knowledge.characters)}")
    
    # 步骤 3: 生成播客文稿
    console.print("\n[bold]步骤 3/4: 生成播客文稿...[/bold]")
    generator = ScriptGenerator()
    scripts = []
    
    chapter_range = parse_chapter_range(chapters) if chapters else None
    
    for chapter in track(knowledge.chapters, description="生成文稿"):
        if chapter_range and chapter.number not in chapter_range:
            continue
        script = generator.generate_script(
            chapter.content,
            chapter.title,
            chapter.number
        )
        scripts.append(script)
    
    console.print(f"  生成文稿: {len(scripts)} 章")
    
    # 步骤 4: 合成语音
    console.print("\n[bold]步骤 4/4: 合成语音...[/bold]")
    tts = PodcastTTS()
    
    for script in track(scripts, description="合成语音"):
        output_file = Path(output) / f"chapter_{script.chapter_number:02d}.mp3"
        tts.synthesize_chapter(
            [{"speaker": d.speaker, "content": d.content} for d in script.dialogues],
            str(output_file)
        )
    
    console.print(f"\n[bold green]✅ 转换完成！[/bold green]")
    console.print(f"输出目录: {output}")


@cli.command()
@click.argument("book_path", type=click.Path(exists=True))
def parse(book_path: str):
    """解析图书并显示信息"""
    console.print(f"[bold]解析: {book_path}[/bold]")
    
    with PDFParser(book_path) as parser:
        metadata = parser.extract_metadata()
        chapters = parser.detect_chapters()
        
        console.print(f"\n[bold]元数据:[/bold]")
        for key, value in metadata.items():
            if value:
                console.print(f"  {key}: {value}")
        
        console.print(f"\n[bold]目录 ({len(chapters)} 章):[/bold]")
        for ch in chapters[:20]:
            console.print(f"  {'  ' * (ch['level']-1)}{ch['title']}")


@cli.command()
def check():
    """检查系统环境"""
    console.print("[bold]检查系统环境...[/bold]\n")
    
    # 检查 TTS
    tts_status = check_tts_available()
    console.print(f"edge-tts: {'✅' if tts_status['edge-tts'] else '❌'}")
    console.print(f"ffmpeg: {'✅' if tts_status['ffmpeg'] else '❌'}")
    
    # 检查 Python 包
    packages = ["fitz", "pydantic", "langchain"]
    console.print("\n[bold]Python 包:[/bold]")
    for pkg in packages:
        try:
            __import__(pkg)
            console.print(f"  {pkg}: ✅")
        except ImportError:
            console.print(f"  {pkg}: ❌")


def parse_chapter_range(range_str: str) -> list:
    """解析章节范围，如 '1-3' -> [1,2,3]"""
    if "-" in range_str:
        start, end = map(int, range_str.split("-"))
        return list(range(start, end + 1))
    return [int(range_str)]


if __name__ == "__main__":
    cli()