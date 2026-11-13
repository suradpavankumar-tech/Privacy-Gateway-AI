"""
=========================================================================================
orchestrator.py — Multi-Provider LLM Dispatcher & Transport Boundary Enforcement
=========================================================================================

Tech Stack:
 - Python 3.11+ / Asyncio (Non-blocking network dispatch and exponential backoff)
 - Security Gate HMAC Integration (Cryptographic transport tickets)
 - Pydantic (Strongly-typed outbound payload schemas)

Key Architectural Responsibilities:
 1. Provider-Agnostic Dispatch Architecture:
    - Normalizes interactions across disparate AI runtimes:
      * Google Gemini (`gemini-3.8-flash`)
      * OpenAI (`gpt-4o-mini`)
      * Local On-Premise SLM (`qwen2.5:3b-instruct` via Ollama)

 2. Zero-Bypass Transport Boundary:
    - Mandates a valid, cryptographically signed `SecurityGateTicket` with a matching
      payload SHA-256 hash before permitting any outbound transmission.
    - If a ticket is missing, forged, or unverified, dispatch is immediately blocked.

 3. Upstream Fault Tolerance:
    - Retries transient upstream network errors (502, 503, 504) with exponential backoff.
    - Re-validates the security ticket before every retry attempt.
=========================================================================================
"""

from __future__ import annotations

import asyncio
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.gateway import OutboundPayloadSchema, ProviderStatus
from app.services.llm.base import BaseLLMProvider, LLMGenerationResult, LLMProviderError
from app.services.llm.gemini_adapter import GeminiAdapter
from app.services.llm.local_slm_adapter import LocalSLMAdapter
from app.services.llm.openai_adapter import OpenAIAdapter
from app.services.security_gate.gate import (
    SecurityGateTicket,
    SecurityGateViolationError,
    verify_gate_ticket,
)

logger = get_logger(__name__)


class LLMOrchestrationEngine:
    """Engine 4: Provider-independent LLM dispatcher with strict transport-boundary ticket checks."""

    def __init__(self, providers: dict[str, BaseLLMProvider] | None = None) -> None:
        self._settings = get_settings()
        self._providers: dict[str, BaseLLMProvider] = providers or {
            "gemini": GeminiAdapter(),
            "openai": OpenAIAdapter(),
            "local_slm": LocalSLMAdapter(),
        }

    def register_provider(self, adapter: BaseLLMProvider) -> None:
        self._providers[adapter.name.lower()] = adapter

    def get_provider(self, provider_name: str) -> BaseLLMProvider:
        key = provider_name.strip().lower()
        if key not in self._settings.allowed_providers_list:
            raise SecurityGateViolationError(f"Provider '{provider_name}' is not allowlisted.")
        adapter = self._providers.get(key)
        if adapter is None:
            raise LLMProviderError(f"Unknown provider '{provider_name}'.", error_code="unknown_provider", status_code=400)
        return adapter

    def list_provider_statuses(self) -> list[ProviderStatus]:
        statuses: list[ProviderStatus] = []
        allowlist = set(self._settings.allowed_providers_list)
        for name, adapter in self._providers.items():
            configured = adapter.is_configured()
            allowlisted = name in allowlist
            status = "ready" if (configured and allowlisted) else ("unconfigured" if not configured else "blocked")
            statuses.append(
                ProviderStatus(
                    name=name,
                    configured=configured,
                    allowlisted=allowlisted,
                    default_model=adapter.default_model(),
                    status=status,
                )
            )
        return statuses

    async def dispatch(
        self,
        payload: OutboundPayloadSchema,
        ticket: SecurityGateTicket | None,
    ) -> LLMGenerationResult:
        """
        Transport boundary guard: refuses to dispatch unless the exact serialized
        payload holds a cryptographically valid PASS SecurityGateTicket.
        """
        if not verify_gate_ticket(ticket, payload):
            logger.error(
                "unverified_outbound_dispatch_blocked",
                request_id=payload.request_id,
                provider=payload.provider,
            )
            raise SecurityGateViolationError(
                "Outbound transmission blocked: payload lacks a valid PASS security gate ticket."
            )

        adapter = self.get_provider(payload.provider)
        max_attempts = 1 + max(0, self._settings.LLM_MAX_RETRIES)
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            if not verify_gate_ticket(ticket, payload):
                raise SecurityGateViolationError("Security gate ticket invalid before retry.")
            try:
                return await adapter.generate(payload)
            except LLMProviderError as exc:
                last_exc = exc
                if attempt < max_attempts and exc.status_code in (502, 503, 504):
                    await asyncio.sleep(0.4 * attempt)
                    continue
                raise

        assert last_exc is not None
        raise last_exc


_orchestrator: LLMOrchestrationEngine | None = None


def get_llm_orchestrator() -> LLMOrchestrationEngine:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LLMOrchestrationEngine()
    return _orchestrator
