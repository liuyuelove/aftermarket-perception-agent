"""从 LangGraph 的 RunnableConfig 提取运行上下文。

原实现 `run_context.from_config` 返回裸 dict，且硬编码 thread_id='default'
的地方另有一处，导致多会话互相污染、日志互相覆盖。这里统一成不可变对象，
让「一次运行的身份」只有一个来源。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunContext:
    """一次图运行的上下文标识。"""

    thread_id: str = "default"
    user_id: str = "default"

    @property
    def is_anonymous(self) -> bool:
        return self.thread_id == "default"


def from_config(config: Any) -> RunContext:
    """从 config.configurable 读取 thread_id / user_id。

    LangGraph 注入的 config 是 dict 形态（RunnableConfig 是 TypedDict），
    但节点未声明 config 参数时会拿到 None，这里一并兜底。
    """
    if not isinstance(config, dict):
        return RunContext()

    configurable = config.get("configurable")
    if not isinstance(configurable, dict):
        return RunContext()

    thread_id = str(configurable.get("thread_id") or "default")
    user_id = str(configurable.get("user_id") or "default")
    return RunContext(thread_id=thread_id, user_id=user_id)
