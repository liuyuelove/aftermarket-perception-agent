"""
命令行对话（不依赖 langgraph dev / Studio）。

用途：填好 `.env` 里的 key 之后，不启服务也能验证「意图 → 子图 → 回话」通不通，
以及人在回路的挂起/恢复是不是真的能用。

用法：
    python scripts/run_demo.py
    python scripts/run_demo.py "DMS2.0-人头-易甲文-NT98323-测试，做评估，不用下载数据"

交互说明：
    - 直接输入内容 → 发一条消息
    - 出现「等待人工确认」时，输入 y 继续、n 跳过
    - exit / quit / Ctrl-D 退出

为什么是交互式而不是一条命令一次：`interrupt()` 的 checkpoint 由 checkpointer 持有，
本脚本用 MemorySaver（进程内），跨进程恢复拿不到断点。要跨进程恢复请用 `langgraph dev`。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# 允许从任意目录执行：把项目根放进 sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.messages import HumanMessage  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.types import Command  # noqa: E402

from graph.main_graph import build_main_graph  # noqa: E402


def show_new_messages(state: dict, seen: int) -> int:
    """打印本轮新增的消息，返回累计条数。"""
    messages = state.get("messages", [])
    for msg in messages[seen:]:
        role = type(msg).__name__.replace("Message", "")
        print(f"\n[{role}] {msg.content}")
    return len(messages)


def describe_interrupt(state: dict) -> list[str]:
    """把 interrupt 的 payload 转成可读提示。"""
    lines = []
    for item in state.get("__interrupt__") or []:
        for req in item.value or []:
            lines.append(str(req.get("description") or req))
    return lines


def main() -> int:
    logging.basicConfig(
        level=logging.INFO if "--verbose" in sys.argv else logging.WARNING,
        format="%(levelname)-7s %(name)s | %(message)s",
    )

    app = build_main_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "cli"}}
    seen = 0

    pending = [a for a in sys.argv[1:] if not a.startswith("--")]
    print("后装 Agent 命令行。输入内容开始；exit 退出。")
    if pending:
        print(f"> {pending[0]}")

    while True:
        try:
            text = pending.pop(0) if pending else input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            return 0

        # 上一轮挂起了：这次输入当成「确认继续 / 跳过」
        state = app.get_state(config)
        if state.next:
            if text.lower() not in {"y", "yes", "确认", "继续"}:
                print("已取消本轮（未恢复挂起的节点）。")
                return 0
            state = app.invoke(Command(resume=[{"type": "accept"}]), config=config)
            print("\n（已确认继续）")
        else:
            state = app.invoke({"messages": [HumanMessage(text)]}, config=config)

        seen = show_new_messages(state, seen)

        prompts = describe_interrupt(state)
        if prompts:
            print("\n⏸  等待人工确认：")
            for line in prompts:
                print(f"   - {line}")
            print("   输入 y 继续，其它任意内容退出。")

        if state.get("task_proc_output"):
            print(f"\n[task_proc_output] {state['task_proc_output']}")


if __name__ == "__main__":
    raise SystemExit(main())
