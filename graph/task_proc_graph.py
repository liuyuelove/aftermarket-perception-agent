"""task_proc 子图的组装。

节点之间全部通过 `Command(goto=...)` 动态路由，因此没有静态边。
子图作为主图的一个节点挂载 —— 这样 `interrupt()` 挂起的是整个 run，
resume 能从断点恢复（早期用 `invoke()` 调用子图会导致 run 直接结束）。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

from langgraph.graph import StateGraph

from graph.state import State
from nodes.task_proc import (
    node_data_download,
    node_data_labeling,
    node_func_proc,
    node_task_classify,
    node_train_data_gen,
)


def build_task_proc_graph():
    """构建并编译 task_proc 子图。"""
    builder = StateGraph(State)

    builder.add_node("node_task_classify", node_task_classify)
    builder.add_node("node_data_download", node_data_download)
    builder.add_node("node_data_labeling", node_data_labeling)
    builder.add_node("node_train_data_gen", node_train_data_gen)
    builder.add_node("node_func_proc", node_func_proc)

    builder.set_entry_point("node_task_classify")
    return builder.compile()
