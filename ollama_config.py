"""主 Agent 的 ChatOllama 客户端；模型名与地址均可通过环境变量覆盖。"""
from __future__ import annotations

import os

from langchain_ollama import ChatOllama

# 与 .env.example 默认一致；改一处即可全局对齐
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"


def get_chat_ollama() -> ChatOllama:
    base = (os.getenv("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    model = os.getenv("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL
    temperature = float(os.getenv("OLLAMA_TEMPERATURE") or "0.1")
    return ChatOllama(model=model, base_url=base, temperature=temperature)
