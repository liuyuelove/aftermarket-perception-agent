"""
训练日志捕获与 metrics 解析。供 func_proc.run_prj 去调用
"""
import os
import re
import json
import subprocess
from typing import Callable

# pytorch-detection 日志格式的解析模式: (regex, key=None 表示总 loss 行)
LOSS_PATTERNS = [
    (r'\[epoch\s+(\d+),\s*iter_sample\s+(\d+).*?\]\s+Total training loss:\s+([\d.]+)', None),
    (r'level_p3_det_cls_loss_dfl:\s+([\d.]+)', 'cls_loss'),
    (r'level_p3_det_bbox_loss_diou:\s+([\d.]+)', 'bbox_loss'),
    (r'level_p3_det_cen_loss_dfl:\s+([\d.]+)', 'cen_loss'),
]


def parse_pytorch_detection_metrics(line: str, last_point: dict) -> dict:
    """
    解析 pytorch-detection 训练日志行，提取 loss 指标。
    Args:
        line: 日志行
        last_point: 上一数据点（用于子 loss 追加）
    Returns:
        更新后的 last_point，若无匹配则返回原 last_point
    """
    for pat, key in LOSS_PATTERNS:
        m = re.search(pat, line)
        if not m:
            continue
        if key is None:
            return {'iter': int(m.group(2)), 'epoch': int(m.group(1)), 'total_loss': float(m.group(3))}
        if last_point:
            last_point[key] = float(m.group(1))
        return last_point
    return last_point


def append_metrics_point(metrics_path: str, point: dict) -> None:
    """将单个 metrics 数据点追加写入 jsonl 文件。"""
    with open(metrics_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(point, ensure_ascii=False) + '\n')
        f.flush()


def run_subprocess_with_log_capture(
    cmd: list,
    log_path: str,
    metrics_path: str,
    parse_fn: Callable[[str, dict], dict],
    env: dict | None = None,
) -> None:
    """
    运行子进程，将 stdout/stderr 写入 log_path，并逐行用 parse_fn 解析后追加到 metrics_path。

    env 为 None 时继承当前进程环境；需要指定解释器（如 PYTHON_BIN）时传入。
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    last_point = {}
    with open(log_path, 'a', encoding='utf-8') as log_f:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        for line in iter(proc.stdout.readline, ''):
            log_f.write(line)
            log_f.flush()
            new_point = parse_fn(line, last_point)
            if new_point is not last_point:
                if last_point:
                    append_metrics_point(metrics_path, last_point)
                last_point = new_point
    if last_point:
        append_metrics_point(metrics_path, last_point)
    proc.wait()
    if proc.returncode != 0:
        # 原实现忽略返回码，训练脚本崩了上层也当成功，结果目录里躺着一堆空文件
        raise RuntimeError(
            f"子进程失败（exit={proc.returncode}）：{' '.join(str(c) for c in cmd)}\n"
            f"完整日志：{log_path}"
        )
