from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMResponse:
    provider: str
    model: str
    text: str
    response_id: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    provider_name: str
    model: str

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
    ) -> LLMResponse: ...


class OpenAIProvider:
    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or getenv("OPENAI_API_KEY")
        self.model = model or getenv("OPENAI_MODEL", "gpt-5.6-terra")
        self._client = self._build_client()

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        input_payload: str | list[dict[str, Any]]
        if system:
            input_payload = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
        else:
            input_payload = prompt

        request_args: dict[str, Any] = {
            "model": self.model,
            "input": input_payload,
        }
        if temperature is not None:
            request_args["temperature"] = temperature

        response = self._client.responses.create(**request_args)
        usage = getattr(response, "usage", None)
        usage_payload: dict[str, int] = {}
        if usage is not None:
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                value = getattr(usage, key, None)
                if isinstance(value, int):
                    usage_payload[key] = value

        return LLMResponse(
            provider=self.provider_name,
            model=self.model,
            text=getattr(response, "output_text", "") or "",
            response_id=getattr(response, "id", None),
            usage=usage_payload,
        )

    def _build_client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - import error is environment specific
            raise RuntimeError(
                "The OpenAI provider requires the `openai` package. "
                "Install it and set OPENAI_API_KEY."
            ) from exc

        client_kwargs: dict[str, str] = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        return OpenAI(**client_kwargs)


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    name = (provider_name or getenv("LLM_PROVIDER", "openai")).strip().lower()
    if name in {"openai", "default"}:
        return OpenAIProvider()
    raise ValueError(f"Unsupported LLM provider: {name}")

