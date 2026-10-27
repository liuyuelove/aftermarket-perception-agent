"""图的形状：节点、入口、子图挂载方式。

锁这些是因为「分层」最容易出的问题就是：文件拆得好看，但图少了一个节点、
或者子图被改成在节点里 `invoke()`（那样 interrupt 挂不住整个 run）。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

from graph.main_graph import ENTRY_POINT, build_main_graph
from graph.task_proc_graph import build_task_proc_graph

MAIN_NODES = {
    "node_task_proc_assistant",
    "node_task_proc_prepare",
    "node_task_proc",
    "node_result_display",
    "node_end",
}

SUB_NODES = {
    "node_task_classify",
    "node_data_download",
    "node_data_labeling",
    "node_train_data_gen",
    "node_func_proc",
}


def test_main_graph_nodes():
    app = build_main_graph()
    nodes = set(app.get_graph().nodes)
    assert MAIN_NODES <= nodes
    # 不该有历史遗留的 test 节点
    assert not any(n.startswith("test") for n in nodes)


def test_main_entry_point():
    app = build_main_graph()
    assert ENTRY_POINT == "node_task_proc_assistant"
    edges = {(e.source, e.target) for e in app.get_graph().edges}
    assert ("__start__", ENTRY_POINT) in edges


def test_subgraph_nodes():
    g = build_task_proc_graph()
    assert SUB_NODES == {n for n in g.get_graph().nodes if not n.startswith("__")}


def test_subgraph_is_mounted_not_invoked():
    """node_task_proc 必须是一个「编译后的图」，不是普通函数。

    只有挂载子图，子图里的 interrupt() 才能挂起整个 run。
    """
    from langgraph.graph.state import CompiledStateGraph

    app = build_main_graph()
    node = app.get_graph().nodes["node_task_proc"]
    assert isinstance(node.data, CompiledStateGraph), (
        "node_task_proc 不是编译后的子图 —— interrupt() 会挂不住整个 run"
    )


def test_result_display_has_static_edge_from_subgraph():
    """子图不返回 Command，靠静态边进入汇总节点。

    注意不能用 `app.get_graph().edges` 断言：绘图只画从 START 沿静态边可达的部分，
    而 node_task_proc 是运行时由 Command 进入的，画不出来。这里查 builder 的边定义。
    """
    app = build_main_graph()
    assert ("node_task_proc", "node_result_display") in set(app.builder.edges)
