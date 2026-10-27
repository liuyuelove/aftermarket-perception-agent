#!/bin/bash
# mock 模型转换：造一个假产物目录，让链路能走到「结果已保存」。
# 真实转换脚本在 fcos/<func_type>/lib/model_cvt/docker_model_cvt.sh。
#
# 用法: docker_model_cvt.sh <prj_path> <model_tag>

set -euo pipefail

prj_path="${1:?prj_path required}"
model_tag="${2:-latest}"

if [ ! -d "$prj_path" ]; then
  echo "[mock_cvt] 工程目录不存在: $prj_path" >&2
  exit 1
fi

out_dir="$prj_path/mode_convert/converted_models"
mkdir -p "$out_dir"

prj_name="$(basename "$prj_path")"
target="$out_dir/${prj_name}_384x256_${model_tag}.tar.gz"

# 打一个只含说明文本的假包，避免产物目录为空导致下游误判
tmp_dir="$(mktemp -d)"
printf 'mock converted model (not runnable)\nproject=%s\nmodel_tag=%s\n' \
  "$prj_name" "$model_tag" > "$tmp_dir/README.txt"
tar -czf "$target" -C "$tmp_dir" README.txt
rm -rf "$tmp_dir"

echo "[mock_cvt] $target"
