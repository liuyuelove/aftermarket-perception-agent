#!/bin/bash
# 一键准备开发环境：建 venv → 装依赖 → 自检。
#
# 为什么需要脚本而不是两行命令：本机 pip 装 `langgraph-cli[inmem]` 时，
# 它依赖的 `forbiddenfruit 0.1.4`（sdist）解包会报
# `EEXIST: mkdir .../forbiddenfruit_<hash>`，导致整单回滚。
# 这个脚本会先把 forbiddenfruit 手动塞进 site-packages，再装其余依赖。
#
# 用法:
#   bash scripts/bootstrap.sh          # 幂等，已装好的会跳过
#   PYTHON_BIN=/path/to/python3 bash scripts/bootstrap.sh
#
# @Time: 2026/10/19
# @Author: 刘越的不努力日记本

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"
FORBIDDENFRUIT_URL="https://files.pythonhosted.org/packages/e6/79/d4f20e91327c98096d605646bdc6a5ffedae820f38d378d3515c42ec5e60/forbiddenfruit-0.1.4.tar.gz"

# ---------------------------------------------------------------- 解释器
if [ -n "${PYTHON_BIN:-}" ]; then
  PY="$PYTHON_BIN"
elif [ -x "/Users/liuyue/.workbuddy-ai/binaries/python/versions/3.13.12/bin/python3" ]; then
  PY="/Users/liuyue/.workbuddy-ai/binaries/python/versions/3.13.12/bin/python3"
else
  PY="$(command -v python3 || true)"
fi

if [ -z "$PY" ] || [ ! -x "$PY" ]; then
  echo "[bootstrap] 找不到 python3，请用 PYTHON_BIN=... 指定" >&2
  exit 1
fi
echo "[bootstrap] 解释器: $PY ($("$PY" -V 2>&1))"

# ---------------------------------------------------------------- venv
if [ -d "$VENV" ]; then
  echo "[bootstrap] .venv 已存在，跳过创建"
else
  echo "[bootstrap] 创建 .venv ..."
  "$PY" -m venv "$VENV"
fi
VPY="$VENV/bin/python"
"$VPY" -m pip install -q -U pip setuptools wheel

# ---------------------------------------------------------------- forbiddenfruit
# 只在缺失时装：pip 装它的 sdist 会失败，所以手动解包 + 手写 dist-info
if "$VPY" -c "import importlib.metadata as m; m.version('forbiddenfruit')" >/dev/null 2>&1; then
  echo "[bootstrap] forbiddenfruit 已就绪"
else
  echo "[bootstrap] 手动安装 forbiddenfruit（绕过 pip 的 sdist 解包问题）..."
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  curl -sS --max-time 180 -o "$tmp/ff.tar.gz" "$FORBIDDENFRUIT_URL"
  tar xzf "$tmp/ff.tar.gz" -C "$tmp"

  sp="$("$VPY" -c 'import sysconfig;print(sysconfig.get_paths()["purelib"])')"
  cp -R "$tmp/forbiddenfruit-0.1.4/forbiddenfruit" "$sp/"
  mkdir -p "$sp/forbiddenfruit-0.1.4.dist-info"
  printf 'Metadata-Version: 2.1\nName: forbiddenfruit\nVersion: 0.1.4\nSummary: manually installed (pip sdist unpack fails on this machine)\n' \
    > "$sp/forbiddenfruit-0.1.4.dist-info/METADATA"
  printf 'pip\n' > "$sp/forbiddenfruit-0.1.4.dist-info/INSTALLER"
  printf 'Wheel-Version: 1.0\nGenerator: manual\nRoot-Is-Purelib: true\nTag: py3-none-any\n' \
    > "$sp/forbiddenfruit-0.1.4.dist-info/WHEEL"
  : > "$sp/forbiddenfruit-0.1.4.dist-info/RECORD"
  "$VPY" -c "import forbiddenfruit; print('[bootstrap] forbiddenfruit ok')"
fi

# ---------------------------------------------------------------- 依赖
echo "[bootstrap] 安装项目依赖（网络慢的话要几分钟）..."
"$VPY" -m pip install -q -r requirements.txt -r requirements-dev.txt

# ---------------------------------------------------------------- 自检
echo "[bootstrap] 自检 ..."
"$VPY" - <<'PY'
import logging
logging.disable(logging.WARNING)
import main
from config import env

print("  配置:", env.describe())
print("  节点:", sorted(n for n in main.app.get_graph().nodes if not n.startswith("__")))
PY

cat <<'EOF'

[bootstrap] 完成。接下来：

  source .venv/bin/activate
  langgraph dev                      # Studio: http://127.0.0.1:2024

  .venv/bin/python -m pytest tests -q --basetemp=.pytest_tmp
EOF
