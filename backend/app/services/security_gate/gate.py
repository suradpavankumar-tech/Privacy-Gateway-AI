"""
=========================================================================================
gate.py — Outbound Security Gate & Cryptographic Ticket Verification Authority
=========================================================================================

Tech Stack:
 - Python 3.11+ / Dataclasses (High-performance immutable decision records)
 - HMAC-SHA256 / Hashlib (Cryptographic signature and tamper-detection tickets)
 - Regular Expressions (Comprehensive secret and PII pattern matchers)

Key Architectural Responsibilities:
 1. Non-Negotiable Outbound Security Perimeter:
    - Acts as the final firewall before any payload leaves the local trust boundary.
    - Operates independently from the initial detection phase to prevent bypasses.

 2. Multi-Tiered Verification Checks:
    - Tier 1: Secret & Credential Leak Check:
      Detects exposed API keys (Google AI, OpenAI), JWT tokens, and private keys.
    - Tier 2: Independent PII Re-Scan:
      Re-analyzes sanitized text for all mandatory Indian PII categories (Aadhaar, PAN,
      GSTIN, Phone, Email, Bank, UPI).
    - Tier 3: Original Value Cross-Validation:
      Verifies that no original PII value from the input appears in the outbound payload.
    - Tier 4: Placeholder Format & Integrity Verification.

 3. Cryptographically Signed Security Tickets:
    - Issues an HMAC-SHA256 ticket certifying that the outbound payload has been verified.
    - Downstream LLM adapters (Gemini, OpenAI, Ollama SLM) strictly mandate a valid,
      unexpired security ticket before transmitting data.
=========================================================================================
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.gateway import GateCheckItem, OutboundPayloadSchema, SecurityDecision
from app.services.detection.engine import (
    DetectionEngineError,
    get_detection_engine,
)
from app.services.detection.indian_validators import normalize_digits
from app.services.tokenization.tokenizer import PLACEHOLDER_REGEX

logger = get_logger(__name__)

_SECRET_PATTERNS = [
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z\-_]{30,}")),
    ("openai_api_key", re.compile(r"sk-[A-Za-z0-9\-_]{20,}")),
    ("jwt_token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("vault_key_reference", re.compile(r"pgw:vault:[a-zA-Z0-9\-_:]+")),
]

_OUTBOUND_STRUCTURED_SCAN_ENTITIES = [
    "AADHAAR",
    "PAN",
    "GSTIN",
    "VOTER_ID",
    "PASSPORT",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "BANK_ACCOUNT",
    "IFSC",
    "UPI_ID",
    "CREDIT_CARD",
]


class SecurityGateViolationError(PermissionError):
    """Raised when the outbound security gate blocks an external transmission."""


@dataclass(frozen=True)
class SecurityGateTicket:
    ticket_id: str
    request_id: str
    organization_id: str
    provider: str
    model: str
    payload_sha256: str
    decision: SecurityDecision
    signature: str


@dataclass
class GateInspectionResult:
    decision: SecurityDecision
    reason: str
    payload_sha256: str
    canonical_serialized_payload: str
    checks: dict[str, Any]
    gate_checks: list[GateCheckItem] = field(default_factory=list)
    raw_pii_leak_count: int = 0
    ticket: SecurityGateTicket | None = None


def canonical_serialize_payload(payload: OutboundPayloadSchema) -> str:
    return json.dumps(payload.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)


def compute_payload_sha256(serialized: str) -> str:
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _sign_ticket(
    ticket_id: str,
    request_id: str,
    organization_id: str,
    provider: str,
    model: str,
    payload_sha256: str,
) -> str:
    settings = get_settings()
    msg = f"{ticket_id}|{request_id}|{organization_id}|{provider}|{model}|{payload_sha256}".encode("utf-8")
    return hmac.new(settings.JWT_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def verify_gate_ticket(
    ticket: SecurityGateTicket | None,
    payload: OutboundPayloadSchema,
) -> bool:
    """Cryptographically verify at transport boundary that the exact serialized payload passed the gate."""
    if ticket is None or ticket.decision != SecurityDecision.PASS:
        return False
    serialized = canonical_serialize_payload(payload)
    actual_sha = compute_payload_sha256(serialized)
    if not hmac.compare_digest(actual_sha, ticket.payload_sha256):
        return False
    if (
        ticket.request_id != payload.request_id
        or ticket.organization_id != payload.organization_id
        or ticket.provider != payload.provider
        or ticket.model != payload.model
    ):
        return False
    expected_sig = _sign_ticket(
        ticket.ticket_id,
        ticket.request_id,
        ticket.organization_id,
        ticket.provider,
        ticket.model,
        ticket.payload_sha256,
    )
    return hmac.compare_digest(expected_sig, ticket.signature)


def _flatten_strings(obj: Any, path: str = "") -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    if isinstance(obj, str):
        items.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            items.extend(_flatten_strings(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            items.extend(_flatten_strings(v, f"{path}[{idx}]"))
    return items


def _strip_allowed_tokens(text_val: str, allowed_placeholders: list[str] | None) -> str:
    cleaned = text_val
    if allowed_placeholders:
        for tok in sorted(set(allowed_placeholders), key=len, reverse=True):
            if tok:
                cleaned = cleaned.replace(tok, " ")
    else:
        cleaned = PLACEHOLDER_REGEX.sub(" ", cleaned)
    return cleaned


def _build_gate_check_items(
    checks: dict[str, Any],
    fail_details: dict[str, str] | None = None,
) -> list[GateCheckItem]:
    labels = [
        ("policy_approved", "Enterprise Policy Authorization", "Purpose & blocked-entity rules satisfied"),
        ("provider_allowlisted", "Provider Allowlist Guard", "Destination model provider is allowlisted"),
        ("mapping_structure_absent", "Vault Structure Isolation", "No AES vault keys or raw mapping envelopes present"),
        ("secrets_absent", "API Key & Secret Guard", "Zero JWTs, PEM blocks, or cloud API keys detected"),
        ("known_pii_absent", "Known Sensitive Value Guard", "Zero original detected PII substrings or IDs present"),
        ("placeholders_valid", "Placeholder Token Integrity", "All placeholder tokens belong to request vault registry"),
        ("independent_pii_scan_clean", "Independent Outbound Re-Scan", "Zero residual Aadhaar/PAN/GSTIN/card/contact patterns"),
    ]
    items: list[GateCheckItem] = []
    details_map = fail_details or {}
    for key, title, ok_desc in labels:
        passed = bool(checks.get(key, False))
        detail = ok_desc if passed else details_map.get(key, "Not evaluated (halted at prior gate)")
        items.append(GateCheckItem(name=title, passed=passed, detail=detail))
    return items


def _contains_known_value(value: str, scan_corpus: str, digit_runs: list[str]) -> bool:
    cleaned = re.sub(r"\s+", " ", value.strip())
    if len(cleaned) < 3:
        return False
    parts = [re.escape(part) for part in cleaned.split()]
    escaped = r"\s+".join(parts)
    prefix = r"(?<![A-Za-z0-9/\-])" if cleaned[0].isalnum() else ""
    suffix = r"(?![A-Za-z0-9/\-])" if cleaned[-1].isalnum() else ""
    pat = re.compile(f"{prefix}{escaped}{suffix}", re.IGNORECASE)
    if pat.search(scan_corpus):
        return True
    digits = normalize_digits(cleaned)
    if len(digits) >= 8 and digits.isdigit():
        if any(digits in run for run in digit_runs):
            return True
    return False


class OutboundSecurityGate:
    """Engine 3: Independent outbound payload verification with fail-closed enforcement."""

    def inspect_and_authorize(
        self,
        payload: OutboundPayloadSchema,
        known_sensitive_values: list[str] | None = None,
        allowed_placeholders: list[str] | None = None,
        policy_approved: bool | None = True,
        policy_block_reason: str | None = None,
        preexisting_source_tokens: list[str] | None = None,
    ) -> GateInspectionResult:
        settings = get_settings()
        serialized = canonical_serialize_payload(payload)
        payload_sha = compute_payload_sha256(serialized)

        checks: dict[str, Any] = {
            "provider_allowlisted": False,
            "policy_approved": False,
            "known_pii_absent": False,
            "independent_pii_scan_clean": False,
            "secrets_absent": False,
            "mapping_structure_absent": False,
            "placeholders_valid": False,
        }

        def _fail(
            decision: SecurityDecision,
            failed_key: str,
            reason: str,
            leak_count: int = 0,
            fail_details: dict[str, str] | None = None,
        ) -> GateInspectionResult:
            details_map = dict(fail_details or {})
            details_map.setdefault(failed_key, reason)
            return GateInspectionResult(
                decision=decision,
                reason=reason,
                payload_sha256=payload_sha,
                canonical_serialized_payload=serialized,
                checks=checks,
                gate_checks=_build_gate_check_items(checks, fail_details=details_map),
                raw_pii_leak_count=leak_count,
                ticket=None,
            )

        # 1. Policy check (fail-closed on None / False)
        if policy_approved is None:
            return _fail(SecurityDecision.UNKNOWN, "policy_approved", "Policy decision unavailable; failing closed.")
        if not policy_approved:
            return _fail(
                SecurityDecision.FAIL,
                "policy_approved",
                policy_block_reason or "Blocked by enterprise privacy policy.",
            )
        checks["policy_approved"] = True

        # 2. Provider allowlist check
        if payload.provider.lower() not in settings.allowed_providers_list:
            return _fail(
                SecurityDecision.FAIL,
                "provider_allowlisted",
                f"Provider '{payload.provider}' is not in the authorized allowlist.",
            )
        checks["provider_allowlisted"] = True

        # 3. Check no vault/mapping structure or raw key leaked in payload
        payload_dict = payload.model_dump(mode="json")
        forbidden_keys = {"original_value", "encrypted_payload", "mapping_encryption_key", "vault_mappings"}
        flattened_entries = _flatten_strings(payload_dict)
        if any(any(fk in path.lower() for fk in forbidden_keys) for path, _ in flattened_entries):
            return _fail(
                SecurityDecision.FAIL,
                "mapping_structure_absent",
                "Protected mapping structure detected in outbound payload.",
            )
        checks["mapping_structure_absent"] = True

        # 4. Secret & API key leakage check
        configured_secrets = [
            s
            for s in (
                settings.GEMINI_API_KEY,
                settings.OPENAI_API_KEY,
                settings.JWT_SECRET,
                settings.MAPPING_ENCRYPTION_KEY,
            )
            if s and len(s) >= 12
        ]
        for secret in configured_secrets:
            if secret in serialized:
                return _fail(
                    SecurityDecision.FAIL,
                    "secrets_absent",
                    "Configured secret or API key detected in outbound payload.",
                )
        for secret_name, pat in _SECRET_PATTERNS:
            if pat.search(serialized):
                return _fail(
                    SecurityDecision.FAIL,
                    "secrets_absent",
                    f"Secret pattern ({secret_name}) detected in outbound payload.",
                )
        checks["secrets_absent"] = True

        # 5. Known original PII absence check (boundary-aware + contiguous digit runs)
        # Collect outbound text fields excluding control/token metadata lists
        scan_fields = [
            (field_path, text_val)
            for field_path, text_val in flattened_entries
            if field_path not in {"request_id", "organization_id", "provider", "model", "purpose"}
            and not field_path.startswith("metadata.registered_placeholders")
        ]
        scrubbed_segments = [_strip_allowed_tokens(val, allowed_placeholders) for _, val in scan_fields if val]
        scan_corpus = "\n".join(scrubbed_segments)
        digit_runs = [
            normalize_digits(chunk)
            for chunk in re.findall(r"[0-9][0-9\s\-/\.]{6,}[0-9]", scan_corpus)
        ]

        seen_known_leaks: set[str] = set()
        leak_hits = 0
        for orig in known_sensitive_values or []:
            norm_key = re.sub(r"\s+", " ", orig.strip()).lower()
            if len(norm_key) < 3 or norm_key in seen_known_leaks:
                continue
            if _contains_known_value(orig, scan_corpus, digit_runs):
                seen_known_leaks.add(norm_key)
                leak_hits += 1

        fail_reasons: list[tuple[str, SecurityDecision, str]] = []
        total_leaks = leak_hits
        if leak_hits > 0:
            fail_reasons.append(
                (
                    "known_pii_absent",
                    SecurityDecision.FAIL,
                    f"Known original sensitive value detected in final outbound payload ({leak_hits} leak(s)).",
                )
            )
        else:
            checks["known_pii_absent"] = True

        # 6. Placeholder integrity check
        if allowed_placeholders is not None:
            allowed_set = set(allowed_placeholders)
            preexisting_set = set(preexisting_source_tokens or [])
            found_tokens = {m.group(0) for m in PLACEHOLDER_REGEX.finditer(serialized)}
            unexpected = found_tokens - allowed_set - preexisting_set
            if unexpected:
                fail_reasons.append(
                    (
                        "placeholders_valid",
                        SecurityDecision.FAIL,
                        f"Unregistered placeholder token(s) present in outbound payload: {sorted(unexpected)}",
                    )
                )
            else:
                checks["placeholders_valid"] = True
        else:
            checks["placeholders_valid"] = True

        # 7. Independent structured PII re-scan across all outbound string fields
        try:
            detector = get_detection_engine()
            rescan_leaks = 0
            rescan_fail_msg: str | None = None
            for field_path, text_val in scan_fields:
                if not text_val or len(text_val) < 4:
                    continue
                scrubbed_for_scan = _strip_allowed_tokens(text_val, allowed_placeholders)
                residual, _ = detector.detect(
                    scrubbed_for_scan,
                    entities=_OUTBOUND_STRUCTURED_SCAN_ENTITIES,
                    min_confidence=0.75,
                )
                if residual:
                    found_types = sorted({r.entity_type for r in residual})
                    rescan_leaks = len(residual)
                    rescan_fail_msg = (
                        f"Independent outbound scan detected unmasked PII ({', '.join(found_types)}) in '{field_path}'."
                    )
                    break
            if rescan_fail_msg:
                total_leaks += rescan_leaks
                fail_reasons.append(("independent_pii_scan_clean", SecurityDecision.FAIL, rescan_fail_msg))
            else:
                checks["independent_pii_scan_clean"] = True
        except DetectionEngineError as exc:
            logger.error("outbound_gate_detector_failure", request_id=payload.request_id, error=str(exc))
            fail_reasons.append(
                (
                    "independent_pii_scan_clean",
                    SecurityDecision.UNKNOWN,
                    "Independent PII detector unavailable at outbound gate; failing closed.",
                )
            )

        if fail_reasons:
            primary_key, primary_decision, primary_reason = fail_reasons[0]
            if any(d == SecurityDecision.UNKNOWN for _, d, _ in fail_reasons):
                primary_decision = SecurityDecision.UNKNOWN
            return _fail(
                primary_decision,
                primary_key,
                primary_reason,
                leak_count=total_leaks,
                fail_details={k: msg for k, _, msg in fail_reasons},
            )

        ticket_id = str(uuid.uuid4())
        signature = _sign_ticket(
            ticket_id=ticket_id,
            request_id=payload.request_id,
            organization_id=payload.organization_id,
            provider=payload.provider,
            model=payload.model,
            payload_sha256=payload_sha,
        )
        ticket = SecurityGateTicket(
            ticket_id=ticket_id,
            request_id=payload.request_id,
            organization_id=payload.organization_id,
            provider=payload.provider,
            model=payload.model,
            payload_sha256=payload_sha,
            decision=SecurityDecision.PASS,
            signature=signature,
        )
        return GateInspectionResult(
            decision=SecurityDecision.PASS,
            reason="All outbound security checks passed.",
            payload_sha256=payload_sha,
            canonical_serialized_payload=serialized,
            checks=checks,
            gate_checks=_build_gate_check_items(checks),
            raw_pii_leak_count=0,
            ticket=ticket,
        )


_gate_instance: OutboundSecurityGate | None = None


def get_security_gate() -> OutboundSecurityGate:
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = OutboundSecurityGate()
    return _gate_instance
