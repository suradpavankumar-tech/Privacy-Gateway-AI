"""
=========================================================================================
config.py — Centralized Configuration, Security Posture & Environment Settings
=========================================================================================

Tech Stack:
 - Pydantic v2 / Pydantic-Settings (Strict schema validation and type parsing)
 - Python Standard Library (functools.lru_cache, base64)

Key Architectural Responsibilities:
 1. Environment Parsing & Decoupling:
    - Reads environment variables from `.env` files or container runtime environments.
    - Decouples operational settings (DB URLs, Redis, Log Level) from application logic.

 2. Cryptographic Key Ingestion & Validation:
    - Validates that `MAPPING_ENCRYPTION_KEY` provides exactly 256 bits (32 bytes) of entropy
      in base64 or hex format for AES-256-GCM vault operations.

 3. Production Security Hardening:
    - Rejects startup in `production` or `staging` if default developer JWT secrets,
      insecure AES keys, or in-memory stores are detected.

 4. Multi-Provider LLM & SLM Routing Parameters:
    - Configures provider endpoints, timeouts, and fallback toggles for Google Gemini,
      OpenAI, and local on-premise Ollama / Qwen 2.5 3B instances.
=========================================================================================
"""

from __future__ import annotations

import base64
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_DEFAULT = "dev-only-jwt-secret-replace-before-production-0001"
_DEV_AES_DEFAULT = "ZGV2LW9ubHktYWVzMjU2LWdjbS1rZXktMzJieXRlcw=="  # 32 bytes base64


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "Privacy Gateway AI"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"

    # Database & Redis
    DATABASE_URL: str = "sqlite+pysqlite:///./privacy_gateway.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & Encryption
    JWT_SECRET: str = Field(default=_DEV_JWT_DEFAULT, min_length=16)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 480
    MAPPING_ENCRYPTION_KEY: str = Field(default=_DEV_AES_DEFAULT, min_length=32)
    MAPPING_TTL_SECONDS: int = 900

    # External & Local LLM Providers
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    DEFAULT_LLM_PROVIDER: str = "gemini"
    ALLOWED_PROVIDERS: str = "gemini,openai,local_slm"
    ENABLE_LOCAL_SLM_FALLBACK: bool = True
    LLM_TIMEOUT_SECONDS: float = 45.0
    LLM_MAX_RETRIES: int = 1

    # Detection
    ENABLE_GLINER: bool = False
    SPACY_MODEL: str = "en_core_web_sm"

    # CORS & Rate Limiting
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    RATE_LIMIT_PER_MINUTE: int = 120

    @field_validator("MAPPING_ENCRYPTION_KEY")
    @classmethod
    def validate_aes_key(cls, value: str) -> str:
        raw: bytes | None = None
        try:
            decoded = base64.b64decode(value, validate=True)
            if len(decoded) == 32:
                raw = decoded
        except Exception:
            pass
        if raw is None:
            try:
                decoded = bytes.fromhex(value)
                if len(decoded) == 32:
                    raw = decoded
            except Exception:
                pass
        if raw is None:
            raise ValueError(
                "MAPPING_ENCRYPTION_KEY must be a base64-encoded 32-byte key or 64-char hex string for AES-256-GCM."
            )
        return value

    @model_validator(mode="after")
    def validate_production_posture(self) -> "Settings":
        if self.ENVIRONMENT in ("production", "staging"):
            if self.JWT_SECRET == _DEV_JWT_DEFAULT or "replace" in self.JWT_SECRET.lower():
                raise ValueError("Production/staging requires a non-default JWT_SECRET.")
            if self.MAPPING_ENCRYPTION_KEY == _DEV_AES_DEFAULT:
                raise ValueError("Production/staging requires a non-default MAPPING_ENCRYPTION_KEY.")
            if self.REDIS_URL.startswith("memory://"):
                raise ValueError("In-memory Redis (memory://) is forbidden outside development/test.")
        return self

    def get_encryption_key_bytes(self) -> bytes:
        try:
            decoded = base64.b64decode(self.MAPPING_ENCRYPTION_KEY, validate=True)
            if len(decoded) == 32:
                return decoded
        except Exception:
            pass
        return bytes.fromhex(self.MAPPING_ENCRYPTION_KEY)

    @property
    def allowed_providers_list(self) -> list[str]:
        return [p.strip().lower() for p in self.ALLOWED_PROVIDERS.split(",") if p.strip()]

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
