"""
项目入口。

`langgraph.json` 的 `graphs.agent` 指向本文件的 `app`，所以：

    langgraph dev          # 本地开发（带 Studio 界面）
    langgraph build/up     # 打包上服务器

图本身在 `graph/main_graph.py` 里组装，本文件只做「进程级初始化」：
日志格式、运行目录、配置自检。保持入口薄，方便单测直接 import 图。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging
import os

from config import env
from config.tasks import validate
from graph.main_graph import app

__all__ = ["app"]

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
log = logging.getLogger("aftermarket.main")


def _startup_report() -> None:
    """启动自检：目录、配置、任务注册表缺口。只报告，不阻塞启动。"""
    env.ensure_dirs()
    log.info("配置：%s", env.describe())

    problems = validate()
    if problems:
        log.warning("任务注册表有 %d 项配置缺口，相关任务会在运行时报可读错误", len(problems))
        for item in problems:
            log.debug("缺口 %s", item)


_startup_report()
