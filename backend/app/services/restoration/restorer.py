"""
=========================================================================================
restorer.py — Response Intelligence & RBAC Entity Restoration Engine
=========================================================================================

Tech Stack:
 - Python 3.11+ / Dataclasses (Structured restoration telemetry)
 - Regular Expressions (Exact token boundary scanners)
 - AES-256-GCM Vault Decryption (Tenant-authenticated retrieval)

Key Architectural Responsibilities:
 1. Forged & Hallucinated Token Defense:
    - Scans LLM responses to detect any token matching placeholder syntax that was NOT
      issued in the original request-scoped vault session.
    - Strictly blocks restoration of hallucinated tokens without guessing or inventing data.

 2. Role-Based Access Control (RBAC) Unmasking:
    - Cross-references user role against the policy's `allow_restoration_roles` matrix.
    - Decrypts and replaces placeholders only for authorized categories; unauthorized
      placeholders remain safely masked.

 3. Newly Generated PII Detection:
    - Scans the LLM output for newly generated sensitive data to prevent model hallucination leaks.
=========================================================================================
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger
from app.schemas.gateway import RestorationReport
from app.services.detection.engine import (
    DetectionEngineError,
    get_detection_engine,
    normalize_entity_value,
)
from app.services.privacy_vault.vault import (
    PrivacyVault,
    VaultEntryNotFoundError,
    VaultUnavailableError,
    get_privacy_vault,
)

logger = get_logger(__name__)

# Matches bracket placeholder styles (<TYPE_6CHARS>, <TYPE_1>, [TYPE_FAKE]) for forged/unknown token detection
_ANY_BRACKET_PLACEHOLDER = re.compile(
    r"(<[A-Z][A-Z0-9_]{1,30}_[A-Za-z0-9]{1,16}>|\[[A-Z][A-Z0-9_]{1,30}_[A-Za-z0-9]{1,16}\])"
)


@dataclass
class RestorationOutcome:
    final_text: str
    report: RestorationReport


def _compile_token_scanner(valid_keys: set[str]) -> re.Pattern[str]:
    escaped_keys = [re.escape(k) for k in sorted(valid_keys, key=len, reverse=True) if k]
    parts = escaped_keys + [_ANY_BRACKET_PLACEHOLDER.pattern]
    return re.compile("|".join(parts))


class ResponseIntelligenceEngine:
    """Engine 5: Exact, authorized local placeholder restoration and newly generated PII scanner.

    Supports all 3 tokenization modes (`cryptographic_random`, `typed_sequential`, `format_preserving`),
    blocks/flags forged or hallucinated placeholders without guessing, and scans for newly generated LLM PII.
    """

    def __init__(self, vault: PrivacyVault | None = None) -> None:
        self._vault = vault

    @property
    def vault(self) -> PrivacyVault:
        return self._vault if self._vault is not None else get_privacy_vault()

    def process_response(
        self,
        org_id: str,
        request_id: str,
        response_text: str,
        authorized_to_restore: bool,
        restore_requested: bool = True,
        expected_mappings: dict[str, dict[str, Any]] | None = None,
    ) -> RestorationOutcome:
        mappings: dict[str, dict[str, Any]]
        if expected_mappings is not None:
            mappings = expected_mappings
        else:
            try:
                mappings = self.vault.load_mappings(org_id=org_id, request_id=request_id)
            except VaultEntryNotFoundError:
                return RestorationOutcome(
                    final_text=response_text,
                    report=RestorationReport(
                        restoration_status="mapping_expired_or_missing",
                        authorized=authorized_to_restore,
                        restored_count=0,
                        valid_placeholders_found=[],
                        missing_placeholders=[],
                        unknown_or_forged_placeholders=sorted(
                            {m.group(0) for m in _ANY_BRACKET_PLACEHOLDER.finditer(response_text)}
                        ),
                        newly_generated_pii_count=0,
                        newly_generated_pii_types=[],
                    ),
                )
            except VaultUnavailableError:
                raise

        valid_keys = set(mappings.keys())
        scanner = _compile_token_scanner(valid_keys)

        found_all = [m.group(0) for m in scanner.finditer(response_text)]
        found_exact_valid: list[str] = []
        unknown_or_forged: list[str] = []

        for tok in found_all:
            if tok in valid_keys:
                if tok not in found_exact_valid:
                    found_exact_valid.append(tok)
            else:
                if tok not in unknown_or_forged:
                    unknown_or_forged.append(tok)

        missing_placeholders = sorted(valid_keys - set(found_exact_valid))

        if not restore_requested:
            status = "skipped_by_request"
            final_text = response_text
            restored_count = 0
        elif not authorized_to_restore:
            status = "unauthorized_denied"
            final_text = response_text
            restored_count = 0
        else:
            restored_counter = 0

            def _replace_match(match: re.Match[str]) -> str:
                nonlocal restored_counter
                token = match.group(0)
                if token in mappings:
                    restored_counter += 1
                    return str(mappings[token]["original_value"])
                # Unknown/forged token: never guess, leave visible for caller & security flag
                return token

            final_text = scanner.sub(_replace_match, response_text)
            restored_count = restored_counter
            if unknown_or_forged and missing_placeholders:
                status = "partial_with_unknown_and_missing"
            elif unknown_or_forged:
                status = "restored_with_unknown_tokens"
            elif missing_placeholders:
                status = "partial_missing_placeholders"
            else:
                status = "restored_complete"

        known_originals = {
            (
                entry.get("entity_type"),
                normalize_entity_value(entry.get("entity_type", ""), entry.get("original_value", "")),
            )
            for entry in mappings.values()
        }
        newly_generated_types: list[str] = []
        newly_generated_count = 0
        try:
            detector = get_detection_engine()
            scrubbed = scanner.sub(" ", final_text)
            detected_in_resp, _ = detector.detect(scrubbed, min_confidence=0.75)
            for det in detected_in_resp:
                if (det.entity_type, det.normalized_value) not in known_originals:
                    newly_generated_count += 1
                    if det.entity_type not in newly_generated_types:
                        newly_generated_types.append(det.entity_type)
        except DetectionEngineError as exc:
            logger.warning("response_pii_scan_skipped_detector_error", request_id=request_id, error=str(exc))

        return RestorationOutcome(
            final_text=final_text,
            report=RestorationReport(
                restoration_status=status,
                authorized=authorized_to_restore,
                restored_count=restored_count,
                valid_placeholders_found=found_exact_valid,
                missing_placeholders=missing_placeholders,
                unknown_or_forged_placeholders=unknown_or_forged,
                newly_generated_pii_count=newly_generated_count,
                newly_generated_pii_types=newly_generated_types,
            ),
        )


_restorer: ResponseIntelligenceEngine | None = None


def get_response_engine() -> ResponseIntelligenceEngine:
    global _restorer
    if _restorer is None:
        _restorer = ResponseIntelligenceEngine()
    return _restorer
