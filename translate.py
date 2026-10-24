"""把英文句子翻译成中文，生成中英双语 SRT。"""
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, APIError

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
IN_JSON = HERE / "sample.short.json"
OUT_SRT = HERE / "sample.short.bi.srt"
BATCH_SIZE = 10

load_dotenv(HERE / ".env")


def check_env() -> None:
    required = ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]
    missing = []
    for key in required:
        if not os.getenv(key):
            missing.append(key)
    if missing:
        raise SystemExit(
            f"缺少环境变量:{','.join(missing)}。"
                "模型信息没写全,格式参考env.example。请检查.env文件"
        )



def seconds_to_srt(seconds: float) -> str:
    """把秒数格式化为 SRT 时间戳，如 14.92 -> "00:00:14,920"。"""
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    hours = int(total_s // 3600)
    minutes = int((total_s // 60) % 60)
    secs = total_s % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def translate_batch(client: OpenAI, texts: list[str]) -> list[str]:
    """把一批英文字幕翻成中文；条数不匹配时最多重试 3 次，仍不匹配抛 RuntimeError。返回与 texts
  等长的译文列表。"""
    payload = json.dumps(
        [{"id": i + 1, "text": t} for i, t in enumerate(texts)],
        ensure_ascii=False,
    )
    last_error = ""
    for attempt in range(1, 4):
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL"),
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是专业的字幕翻译。把每条英文字幕翻成简体中文，"
                        "保持条数和顺序完全一致；不要合并、拆分或省略。"
                        "专有名词保留英文，译文要简洁自然，适合字幕阅读。"
                        '只输出 JSON，格式为 {"translations": ["译文1", "译文2", ...]}，'
                        "不要任何解释。"
                    ),
                },
                {"role": "user", "content": payload},
            ],
        )
        data = json.loads(response.choices[0].message.content)
        translations = data["translations"]
        if len(translations) == len(texts):
            return translations
        last_error = f"期望 {len(texts)} 条，收到 {len(translations)} 条"
        print(f"  条数不匹配（{last_error}），重试 {attempt}/3 ...")
    raise RuntimeError(last_error)


def write_bilingual_srt(blocks: list[dict], translations: list[str], path: Path) -> None:
    """输入分块好的等长英文字幕与中文字幕，以及保存路径。保存双语srt。"""
    lines = []
    for i, (block, zh) in enumerate(zip(blocks, translations), start=1):
        lines.append(str(i))
        lines.append(
            f"{seconds_to_srt(block['start'])} --> {seconds_to_srt(block['end'])}"
        )
        lines.append(block["text"])
        lines.append(zh)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def translate_blocks(blocks: list[dict], out_srt: Path) -> None:
    """输入清洗的英文字幕块和输出路径，执行LLM翻译写成双语srt到out_srt路径。翻译失败或字幕为空抛SystemExit"""
    if not blocks:
        raise SystemExit("没有可翻译的字幕")
    check_env()
    client = OpenAI(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    )

    translations: list[str] = []
    for start in range(0, len(blocks), BATCH_SIZE):
        batch = blocks[start:start + BATCH_SIZE]
        texts = [b["text"] for b in batch]
        print(f"翻译第 {start + 1}~{start + len(batch)} 句 ...")
        try:
            zh = translate_batch(client, texts)
        except (APIError, json.JSONDecodeError, KeyError, TypeError,RuntimeError) as e:
            raise SystemExit(
                f"翻译失败（第 {start + 1}~{start + len(batch)} 句）：{e}"
            )
        translations.extend(zh)
        time.sleep(0.5)

    write_bilingual_srt(blocks, translations, out_srt)


def main() -> None:
    blocks = json.loads(IN_JSON.read_text(encoding="utf-8"))
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(blocks)
    blocks = blocks[:limit]
    translate_blocks(blocks, OUT_SRT)
    print(f"完成：{len(blocks)} 句 -> {OUT_SRT}")


if __name__ == "__main__":
    main()
