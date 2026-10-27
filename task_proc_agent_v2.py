"""
兼容旧入口。

`langgraph.json` 早期指向 `./task_proc_agent_v2.py:app`。重构后图在
`graph/main_graph.py` 组装、入口是 `main.py`，本文件只做转发，
避免旧脚本 / 旧部署配置里的 import 直接崩掉。

新代码请直接 `from main import app`。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import warnings

warnings.warn(
    "task_proc_agent_v2 已拆分为 main.py + graph/ + nodes/ + services/，请改从 main 导入 app",
    DeprecationWarning,
    stacklevel=2,
)

from main import app  # noqa: E402 - 故意放在 warning 之后

__all__ = ["app"]
