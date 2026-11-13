from __future__ import annotations

import pytest
from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.entities import DetectedEntityAudit, OutboundAudit
from app.schemas.gateway import OutboundPayloadSchema, SecurityDecision
from app.services.detection.indian_validators import compute_verhoeff_check_digit
from app.services.llm.orchestrator import get_llm_orchestrator
from app.services.privacy_vault.vault import PrivacyVault, set_privacy_vault
from app.services.security_gate.gate import SecurityGateViolationError, get_security_gate


def _login(client, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.mark.parametrize("token_mode", ["cryptographic_random", "typed_sequential", "format_preserving"])
def test_end_to_end_process_zero_pii_leakage_all_modes(client, stub_gemini, token_mode: str):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    aadhaar = "56789012345" + compute_verhoeff_check_digit("56789012345")
    doc_text = (
        f"Applicant Name: Vikramaditya Kulkarni\n"
        f"Aadhaar Number: {aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:12]}\n"
        f"PAN Number: ABCPK5678R\n"
        f"Residential Address: Plot 27, Shanti Niketan Colony, Kothrud, Pune, Maharashtra - 411038\n"
    )

    resp = client.post(
        "/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": doc_text,
            "document_category": "loan_application",
            "purpose": "loan_underwriting",
            "tokenization_mode": token_mode,
            "provider": "gemini",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["security_decision"] == "PASS"
    assert data["raw_pii_leak_count"] == 0
    assert data["tokenization_mode"] == token_mode
    assert len(data["gate_checks"]) == 7
    assert all(chk["passed"] for chk in data["gate_checks"])
    assert len(data["vault_metadata"]) >= 4
    assert len(data["execution_trace"]) >= 5
    assert stub_gemini.called_count == 1

    sent_prompt = stub_gemini.last_payload.user_prompt
    assert "Vikramaditya Kulkarni" not in sent_prompt
    assert aadhaar[:4] not in sent_prompt
    assert "ABCPK5678R" not in sent_prompt
    assert "411038" not in sent_prompt

    assert "Vikramaditya Kulkarni" in data["final_response"]
    assert "ABCPK5678R" in data["final_response"]
    assert data["restoration"]["authorized"] is True
    assert data["restoration"]["restored_count"] >= 4

    with SessionLocal() as db:
        out_audit = db.scalar(select(OutboundAudit).where(OutboundAudit.request_id == data["request_id"]))
        assert out_audit is not None
        assert "Vikramaditya Kulkarni" not in out_audit.sanitized_payload_text
        assert "ABCPK5678R" not in out_audit.sanitized_payload_text
        entities = db.scalars(select(DetectedEntityAudit).where(DetectedEntityAudit.request_id == data["request_id"])).all()
        assert len(entities) >= 4
        for ent in entities:
            assert "Vikramaditya" not in ent.placeholder
            assert "ABCPK5678R" not in ent.placeholder


def test_tampered_outbound_payload_blocked_fail_closed(client, stub_gemini):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    resp = client.post(
        "/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": "Applicant Name: Neha Deshpande\nPAN: ABCPD4321K",
            "document_category": "loan_application",
            "purpose": "loan_underwriting",
            "provider": "gemini",
            "simulate_tampered_outbound": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["security_decision"] == "FAIL"
    assert data["status"] == "blocked_security_gate"
    assert data["raw_pii_leak_count"] >= 1
    assert stub_gemini.called_count == 0


def test_purpose_policy_blocks_aadhaar_for_marketing(client, stub_gemini):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    aadhaar = "67890123456" + compute_verhoeff_check_digit("67890123456")
    resp = client.post(
        "/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": f"Applicant Name: Arjun Malhotra\nAadhaar: {aadhaar}",
            "document_category": "kyc_document",
            "purpose": "marketing_analytics",
            "provider": "gemini",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["security_decision"] == "FAIL"
    assert data["status"] == "blocked_policy"
    assert stub_gemini.called_count == 0


def test_unauthorized_role_cannot_restore_and_dynamic_matrix_toggle(client, stub_gemini):
    analyst_token = _login(client, "analyst@bharatfin.in", "Analyst@2026!")
    resp = client.post(
        "/api/v1/process",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={
            "text": "Applicant Name: Deepika Joshi\nPAN: ABCPJ9988L",
            "document_category": "loan_application",
            "purpose": "loan_underwriting",
            "provider": "gemini",
            "restore_response": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["security_decision"] == "PASS"
    assert data["restoration"]["authorized"] is False
    assert data["restoration"]["restoration_status"] == "unauthorized_denied"
    assert "Deepika Joshi" not in data["final_response"]
    assert "ABCPJ9988L" not in data["final_response"]

    restore_resp = client.post(
        "/api/v1/restore",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"request_id": data["request_id"], "response_text": data["raw_llm_response"]},
    )
    assert restore_resp.status_code == 403

    # Admin enables 'analyst' in Role Restoration Matrix via PATCH -> analyst can now restore!
    admin_token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    pols = client.get("/api/v1/policies", headers={"Authorization": f"Bearer {admin_token}"}).json()
    loan_pol = next(p for p in pols if p["purpose"] == "loan_underwriting")
    patch_resp = client.patch(
        f"/api/v1/policies/{loan_pol['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"allow_restoration_roles": loan_pol["allow_restoration_roles"] + ["analyst"]},
    )
    assert patch_resp.status_code == 200

    restore_after = client.post(
        "/api/v1/restore",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"request_id": data["request_id"], "response_text": data["raw_llm_response"]},
    )
    assert restore_after.status_code == 200
    assert "Deepika Joshi" in restore_after.json()["restored_text"]


def test_local_slm_offline_fallback_and_forged_token_simulation(client):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    resp = client.post(
        "/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": "Applicant Name: Suresh Reddy\nPAN: ABCPR1122T",
            "document_category": "loan_application",
            "purpose": "loan_underwriting",
            "provider": "gemini",
            "enable_fallback": True,
            "simulate_provider_offline": True,
            "simulate_forged_token": True,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["fallback_triggered"] is True
    assert data["provider"] == "local_slm"
    assert data["model"] == "local-slm-indic-v1"
    assert "<PAN_FORGED99>" in data["restoration"]["unknown_or_forged_placeholders"]
    assert "Suresh Reddy" in data["final_response"]
    assert "ABCPR1122T" in data["final_response"]


def test_forged_placeholder_and_newly_generated_pii_handled_safely(client, stub_gemini):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    stub_gemini.next_response_fn = lambda p: (
        f"Reordered response: {p.user_prompt.splitlines()[-1]} | "
        f"Forged token: <PAN_FORGED> | Hallucinated PAN: ZZZZZ9999Z"
    )
    resp = client.post(
        "/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": "Applicant Name: Suresh Reddy\nPAN: ABCPR1122T",
            "document_category": "loan_application",
            "purpose": "loan_underwriting",
            "provider": "gemini",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "<PAN_FORGED>" in data["restoration"]["unknown_or_forged_placeholders"]
    assert "<PAN_FORGED>" in data["final_response"]
    assert data["restoration"]["newly_generated_pii_count"] >= 1
    assert "PAN" in data["restoration"]["newly_generated_pii_types"]


def test_redis_down_causes_fail_closed_503_and_blocks_llm(client, stub_gemini):
    class DownRedis:
        def set(self, *args, **kwargs):
            raise ConnectionError("Redis offline")

        def get(self, *args, **kwargs):
            raise ConnectionError("Redis offline")

        def ping(self):
            return False

    set_privacy_vault(PrivacyVault(redis_client=DownRedis()))  # type: ignore[arg-type]
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    resp = client.post(
        "/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": "Applicant Name: Meera Iyer\nPAN: ABCPI3344K",
            "document_category": "loan_application",
            "purpose": "loan_underwriting",
            "provider": "gemini",
        },
    )
    assert resp.status_code == 503
    assert stub_gemini.called_count == 0


@pytest.mark.asyncio
async def test_transport_boundary_rejects_unverified_or_modified_payload(stub_gemini):
    orch = get_llm_orchestrator()
    gate = get_security_gate()

    payload = OutboundPayloadSchema(
        request_id="req-t1",
        organization_id="org-1",
        provider="gemini",
        model="gemini-3.8-flash",
        purpose="loan_underwriting",
        system_prompt="System",
        user_prompt="Sanitized <PERSON_ABC123>",
    )
    with pytest.raises(SecurityGateViolationError):
        await orch.dispatch(payload, ticket=None)

    gate_res = gate.inspect_and_authorize(payload, allowed_placeholders=["<PERSON_ABC123>"])
    assert gate_res.decision == SecurityDecision.PASS
    mutated = payload.model_copy(update={"user_prompt": "Injected raw PAN ABCPK1234M"})
    with pytest.raises(SecurityGateViolationError):
        await orch.dispatch(mutated, ticket=gate_res.ticket)
    assert stub_gemini.called_count == 0
