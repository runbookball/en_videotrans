"""YouTube 交互：链接解析、yt-dlp 配置、字幕/视频/音频下载。"""
import re
import shutil
import sys
from pathlib import Path

import imageio_ffmpeg
import yt_dlp

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent


def find_deno() -> str | None:
    """优先用项目内 tools/deno，其次 PATH，最后 winget 安装目录。"""
    local = HERE / "tools" / "deno" / ("deno.exe" if sys.platform == "win32" else "deno")
    if local.exists():
        return str(local)
    found = shutil.which("deno")
    if found:
        return found
    # winget 装完后，已经打开的终端 PATH 不会立即刷新
    winget = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    matches = list(winget.glob("DenoLand.Deno_*/deno.exe"))
    return str(matches[0]) if matches else None


def common_opts() -> dict:
    opts: dict = {"ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe()}
    deno = find_deno()
    if deno:
        opts["js_runtimes"] = {"deno": {"path": deno}}
        opts["remote_components"] = {"ejs:github"}
    return opts


def video_id(url: str) -> str:
    """提取youtube id"""
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", url)
    if m:
        return m.group(1)
    return "video"


def friendly_download_error(err: Exception) -> str:
    msg = str(err)
    low = msg.lower()
    if "sign in to confirm " in low or "bot" in low:
        return "YouTube 要求登录验证，可稍后重试或更换网络"
    if "429" in low or "too many requests" in low:
        return "限流，等几分钟再试"
    if "urlopen error" in low or "connection" in low or "timed out" in low:
        return "网络失败，检查代理"
    return str(err)


def download_subtitles(url: str, workdir: Path) -> Path | None:
    """下载英文自动字幕到 workdir/source.en.srt；没有字幕时返回 None。"""
    opts = common_opts()
    opts.update({
        "skip_download": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "srt",
        "outtmpl": str(workdir / "source.%(ext)s"),
        # 只取字幕、不要视频格式；web_embedded 能绕过 YouTube 的机器人验证
        "ignore_no_formats_error": True,
        "extractor_args": {"youtube": {"player_client": ["web_embedded"]}},
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise SystemExit(f"字幕下载失败：{friendly_download_error(e)}")

    srt = workdir / "source.en.srt"
    return srt if srt.exists() else None


def download_video(url: str, workdir: Path) -> Path:
    """下载视频（优先 H.264 MP4）到 workdir，返回本地文件路径。"""
    opts = common_opts()
    opts.update({
        # 优先 H.264 MP4，PotPlayer 等播放器兼容性最好
        "format": (
            "bv*[vcodec^=avc1][ext=mp4]+ba[ext=m4a]/"
            "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b"
        ),
        "merge_output_format": "mp4",
        "outtmpl": str(workdir / "%(id)s.%(ext)s"),
        "extractor_args": {"youtube": {"player_client": ["web_embedded"]}},
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise SystemExit(f"视频下载失败：{friendly_download_error(e)}")

    video = workdir / f"{info['id']}.mp4"
    if not video.exists():
        raise SystemExit(f"视频下载失败：{url}")
    return video


def download_audio(url: str, workdir: Path) -> Path:
    """只下载音频（优先 m4a）供 Whisper 转写，返回本地文件路径。"""
    opts = common_opts()
    opts.update({
        "format": "bestaudio[ext=m4a]/bestaudio",
        "outtmpl": str(workdir / "audio.%(ext)s"),
        "extractor_args": {"youtube": {"player_client": ["web_embedded"]}},
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio = Path(ydl.prepare_filename(info))
    except yt_dlp.utils.DownloadError as e:
        raise SystemExit(f"音频下载失败：{friendly_download_error(e)}")

    if not audio.exists():
        raise SystemExit(f"音频下载失败：{url}")
    return audio
