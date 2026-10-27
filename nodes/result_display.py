"""结果汇总节点：把子图的执行结果交回助手，组织成人话后结束本轮。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage
from langgraph.graph import END
from langgraph.types import Command

from config import from_config
from graph.state import Context, State
from nodes.assistant import get_assistant_agent

log = logging.getLogger("aftermarket.node.result_display")


def node_result_display(state: State, config=None) -> Command:
    """让 assistant 总结 task_proc_output，然后结束本轮。

    结束而非循环，是为了避免任务失败时反复重试。
    """
    output = state.get("task_proc_output") or "（无输出）"
    ctx = from_config(config)

    try:
        response = get_assistant_agent().invoke(
            {"messages": [{"role": "user", "content": f"任务处理结果: {output}"}]},
            config={"configurable": {"thread_id": ctx.thread_id}},
            context=Context(user_id=ctx.user_id),
        )
        text = response["structured_response"].response or output
    except Exception:  # noqa: BLE001 - 汇总失败不应吞掉原始结果
        log.exception("结果汇总失败，直接透传原始输出")
        text = output

    log.info("result_display 完成 thread=%s", ctx.thread_id)
    return Command(
        goto=END,
        update={
            # 只返回新增消息：messages 挂了 add_messages reducer，
            # 回吐全量历史会导致重复（原实现有此问题）。
            "messages": [AIMessage(content=text)],
            "task_proc_output": output,
        },
    )
