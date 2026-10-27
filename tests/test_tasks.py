"""任务注册表：查得到、查不到、缺配置时的行为。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import pytest

from config.tasks import TASKS, UnknownTaskError, get_task, validate


def test_get_task_returns_spec():
    spec = get_task("DMS2.0", "人头")
    assert spec.prj == "dms_head_det"
    assert spec.pipeline, "人头任务应当有 pre_proc / post_proc 流水线"


def test_task_type_is_case_insensitive():
    """LLM 可能吐小写，注册表要能接住。"""
    assert get_task("dms2.0", "人头") is get_task("DMS2.0", "人头")


def test_unknown_task_raises_with_hint():
    with pytest.raises(UnknownTaskError) as exc:
        get_task("DMS9.9", "不存在")
    msg = str(exc.value)
    # 报错要能直接告诉人「有哪些可选」，而不是只抛一个 key
    assert "DMS9.9" in msg
    assert "DMS2.0" in msg


def test_validate_reports_gaps_without_raising():
    """缺配置只报告，不抛异常 —— 否则启动就挂。"""
    problems = validate()
    assert isinstance(problems, list)
    # 已知有缺口的任务应当被点名（HOD 三个功能都没配 prj）
    assert any("HOD" in p for p in problems)


def test_every_spec_key_is_registered_consistently():
    """注册表的 key 必须和 spec 自身字段一致，避免查到了但内容对不上。"""
    for (task_type, task_func), spec in TASKS.items():
        assert spec.task_type == task_type
        assert spec.task_func == task_func


def test_pre_cnn_points_to_registered_func():
    """pre_cnn 若填写，必须指向同类型下已注册的功能，否则级联跑不起来。"""
    for (task_type, _), spec in TASKS.items():
        if spec.pre_cnn:
            assert (task_type, spec.pre_cnn) in TASKS
