#!/bin/bash
# 训练 / 评估执行器。
#
# 用法: prj_run.sh <func_type> <run_type> <prj_path> <model_tag> <aftermarket_data_path>
#
# RUNNER=local  直接在本机 python 环境跑（无 GPU / 无 docker 时用这个）
# RUNNER=docker 在容器里跑（生产环境；原实现只有这一种）
#
# 与旧版差异：checkpoint 归档已移到 Python（services/training.py），
# 本脚本只负责「把 train.py / eval.py 跑起来」。

set -euo pipefail

func_type="${1:?func_type required}"
run_type="${2:?run_type required}"
prj_path="${3:?prj_path required}"
model_tag="${4:-latest}"
aftermarket_data_path="${5:-./data/aftermarket_data}"

RUNNER="${RUNNER:-local}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

case "$func_type" in
  dms|bsd|hod|cargo) ;;
  *) echo "[prj_run] func_type 非法: $func_type（可选 dms/bsd/hod/cargo）" >&2; exit 1 ;;
esac

case "$run_type" in
  train|eval) ;;
  *) echo "[prj_run] run_type 非法: $run_type（可选 train/eval）" >&2; exit 1 ;;
esac

if [ ! -d "$prj_path" ]; then
  echo "[prj_run] 工程目录不存在: $prj_path" >&2
  echo "[prj_run] 提示: 放入真实 fcos 代码，或保留 fcos/_mock 用于演示" >&2
  exit 1
fi

abs_prj_dir="$(cd "$prj_path" && pwd)"
entry_script="$run_type.py"

if [ ! -f "$abs_prj_dir/$entry_script" ]; then
  echo "[prj_run] 缺少入口脚本: $abs_prj_dir/$entry_script" >&2
  exit 1
fi

# 解析工程参数（模型路径 / 配置 / 分辨率）。缺脚本时用兜底值。
param_script="$abs_prj_dir/../lib/model_cvt/get_prj_params.py"
model_path=""
if [ -f "$param_script" ]; then
  model_path="$("$PYTHON_BIN" "$param_script" --prj-dir "$abs_prj_dir" --model-tag "$model_tag" 2>/dev/null \
    | "$PYTHON_BIN" -c 'import json,sys;print(json.load(sys.stdin).get("model_path",""))' 2>/dev/null || true)"
fi

echo "[prj_run] runner=$RUNNER func=$func_type run=$run_type prj=$abs_prj_dir tag=$model_tag"
echo "[prj_run] model_path=${model_path:-<未解析>}"

run_local() {
  cd "$abs_prj_dir"
  if [ "$run_type" = "train" ]; then
    rm -rf checkpoints runs
    "$PYTHON_BIN" train.py --model-path "$model_path"
  else
    rm -rf results
    "$PYTHON_BIN" eval.py --model-path "$model_path"
  fi
}

run_docker() {
  case "$func_type" in
    dms|hod) CONTAINER_NAME=ai_dms; DOCKER_IMAGE="${DOCKER_IMAGE:-docker_dms:v3}" ;;
    bsd)     CONTAINER_NAME=ai_bsd; DOCKER_IMAGE="${DOCKER_IMAGE:-docker_bsd:v1}" ;;
    cargo)   CONTAINER_NAME=ai_cargo; DOCKER_IMAGE="${DOCKER_IMAGE:-docker_cargo:v1}" ;;
  esac

  if [ "$(docker ps -a --format '{{.Names}}' | grep -cx "$CONTAINER_NAME" || true)" -eq 0 ]; then
    docker run --gpus all --privileged --name "$CONTAINER_NAME" \
      --shm-size="${DOCKER_SHM:-8G}" \
      -v /:/work/ -v "$aftermarket_data_path:/ssd/aftermarket_data/" \
      -d -e LANG=C.UTF-8 "$DOCKER_IMAGE" /bin/bash
  fi
  docker start "$CONTAINER_NAME" >/dev/null

  if [ "$run_type" = "train" ]; then
    rm -rf "$abs_prj_dir/checkpoints" "$abs_prj_dir/runs"
    script="python train.py --model-path $model_path"
  else
    rm -rf "$abs_prj_dir/results"
    script="python eval.py --model-path $model_path"
  fi

  docker exec -i "$CONTAINER_NAME" /bin/bash -c "
    set -e
    [ -f /opt/conda/etc/profile.d/conda.sh ] && source /opt/conda/etc/profile.d/conda.sh
    export LANG=C.UTF-8 LC_ALL=C.UTF-8
    conda activate base 2>/dev/null || true
    cd /work$abs_prj_dir
    $script
  "
  docker stop "$CONTAINER_NAME" >/dev/null
}

if [ "$RUNNER" = "docker" ]; then
  run_docker
else
  run_local
fi

echo "[prj_run] $abs_prj_dir $run_type done"
