"""无字幕时用 faster-whisper 把音频转写成英文 SRT。"""
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")

MODEL_DIR = HERE / "models"
DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "small.en")
PROGRESS_STEP = 30.0


def choose_hf_endpoint(model_name: str) -> None:
    """优先直连 HuggingFace，不通时回退镜像；用户设置 HF_ENDPOINT 则尊重。"""
    if os.getenv("HF_ENDPOINT"):
        return
    if (MODEL_DIR / f"models--Systran--faster-whisper-{model_name}").exists():
        return
    try:
        with urllib.request.urlopen("https://huggingface.co", timeout=3):
            pass
    except Exception:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


choose_hf_endpoint(DEFAULT_MODEL)
# 镜像的 Xet 存储会返回 401，禁用后改走普通 HTTP 下载
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from faster_whisper import WhisperModel  # noqa: E402

from translate import seconds_to_srt  # noqa: E402


def transcribe_audio(audio: Path, out_srt: Path, model_name: str = DEFAULT_MODEL) -> Path:
    """加载 Whisper 模型转写音频，写入 out_srt 并返回该文件路径；模型加载或转写失败时抛 SystemExit。"""
    print(f"  加载 Whisper 模型 {model_name}（首次运行会下载模型）...")
    try:
        model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
            download_root=str(MODEL_DIR),
        )
    except Exception as e:
        raise SystemExit(
            f"Whisper 模型加载失败：{e}\n"
            "首次运行需要下载模型；请检查网络，或设置 HF_ENDPOINT 指向可用镜像。"
        )

    print("  开始转写 ...")
    try:
        segments, info = model.transcribe(
            str(audio),
            language="en",
            vad_filter=True,
            beam_size=5,
            condition_on_previous_text=False,
        )
        return write_srt(segments, info, out_srt)
    except Exception as e:
        raise SystemExit(f"Whisper 转写失败：{e}")


def write_srt(segments, info, out_srt: Path) -> Path:
    """把转写结果写进 out_srt 这个文件，然后把这个路径还回去。没识别出任何语音时抛 SystemExit。"""
    count = 0
    next_report = PROGRESS_STEP
    with out_srt.open("w", encoding="utf-8") as f:
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            count += 1
            f.write(
                f"{count}\n"
                f"{seconds_to_srt(seg.start)} --> {seconds_to_srt(seg.end)}\n"
                f"{text}\n\n"
            )
            if seg.end >= next_report:
                if info.duration:
                    print(f"  已转写 {seg.end / 60:.1f} / {info.duration / 60:.1f} 分钟")
                else:
                    print(f"  已转写 {seg.end / 60:.1f} 分钟")
                while next_report <= seg.end:
                    next_report += PROGRESS_STEP

    if count == 0:
        raise SystemExit("Whisper 没有识别出任何语音（可能是纯音乐或静音视频）")
    return out_srt


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("用法: python transcribe.py <音频文件> <输出.srt>")
    out = Path(sys.argv[2])
    transcribe_audio(Path(sys.argv[1]), out)
    print(f"完成: {out}")


if __name__ == "__main__":
    main()
