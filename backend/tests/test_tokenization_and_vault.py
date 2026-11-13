from __future__ import annotations

import fakeredis
import pytest

from app.schemas.gateway import TokenizationMode
from app.services.detection.engine import get_detection_engine
from app.services.detection.indian_validators import compute_verhoeff_check_digit
from app.services.privacy_vault.vault import (
    PrivacyVault,
    VaultEntryNotFoundError,
    VaultUnavailableError,
)
from app.services.restoration.restorer import ResponseIntelligenceEngine
from app.services.tokenization.tokenizer import PLACEHOLDER_REGEX, TokenizerEngine


def test_consistent_tokenization_and_aes256_ciphertext_in_redis(reset_test_state):
    fake_redis: fakeredis.FakeRedis = reset_test_state
    vault = PrivacyVault(redis_client=fake_redis)
    tokenizer = TokenizerEngine(vault=vault)
    detector = get_detection_engine()

    aadhaar = "34567890123" + compute_verhoeff_check_digit("34567890123")
    text = f"Applicant Name: Priya Nair. Aadhaar: {aadhaar}. Confirming Priya Nair again."
    detections, _ = detector.detect(text)

    res = tokenizer.tokenize(org_id="org-1", request_id="req-1", text=text, detections=detections)
    assert "Priya Nair" not in res.sanitized_text
    assert aadhaar not in res.sanitized_text

    # Vault proof metadata must contain genuine 12-byte (24-hex) nonces & 16-byte (32-hex) GCM auth tags
    assert len(res.vault_metadata) >= 2
    for meta in res.vault_metadata:
        assert len(meta.nonce_hex) == 24
        assert len(meta.auth_tag_hex) == 32
        assert meta.aad_scope == "org-1|req-1"

    # Same entity repeated in request must receive the EXACT same placeholder
    person_tokens = [m.group(0) for m in PLACEHOLDER_REGEX.finditer(res.sanitized_text) if m.group(1) == "PERSON"]
    assert len(person_tokens) == 2
    assert person_tokens[0] == person_tokens[1]

    # Verify raw Redis value is AES-256-GCM encrypted and contains NO plaintext PII
    raw_blob = fake_redis.get("pgw:vault:org-1:req-1")
    assert raw_blob is not None
    assert b"Priya Nair" not in raw_blob
    assert aadhaar.encode("utf-8") not in raw_blob

    # Cross-tenant lookup MUST fail AAD verification
    with pytest.raises(VaultEntryNotFoundError):
        vault.load_mappings(org_id="org-2", request_id="req-1")

    fake_redis.set("pgw:vault:org-2:req-1", raw_blob)
    with pytest.raises(VaultUnavailableError):
        vault.load_mappings(org_id="org-2", request_id="req-1")


@pytest.mark.parametrize(
    "mode",
    [
        TokenizationMode.CRYPTOGRAPHIC_RANDOM,
        TokenizationMode.TYPED_SEQUENTIAL,
        TokenizationMode.FORMAT_PRESERVING,
    ],
)
def test_all_three_tokenization_modes_roundtrip_restoration(reset_test_state, mode: TokenizationMode):
    vault = PrivacyVault(redis_client=reset_test_state)
    tokenizer = TokenizerEngine(vault=vault)
    restorer = ResponseIntelligenceEngine(vault=vault)
    detector = get_detection_engine()

    aadhaar = "23456789012" + compute_verhoeff_check_digit("23456789012")
    text = f"Applicant Name: Aarav Sharma\nAadhaar Number: {aadhaar}\nPAN: ABCPK1234M"
    detections, _ = detector.detect(text)

    tok_res = tokenizer.tokenize(
        org_id="org-1",
        request_id=f"req-{mode.value}",
        text=text,
        detections=detections,
        mode=mode,
    )
    assert "Aarav Sharma" not in tok_res.sanitized_text
    assert aadhaar not in tok_res.sanitized_text
    assert "ABCPK1234M" not in tok_res.sanitized_text

    if mode == TokenizationMode.TYPED_SEQUENTIAL:
        assert "<PERSON_1>" in tok_res.sanitized_text
    elif mode == TokenizationMode.FORMAT_PRESERVING:
        assert "Applicant_1" in tok_res.sanitized_text

    outcome = restorer.process_response(
        org_id="org-1",
        request_id=f"req-{mode.value}",
        response_text=f"Approved for: {tok_res.sanitized_text}",
        authorized_to_restore=True,
        restore_requested=True,
    )
    assert outcome.report.restoration_status == "restored_complete"
    assert "Aarav Sharma" in outcome.final_text
    assert aadhaar in outcome.final_text
    assert "ABCPK1234M" in outcome.final_text


def test_user_supplied_placeholder_collision_avoided(reset_test_state):
    vault = PrivacyVault(redis_client=reset_test_state)
    tokenizer = TokenizerEngine(vault=vault)
    detector = get_detection_engine()

    text = "Applicant Name: Rohan Hegde. Attacker injected <PERSON_ABCDEF> and <PERSON_1>."
    detections, _ = detector.detect(text)
    res_seq = tokenizer.tokenize(
        org_id="org-1",
        request_id="req-coll-seq",
        text=text,
        detections=detections,
        mode=TokenizationMode.TYPED_SEQUENTIAL,
    )
    assert "<PERSON_1>" not in res_seq.placeholder_to_original
    assert "<PERSON_2>" in res_seq.placeholder_to_original


def test_redis_unavailable_fails_closed():
    class BrokenRedis:
        def set(self, *args, **kwargs):
            raise ConnectionError("Redis connection refused")

        def get(self, *args, **kwargs):
            raise ConnectionError("Redis connection refused")

        def ping(self):
            raise ConnectionError("Redis connection refused")

    broken_vault = PrivacyVault(redis_client=BrokenRedis())  # type: ignore[arg-type]
    tokenizer = TokenizerEngine(vault=broken_vault)
    detector = get_detection_engine()
    detections, _ = detector.detect("Applicant Name: Meera Iyer.")

    with pytest.raises(VaultUnavailableError):
        tokenizer.tokenize(
            org_id="org-1",
            request_id="req-fail",
            text="Applicant Name: Meera Iyer.",
            detections=detections,
        )
