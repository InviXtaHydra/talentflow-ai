import json
import time
from typing import TypeVar

import openai
from pydantic import BaseModel, ValidationError

from app.integrations.ai.base import AIOutputError, AIUnavailableError, ChatMessage, Usage

T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleProvider:
    """Any OpenAI-compatible chat API (official `openai` SDK): OpenAI, Azure OpenAI, Mistral, vLLM, ...

    Note: with a hosted provider, CV content is sent to that vendor. Check its data-processing terms and
    mention it in the privacy notice before enabling this (see docs/security.md)."""

    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None, timeout: float) -> None:
        self.model = model
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url or None, timeout=timeout, max_retries=1)

    def _complete(self, messages: list[dict[str, str]], *, json_mode: bool, temperature: float) -> tuple[str, Usage]:
        started = time.monotonic()
        try:
            response = self._client.chat.completions.create(  # type: ignore[call-overload]
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"} if json_mode else openai.NOT_GIVEN,
            )
        except (openai.APIConnectionError, openai.APITimeoutError, openai.RateLimitError, openai.InternalServerError) as exc:
            raise AIUnavailableError(str(exc)) from exc
        except openai.APIStatusError as exc:
            raise AIUnavailableError(f"Provider returned HTTP {exc.status_code}") from exc
        usage = Usage(
            provider=self.name,
            model=self.model,
            prompt_tokens=response.usage.prompt_tokens if response.usage else None,
            completion_tokens=response.usage.completion_tokens if response.usage else None,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return response.choices[0].message.content or "", usage

    def generate_structured(self, *, system: str, user: str, schema: type[T], temperature: float = 0.2) -> tuple[T, Usage]:
        system_with_schema = (
            f"{system}\n\nReturn only a JSON object that matches this JSON schema:\n{json.dumps(schema.model_json_schema())}"
        )
        messages = [{"role": "system", "content": system_with_schema}, {"role": "user", "content": user}]
        content, usage = self._complete(messages, json_mode=True, temperature=temperature)
        try:
            return schema.model_validate_json(content), usage
        except (ValidationError, json.JSONDecodeError) as exc:
            raise AIOutputError(str(exc)) from exc

    def chat(self, *, system: str, messages: list[ChatMessage], temperature: float = 0.4) -> tuple[str, Usage]:
        payload = [{"role": "system", "content": system}, *({"role": m.role, "content": m.content} for m in messages)]
        return self._complete(payload, json_mode=False, temperature=temperature)


class OpenAIEmbeddings:
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None, timeout: float) -> None:
        self.model = model
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url or None, timeout=timeout)

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.embeddings.create(model=self.model, input=texts)
        except openai.APIError as exc:
            raise AIUnavailableError(str(exc)) from exc
        return [item.embedding for item in response.data]
