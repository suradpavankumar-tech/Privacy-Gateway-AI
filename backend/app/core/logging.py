from __future__ import annotations

import logging
import re
from typing import Any

import structlog

_SENSITIVE_PATTERNS = [
    (re.compile(r"\b[2-9][0-9]{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b"), "[REDACTED_AADHAAR]"),
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), "[REDACTED_PAN]"),
    (re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"), "[REDACTED_GSTIN]"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "[REDACTED_API_KEY]"),
    (re.compile(r"sk-[A-Za-z0-9\-_]{20,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-_.]+"), "Bearer [REDACTED_TOKEN]"),
]

_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "secret",
    "token",
    "api_key",
    "authorization",
    "original_value",
    "raw_text",
    "encrypted_payload",
    "mapping_encryption_key",
    "gemini_api_key",
    "openai_api_key",
}


def _scrub_string(value: str) -> str:
    result = value
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def _scrub_value(val: Any) -> Any:
    if isinstance(val, str):
        return _scrub_string(val)
    if isinstance(val, dict):
        return {
            k: ("[REDACTED]" if str(k).lower() in _SENSITIVE_KEYS else _scrub_value(v))
            for k, v in val.items()
        }
    if isinstance(val, list):
        return [_scrub_value(item) for item in val]
    return val


def pii_scrubber_processor(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return _scrub_value(event_dict)


def configure_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            pii_scrubber_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)
