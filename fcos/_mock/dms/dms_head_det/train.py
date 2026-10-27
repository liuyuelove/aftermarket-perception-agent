"""
mock 训练脚本 —— 只为跑通链路，不做任何真实训练。

它做三件事：
  1. 打印几行带 loss 的日志（格式与真实 pytorch-detection 一致，
     好让 `parse_pytorch_detection_metrics` 能解析出曲线）
  2. 生成一个假 checkpoint（`services/training.py` 训练完会归档它）
  3. 正常退出（返回码 0）

真实训练请把 fcos 工程放到 `fcos/<func_type>/<prj>/`，本文件不会被用到。
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

EPOCHS = 3
ITERS_PER_EPOCH = 5


def main() -> int:
    parser = argparse.ArgumentParser(description="mock train")
    parser.add_argument("--model-path", default="", help="预训练模型路径（mock 忽略）")
    parser.parse_args()

    prj_dir = Path(__file__).resolve().parent
    ckpt_dir = prj_dir / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    print("[mock] 这是演示用假训练，不产生真实模型", flush=True)

    for epoch in range(1, EPOCHS + 1):
        for it in range(1, ITERS_PER_EPOCH + 1):
            total = round(4.0 / (epoch * it) ** 0.5, 4)
            print(
                f"[epoch {epoch}, iter_sample {it}] Total training loss: {total}",
                flush=True,
            )
            print(f"level_p3_det_cls_loss_dfl: {total * 0.5:.4f}", flush=True)
            print(f"level_p3_det_bbox_loss_diou: {total * 0.3:.4f}", flush=True)
            print(f"level_p3_det_cen_loss_dfl: {total * 0.2:.4f}", flush=True)
        print(f"[mock] epoch {epoch}/{EPOCHS} done", flush=True)

    ckpt = ckpt_dir / "mock_epochs.pth"
    ckpt.write_bytes(b"mock-checkpoint-not-a-real-model\n")
    print(f"[mock] checkpoint written: {ckpt}", flush=True)
    time.sleep(0.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
