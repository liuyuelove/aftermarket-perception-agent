"""
图状态与结构化输出契约。

主图与 task_proc 子图共用同一份 State：子图作为节点被挂载时，直接读写
这些通道，无需再做字段搬运（原实现的注释也是这个意图，但代码里写了两份
State，容易漂移）。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

#: 任务处理类型
TaskProcType = Literal["train", "eval", "model_cvt"]


class State(TypedDict, total=False):
    """贯穿主图与子图的共享状态。

    total=False：每个节点只返回自己改动的那部分，不必回吐整份 state。
    只有 `messages` 挂了 reducer（追加语义），其余字段都是覆盖语义 ——
    这是刻意的：`task_proc_type` 这类「决策字段」本来就该被后写者覆盖。
    """

    # 对话层
    messages: Annotated[list[BaseMessage], add_messages]
    user_input: str

    # 决策层（由 assistant 节点的结构化输出写入）
    task_name: str
    task_proc_type: str
    model_tag: str
    data_need_download: bool
    data_need_labeling: bool

    # 结果层
    task_proc_output: str

    # 运行上下文（由 prepare 节点从 config 注入）
    user_id: str
    thread_id: str

    # 任务分类结果（由 classify 节点写入）
    task_type: str
    task_func: str


@dataclass
class Context:
    """运行时上下文 schema（LangGraph context_schema）。"""

    user_id: str = ""


@dataclass
class AssistantResponseFormat:
    """assistant 节点的结构化输出契约。

    `next_node` 由 LLM 填写，是「LLM 当路由器」的关键字段；
    非法值由 assistant 节点做白名单校验后兜底。
    """

    response: str = ""              # 给用户看的回答
    task_proc_type: str = ""        # train / eval / model_cvt
    task_name: str = ""             # 任务类型-任务功能-任务信息
    data_need_download: bool = True
    data_need_labeling: bool = True
    model_tag: str = "latest"
    next_node: str = ""             # 路由目标
