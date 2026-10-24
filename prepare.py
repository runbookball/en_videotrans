"""把 YouTube 自动字幕的碎句清洗、合并成句子级台词本。

输入: sample.en.srt
输出: sample.sentences.json
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
SRT_IN = HERE / "sample.en.srt"
JSON_OUT = HERE / "sample.sentences.json"


def to_seconds(stamp: str) -> float:
    hms, ms = stamp.strip().split(",")
    h, m, s = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path: Path) -> list[dict]:
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip())
    cues = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        start_s, end_s = lines[1].split(" --> ")
        cues.append({
            "start": to_seconds(start_s),
            "end": to_seconds(end_s),
            "text": " ".join(lines[2:]),
        })
    return cues


def has_cues(srt_path: Path) -> bool:
    try:
        return bool(parse_srt(srt_path))
    except Exception:
        return False


def clean_text(text: str) -> str:
    text = text.replace(">>","")
    text = text.replace("[music]","")
    text = text.strip()
    return text


def merge_sentences(cues: list[dict]) -> list[dict]:
    chars: list[str] = []
    times: list[float] = []
    for i, cue in enumerate(cues):
        text = clean_text(cue["text"])
        if not text:
            continue
        start = cue["start"]
        # 滚动字幕的时间会重叠，这里用下一句的开始时间截断本条
        if i + 1 < len(cues) and cues[i + 1]["start"] > start:
            end = cues[i + 1]["start"]
        else:
            end = cue["end"]
        n = max(len(text), 1)
        for j, ch in enumerate(text):
            chars.append(ch)
            times.append(start + (end - start) * j / n)
        chars.append(" ")
        times.append(end)

    full = "".join(chars)
    blocks = []
    cursor = 0
    for m in re.finditer(r'[.!?]+["\'”’)]*\s+', full):
        block = make_block(full, times, cursor, m.end())
        if block:
            blocks.append(block)
        cursor = m.end()
    if cursor < len(full):
        block = make_block(full, times, cursor, len(full))
        if block:
            blocks.append(block)
    return blocks


def make_block(full: str, times: list[float], start: int, end: int) -> dict | None:
    raw = full[start:end]
    text = raw.strip()
    if not text:
        return None
    first = start + (len(raw) - len(raw.lstrip()))
    last = end - (len(raw) - len(raw.rstrip())) - 1
    t0 = times[first]
    t1 = times[max(last, first)]
    if t1 <= t0:
        t1 = t0 + 0.5
    return {"start": round(t0, 3), "end": round(t1, 3), "text": text}


def build_sentences(srt_path: Path) -> list[dict]:
    """读取 SRT，按标点合并成句子；返回 [{"start","end","text"}, ...]。"""
    cues = parse_srt(srt_path)
    return merge_sentences(cues)


def main() -> None:
    cues = parse_srt(SRT_IN)
    blocks = merge_sentences(cues)
    JSON_OUT.write_text(
        json.dumps(blocks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"原始碎片: {len(cues)} 条")
    print(f"合并后句子: {len(blocks)} 条")
    for b in blocks[:5]:
        print(f"[{b['start']:.2f} -> {b['end']:.2f}] {b['text']}")


if __name__ == "__main__":
    main()
