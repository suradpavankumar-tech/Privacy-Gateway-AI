from __future__ import annotations

from app.services.detection.engine import DetectionEngineError, get_detection_engine
from app.services.privacy_vault.vault import PrivacyVault, set_privacy_vault


def _login(client, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_detector_failure_causes_fail_closed_503(client, stub_gemini, monkeypatch):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    detector = get_detection_engine()

    def _broken_detect(*args, **kwargs):
        raise DetectionEngineError("Simulated local NER crash")

    monkeypatch.setattr(detector, "detect", _broken_detect)
    resp = client.post(
        "/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": "Applicant Name: Aarav Sharma\nPAN: ABCPK1234M",
            "document_category": "loan_application",
            "purpose": "loan_underwriting",
        },
    )
    assert resp.status_code == 503
    assert stub_gemini.called_count == 0


def test_expired_mapping_ttl_cannot_restore(client, reset_test_state):
    vault = PrivacyVault(redis_client=reset_test_state)
    set_privacy_vault(vault)
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")

    mask_resp = client.post(
        "/api/v1/mask",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "Applicant Name: Priya Nair\nPAN: ABCPN1234K", "ttl_seconds": 60},
    )
    assert mask_resp.status_code == 200
    req_id = mask_resp.json()["request_id"]
    sanitized = mask_resp.json()["sanitized_text"]

    reset_test_state.flushall()

    restore_resp = client.post(
        "/api/v1/restore",
        headers={"Authorization": f"Bearer {token}"},
        json={"request_id": req_id, "response_text": sanitized},
    )
    assert restore_resp.status_code == 200
    assert restore_resp.json()["report"]["restoration_status"] == "mapping_expired_or_missing"
    assert "Priya Nair" not in restore_resp.json()["restored_text"]


def test_governance_policies_dataset_audit_export_and_benchmark_api(client):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    headers = {"Authorization": f"Bearer {token}"}

    # Full 50-doc dataset endpoint
    ds_resp = client.get("/api/v1/dataset", headers=headers)
    assert ds_resp.status_code == 200
    ds = ds_resp.json()
    assert ds["total_documents"] == 50
    assert ds["total_annotations"] == 442
    assert ds["negative_control_count"] == 2

    # List & update policy via PUT
    pol_resp = client.get("/api/v1/policies", headers=headers)
    assert pol_resp.status_code == 200
    policies = pol_resp.json()
    assert len(policies) >= 5
    first_pol = policies[0]
    upd_resp = client.put(
        f"/api/v1/policies/{first_pol['id']}",
        headers=headers,
        json={"retention_days": 120},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["version"] == first_pol["version"] + 1

    # Run 50-doc benchmark via API with format_preserving mode
    eval_resp = client.post(
        "/api/v1/evaluation/run",
        headers=headers,
        json={"tokenization_mode": "format_preserving"},
    )
    assert eval_resp.status_code == 200
    rep = eval_resp.json()
    assert rep["total_documents"] == 50
    assert rep["outbound_leakage_count"] == 0
    assert rep["overall_f1"] >= 0.99
    assert len(rep["per_doc_results"]) == 50

    metrics_resp = client.get("/api/v1/metrics", headers=headers)
    assert metrics_resp.status_code == 200
    assert metrics_resp.json()["latest_evaluation"]["total_documents"] == 50

    csv_resp = client.get("/api/v1/audit/export?format=csv", headers=headers)
    assert csv_resp.status_code == 200
    assert "request_id,timestamp,user_role,purpose" in csv_resp.text
