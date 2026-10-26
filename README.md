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

> 下面的命令都要在**终端**里输入并回车运行，不是双击 `.py` 文件。
> Windows 推荐用 PowerShell：在文件夹空白处右键 →「在终端中打开」；或先打开 PowerShell，再用 `cd` 进入项目目录。

### 方式一：git clone（推荐）

前提：已安装 Python 3.11+ 和 Git。克隆会在**当前目录**下创建 `en_videotrans` 文件夹。

```powershell
git clone https://github.com/runbookball/en_videotrans.git
cd en_videotrans
python setup_env.py
```

想指定放在哪里，先 `cd` 到目标位置再克隆：

```powershell
cd D:\deeptalk
git clone https://github.com/runbookball/en_videotrans.git
```

### 方式二：下载 Release 源码包（不需要 Git）

1. 打开 [Releases](https://github.com/runbookball/en_videotrans/releases) 页面
2. 在最新版本下方下载 **Source code (zip)**
3. 右键压缩包 → **全部解压缩**，解到普通文件夹
4. 打开解压后的文件夹，在地址栏输入 `powershell` 回车，或右键选择「在终端中打开」
5. 运行 `python setup_env.py`

> ⚠️ 不要在压缩包的预览窗口里直接双击 `setup_env.py`。Windows 只会把脚本临时解出来，`requirements.txt` 不在旁边，安装会失败。先把整个 zip 完整解压。

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

这几个参数可以按需组合。比如：

```bash
# 下载视频 + 用 Whisper 转写 + 烧录字幕
python sub.py "<YouTube 链接>" --video --whisper --burn
```

注意 `--burn` 本身已包含 `--video`，只写 `--burn` 就够；两个一起写也不会出错。

**Whisper 是什么？** 它是 OpenAI 开源的语音识别模型，作用是把视频里的声音转成文字。本项目通过 faster-whisper 在本地 CPU 上运行，不需要 GPU。

默认情况下，程序会优先使用 YouTube 自带的英文字幕，只有视频没有英文字幕时才自动调用 Whisper（首次使用会自动下载模型，见下方「说明与限制」）。加上 `--whisper` 则跳过自动字幕，强制用 Whisper 从音频重新转写，适合自动字幕出错较多、断句混乱的视频。

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
- 模型下载默认直连 HuggingFace，连不通时自动回退到 `hf-mirror.com`；可用环境变量 `HF_ENDPOINT` 强制指定。
- 提示「YouTube 要求登录验证」时，可稍后重试或更换网络。
- 烧录样式使用微软雅黑，在非 Windows 系统上需要修改 `burn.py` 里的字体。
- 字幕已做清洗、断行和长度优化，但部分长句的翻译语速（CPS）仍可能偏快。

## 许可证

[MIT](LICENSE)

---

新人创作，欢迎大家修改和使用，欢迎指点，也请大家随意使用与修改，感谢支持！

有问题可发邮箱 runbookball@gmail.com 交流。
