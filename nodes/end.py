"""结束节点：用户显式要求结束时的收尾。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging

from langgraph.graph import END
from langgraph.types import Command

from graph.state import State

log = logging.getLogger("aftermarket.node.end")


def node_end(state: State) -> Command:
    """收尾并结束本次 run。"""
    log.info("会话结束")
    return Command(goto=END)
