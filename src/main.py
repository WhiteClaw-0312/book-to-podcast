#!/usr/bin/env python3
"""图书转播客 - 主程序入口"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import track
from rich.table import Table
import json

console = Console()


@click.group()
def cli():
    """图书转播客 - 将图书内容转换为双人对话式播客音频"""
    pass


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True))
@click.option("--output", "-o", default="data/output", help="输出目录")
@click.option("--api-key", "-k", envvar="BAILIAN_API_KEY", help="百炼 API Key")
def generate(skill_path: str, output: str, api_key: str):
    """从 Skill 生成播客文稿"""
    if not api_key:
        console.print("[red]错误: 请提供百炼 API Key (通过 -k 参数或 BAILIAN_API_KEY 环境变量)[/red]")
        return
    
    console.print(f"[bold green]开始生成播客文稿: {skill_path}[/bold green]")
    
    from src.script.skill_script import generate_podcast_from_skill
    
    scripts = generate_podcast_from_skill(skill_path, api_key, output)
    
    console.print(f"\n[bold green]✅ 生成完成！[/bold green]")
    console.print(f"共生成 {len(scripts)} 章文稿")
    console.print(f"输出目录: {output}")


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True))
def info(skill_path: str):
    """显示 Skill 信息"""
    from src.script.skill_script import SkillKnowledge
    
    skill = SkillKnowledge(skill_path)
    skill.load()
    
    # 显示信息表格
    table = Table(title="Skill 信息")
    table.add_column("项目", style="cyan")
    table.add_column("内容", style="green")
    
    table.add_row("路径", str(skill_path))
    table.add_row("SKILL.md", "✅" if skill.skill_md else "❌")
    table.add_row("引用文件数", str(len(skill.references)))
    
    chapters = skill.get_chapters()
    table.add_row("章节数", str(len(chapters)))
    
    console.print(table)
    
    if chapters:
        console.print("\n[bold]章节列表:[/bold]")
        for i, ch in enumerate(chapters[:10]):
            console.print(f"  {i+1}. {ch['title']}")


@cli.command()
@click.argument("script_path", type=click.Path(exists=True))
@click.option("--output", "-o", default="data/output/audio", help="音频输出目录")
def synthesize(script_path: str, output: str):
    """合成播客音频"""
    console.print(f"[bold]合成音频: {script_path}[/bold]")
    
    from src.tts import PodcastTTS
    
    # 加载文稿
    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)
    
    tts = PodcastTTS()
    output_file = Path(output) / f"{Path(script_path).stem}.mp3"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    dialogues = [
        {"speaker": d["speaker"], "content": d["content"]}
        for d in script_data["dialogues"]
    ]
    
    success = tts.synthesize_chapter(dialogues, str(output_file))
    
    if success:
        console.print(f"[green]✅ 音频已保存: {output_file}[/green]")
    else:
        console.print("[red]❌ 音频合成失败[/red]")


@cli.command()
def check():
    """检查系统环境"""
    console.print("[bold]检查系统环境...[/bold]\n")
    
    # 检查 TTS
    from src.tts import check_tts_available
    tts_status = check_tts_available()
    
    table = Table(title="环境检查")
    table.add_column("组件", style="cyan")
    table.add_column("状态", style="green")
    
    table.add_row("edge-tts", "✅" if tts_status["edge-tts"] else "❌")
    table.add_row("ffmpeg", "✅" if tts_status["ffmpeg"] else "❌")
    
    console.print(table)
    
    # 检查 API Key
    import os
    api_key = os.environ.get("BAILIAN_API_KEY")
    console.print(f"\n百炼 API Key: {'✅ 已配置' if api_key else '❌ 未配置'}")


if __name__ == "__main__":
    cli()