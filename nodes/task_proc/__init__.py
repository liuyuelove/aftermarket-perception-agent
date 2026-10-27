"""task_proc 子图节点。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from .classify import node_task_classify, split_task_name
from .download import node_data_download
from .func_proc import node_func_proc
from .labeling import node_data_labeling
from .train_data_gen import node_train_data_gen

__all__ = [
    "node_task_classify",
    "split_task_name",
    "node_data_download",
    "node_data_labeling",
    "node_train_data_gen",
    "node_func_proc",
]
