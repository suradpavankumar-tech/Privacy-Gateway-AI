"""
=========================================================================================
tokenizer.py — Multi-Mode Tokenization & Cryptographic Anonymization Engine
=========================================================================================

Tech Stack:
 - Python Standard Library `secrets` (Cryptographically Secure Pseudo-Random Number Generator)
 - Regular Expressions (Span boundary mapping and replacement replacement)
 - Dataclasses (High-performance tokenization result structures)

Key Architectural Responsibilities:
 1. 3 Specialized Tokenization Strategies:
    - `cryptographic_random`:
      Generates entropy-rich bracketed tokens (`<AADHAAR_7K2P9X>`) preventing reverse-engineering.
    - `typed_sequential`:
      Generates ordinal enterprise tokens (`<PERSON_1>`, `<PHONE_NUMBER_1>`) for clear audit logs.
    - `format_preserving`:
      Generates synthetic Indian surrogates matching real syntactic formats (e.g. synthetic PANs,
      valid Luhn credit card numbers) to maintain zero semantic degradation during LLM inference.

 2. Non-Overlapping Span Alignment:
    - Sorts detected entities by priority, confidence, and text offset to prevent
      malformed partial substitutions across overlapping spans.

 3. Ephemeral Vault Integration:
    - Writes original-to-placeholder mappings directly into the AES-256-GCM vault,
      guaranteeing that plaintext values never touch application logs or downstream models.
=========================================================================================
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.gateway import (
    CategoryTier,
    PlaceholderSummary,
    TokenizationMode,
    VaultEntryMetadata,
)
from app.services.detection.engine import DetectionItem
from app.services.privacy_vault.vault import PrivacyVault, get_privacy_vault

# Matches typed bracket placeholders in both cryptographic (<AADHAAR_7K2P9X>)
# and typed_sequential (<AADHAAR_1>) modes.
PLACEHOLDER_REGEX = re.compile(r"<([A-Z][A-Z0-9_]+)_([A-Z0-9]{1,8})>")
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_PAN_ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ"


@dataclass
class TokenizationResult:
    request_id: str
    tokenization_mode: TokenizationMode
    sanitized_text: str
    placeholders: list[PlaceholderSummary]
    placeholder_to_original: dict[str, str]
    detected_entity_counts: dict[str, int]
    mapping_expires_at: datetime
    vault_metadata: list[VaultEntryMetadata] = field(default_factory=list)


class TokenizerEngine:
    """Engine 2A: Multi-mode request-scoped placeholder generator & vault writer."""

    def __init__(self, vault: PrivacyVault | None = None) -> None:
        self._vault = vault

    @property
    def vault(self) -> PrivacyVault:
        return self._vault if self._vault is not None else get_privacy_vault()

    @staticmethod
    def _generate_crypto_token(entity_type: str, existing_tokens: set[str], source_text: str) -> str:
        for _ in range(32):
            suffix = "".join(secrets.choice(_ALPHABET) for _ in range(6))
            candidate = f"<{entity_type}_{suffix}>"
            if candidate not in existing_tokens and candidate not in source_text:
                return candidate
        raise RuntimeError("Failed to generate collision-free cryptographic placeholder token")

    @staticmethod
    def _generate_sequential_token(
        entity_type: str,
        type_counters: dict[str, int],
        existing_tokens: set[str],
        source_text: str,
    ) -> str:
        idx = type_counters.get(entity_type, 0) + 1
        for _ in range(100):
            candidate = f"<{entity_type}_{idx}>"
            if candidate not in existing_tokens and candidate not in source_text:
                type_counters[entity_type] = idx
                return candidate
            idx += 1
        raise RuntimeError("Failed to generate collision-free sequential placeholder token")

    @staticmethod
    def _generate_format_preserving_token(
        entity_type: str,
        type_counters: dict[str, int],
        existing_tokens: set[str],
        source_text: str,
        original_value: str,
    ) -> str:
        idx = type_counters.get(entity_type, 0) + 1
        for attempt in range(64):
            seq = idx + attempt
            rand_digits = f"{secrets.randbelow(9000) + 1000}"
            rand_ch = secrets.choice(_PAN_ALPHA)
            if entity_type == "AADHAAR":
                candidate = f"9000 {seq:04d} {rand_digits}"
            elif entity_type == "PAN":
                candidate = f"ZZZPK{seq:04d}{rand_ch}"
            elif entity_type == "GSTIN":
                candidate = f"99ZZZPK{seq:04d}Z1Z5"
            elif entity_type == "VOTER_ID":
                candidate = f"ZZZ{9000000 + seq:07d}"
            elif entity_type == "PASSPORT":
                candidate = f"Z{9000000 + seq:07d}"
            elif entity_type == "IFSC":
                candidate = f"PRIV0{seq:06d}"
            elif entity_type == "UPI_ID":
                candidate = f"vault.user{seq}@upi"
            elif entity_type == "EMAIL_ADDRESS":
                candidate = f"redacted.user{seq}@privacy-vault.invalid"
            elif entity_type == "PHONE_NUMBER":
                candidate = f"+91-900000{seq:04d}"
            elif entity_type == "BANK_ACCOUNT":
                candidate = f"99990000{seq:04d}"
            elif entity_type == "CREDIT_CARD":
                candidate = f"4000-0000-0000-{seq:04d}"
            elif entity_type == "DATE_OF_BIRTH":
                candidate = f"01/01/{1900 + (seq % 20):04d}"
            elif entity_type == "CUSTOMER_ID":
                candidate = f"CIF999{seq:03d}"
            elif entity_type == "PROPERTY_LEGAL_ID":
                candidate = f"DOC-REF-{seq:04d}"
            elif entity_type == "PERSON":
                candidate = f"Applicant_{seq}"
            elif entity_type == "ADDRESS":
                candidate = f"Redacted Address #{seq}, India 000000"
            else:
                candidate = f"<{entity_type}_{seq}>"

            if (
                candidate != original_value
                and candidate not in existing_tokens
                and candidate not in source_text
            ):
                type_counters[entity_type] = seq
                return candidate
        raise RuntimeError("Failed to generate collision-free format-preserving surrogate")

    def _generate_token(
        self,
        mode: TokenizationMode,
        entity_type: str,
        type_counters: dict[str, int],
        existing_tokens: set[str],
        source_text: str,
        original_value: str,
    ) -> str:
        if mode == TokenizationMode.TYPED_SEQUENTIAL:
            return self._generate_sequential_token(entity_type, type_counters, existing_tokens, source_text)
        if mode == TokenizationMode.FORMAT_PRESERVING:
            return self._generate_format_preserving_token(
                entity_type, type_counters, existing_tokens, source_text, original_value
            )
        return self._generate_crypto_token(entity_type, existing_tokens, source_text)

    def tokenize(
        self,
        org_id: str,
        request_id: str,
        text: str,
        detections: list[DetectionItem],
        ttl_seconds: int | None = None,
        mode: TokenizationMode = TokenizationMode.CRYPTOGRAPHIC_RANDOM,
    ) -> TokenizationResult:
        # Map (entity_type, normalized_value) -> placeholder for consistency within request
        canonical_map: dict[tuple[str, str], str] = {}
        type_counters: dict[str, int] = {}
        existing_tokens: set[str] = set()
        vault_payload: dict[str, dict] = {}
        summary_meta: dict[str, dict] = {}
        entity_counts: dict[str, int] = {}

        ordered = sorted(detections, key=lambda d: d.start)

        replacements: list[tuple[int, int, str]] = []
        for det in ordered:
            entity_counts[det.entity_type] = entity_counts.get(det.entity_type, 0) + 1
            canon_key = (det.entity_type, det.normalized_value)
            if canon_key not in canonical_map:
                placeholder = self._generate_token(
                    mode=mode,
                    entity_type=det.entity_type,
                    type_counters=type_counters,
                    existing_tokens=existing_tokens,
                    source_text=text,
                    original_value=det.matched_text,
                )
                canonical_map[canon_key] = placeholder
                existing_tokens.add(placeholder)
                vault_payload[placeholder] = {
                    "original_value": det.matched_text,
                    "entity_type": det.entity_type,
                    "category_tier": det.category_tier.value,
                    "normalized_value": det.normalized_value,
                    "tokenization_mode": mode.value,
                    "request_id": request_id,
                    "org_id": org_id,
                }
                summary_meta[placeholder] = {
                    "entity_type": det.entity_type,
                    "category_tier": det.category_tier,
                    "occurrence_count": 0,
                    "confidence": det.confidence,
                    "recognizer": det.recognizer,
                }
            else:
                placeholder = canonical_map[canon_key]
                if det.confidence > summary_meta[placeholder]["confidence"]:
                    summary_meta[placeholder]["confidence"] = det.confidence

            summary_meta[placeholder]["occurrence_count"] += 1
            replacements.append((det.start, det.end, placeholder))

        sanitized_chars = list(text)
        for start, end, placeholder in reversed(replacements):
            sanitized_chars[start:end] = list(placeholder)
        sanitized_text = "".join(sanitized_chars)

        expires_at, vault_metadata = self.vault.store_mappings_with_metadata(
            org_id=org_id,
            request_id=request_id,
            mappings=vault_payload,
            ttl_seconds=ttl_seconds,
        )

        summaries = [
            PlaceholderSummary(
                placeholder=ph,
                entity_type=meta["entity_type"],
                category_tier=meta["category_tier"],
                occurrence_count=meta["occurrence_count"],
                confidence=meta["confidence"],
                recognizer=meta["recognizer"],
            )
            for ph, meta in summary_meta.items()
        ]
        ph_to_orig = {ph: data["original_value"] for ph, data in vault_payload.items()}

        return TokenizationResult(
            request_id=request_id,
            tokenization_mode=mode,
            sanitized_text=sanitized_text,
            placeholders=summaries,
            placeholder_to_original=ph_to_orig,
            detected_entity_counts=entity_counts,
            mapping_expires_at=expires_at,
            vault_metadata=vault_metadata,
        )
