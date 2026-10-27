"""
任务处理助手节点：解析用户意图，输出结构化决策，决定下一步去哪。

这是主图的「总调度」—— 任务类型识别、处理类型、任务名、是否需要下载/标注
全部由一次 LLM 调用填完，后续子图直接读 State，不再回头问模型。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from config import from_config
from config.llm import get_chat
from graph.prompts import ALLOWED_NEXT_NODES, ASSISTANT_SYSTEM_PROMPT
from graph.state import AssistantResponseFormat, Context, State

log = logging.getLogger("aftermarket.node.assistant")


@lru_cache(maxsize=1)
def get_assistant_agent():
    """构建（并缓存）带结构化输出的助手 agent。

    不挂任何工具：它只负责「理解 + 决策」，动作全部交给子图。
    """
    return create_agent(
        model=get_chat(),
        tools=[],
        system_prompt=ASSISTANT_SYSTEM_PROMPT,
        context_schema=Context,
        response_format=AssistantResponseFormat,
    )


def latest_human_text(messages: list[BaseMessage]) -> str:
    """取最后一条用户消息的纯文本；兼容多模态 content 列表。"""
    for msg in reversed(messages or []):
        if not isinstance(msg, HumanMessage):
            continue
        content = msg.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("text")
            ]
            return " ".join(p for p in parts if p).strip()
    return ""


def _log_thinking(text: str) -> None:
    """把模型 reasoning 段落单独记一条日志，便于排查误判。"""
    if "<think>" in text and "</think>" in text:
        think = text.split("</think>")[0].split("<think>")[-1].strip()
        if think:
            log.debug("assistant thinking:\n%s", think)


def node_task_proc_assistant(state: State, config: RunnableConfig) -> Command:
    """解析用户输入并路由。"""
    ctx = from_config(config)
    messages = state.get("messages", [])
    user_input = latest_human_text(messages) or (state.get("user_input") or "").strip()

    if not user_input:
        log.warning("未取到用户输入 thread=%s", ctx.thread_id)
        return Command(
            goto=END,
            update={
                "messages": [AIMessage(content="抱歉，我没有收到您的消息。请重新输入。")],
                "user_input": "",
            },
        )

    log.info("assistant 解析 thread=%s input=%r", ctx.thread_id, user_input[:80])

    try:
        response = get_assistant_agent().invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config={"configurable": {"thread_id": ctx.thread_id}},
            context=Context(user_id=ctx.user_id),
        )
        structured = response["structured_response"]

        for msg in response.get("messages", []):
            if isinstance(msg, AIMessage) and isinstance(msg.content, str):
                _log_thinking(msg.content)
    except Exception as exc:  # noqa: BLE001 - 兜底给用户可读错误，避免整轮崩掉
        log.exception("assistant 调用失败 thread=%s", ctx.thread_id)
        return Command(
            goto=END,
            update={"messages": [AIMessage(content=f"抱歉，处理您的请求时发生了错误: {exc}")]},
        )

    next_node = (getattr(structured, "next_node", "") or "").strip()
    if next_node not in ALLOWED_NEXT_NODES:
        log.warning("next_node=%r 非法，按默认处理", next_node)
        next_node = ""

    update = {
        "messages": [AIMessage(content=structured.response or "")],
        "user_input": user_input,
    }
    for field_name in (
        "task_name",
        "task_proc_type",
        "model_tag",
        "data_need_download",
        "data_need_labeling",
    ):
        value = getattr(structured, field_name, None)
        if value is not None:
            update[field_name] = value

    if next_node == "node_task_proc":
        goto: str = "node_task_proc_prepare"
    elif next_node == "node_end":
        goto = "node_end"
    else:
        # node_user_input 已不在图中：结束本轮，用户下一条消息会重新进入本节点
        goto = END

    log.info(
        "assistant 决策 thread=%s next=%s proc_type=%s task=%s model=%s",
        ctx.thread_id,
        goto,
        update.get("task_proc_type"),
        update.get("task_name"),
        update.get("model_tag"),
    )
    return Command(goto=goto, update=update)
