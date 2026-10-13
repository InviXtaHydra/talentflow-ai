"""Provider-independent AI interface.

Services ask for structured output (a Pydantic model) or a chat reply; which model or vendor answers
is configuration. Every structured response is validated against its schema before it is used."""

from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIError(Exception):
    code = "ai_error"
    user_message = "De AI-dienst gaf een fout. Probeer het later opnieuw."


class AINotConfiguredError(AIError):
    code = "ai_not_configured"
    user_message = (
        "Er is geen AI-model ingesteld. Zet AI_PROVIDER op 'ollama' (lokaal) of 'openai' (met AI_API_KEY) "
        "in het .env-bestand en herstart de API en de worker."
    )


class AIUnavailableError(AIError):
    code = "ai_unavailable"
    user_message = "De AI-dienst is niet bereikbaar. Controleer of Ollama draait (ollama serve) en probeer het opnieuw."


class AIOutputError(AIError):
    code = "ai_invalid_output"
    user_message = "Het AI-model gaf een antwoord dat niet aan de verwachte structuur voldoet. Probeer het opnieuw."


@dataclass
class Usage:
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    duration_ms: int = 0


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str


class LLMProvider(Protocol):
    name: str
    model: str

    def generate_structured(self, *, system: str, user: str, schema: type[T], temperature: float = 0.2) -> tuple[T, Usage]: ...

    def chat(self, *, system: str, messages: list[ChatMessage], temperature: float = 0.4) -> tuple[str, Usage]: ...


class EmbeddingProvider(Protocol):
    name: str
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def schema_for_prompt(schema: type[BaseModel]) -> dict[str, Any]:
    return schema.model_json_schema()
