"""测试公共配置。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _quiet_logging():
    """测试期间关掉 INFO 级日志，只保留 ERROR，避免输出被日志淹没。"""
    logging.disable(logging.WARNING)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture
def fake_images(tmp_path: Path) -> Path:
    """造 20 张假 jpg（内容是占位字节，只要后缀对就行）。"""
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    for i in range(20):
        (img_dir / f"{i:03d}.jpg").write_bytes(b"fake")
    return img_dir
