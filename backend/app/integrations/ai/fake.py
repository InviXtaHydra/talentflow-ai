"""Deterministic in-memory provider for automated tests only (APP_ENV=test, AI_PROVIDER=fake).

Tests register a response per output schema; nothing here is ever used by the running application."""

import hashlib
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from app.integrations.ai.base import AIUnavailableError, ChatMessage, Usage

T = TypeVar("T", bound=BaseModel)


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.structured: dict[type[BaseModel], Callable[[str, str], Any]] = {}
        self.chat_reply: Callable[[str, list[ChatMessage]], str] = lambda system, messages: "Testantwoord."
        self.unavailable = False
        self.calls: list[tuple[str, str]] = []

    def generate_structured(self, *, system: str, user: str, schema: type[T], temperature: float = 0.2) -> tuple[T, Usage]:
        if self.unavailable:
            raise AIUnavailableError("fake provider offline")
        self.calls.append((schema.__name__, user))
        factory = self.structured.get(schema)
        if factory is None:
            raise AssertionError(f"No fake response registered for {schema.__name__}")
        value = factory(system, user)
        result = value if isinstance(value, schema) else schema.model_validate(value)
        return result, Usage(provider=self.name, model=self.model, prompt_tokens=10, completion_tokens=10, duration_ms=1)

    def chat(self, *, system: str, messages: list[ChatMessage], temperature: float = 0.4) -> tuple[str, Usage]:
        if self.unavailable:
            raise AIUnavailableError("fake provider offline")
        self.calls.append(("chat", messages[-1].content if messages else ""))
        return self.chat_reply(system, messages), Usage(provider=self.name, model=self.model, duration_ms=1)


class FakeEmbeddings:
    name = "fake"
    model = "fake-embedding"

    def __init__(self, dimensions: int = 768) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vectors.append([(digest[i % len(digest)] - 128) / 128 for i in range(self.dimensions)])
        return vectors
