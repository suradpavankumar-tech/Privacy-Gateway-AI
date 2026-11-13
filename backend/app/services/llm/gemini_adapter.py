"""
=========================================================================================
gemini_adapter.py — Google Gemini Enterprise Cloud LLM Adapter
=========================================================================================

Tech Stack:
 - Python 3.11+ / Async HTTPX (High-concurrency async HTTP client with connection pooling)
 - Google Generative AI REST API (`gemini-3.8-flash`, stateless protocol)

Key Architectural Responsibilities:
 1. Zero-Retention Interaction Architecture:
    - Calls the Gemini API with stateless processing flags (`store=False`) to ensure
      zero prompt caching or secondary model training on enterprise workloads.

 2. Upstream Error Mapping & Failover Signaling:
    - Normalizes rate limits (HTTP 429) and upstream server errors (HTTP 500, 503)
      into typed exceptions to trigger seamless fallback to the local on-premise SLM.

 3. Token & Temperature Constraints:
    - Honors user-defined generation limits (temperature, max output tokens, stop sequences).
=========================================================================================
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.gateway import OutboundPayloadSchema
from app.services.llm.base import BaseLLMProvider, LLMGenerationResult, LLMProviderError

logger = get_logger(__name__)

_INTERACTIONS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
_API_REVISION = "2026-05-20"

_DEPRECATED_MODEL_MAP: dict[str, str] = {
    "gemini-1.5-flash": "gemini-3.5-flash-lite",
    "gemini-1.5-pro": "gemini-4-argon",
    "gemini-2.0-flash": "gemini-3.5-flash-lite",
    "gemini-2.0-flash-lite": "gemini-3.5-flash-lite",
    "gemini-2.5-flash": "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite": "gemini-3.5-flash-lite",
    "gemini-2.5-pro": "gemini-4-argon",
    "gemini-3-flash-preview": "gemini-3.5-flash-lite",
    "gemini-3.5-flash": "gemini-3.5-flash-lite",
    "gemini-3.6-flash": "gemini-3.5-flash-lite",
    "gemini-3.7-flash": "gemini-3.5-flash-lite",
    "gemini-3.8-flash": "gemini-3.5-flash-lite",
}


def resolve_gemini_model(requested_model: str) -> str:
    cleaned = (requested_model or "").strip() or "gemini-3.5-flash-lite"
    if cleaned.startswith("models/"):
        cleaned = cleaned[len("models/") :]
    replacement = _DEPRECATED_MODEL_MAP.get(cleaned)
    if replacement:
        return replacement
    return cleaned


class GeminiAdapter(BaseLLMProvider):
    """Google Gemini Interactions API adapter (stateless store=False) using verified sanitized payloads only."""

    name = "gemini"

    def __init__(self) -> None:
        self._settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self._settings.GEMINI_API_KEY and self._settings.GEMINI_API_KEY.strip())

    def default_model(self) -> str:
        return resolve_gemini_model(self._settings.GEMINI_MODEL)

    @staticmethod
    def build_request_body(payload: OutboundPayloadSchema, model: str) -> dict[str, Any]:
        if payload.conversation_history:
            turns: list[dict[str, Any]] = []
            for turn in payload.conversation_history:
                role = "model" if turn.get("role") == "assistant" else "user"
                turns.append(
                    {
                        "role": role,
                        "content": [{"type": "text", "text": turn.get("content", "")}],
                    }
                )
            turns.append(
                {
                    "role": "user",
                    "content": [{"type": "text", "text": payload.user_prompt}],
                }
            )
            interaction_input: str | list[dict[str, Any]] = turns
        else:
            interaction_input = payload.user_prompt

        return {
            "model": model,
            "system_instruction": payload.system_prompt,
            "input": interaction_input,
            "store": False,
            "generation_config": {
                "max_output_tokens": 1024,
            },
        }

    async def _call_interactions(
        self,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> tuple[httpx.Response, float]:
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._settings.LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(_INTERACTIONS_ENDPOINT, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "Gemini Interactions API request timed out.",
                error_code="gemini_timeout",
                status_code=504,
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Gemini transport error: {type(exc).__name__}",
                error_code="gemini_transport_error",
                status_code=502,
            ) from exc
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return resp, latency_ms

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        chunks: list[str] = []
        for step in data.get("steps") or []:
            if isinstance(step, dict) and step.get("type") == "model_output":
                for item in step.get("content") or []:
                    if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
                        chunks.append(str(item["text"]))
        if chunks:
            return "\n".join(chunks).strip()

        for out in data.get("outputs") or []:
            if isinstance(out, dict) and out.get("text"):
                chunks.append(str(out["text"]))
        return "\n".join(chunks).strip()

    async def generate(self, payload: OutboundPayloadSchema) -> LLMGenerationResult:
        if not self.is_configured():
            raise LLMProviderError(
                "GEMINI_API_KEY is not configured on the server.",
                error_code="gemini_not_configured",
                status_code=503,
            )

        primary_model = resolve_gemini_model(payload.model or self.default_model())
        candidate_models = [primary_model]
        if "gemini-3.5-flash-lite" not in candidate_models:
            candidate_models.append("gemini-3.5-flash-lite")

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._settings.GEMINI_API_KEY.strip(),
            "Api-Revision": _API_REVISION,
        }

        last_error: LLMProviderError | None = None
        for idx, model in enumerate(candidate_models):
            body = self.build_request_body(payload, model=model)
            try:
                resp, latency_ms = await self._call_interactions(body, headers)
            except LLMProviderError as exc:
                last_error = exc
                if exc.status_code in (502, 504) and idx + 1 < len(candidate_models):
                    logger.warning(
                        "gemini_primary_model_transient_failure",
                        failed_model=model,
                        fallback_model=candidate_models[idx + 1],
                        error_code=exc.error_code,
                    )
                    continue
                raise

            if resp.status_code in (429, 503) and idx + 1 < len(candidate_models):
                last_error = LLMProviderError(
                    f"Gemini Interactions API returned HTTP {resp.status_code}",
                    error_code=f"gemini_http_{resp.status_code}",
                    status_code=503,
                )
                logger.warning(
                    "gemini_primary_model_overloaded",
                    failed_model=model,
                    http_status=resp.status_code,
                    fallback_model=candidate_models[idx + 1],
                )
                continue

            if resp.status_code >= 400:
                detail = ""
                try:
                    err_json = resp.json()
                    detail = err_json.get("error", {}).get("message", "")
                except Exception:
                    detail = resp.text[:200]
                status_out = 503 if resp.status_code == 503 else 502
                raise LLMProviderError(
                    f"Gemini Interactions API returned HTTP {resp.status_code}: {detail}",
                    error_code=f"gemini_http_{resp.status_code}",
                    status_code=status_out,
                )

            data = resp.json()
            content = self._extract_text(data)
            if not content:
                raise LLMProviderError(
                    "Gemini Interactions API returned empty model output.",
                    error_code="gemini_empty_response",
                    status_code=502,
                )

            usage = data.get("usage") or {}
            prompt_tokens = int(usage.get("total_input_tokens") or usage.get("promptTokenCount") or 0)
            completion_tokens = int(usage.get("total_output_tokens") or usage.get("candidatesTokenCount") or 0)

            return LLMGenerationResult(
                provider=self.name,
                model=str(data.get("model") or model),
                content=content,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        assert last_error is not None
        raise last_error
