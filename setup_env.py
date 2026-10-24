"""一键准备运行环境：项目内虚拟环境、依赖、deno、.env。

用法: python setup_env.py
"""
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
VENV = HERE / "venv"
TOOLS = HERE / "tools"
DENO_DIR = TOOLS / "deno"
DENO_EXE = DENO_DIR / ("deno.exe" if sys.platform == "win32" else "deno")
MIN_PYTHON = (3, 11)


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"命令失败（退出码 {e.returncode}）：{' '.join(cmd)}")


def check_python() -> None:
    if sys.version_info < MIN_PYTHON:
        raise SystemExit(
            f"需要 Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} 或更高版本，"
            f"当前是 {platform.python_version()}。"
        )
    print(f"[1/5] Python {platform.python_version()} ✓")


def create_venv() -> Path:
    py = venv_python()
    if py.exists():
        print(f"[2/5] 虚拟环境已存在: {VENV}")
        return py
    print(f"[2/5] 创建虚拟环境: {VENV}")
    run([sys.executable, "-m", "venv", str(VENV)])
    return py


def install_requirements(py: Path) -> None:
    print("[3/5] 安装依赖（首次可能需要几分钟）")
    run([str(py), "-m", "pip", "install", "-r", str(HERE / "requirements.txt")])


def deno_url() -> str | None:
    system = platform.system()
    machine = platform.machine().lower()
    base = "https://github.com/denoland/deno/releases/latest/download/"
    if system == "Windows" and machine in ("amd64", "x86_64"):
        return base + "deno-x86_64-pc-windows-msvc.zip"
    if system == "Linux" and machine in ("x86_64", "amd64"):
        return base + "deno-x86_64-unknown-linux-gnu.zip"
    if system == "Darwin":
        if machine in ("arm64", "aarch64"):
            return base + "deno-aarch64-apple-darwin.zip"
        return base + "deno-x86_64-apple-darwin.zip"
    return None


def download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url) as resp, dest.open("wb") as f:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                print(
                    f"\r      下载中 {done / 1e6:.1f} / {total / 1e6:.1f} MB",
                    end="",
                    flush=True,
                )
    print()


def install_deno() -> None:
    if DENO_EXE.exists():
        print(f"[4/5] deno 已存在: {DENO_EXE}")
        return
    url = deno_url()
    if url is None:
        print("[4/5] 当前平台没有预置 deno 下载，请手动安装: https://deno.com/")
        return
    DENO_DIR.mkdir(parents=True, exist_ok=True)
    archive = TOOLS / "deno.zip"
    print(f"[4/5] 下载 deno: {url}")
    try:
        download(url, archive)
    except Exception as e:
        raise SystemExit(
            f"deno 下载失败：{e}\n"
            f"可手动下载 {url}\n解压到 {DENO_DIR}；"
            "网络受限时可先设置 HTTPS_PROXY 再重试。"
        )
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(DENO_DIR)
    archive.unlink()
    if not DENO_EXE.exists():
        raise SystemExit(f"deno 解压后未找到 {DENO_EXE}")
    if sys.platform != "win32":
        DENO_EXE.chmod(0o755)
    print(f"      deno 已就位: {DENO_EXE}")


def ensure_env_file() -> None:
    env = HERE / ".env"
    if env.exists():
        print("[5/5] .env 已存在")
        return
    shutil.copyfile(HERE / ".env.example", env)
    print("[5/5] 已生成 .env —— 请填写 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL")


def main() -> None:
    print("videotrans 环境安装")
    check_python()
    py = create_venv()
    install_requirements(py)
    install_deno()
    ensure_env_file()
    rel = py.relative_to(HERE)
    print()
    print("安装完成。下一步：")
    print("  1. 打开 .env，填写 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL")
    print(f'  2. 运行: {rel} sub.py "<YouTube 链接>"')


if __name__ == "__main__":
    main()
