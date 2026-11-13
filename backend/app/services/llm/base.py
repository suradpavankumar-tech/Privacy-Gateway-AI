from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.schemas.gateway import OutboundPayloadSchema


class LLMProviderError(RuntimeError):
    """Raised when an external LLM provider call fails or is misconfigured."""

    def __init__(self, message: str, error_code: str = "provider_error", status_code: int = 502) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


@dataclass
class LLMGenerationResult:
    provider: str
    model: str
    content: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0


class BaseLLMProvider(ABC):
    """Provider-independent interface for external and local LLM adapters."""

    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def default_model(self) -> str:
        ...

    @abstractmethod
    async def generate(self, payload: OutboundPayloadSchema) -> LLMGenerationResult:
        ...
