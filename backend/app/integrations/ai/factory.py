from functools import lru_cache

from app.core.config import get_settings
from app.integrations.ai.base import AINotConfiguredError, EmbeddingProvider, LLMProvider


@lru_cache
def _build_llm() -> LLMProvider | None:
    settings = get_settings()
    if settings.ai_provider == "ollama":
        from app.integrations.ai.ollama_provider import OllamaProvider

        return OllamaProvider(settings.ai_base_url, settings.ai_model, settings.ai_timeout_seconds)
    if settings.ai_provider == "openai":
        if not settings.ai_api_key:
            return None
        from app.integrations.ai.openai_provider import OpenAICompatibleProvider

        base_url = settings.ai_base_url if "11434" not in settings.ai_base_url else None
        return OpenAICompatibleProvider(settings.ai_api_key, settings.ai_model, base_url, settings.ai_timeout_seconds)
    if settings.ai_provider == "fake":
        from app.integrations.ai.fake import FakeProvider

        return FakeProvider()
    return None


@lru_cache
def _build_embeddings() -> EmbeddingProvider | None:
    settings = get_settings()
    if settings.embedding_provider == "ollama":
        from app.integrations.ai.ollama_provider import OllamaEmbeddings

        return OllamaEmbeddings(settings.ai_base_url, settings.embedding_model, 60)
    if settings.embedding_provider == "openai" and settings.ai_api_key:
        from app.integrations.ai.openai_provider import OpenAIEmbeddings

        return OpenAIEmbeddings(settings.ai_api_key, settings.embedding_model, None, 60)
    if settings.embedding_provider == "fake":
        from app.integrations.ai.fake import FakeEmbeddings

        return FakeEmbeddings(settings.embedding_dimensions)
    return None


def get_llm() -> LLMProvider:
    """The configured language model, or AINotConfiguredError with instructions to configure one."""
    provider = _build_llm()
    if provider is None:
        raise AINotConfiguredError("no LLM provider configured")
    return provider


def llm_configured() -> bool:
    return _build_llm() is not None


def get_embeddings() -> EmbeddingProvider | None:
    return _build_embeddings()


def reset_providers() -> None:
    _build_llm.cache_clear()
    _build_embeddings.cache_clear()
