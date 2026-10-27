"""
预标注服务封装。

未配置 `PREANNOTATION_SERVER_URL` 或本地没有待标注数据时，
`is_available()` 返回 False，调用方据此降级到人在回路 —— 不发起网络请求。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging

from config import env
from tools.data_pre_proc.annotation_service import AnnotationService

log = logging.getLogger("aftermarket.annotation")


def try_auto_annotate(task_name: str) -> bool:
    """尝试用 VLM 预标注服务自动标注；失败返回 False，由调用方降级。"""
    service = AnnotationService(
        server_url=env.PREANNOTATION_SERVER_URL or None,
        ftp_data_dir=str(env.FTP_DATA_DIR),
    )
    if not service.is_available():
        log.info(
            "预标注不可用（server_url=%r, ftp_data_dir=%s），将降级到人工标注",
            env.PREANNOTATION_SERVER_URL or None,
            env.FTP_DATA_DIR,
        )
        return False

    env.IMG_WITH_LABEL_DIR.mkdir(parents=True, exist_ok=True)
    log.info("尝试预标注 task=%s", task_name)
    ok = service.annotate(task_name, str(env.IMG_WITH_LABEL_DIR))
    log.info("预标注结果 task=%s ok=%s", task_name, ok)
    return ok
