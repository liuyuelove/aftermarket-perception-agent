"""数据标注节点：优先用 VLM 预标注，失败则降级到人在回路。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging

from langgraph.graph import END
from langgraph.types import Command
from langgraph.types import interrupt

from config import env
from graph.state import State
from services.annotation import try_auto_annotate
from services.human_interrupt import build_request, parse_response

log = logging.getLogger("aftermarket.node.labeling")


def node_data_labeling(state: State) -> Command:
    """自动标注 → 失败则 interrupt 等人放数据。

    注意：`interrupt()` 挂起后，恢复时本节点会**重新执行一遍**，
    因此 `try_auto_annotate` 可能被调用两次（第二次仍会失败并落到 interrupt）。
    这是 LangGraph 的固有语义 —— 若预标注有副作用，需自行保证幂等。
    """
    task_name = state.get("task_name") or ""
    label_dir = env.IMG_WITH_LABEL_DIR
    label_dir.mkdir(parents=True, exist_ok=True)

    if try_auto_annotate(task_name):
        log.info("预标注成功，跳过人工确认")
        return Command(goto="node_train_data_gen")

    rel_path = label_dir.relative_to(env.ROOT) if label_dir.is_relative_to(env.ROOT) else label_dir
    request = build_request(
        action="place_label_data",
        args={"path": str(label_dir), "rel_path": str(rel_path)},
        description=f"请将标注数据放在 {rel_path} 目录下，完成后点击「确认继续」。",
    )
    log.info("等待人工标注确认 dir=%s", label_dir)
    resp_type, _payload = parse_response(interrupt(request))
    log.info("人工标注确认结果 type=%s", resp_type)

    if resp_type == "ignore":
        return Command(goto=END, update={"task_proc_output": "用户跳过手动标注步骤"})

    if not any(label_dir.iterdir()):
        return Command(
            goto=END,
            update={"task_proc_output": f"目录 {label_dir} 为空，请放入标注数据后重试"},
        )

    return Command(goto="node_train_data_gen")
