"""
mock 评估脚本 —— 不跑模型，给每张图写一个固定位置的框。

输出格式与真实 fcos 一致（`tools/lib/cnn_result_proc.cnn_result_file_read` 解析）：

    <图片名> <框数> [<类别> <x0> <y0> <x1> <y1> <score>] * 框数

坐标是**模型输出空间**（`config/mock.yml` 里的 EVAL_OUTPUT_SIZE），
后续 `cnn_bbox_remap_to_src` 会把它反算回原图坐标 —— 这条链路是真的，
只有「框从哪来」是假的。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PRJ_DIR = Path(__file__).resolve().parent
EVAL_DATA_DIR = PRJ_DIR / "eval_data"
RESULT_DIR = PRJ_DIR / "results"


def _output_size() -> tuple[int, int]:
    cfg_file = next((PRJ_DIR / "config").glob("*.yml"))
    cfg = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    w, h = cfg["MODEL_CONFIG"]["OVERRIDE"]["EVAL_OUTPUT_SIZE"][0]
    return int(w), int(h)


def main() -> int:
    parser = argparse.ArgumentParser(description="mock eval")
    parser.add_argument("--model-path", default="", help="模型路径（mock 忽略）")
    parser.parse_args()

    if not EVAL_DATA_DIR.is_dir():
        print(f"[mock] 缺少评估数据目录：{EVAL_DATA_DIR}", file=sys.stderr, flush=True)
        return 1

    images = sorted(EVAL_DATA_DIR.rglob("*.jpg"))
    if not images:
        print(f"[mock] {EVAL_DATA_DIR} 下没有 .jpg，无法评估", file=sys.stderr, flush=True)
        return 1

    out_w, out_h = _output_size()
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULT_DIR / "cnn_result.txt"

    with result_file.open("w", encoding="utf-8") as fp:
        for img in images:
            # 固定框：宽 30%、高 55%，左上角在 (15%, 15%)。
            # 写相对路径且**不带扩展名** —— 这是 cnn_result.txt 的约定，
            # 下游按 `{名字}.xml` 生成标注、按 `{名字}.jpg` 找原图。
            rel = img.relative_to(EVAL_DATA_DIR).with_suffix("")
            x0, y0 = out_w * 0.15, out_h * 0.15
            x1, y1 = out_w * 0.45, out_h * 0.70
            fp.write(f"{rel.as_posix()} 1 0 {x0:.1f} {y0:.1f} {x1:.1f} {y1:.1f} 0.9900\n")

    print(f"[mock] 这是演示用假评估，共 {len(images)} 张图", flush=True)
    print(f"[mock] 结果写入 {result_file}", flush=True)
    print(f"[mock] mAP@0.5: 0.0000 (mock 不计算指标)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
