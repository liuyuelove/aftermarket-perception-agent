"""
主图组装。

拓扑（5 个节点）：

    node_task_proc_assistant ──┬─→ node_end ─→ END
                               ├─→ node_task_proc_prepare ─→ node_task_proc（子图）
                               │                                   │
                               └─→ END                             ↓
                                                        node_result_display ─→ END

节点间跳转几乎全由 `Command(goto=...)` 在运行时决定（LLM 当路由器），
唯一的静态边是「子图跑完必然去汇总结果」—— 子图本身不返回 Command。

task_proc 以**编译后的子图对象**作为节点挂载，而不是在节点里 `invoke()`：
这样 `interrupt()` 挂起的是整个 run，resume 能从断点继续。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph

from graph.state import State
from graph.task_proc_graph import build_task_proc_graph
from nodes import (
    node_end,
    node_result_display,
    node_task_proc_assistant,
    node_task_proc_prepare,
)

log = logging.getLogger("aftermarket.graph.main")

ENTRY_POINT = "node_task_proc_assistant"


def build_main_graph(checkpointer=None):
    """构建并编译主图。

    checkpointer 只在本地脚本 / 单测里传（`interrupt()` 必须有它才能挂起）；
    LangGraph Server 会忽略它并用自己的持久化。
    """
    builder = StateGraph(State)

    builder.add_node("node_task_proc_assistant", node_task_proc_assistant)
    builder.add_node("node_task_proc_prepare", node_task_proc_prepare)
    builder.add_node("node_task_proc", build_task_proc_graph())
    builder.add_node("node_result_display", node_result_display)
    builder.add_node("node_end", node_end)

    builder.set_entry_point(ENTRY_POINT)

    # 子图不返回 Command，跑完固定进入结果汇总
    builder.add_edge("node_task_proc", "node_result_display")

    return builder.compile(checkpointer=checkpointer)


app = build_main_graph()
log.info("主图已编译，节点：%s", list(app.get_graph().nodes))
