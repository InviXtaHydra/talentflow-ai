import json
import time
from typing import TypeVar

import httpx
import ollama
from pydantic import BaseModel, ValidationError

from app.integrations.ai.base import AIOutputError, AIUnavailableError, ChatMessage, Usage

T = TypeVar("T", bound=BaseModel)


class OllamaProvider:
    """Local models through Ollama (official `ollama` SDK). CV data never leaves the machine."""

    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float) -> None:
        self.model = model
        self._client = ollama.Client(host=base_url, timeout=timeout)

    def _call(self, messages: list[dict[str, str]], *, fmt: dict | None, temperature: float) -> tuple[str, Usage]:
        started = time.monotonic()
        try:
            response = self._client.chat(
                model=self.model,
                messages=messages,
                format=fmt,
                think=False,
                options={"temperature": temperature, "num_ctx": 16384},
            )
        except (httpx.ConnectError, httpx.TimeoutException, ConnectionError) as exc:
            raise AIUnavailableError(str(exc)) from exc
        except ollama.ResponseError as exc:
            raise AIUnavailableError(f"Ollama error: {exc.error}") from exc
        usage = Usage(
            provider=self.name,
            model=self.model,
            prompt_tokens=response.prompt_eval_count,
            completion_tokens=response.eval_count,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return response.message.content or "", usage

    def generate_structured(self, *, system: str, user: str, schema: type[T], temperature: float = 0.2) -> tuple[T, Usage]:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        json_schema = schema.model_json_schema()
        last_error: Exception | None = None
        total = Usage(provider=self.name, model=self.model, prompt_tokens=0, completion_tokens=0)
        for _attempt in range(2):
            content, usage = self._call(messages, fmt=json_schema, temperature=temperature)
            total.prompt_tokens = (total.prompt_tokens or 0) + (usage.prompt_tokens or 0)
            total.completion_tokens = (total.completion_tokens or 0) + (usage.completion_tokens or 0)
            total.duration_ms += usage.duration_ms
            try:
                return schema.model_validate_json(content), total
            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                messages += [
                    {"role": "assistant", "content": content[:4000]},
                    {
                        "role": "user",
                        "content": "Your answer did not match the JSON schema. Return only valid JSON that matches the schema.",
                    },
                ]
        raise AIOutputError(str(last_error))

    def chat(self, *, system: str, messages: list[ChatMessage], temperature: float = 0.4) -> tuple[str, Usage]:
        payload = [{"role": "system", "content": system}, *({"role": m.role, "content": m.content} for m in messages)]
        return self._call(payload, fmt=None, temperature=temperature)


class OllamaEmbeddings:
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float) -> None:
        self.model = model
        self._client = ollama.Client(host=base_url, timeout=timeout)

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.embed(model=self.model, input=texts)
        except (httpx.ConnectError, httpx.TimeoutException, ConnectionError, ollama.ResponseError) as exc:
            raise AIUnavailableError(str(exc)) from exc
        return [list(vector) for vector in response.embeddings]
