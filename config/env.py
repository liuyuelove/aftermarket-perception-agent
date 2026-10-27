"""
环境变量与路径的单一来源。

原则：
  1. 代码里不出现内网 IP / 绝对路径，全部走环境变量。
  2. 默认值只保证「本机能跑起来」，真实环境用 .env 覆盖。
  3. 所有路径统一为绝对 Path，避免不同工作目录下行为不一致。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# .env 载入
# --------------------------------------------------------------------------- #
def load_env_file(path: Path | str | None = None) -> Path | None:
    """把 .env 载入进程环境（不覆盖已存在的变量）。

    为什么必须在这里做：`langgraph dev` 会自己读 langgraph.json 里的 "env"，
    但 `python scripts/run_demo.py`、pytest、以及任何直接 import 的入口都不会。
    不统一载入的话，同一个 `.env` 只在 Studio 里生效 —— 填了 key 却只有一半地方能用。

    返回实际载入的文件路径；文件不存在返回 None。
    """
    env_path = Path(path) if path else ROOT / ".env"
    if not env_path.exists():
        return None

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
        return env_path
    except ImportError:
        pass

    # 没装 python-dotenv 时的兜底：只认 KEY=VALUE 与 # 注释
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")
    return env_path


ENV_FILE = load_env_file()


# --------------------------------------------------------------------------- #
# 读取工具
# --------------------------------------------------------------------------- #
def _str(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _float(key: str, default: float) -> float:
    raw = _str(key)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int(key: str, default: int) -> int:
    raw = _str(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _path(key: str, default: str) -> Path:
    """相对路径一律相对项目根解析。"""
    raw = _str(key) or default
    p = Path(raw).expanduser()
    return p if p.is_absolute() else (ROOT / p)


def _resolution(key: str, default: tuple[int, int]) -> tuple[int, int]:
    raw = _str(key)
    if not raw:
        return default
    try:
        w, h = (int(x) for x in raw.lower().replace("x", ",").split(",")[:2])
        return (w, h)
    except (ValueError, TypeError):
        return default


# --------------------------------------------------------------------------- #
# LLM 后端（优先级：DeepSeek → OpenAI 兼容端点 → Ollama）
# --------------------------------------------------------------------------- #
DEEPSEEK_API_KEY = _str("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _str("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = _str("DEEPSEEK_MODEL", "deepseek-chat")

LLM_BASE_URL = _str("LLM_BASE_URL")
LLM_MODEL = _str("LLM_MODEL", "qwen3.5:9b")
LLM_API_KEY = _str("LLM_API_KEY", "EMPTY")

OLLAMA_BASE_URL = _str("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = _str("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TEMPERATURE = _float("OLLAMA_TEMPERATURE", 0.1)

LLM_TEMPERATURE = _float("LLM_TEMPERATURE", 0.1)
LLM_TIMEOUT = _int("LLM_TIMEOUT", 120)


# --------------------------------------------------------------------------- #
# 目录
# --------------------------------------------------------------------------- #
DATA_DIR = _path("DATA_DIR", "data")
TRAINING_LOGS_DIR = _path("TRAINING_LOGS_DIR", "data/training_logs")

AI_DATA_DIR = _path("AI_DATA_DIR", "ai_data")
FTP_DATA_DIR = _path("FTP_DATA_DIR", "ai_data/ftp_data")
EXTRACTED_DATA_DIR = _path("EXTRACTED_DATA_DIR", "ai_data/extracted_data")
IMG_DIR = _path("IMG_DIR", "ai_data/images")
IMG_WITH_LABEL_DIR = _path("IMG_WITH_LABEL_DIR", "ai_data/images_with_label")

AI_RESULTS_DIR = _path("AI_RESULTS_DIR", "ai_results")
MODEL_EVAL_RESULT_DIR = AI_RESULTS_DIR / "model_eval_result"
MODEL_CVT_RESULT_DIR = AI_RESULTS_DIR / "model_cvt_result"

# 训练数据 / 原始数据的根
AFTERMARKET_DATA_PATH = _path("AFTERMARKET_DATA_PATH", "data/aftermarket_data")

FCOS_DIR = _path("FCOS_DIR", "fcos")

#: 演示用 mock 工程目录。真实工程缺失时按同名子目录兜底，
#: 这样「放进真实 fcos 代码」与「克隆即可跑」两种情况都不需要改配置。
FCOS_MOCK_DIR = FCOS_DIR / "_mock"


# --------------------------------------------------------------------------- #
# 外部服务
# --------------------------------------------------------------------------- #
DATA_SERVER_URL = _str("DATA_SERVER_URL", "")
PREANNOTATION_SERVER_URL = _str("PREANNOTATION_SERVER_URL", "")

#: 未配 DATA_SERVER_URL 时，本地数据与任务名不匹配要不要直接拒绝。
#: 默认 0（只警告）——保留「手上就这一份数据，先跑起来」的用法；
#: 真跑任务时建议设 1，避免 A 任务悄悄用 B 任务的数据。
DATA_REUSE_STRICT = _str("DATA_REUSE_STRICT", "0").lower() in ("1", "true", "yes", "on")


# --------------------------------------------------------------------------- #
# 数据预处理
# --------------------------------------------------------------------------- #
FRAME_FPS = _int("FRAME_FPS", 5)
FRAME_RESOLUTION = _resolution("FRAME_RESOLUTION", (1280, 720))


# --------------------------------------------------------------------------- #
# 执行器：local 直接跑 python，docker 走容器（原实现只有 docker）
# --------------------------------------------------------------------------- #
RUNNER = _str("RUNNER", "local").lower()


def ensure_dirs() -> None:
    """启动时创建必需的运行目录（不创建则首次运行必然失败）。"""
    for p in (
        TRAINING_LOGS_DIR,
        FTP_DATA_DIR,
        EXTRACTED_DATA_DIR,
        IMG_DIR,
        IMG_WITH_LABEL_DIR,
        MODEL_EVAL_RESULT_DIR,
        MODEL_CVT_RESULT_DIR,
        AFTERMARKET_DATA_PATH,
    ):
        p.mkdir(parents=True, exist_ok=True)


def describe() -> str:
    """返回一行可读的当前配置摘要，用于启动日志。"""
    if DEEPSEEK_API_KEY:
        backend = f"deepseek({DEEPSEEK_MODEL})"
    elif LLM_BASE_URL:
        backend = f"openai-compat({LLM_MODEL} @ {LLM_BASE_URL})"
    else:
        backend = f"ollama({OLLAMA_MODEL} @ {OLLAMA_BASE_URL})"
    return f"llm={backend} runner={RUNNER} root={ROOT} env={ENV_FILE or '<未找到 .env>'}"
