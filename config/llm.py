"""
LLM 后端选择。

优先级：
  1. DEEPSEEK_API_KEY 有值        → DeepSeek（OpenAI 兼容协议）
  2. LLM_BASE_URL 有值            → 任意 OpenAI 兼容端点（vLLM / 自建网关）
  3. 兜底                         → 本地 Ollama

原 `ollama_config.py` 只实现了第 3 档，但主图注释与 langgraph.json 的
`langchain-openai` 依赖都表明第 1/2 档是设计意图，这里补齐。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from . import env

log = logging.getLogger("aftermarket.llm")

# 占位符特征：填了这些等于没填，避免首次运行就打到不存在的服务
_PLACEHOLDERS = ("your", "xxx", "<", "填入", "todo", "changeme", "sk-xxx")


def _usable(value: str) -> bool:
    """判断一个密钥/地址是否真的可用（排除空值与占位符）。"""
    if not value or not value.strip():
        return False
    low = value.strip().lower()
    return not any(marker in low for marker in _PLACEHOLDERS)


@lru_cache(maxsize=1)
def get_chat() -> BaseChatModel:
    """按优先级返回一个 Chat 模型实例（进程内缓存）。"""
    if _usable(env.DEEPSEEK_API_KEY):
        from langchain_openai import ChatOpenAI

        log.info("LLM 后端: DeepSeek (%s)", env.DEEPSEEK_MODEL)
        return ChatOpenAI(
            model=env.DEEPSEEK_MODEL,
            base_url=env.DEEPSEEK_BASE_URL,
            api_key=env.DEEPSEEK_API_KEY,
            temperature=env.LLM_TEMPERATURE,
            timeout=env.LLM_TIMEOUT,
        )

    if _usable(env.LLM_BASE_URL):
        from langchain_openai import ChatOpenAI

        log.info("LLM 后端: OpenAI 兼容端点 (%s @ %s)", env.LLM_MODEL, env.LLM_BASE_URL)
        return ChatOpenAI(
            model=env.LLM_MODEL,
            base_url=env.LLM_BASE_URL,
            api_key=env.LLM_API_KEY or "EMPTY",
            temperature=env.LLM_TEMPERATURE,
            timeout=env.LLM_TIMEOUT,
        )

    log.info("LLM 后端: Ollama (%s @ %s)", env.OLLAMA_MODEL, env.OLLAMA_BASE_URL)
    return get_chat_ollama()


def get_chat_ollama() -> BaseChatModel:
    """本地 Ollama 后端（保留原有配置语义）。"""
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=env.OLLAMA_MODEL,
        base_url=env.OLLAMA_BASE_URL.rstrip("/"),
        temperature=env.OLLAMA_TEMPERATURE,
    )


def backend_name() -> str:
    """当前会选中哪个后端（不实例化模型，供日志/健康检查用）。"""
    if _usable(env.DEEPSEEK_API_KEY):
        return "deepseek"
    if _usable(env.LLM_BASE_URL):
        return "openai-compatible"
    return "ollama"
