""".env 载入：所有入口行为一致。

不加这层时，`.env` 只有 `langgraph dev` 会读（它自己解析 langgraph.json 的 "env"），
`scripts/run_demo.py` / pytest / 直接 import 全都读不到 —— 填了 key 只有一半地方生效。

@Time: 2026/10/19
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import os
from pathlib import Path

from config.env import load_env_file


def test_load_env_file_sets_variables(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("HOUZHUANG_TEST_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# 注释行\nHOUZHUANG_TEST_KEY=abc123\nQUOTED_KEY=\"带引号\"\n", encoding="utf-8"
    )

    loaded = load_env_file(env_file)

    assert loaded == env_file
    assert os.environ["HOUZHUANG_TEST_KEY"] == "abc123"
    assert os.environ["QUOTED_KEY"] == "带引号"
    monkeypatch.delenv("QUOTED_KEY", raising=False)


def test_load_env_file_does_not_override_existing(tmp_path: Path, monkeypatch):
    """真实环境变量优先级高于 .env —— 部署时才能用环境变量盖掉文件。"""
    monkeypatch.setenv("HOUZHUANG_TEST_KEY", "from-shell")
    env_file = tmp_path / ".env"
    env_file.write_text("HOUZHUANG_TEST_KEY=from-file\n", encoding="utf-8")

    load_env_file(env_file)

    assert os.environ["HOUZHUANG_TEST_KEY"] == "from-shell"


def test_load_env_file_missing_returns_none(tmp_path: Path):
    assert load_env_file(tmp_path / "不存在.env") is None


def test_project_env_file_is_loaded():
    """项目根有 .env 时，config.env 导入阶段就该载入它。"""
    from config import env

    assert env.ENV_FILE is None or env.ENV_FILE.name == ".env"
    assert env.ENV_FILE is None or env.ENV_FILE.exists()
