from functools import lru_cache
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from reviewbot.config import settings


@lru_cache(maxsize=None)
def _model(provider: str, name: str, base_url: str | None = None) -> BaseChatModel:
    kwargs: dict[str, Any] = {"base_url": base_url} if base_url else {}
    return init_chat_model(name, model_provider=provider, **kwargs)


def _base_url(provider: str) -> str | None:
    return settings.ollama_base_url if provider == "ollama" else None


def agent_model() -> BaseChatModel:
    provider = settings.agent_model_provider
    return _model(provider, settings.agent_model_name, _base_url(provider))


def summarizer_model() -> BaseChatModel:
    provider = settings.summarizer_model_provider
    return _model(provider, settings.summarizer_model_name, _base_url(provider))


def judge_model() -> BaseChatModel:
    provider = settings.judge_model_provider
    return _model(provider, settings.judge_model_name, _base_url(provider))
