"""
=========================================================================================
openai_adapter.py — OpenAI Cloud LLM Provider Adapter
=========================================================================================

Tech Stack:
 - Python 3.11+ / Async HTTPX (Asynchronous HTTP client)
 - OpenAI REST API v1 (`/v1/chat/completions`, `gpt-4o-mini`)

Key Architectural Responsibilities:
 1. Standardized Chat Completion Integration:
    - Formats sanitized prompts and role history into OpenAI chat completion envelopes.

 2. Transport Boundary Compliance:
    - Invoked only after successful security ticket verification by the orchestrator.
    - Captures latency, token usage, and status codes for gateway performance metrics.
=========================================================================================
"""

from __future__ import annotations

import time
import httpx

from app.core.config import get_settings
from app.schemas.gateway import OutboundPayloadSchema
from app.services.llm.base import BaseLLMProvider, LLMGenerationResult, LLMProviderError


class OpenAIAdapter(BaseLLMProvider):
    """OpenAI Chat Completions REST adapter using verified sanitized payloads only."""

    name = "openai"

    def __init__(self) -> None:
        self._settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self._settings.OPENAI_API_KEY and self._settings.OPENAI_API_KEY.strip())

    def default_model(self) -> str:
        return self._settings.OPENAI_MODEL

    async def generate(self, payload: OutboundPayloadSchema) -> LLMGenerationResult:
        if not self.is_configured():
            raise LLMProviderError(
                "OPENAI_API_KEY is not configured on the server.",
                error_code="openai_not_configured",
                status_code=503,
            )

        model = payload.model or self.default_model()
        url = "https://api.openai.com/v1/chat/completions"

        messages = [{"role": "system", "content": payload.system_prompt}]
        for turn in payload.conversation_history:
            messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
        messages.append({"role": "user", "content": payload.user_prompt})

        body = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._settings.OPENAI_API_KEY.strip()}",
        }

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._settings.LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMProviderError("OpenAI API request timed out.", error_code="openai_timeout", status_code=504) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"OpenAI transport error: {type(exc).__name__}", error_code="openai_transport_error", status_code=502) from exc

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        if resp.status_code >= 400:
            detail = ""
            try:
                err_json = resp.json()
                detail = err_json.get("error", {}).get("message", "")
            except Exception:
                detail = resp.text[:200]
            raise LLMProviderError(
                f"OpenAI API returned HTTP {resp.status_code}: {detail}",
                error_code=f"openai_http_{resp.status_code}",
                status_code=502,
            )

        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise LLMProviderError("OpenAI returned no choices.", error_code="openai_empty_response", status_code=502)

        content = (choices[0].get("message") or {}).get("content", "").strip()
        usage = data.get("usage") or {}

        return LLMGenerationResult(
            provider=self.name,
            model=model,
            content=content,
            latency_ms=latency_ms,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
        )
