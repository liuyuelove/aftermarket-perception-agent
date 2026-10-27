"""人在回路：请求结构、响应解析、以及「只返回新增消息」的契约。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from services.human_interrupt import build_request, parse_response


def test_build_request_shape():
    """前端按 HumanInterrupt 结构渲染面板，字段名不能改。"""
    req = build_request(
        action="place_label_data",
        args={"path": "/tmp/x"},
        description="请放数据",
    )
    assert isinstance(req, list) and len(req) == 1
    item = req[0]
    assert item["action_request"]["action"] == "place_label_data"
    assert item["action_request"]["args"] == {"path": "/tmp/x"}
    assert item["config"] == {
        "allow_accept": True,
        "allow_ignore": True,
        "allow_respond": True,
        "allow_edit": False,
    }
    assert item["description"] == "请放数据"


def test_parse_response_list_form():
    assert parse_response([{"type": "ignore", "args": None}])[0] == "ignore"


def test_parse_response_bare_dict():
    assert parse_response({"type": "response", "args": "继续"})[0] == "response"


def test_parse_response_none_defaults_to_accept():
    """旧客户端可能什么都不回，兜底成 accept 而不是崩。"""
    assert parse_response(None)[0] == "accept"
    assert parse_response([])[0] == "accept"


def test_result_display_returns_only_new_message(monkeypatch):
    """原实现返回 messages + [新消息]，但 messages 挂了 add_messages reducer，
    结果是把整段历史再追加一遍。这里锁「只返回新增」。"""
    import nodes.result_display as rd

    class StubAgent:
        def invoke(self, *a, **k):
            return {"structured_response": SimpleNamespace(response="汇总完成")}

    monkeypatch.setattr(rd, "get_assistant_agent", lambda: StubAgent())

    history = [HumanMessage("你好"), AIMessage("你好，有什么可以帮您")]
    cmd = rd.node_result_display(
        {"messages": history, "task_proc_output": "dms_head_det eval success"}
    )

    new_messages = cmd.update["messages"]
    assert len(new_messages) == 1
    assert isinstance(new_messages[0], AIMessage)
    assert new_messages[0].content == "汇总完成"
    assert cmd.update["task_proc_output"] == "dms_head_det eval success"


def test_result_display_falls_back_when_llm_fails(monkeypatch):
    """汇总失败不能吞掉原始结果。"""
    import nodes.result_display as rd

    class BoomAgent:
        def invoke(self, *a, **k):
            raise RuntimeError("模型挂了")

    monkeypatch.setattr(rd, "get_assistant_agent", lambda: BoomAgent())
    cmd = rd.node_result_display({"messages": [], "task_proc_output": "原始输出"})
    assert cmd.update["messages"][0].content == "原始输出"
