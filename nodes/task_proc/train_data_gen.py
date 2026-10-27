"""训练数据生成节点：格式转换 + train/val 划分 + 原始数据备份。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging

from langgraph.graph import END
from langgraph.types import Command

from graph.state import State
from services.training import TrainingRunner

log = logging.getLogger("aftermarket.node.train_data_gen")


def node_train_data_gen(state: State) -> Command:
    """把标注数据转成训练格式；失败则带着原因结束，不进入训练。"""
    task_type = state.get("task_type") or ""
    task_func = state.get("task_func") or ""

    try:
        runner = TrainingRunner(
            proc_type=state.get("task_proc_type") or "train",
            task_type=task_type,
            task_func=task_func,
            model_tag=state.get("model_tag") or "latest",
        )
        proc_name = runner.build_train_data()
    except Exception as exc:  # noqa: BLE001 - 失败原因要回传给用户
        log.exception("训练数据生成异常")
        return Command(
            goto=END,
            update={"task_proc_output": f"训练数据生成失败：{exc}"},
        )

    if proc_name == "none":
        return Command(
            goto=END,
            update={"task_proc_output": f"{task_type} {task_func} 训练数据生成失败（未匹配预处理）"},
        )

    log.info("训练数据生成完成 proc=%s", proc_name)
    return Command(goto="node_func_proc")
