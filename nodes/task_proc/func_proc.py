"""任务执行节点：训练 / 评估 / 模型转换。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging

from langgraph.graph import END
from langgraph.types import Command

from graph.state import State
from services.training import TrainingRunner

log = logging.getLogger("aftermarket.node.func_proc")


def node_func_proc(state: State) -> Command:
    """调度一次具体任务，把结果文本写回 task_proc_output。

    异常一律转成可读文本而不是抛出：任务失败是业务常态，
    应当交回 `node_result_display` 汇总给用户，而不是让整轮崩溃。
    """
    proc_type = state.get("task_proc_type") or ""
    task_type = state.get("task_type") or ""
    task_func = state.get("task_func") or ""

    try:
        runner = TrainingRunner(
            proc_type=proc_type,
            task_type=task_type,
            task_func=task_func,
            model_tag=state.get("model_tag") or "latest",
        )
        output = runner.run(
            thread_id=state.get("thread_id") or "",
            user_id=state.get("user_id") or "",
            task_name=state.get("task_name") or "",
        )
    except Exception as exc:  # noqa: BLE001 - 失败原因要回传给用户
        log.exception("任务执行异常 proc=%s task=%s/%s", proc_type, task_type, task_func)
        output = f"{task_type} {task_func} {proc_type} 执行失败：{exc}"

    log.info("任务执行完成 output=%r", output)
    return Command(goto=END, update={"task_proc_output": output})
