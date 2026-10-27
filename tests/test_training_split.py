"""训练数据划分：固定种子、可复现。

原实现 `random.sample` 没有种子，同一批数据每次划分不同，
实验没法复现 —— 这条测试锁住种子行为。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.training import SPLIT_SEED, VAL_RATIO, TrainingRunner


def test_split_is_deterministic(fake_images: Path, tmp_path: Path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"

    TrainingRunner.gen_indices(fake_images, out_a)
    TrainingRunner.gen_indices(fake_images, out_b)

    assert (out_a / "train.txt").read_text() == (out_b / "train.txt").read_text()
    assert (out_a / "val.txt").read_text() == (out_b / "val.txt").read_text()


def test_split_ratio_and_containment(fake_images: Path, tmp_path: Path):
    out = tmp_path / "out"
    TrainingRunner.gen_indices(fake_images, out)

    train = (out / "train.txt").read_text().splitlines()
    val = (out / "val.txt").read_text().splitlines()

    assert len(train) == 20
    assert len(val) == max(1, 20 // VAL_RATIO)
    assert set(val) <= set(train), "val 必须来自 train 全集"
    # 路径是相对路径且不带后缀，与 cnn_result.txt 的约定一致
    assert all(not p.endswith(".jpg") for p in train)


def test_split_seed_is_stable_constant():
    """种子是公开常量，改它等于让历史实验不可复现 —— 变化必须是有意识的。"""
    assert SPLIT_SEED == 0


def test_empty_dir_does_not_crash(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    out = tmp_path / "out"
    TrainingRunner.gen_indices(empty, out)
    assert not (out / "train.txt").exists() or (out / "train.txt").read_text() == ""


def test_missing_prj_raises_readable_error():
    """HOD/安全带 没配 fcos 工程名，应当在构造时就给出人话错误。"""
    with pytest.raises(ValueError) as exc:
        TrainingRunner("eval", "HOD", "安全带")
    assert "未配置 fcos 工程名" in str(exc.value)
