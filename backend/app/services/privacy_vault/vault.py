"""
=========================================================================================
vault.py — Cryptographic Privacy Vault & AES-256-GCM Ephemeral Mapping Store
=========================================================================================

Tech Stack:
 - Cryptography (Hazmat primitives: AESGCM AEAD encryption)
 - Redis / Fakeredis (In-memory key-value cache with automatic TTL expiration)
 - Python Standard Library (os, json, datetime)

Key Architectural Responsibilities:
 1. Authenticated Encryption with Associated Data (AEAD):
    - Encrypts all original PII mappings using 256-bit AES-GCM.
    - Generates a unique 96-bit (12-byte) initialization vector (nonce) per entry.
    - Enforces tenant isolation by binding `org_id` and `request_id` as Additional
      Authenticated Data (AAD), mathematically preventing cross-tenant deciphering.

 2. Ephemeral Storage & Auto-Destruction:
    - Persists encrypted ciphertexts in Redis with an enforced Time-To-Live (TTL).
    - Mappings self-destruct after request completion (or max policy TTL, default 15m),
      complying with DPDP data minimization principles.

 3. Fail-Closed Resilience:
    - If vault connectivity or authentication verification fails, the pipeline immediately
      halts with `VaultUnavailableError`. Plaintext data is never held in an unencrypted state.
=========================================================================================
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import redis
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.gateway import VaultEntryMetadata

logger = get_logger(__name__)


class VaultUnavailableError(RuntimeError):
    """Raised when Redis or cryptographic vault operations fail (fail-closed)."""


class VaultEntryNotFoundError(KeyError):
    """Raised when a request-scoped mapping does not exist or has expired."""


def _build_redis_client(redis_url: str) -> redis.Redis:
    if redis_url.startswith("memory://"):
        settings = get_settings()
        if settings.ENVIRONMENT not in ("development", "test"):
            raise VaultUnavailableError(
                "In-memory vault (memory://) is prohibited in production/staging environments."
            )
        import fakeredis

        return fakeredis.FakeRedis(decode_responses=False)
    return redis.Redis.from_url(
        redis_url,
        decode_responses=False,
        socket_connect_timeout=2.0,
        socket_timeout=2.0,
    )


class PrivacyVault:
    """Engine 2B: AES-256-GCM encrypted temporary mapping store backed by Redis."""

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        settings = get_settings()
        self._key_bytes = settings.get_encryption_key_bytes()
        self._aesgcm = AESGCM(self._key_bytes)
        self._default_ttl = settings.MAPPING_TTL_SECONDS
        self._redis = redis_client or _build_redis_client(settings.REDIS_URL)

    @staticmethod
    def _vault_key(org_id: str, request_id: str) -> str:
        return f"pgw:vault:{org_id}:{request_id}"

    @staticmethod
    def _aad(org_id: str, request_id: str) -> bytes:
        return f"{org_id}|{request_id}".encode("utf-8")

    def health_check(self) -> bool:
        try:
            return bool(self._redis.ping())
        except Exception:
            return False

    def store_mappings_with_metadata(
        self,
        org_id: str,
        request_id: str,
        mappings: dict[str, dict[str, Any]],
        ttl_seconds: int | None = None,
    ) -> tuple[datetime, list[VaultEntryMetadata]]:
        """Encrypt and store placeholder -> original mapping scoped to (org_id, request_id),
        returning (expires_at, non-PII cryptographic proof metadata for each entry)."""
        ttl = ttl_seconds or self._default_ttl
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        aad_bytes = self._aad(org_id, request_id)
        aad_scope = f"{org_id}|{request_id}"

        metadata_list: list[VaultEntryMetadata] = []
        for placeholder, entry in mappings.items():
            entry_plaintext = json.dumps(
                {
                    "placeholder": placeholder,
                    "entity_type": entry.get("entity_type", "UNKNOWN"),
                    "original_value": entry.get("original_value", ""),
                    "pad": "0" * 16,
                },
                ensure_ascii=False,
            ).encode("utf-8")
            entry_nonce = os.urandom(12)
            entry_ct_and_tag = self._aesgcm.encrypt(entry_nonce, entry_plaintext, aad_bytes)
            ct_body = entry_ct_and_tag[:-16]
            auth_tag = entry_ct_and_tag[-16:]
            metadata_list.append(
                VaultEntryMetadata(
                    placeholder=placeholder,
                    entity_type=str(entry.get("entity_type", "UNKNOWN")),
                    nonce_hex=entry_nonce.hex(),
                    ciphertext_preview_hex=ct_body[:16].hex(),
                    auth_tag_hex=auth_tag.hex(),
                    aad_scope=aad_scope,
                    expires_at=expires_at,
                )
            )

        envelope = {
            "org_id": org_id,
            "request_id": request_id,
            "expires_at": expires_at.isoformat(),
            "mappings": mappings,
        }
        plaintext = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, aad_bytes)
        blob = nonce + ciphertext

        key = self._vault_key(org_id, request_id)
        try:
            self._redis.set(key, blob, ex=ttl)
        except Exception as exc:
            logger.error("vault_store_failed", request_id=request_id, org_id=org_id, error=str(exc))
            raise VaultUnavailableError(f"Privacy vault storage failed: {exc}") from exc
        return expires_at, metadata_list

    def store_mappings(
        self,
        org_id: str,
        request_id: str,
        mappings: dict[str, dict[str, Any]],
        ttl_seconds: int | None = None,
    ) -> datetime:
        """Backward-compatible wrapper returning only expires_at."""
        expires_at, _ = self.store_mappings_with_metadata(
            org_id=org_id,
            request_id=request_id,
            mappings=mappings,
            ttl_seconds=ttl_seconds,
        )
        return expires_at

    def load_mappings(self, org_id: str, request_id: str) -> dict[str, dict[str, Any]]:
        """Retrieve and decrypt request-scoped mappings. Enforces tenant & request isolation."""
        key = self._vault_key(org_id, request_id)
        try:
            blob = self._redis.get(key)
        except Exception as exc:
            logger.error("vault_read_failed", request_id=request_id, org_id=org_id, error=str(exc))
            raise VaultUnavailableError(f"Privacy vault lookup failed: {exc}") from exc

        if not blob:
            raise VaultEntryNotFoundError(f"Mapping missing or expired for request {request_id}")

        if len(blob) < 28:
            raise VaultUnavailableError("Corrupted vault ciphertext")

        nonce = blob[:12]
        ciphertext = blob[12:]
        try:
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, self._aad(org_id, request_id))
            envelope = json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            logger.error("vault_decrypt_failed", request_id=request_id, org_id=org_id, error=str(exc))
            raise VaultUnavailableError("Vault decryption or tenant AAD verification failed") from exc

        if envelope.get("org_id") != org_id or envelope.get("request_id") != request_id:
            raise VaultUnavailableError("Tenant or request scope mismatch")

        return envelope["mappings"]

    def delete_mappings(self, org_id: str, request_id: str) -> None:
        key = self._vault_key(org_id, request_id)
        try:
            self._redis.delete(key)
        except Exception as exc:
            logger.warning("vault_delete_failed", request_id=request_id, error=str(exc))


_vault_instance: PrivacyVault | None = None


def get_privacy_vault() -> PrivacyVault:
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = PrivacyVault()
    return _vault_instance


def set_privacy_vault(vault: PrivacyVault | None) -> None:
    """Allows injecting a test or custom vault instance."""
    global _vault_instance
    _vault_instance = vault
