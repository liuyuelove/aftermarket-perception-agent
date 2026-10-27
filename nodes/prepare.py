"""进入子图前的上下文注入节点。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from config import from_config
from graph.state import State

log = logging.getLogger("aftermarket.node.prepare")


def node_task_proc_prepare(state: State, config: RunnableConfig) -> Command:
    """把 thread_id / user_id 从 config 注入 State，供子图内的日志与落盘使用。

    单独成节点的原因：子图作为节点挂载时，`interrupt()` 会挂起整个 run，
    resume 才能从断点恢复；因此子图内部拿不到外层 config，必须先落到 State。
    """
    ctx = from_config(config)
    log.info("prepare 注入上下文 thread=%s user=%s", ctx.thread_id, ctx.user_id)
    return Command(
        goto="node_task_proc",
        update={"user_id": ctx.user_id, "thread_id": ctx.thread_id},
    )
