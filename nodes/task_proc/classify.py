"""任务分类节点：把任务名拆成「类型 + 功能」，并决定从哪一步开始。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging

from langgraph.graph import END
from langgraph.types import Command

from config.tasks import UnknownTaskError, get_task
from graph.state import State

log = logging.getLogger("aftermarket.node.classify")


def split_task_name(task_name: str) -> tuple[str, str]:
    """`DMS2.0-人眼-易甲文-NT98323-闭眼误报` → (`DMS2.0`, `人眼`)。

    第三段之后全部算「任务信息」，不参与分类。
    """
    parts = [p.strip() for p in (task_name or "").split("-", 2)]
    if len(parts) < 3:
        raise ValueError(
            f"任务名格式不合法：{task_name!r}，应为「任务类型-任务功能-任务信息」"
        )
    return parts[0].upper(), parts[1]


def node_task_classify(state: State) -> Command:
    """校验任务名并决定入口分支。"""
    task_name = state.get("task_name") or ""
    proc_type = (state.get("task_proc_type") or "").strip()
    need_download = bool(state.get("data_need_download", True))
    need_labeling = bool(state.get("data_need_labeling", True))

    try:
        task_type, task_func = split_task_name(task_name)
        get_task(task_type, task_func)  # 触发注册表校验，缺配置会给出可读错误
    except (ValueError, UnknownTaskError) as exc:
        log.error("任务分类失败 task=%r: %s", task_name, exc)
        return Command(goto=END, update={"task_proc_output": f"任务分类失败：{exc}"})

    if proc_type in ("train", "eval") and need_download:
        goto = "node_data_download"
    elif proc_type == "train" and need_labeling:
        goto = "node_data_labeling"
    else:
        goto = "node_func_proc"

    log.info(
        "分类完成 task=%s type=%s func=%s proc=%s download=%s labeling=%s → %s",
        task_name, task_type, task_func, proc_type, need_download, need_labeling, goto,
    )
    return Command(
        goto=goto,
        update={"task_type": task_type, "task_func": task_func},
    )
