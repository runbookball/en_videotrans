"""用 ffmpeg 把 SRT 烧录进视频，输出带硬字幕的新文件。"""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

sys.stdout.reconfigure(encoding="utf-8")

STYLE = "FontName=Microsoft YaHei,FontSize=22,Outline=1,Shadow=0,MarginV=20"


def burn_subtitles(video: Path, srt: Path) -> Path:
    """把 srt 烧进 video，输出同目录下的 <名字>.hardsub.mp4；失败抛 SystemExit。"""
    out = video.with_name(f"{video.stem}.hardsub{video.suffix}")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    print("  正在烧录（视频要重编码，可能需要几分钟）...")

    cmd = [
        ffmpeg,
        "-y",
        "-i", video.name,
        "-loglevel", "error",
        "-vf", f"subtitles={srt.name}:force_style='{STYLE}'",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        out.name,
    ]

    try:
        subprocess.run(
            cmd,
            cwd=video.parent,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"烧录失败：{e.stderr.strip()[-500:]}")

    if not out.exists():
        raise SystemExit(f"烧录失败，没有生成文件：{out}")
    return out
