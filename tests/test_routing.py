"""子图入口的分类与路由。

这里锁的是「跳过分支」的正确性 —— 原实现只要 proc_type=='train' 就无条件进标注，
无视用户明确说的 data_need_labeling=False。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import pytest
from langgraph.graph import END

from nodes.task_proc.classify import node_task_classify, split_task_name

TASK = "DMS2.0-人头-易甲文-NT98323-测试"


def run_classify(**kwargs):
    state = {
        "task_name": TASK,
        "task_proc_type": "eval",
        "data_need_download": False,
        "data_need_labeling": False,
        **kwargs,
    }
    return node_task_classify(state)


@pytest.mark.parametrize(
    "task_name,expected",
    [
        (TASK, ("DMS2.0", "人头")),
        ("BSD-鱼眼机动车道路-易甲文-NT323-误报", ("BSD", "鱼眼机动车道路")),
        # 任务信息里再出现 '-' 也要正确切开
        ("HOD-方向盘-某某-NT1-A-B-C", ("HOD", "方向盘")),
    ],
)
def test_split_task_name(task_name, expected):
    assert split_task_name(task_name) == expected


@pytest.mark.parametrize("bad", ["", "只有两段", "A-B"])
def test_split_task_name_rejects_bad_format(bad):
    with pytest.raises(ValueError):
        split_task_name(bad)


def test_train_with_download_starts_from_download():
    cmd = run_classify(task_proc_type="train", data_need_download=True, data_need_labeling=True)
    assert cmd.goto == "node_data_download"
    assert cmd.update == {"task_type": "DMS2.0", "task_func": "人头"}


def test_train_without_download_goes_to_labeling():
    cmd = run_classify(task_proc_type="train", data_need_download=False, data_need_labeling=True)
    assert cmd.goto == "node_data_labeling"


def test_train_without_labeling_skips_labeling():
    """这条是原实现的 bug：用户说不标注，代码仍然进 node_data_labeling。"""
    cmd = run_classify(task_proc_type="train", data_need_download=False, data_need_labeling=False)
    assert cmd.goto == "node_func_proc"


def test_eval_never_goes_to_labeling():
    cmd = run_classify(task_proc_type="eval", data_need_download=False, data_need_labeling=True)
    assert cmd.goto == "node_func_proc"


def test_model_cvt_goes_straight_to_func_proc():
    cmd = run_classify(task_proc_type="model_cvt", data_need_download=False, data_need_labeling=False)
    assert cmd.goto == "node_func_proc"


def test_bad_task_name_ends_with_readable_message():
    cmd = node_task_classify(
        {"task_name": "没有横杠", "task_proc_type": "eval", "data_need_download": False}
    )
    assert cmd.goto == END
    assert "任务分类失败" in cmd.update["task_proc_output"]


def test_unknown_task_type_ends_with_readable_message():
    cmd = node_task_classify(
        {"task_name": "DMS9.9-人头-测试", "task_proc_type": "eval", "data_need_download": False}
    )
    assert cmd.goto == END
    assert "任务分类失败" in cmd.update["task_proc_output"]
