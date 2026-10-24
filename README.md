# videotrans

输入一个 YouTube 链接，输出中英双语字幕；可选下载视频，或把字幕直接烧进画面。

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

## 功能

- **中英双语字幕**：YouTube 自动英文字幕 → 清洗合并 → 拆句 → LLM 翻译，输出双语 `.srt`
- **无字幕兜底**：视频没有英文字幕时，自动改用 faster-whisper 本地转写
- **视频下载**：`--video` 下载 H.264 MP4，字幕与视频同名，播放器自动加载
- **字幕烧录**：`--burn` 用 ffmpeg 把双语字幕压进画面，输出 `<视频ID>.hardsub.mp4`
- **中文错误提示**：环境变量缺失、无字幕、限流、LLM 报错、ffmpeg 失败都会明确说明原因

## 环境要求

| 依赖 | 说明 |
|---|---|
| Python 3.11 | 已在 3.11.9 上验证 |
| Git | 用于克隆仓库 |
| deno | 由安装脚本下载到 `tools/deno/`；解析 YouTube 的 n challenge 必需 |
| LLM API | 任意 OpenAI 兼容接口（`.env.example` 以 DeepSeek 为例） |
| ffmpeg | 由 `imageio-ffmpeg` 自带，无需单独安装 |
| 网络 | 需能访问 YouTube；受限网络请配置代理(科学上网) |

## 一键安装

前提：已安装 Python 3.11+ 和 Git。

```powershell
git clone https://github.com/runbookball/en_videotrans.git
cd en_videotrans
python setup_env.py
```

脚本全部在项目文件夹内完成：

| 步骤 | 位置 |
|---|---|
| 创建虚拟环境 | `venv/` |
| 安装 Python 依赖 | `venv/` |
| 下载 deno | `tools/deno/` |
| 生成配置文件 | `.env` |

安装完成后，编辑 `.env`，填写：

```ini
LLM_API_KEY=你的密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

然后运行：

```bash
venv\Scripts\python sub.py "<YouTube 链接>"
```

> `venv/`、`tools/`、`models/`、`work/` 都在项目目录内且被 `.gitignore` 排除；删除它们即可清理环境，不影响仓库。

<details>
<summary>手动安装（脚本失败时）</summary>

```bash
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
# deno：从 https://deno.com/ 安装，或下载 zip 解压到 tools/deno/
# .env：复制 .env.example 为 .env
```

</details>

## 使用

```bash
# 只生成双语字幕
python sub.py "<YouTube 链接>"

# 视频 + 双语字幕
python sub.py "<YouTube 链接>" --video

# 视频 + 双语字幕 + 烧录（自动包含 --video）
python sub.py "<YouTube 链接>" --burn

# 强制用 Whisper 转写（即使有自动字幕）
python sub.py "<YouTube 链接>" --whisper
```

> 链接建议加引号，避免 shell 把 `?`、`&` 当作特殊字符。

## 输出

产物保存在 `work/<视频ID>/`：

| 文件 | 说明 |
|---|---|
| `source.en.srt` | 英文原始字幕（YouTube 自动字幕或 Whisper 转写） |
| `<视频ID>.srt` | 中英双语字幕 |
| `<视频ID>.mp4` | 下载的视频（`--video` / `--burn`） |
| `<视频ID>.hardsub.mp4` | 烧录双语字幕后的视频（`--burn`） |

## 说明与限制

- 仅支持 YouTube，且目前只处理英语音频。
- Whisper 使用 CPU 推理，无需 GPU；首次运行会下载 `small.en` 模型（约 480MB），缓存在 `models/`。
- 模型下载默认走 `hf-mirror.com`；如需其他镜像，可设置环境变量 `HF_ENDPOINT`。
- 提示「YouTube 要求登录验证」时，可稍后重试或更换网络。
- 烧录样式使用微软雅黑，在非 Windows 系统上需要修改 `burn.py` 里的字体。
- 字幕已做清洗、断行和长度优化，但部分长句的翻译语速（CPS）仍可能偏快。

