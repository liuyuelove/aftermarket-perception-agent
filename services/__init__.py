"""服务层：数据获取、预标注、训练调度、人在回路。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from . import annotation, dataset, human_interrupt, training
from .training import TrainingRunner

__all__ = ["annotation", "dataset", "human_interrupt", "training", "TrainingRunner"]
