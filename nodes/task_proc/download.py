"""数据下载节点：拉取 → 解压 → 解帧。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging

from langgraph.graph import END
from langgraph.types import Command

from graph.state import State
from services import dataset

log = logging.getLogger("aftermarket.node.download")


def node_data_download(state: State) -> Command:
    """执行数据准备链路，然后按处理类型决定去向。

    修正点：原实现只要 `task_proc_type == 'train'` 就无条件进入标注节点，
    忽略了用户明确说的 `data_need_labeling=False`。这里补上判断。
    """
    task_name = state.get("task_name") or ""
    log.info("开始数据准备 task=%s", task_name)

    if not dataset.fetch_and_preprocess(task_name):
        return Command(goto=END, update={"task_proc_output": "数据下载和预处理失败"})

    if state.get("task_proc_type") == "train" and bool(state.get("data_need_labeling", True)):
        return Command(goto="node_data_labeling")

    log.info("跳过标注，直接进入任务执行")
    return Command(goto="node_func_proc")
