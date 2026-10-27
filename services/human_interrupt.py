"""
人在回路（Human-in-the-Loop）请求的构造与解析。

`interrupt()` 的语义：节点执行到此处挂起并落 checkpoint，用户确认后
同一个节点会被重新进入，此时 `interrupt()` 直接返回 resume 传入的值。
注意：这意味着 `interrupt()` **之前的代码会执行两次**，所以副作用必须放在
它之后，或做成幂等。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

from typing import Any


def build_request(
    action: str,
    args: dict[str, Any] | None = None,
    description: str = "",
    *,
    allow_accept: bool = True,
    allow_ignore: bool = True,
    allow_respond: bool = True,
    allow_edit: bool = False,
) -> list[dict[str, Any]]:
    """构造 HumanInterrupt 结构（前端按此渲染确认面板）。"""
    return [
        {
            "action_request": {"action": action, "args": args or {}},
            "config": {
                "allow_accept": allow_accept,
                "allow_ignore": allow_ignore,
                "allow_respond": allow_respond,
                "allow_edit": allow_edit,
            },
            "description": description,
        }
    ]


def parse_response(raw: Any) -> tuple[str, dict[str, Any]]:
    """解析 `interrupt()` 的返回值。

    正常形态是 HumanResponse 列表（`[{"type": "accept", ...}]`），
    但旧客户端可能直接回传裸值，这里统一兜底为 accept。
    """
    if isinstance(raw, list) and raw:
        first = raw[0]
        if isinstance(first, dict):
            return str(first.get("type") or "accept"), first
        return "accept", {}
    if isinstance(raw, dict):
        return str(raw.get("type") or "accept"), raw
    return "accept", {}
