"""把过长的句子块拆成更适合字幕阅读的短块。"""
import json
import math
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
IN_JSON = HERE / "sample.sentences.json"
OUT_JSON = HERE / "sample.short.json"

MAX_CHARS = 50   # 一段字幕的目标上限（字号调小后一行约 50 字符）
HARD_MAX = 60    # 超过这个长度必须拆；50~60 允许整行保留
MIN_CHARS = 20   # 少于这个字符数的碎片并到相邻块
MIN_DUR = 1.0    # 少于这个时长（秒）的字幕并到相邻块
MAX_DUR = 8.0    # 一段字幕最多持续多少秒


def wrap_balanced(text: str, limit: int) -> list[str]:
    """按空格把长句均匀切成 n 块，避免最后只剩一个短尾巴。"""
    words = text.split()
    pieces: list[str] = []
    while words:
        rest = " ".join(words)
        n = max(1, math.ceil(len(rest) / limit))
        target = len(rest) / n
        cur = words.pop(0)
        while words and len(cur) + 1 + len(words[0]) <= target:
            cur += " " + words.pop(0)
        pieces.append(cur)
    return pieces


def split_text(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[,;:])\s+", text) if p.strip()]

    merged: list[str] = []
    for part in parts:
        if merged and len(merged[-1]) + 1 + len(part) <= MAX_CHARS:
            merged[-1] = merged[-1] + " " + part
        else:
            merged.append(part)

    chunks: list[str] = []
    for part in merged:
        if len(part) > HARD_MAX:
            chunks.extend(wrap_balanced(part, MAX_CHARS))
        else:
            chunks.append(part)
    return chunks


def merge_short(entries: list[dict]) -> list[dict]:
    """把过短或停留时间不足的片段并到相邻块，避免字幕一闪而过。"""
    merged: list[dict] = []
    for entry in entries:
        cur = dict(entry)
        if merged:
            prev = merged[-1]
            combo = len(prev["text"]) + 1 + len(cur["text"])
            too_short = (
                len(prev["text"]) < MIN_CHARS
                or prev["end"] - prev["start"] < MIN_DUR
                or len(cur["text"]) < MIN_CHARS
                or cur["end"] - cur["start"] < MIN_DUR
            )
            if too_short and combo <= HARD_MAX:
                prev["text"] += " " + cur["text"]
                prev["end"] = cur["end"]
                continue
        merged.append(cur)

    # 开头的碎片没有前一块，并到后一块
    while len(merged) >= 2:
        head = merged[0]
        combo = len(head["text"]) + 1 + len(merged[1]["text"])
        too_short = len(head["text"]) < MIN_CHARS or head["end"] - head["start"] < MIN_DUR
        if too_short and combo <= HARD_MAX:
            merged[1]["text"] = head["text"] + " " + merged[1]["text"]
            merged[1]["start"] = head["start"]
            merged.pop(0)
        else:
            break
    return merged


def split_sentences(blocks: list[dict]) -> list[dict]:
    """用几个规则分割字幕,超过这个长度必须拆；50~60 允许整行保留 and so on..."""
    result: list[dict] = []

    for block in blocks:
        text = block["text"]
        duration = block["end"] - block["start"]
        if len(text) <= MAX_CHARS and duration <= MAX_DUR:
            result.append(block)
            continue

        chunks = split_text(text)
        if len(chunks) <= 1:
            result.append(block)
            continue

        total = sum(len(c) for c in chunks) or 1
        cursor = block["start"]
        for chunk in chunks:
            piece = duration * len(chunk) / total
            result.append({
                "start": round(cursor, 3),
                "end": round(cursor + piece, 3),
                "text": chunk,
            })
            cursor += piece

    return merge_short(result)


def main() -> None:
    blocks = json.loads(IN_JSON.read_text(encoding="utf-8"))
    result = split_sentences(blocks)

    OUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"拆分前: {len(blocks)} 块")
    print(f"拆分后: {len(result)} 块")
    print("\n前 8 块:")
    for x in result[:8]:
        print(f"[{x['start']:.2f} -> {x['end']:.2f}] {x['text']}")


if __name__ == "__main__":
    main()
