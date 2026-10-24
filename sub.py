"""一条命令完成：YouTube 链接 -> 中英双语 SRT。

用法: python sub.py <YouTube 链接> [--video] [--whisper] [--burn]
"""
import sys
from pathlib import Path

import burn
import prepare
import split_blocks
import translate
import transcribe
import youtube


sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
WORK = HERE / "work"


def run_whisper(url: str, workdir: Path) -> Path:
    audio = youtube.download_audio(url, workdir)
    return transcribe.transcribe_audio(audio, workdir / "source.en.srt")


def main() -> None:
    raw = sys.argv[1:]
    args = [a for a in raw if a not in ("--video", "--whisper", "--burn")]
    want_whisper = "--whisper" in raw
    want_burn = "--burn" in raw
    want_video = "--video" in raw or want_burn
    if not args:
        raise SystemExit("用法: python sub.py <YouTube 链接> [--video] [--whisper] [--burn]")

    url = args[0]
    translate.check_env()
    vid = youtube.video_id(url)
    if vid == "video":
        print("提示：没能从链接识别出视频 ID，产物会保存到 work/video/ 下", file=sys.stderr)
    workdir = WORK / vid
    workdir.mkdir(parents=True, exist_ok=True)

    total = 4 + want_video + want_burn
    step = 1

    print(f"[{step}/{total}] 获取英文字幕 ...")
    step += 1
    if want_whisper:
        print("      使用 Whisper 转写（--whisper）")
        srt = run_whisper(url, workdir)
    else:
        srt = youtube.download_subtitles(url, workdir)
        if srt is not None and not prepare.has_cues(srt):
            srt = None
        if srt is None:
            print("      未找到英文自动字幕，改用 Whisper 转写 ...")
            srt = run_whisper(url, workdir)
        else:
            print("      使用 YouTube 自动字幕（加 --whisper 可改用模型转写）")

    if want_video:
        print(f"[{step}/{total}] 下载视频 ...")
        step += 1
        video = youtube.download_video(url, workdir)
        print(f"      {video}")

    print(f"[{step}/{total}] 清洗 + 合并 ...")
    step += 1
    sentences = prepare.build_sentences(srt)
    if not sentences:
        raise SystemExit("清洗后没有可用字幕（视频可能只有音乐或音效）")
    print(f"      合并后 {len(sentences)} 句")

    print(f"[{step}/{total}] 拆分长句 ...")

    step += 1
    short = split_blocks.split_sentences(sentences)
    if not short:
        raise SystemExit("拆分后没有可用字幕")
    print(f"      拆分后 {len(short)} 条")

    out_srt = workdir / f"{vid}.srt"
    print(f"[{step}/{total}] LLM 翻译 {len(short)} 条 ...")
    translate.translate_blocks(short, out_srt)
    print(f"完成: {out_srt}")

    if want_burn:
        step += 1
        print(f"[{step}/{total}] 烧录字幕 ...")
        burned = burn.burn_subtitles(video, out_srt)
        print(f"完成: {burned}")


if __name__ == "__main__":
    main()
