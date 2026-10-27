"""数据获取：本地复用必须能认出「这是不是同一个任务的数据」。

原实现只看 `ftp_data` 里有没有文件，有就复用 —— A 任务会悄悄拿 B 任务的数据训练，
产出的指标看着还挺正常。这条测试锁住「先比对任务名」的行为。

@Time: 2026/10/19
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import env
from services import dataset

TASK = "DMS2.0-人头-易甲文-NT98323-测试"


@pytest.fixture
def ftp_dir(tmp_path: Path, monkeypatch):
    """把 ftp_data 指到临时目录，并清空 DATA_SERVER_URL。"""
    d = tmp_path / "ftp_data"
    d.mkdir()
    monkeypatch.setattr(env, "FTP_DATA_DIR", d)
    monkeypatch.setattr(env, "DATA_SERVER_URL", "")
    return d


def test_matches_task_by_full_name():
    assert dataset.matches_task("DMS2.0-人头-易甲文-NT98323-测试.rar", TASK)


def test_matches_task_by_segment():
    """文件名通常只带项目/任务片段，按段匹配。"""
    assert dataset.matches_task("NT323_MS_人头_V1.0.0.rar", TASK)
    assert dataset.matches_task("DMS2.0_某批数据.zip", TASK)


def test_not_matching_unrelated_archive():
    assert not dataset.matches_task("NT323_MS_闭眼误报_V1.0.0.62.2_T20251020.rar", TASK)


def test_empty_local_dir_fails(ftp_dir: Path):
    assert dataset.download(TASK) is False


def test_reuse_matching_archive(ftp_dir: Path):
    (ftp_dir / "NT323_人头_T20251020.rar").write_bytes(b"x")
    assert dataset.download(TASK) is True


def test_reuse_mismatched_is_refused_in_strict_mode(ftp_dir: Path, monkeypatch):
    (ftp_dir / "NT323_MS_闭眼误报_V1.0.0.62.2_T20251020.rar").write_bytes(b"x")
    monkeypatch.setattr(env, "DATA_REUSE_STRICT", True)
    assert dataset.download(TASK) is False


def test_reuse_mismatched_is_allowed_but_warned_in_lenient_mode(
    ftp_dir: Path, monkeypatch, caplog
):
    """默认（非严格）仍然放行，但必须把「数据对不上」喊出来。"""
    import logging

    logging.disable(logging.NOTSET)  # conftest 默认关了日志，这里要收警告
    caplog.set_level(logging.WARNING)

    (ftp_dir / "NT323_MS_闭眼误报_V1.0.0.62.2_T20251020.rar").write_bytes(b"x")
    monkeypatch.setattr(env, "DATA_REUSE_STRICT", False)

    assert dataset.download(TASK) is True
    assert any("对不上" in r.getMessage() for r in caplog.records)
