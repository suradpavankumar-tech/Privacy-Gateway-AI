# Security Test Report — Privacy Gateway AI

**Executed:** 2026-11-12  
**Automated Test Runner:** `backend\.venv\Scripts\pytest.exe backend\tests -v` (**17 passed**)  
**Live Stack Verification:** Executed against Docker Compose (`pgw-frontend`, `pgw-backend`, `pgw-postgres`, `pgw-redis`) via `http://127.0.0.1:5173` with real Gemini Interactions API (`store=False`).

## Security Verification Matrix

| Test ID | Attack / Failure Scenario | Expected Behavior | Observed Result |
|---|---|---|---|
| SEC-01 | Raw PII leakage in outbound payload | Gate returns `FAIL`, blocks LLM call; zero raw PII in provider wire payload | **PASS** (Unit + Live Gemini wire-body & `LOAN-001` checks: `outbound_leaks=[]`) |
| SEC-02 | Post-masking payload manipulation (`simulate_tampered_outbound=True` & post-ticket mutation) | Transport boundary gate detects mismatch/PII and blocks (`blocked_security_gate`) | **PASS** (Pytest + Live Docker API check) |
| SEC-03 | Unknown / forged placeholder & hallucinated PII in LLM response | Not restored; flagged in `unknown_or_forged_placeholders` & `newly_generated_pii_count` | **PASS** (`test_forged_placeholder_and_newly_generated_pii_handled_safely`) |
| SEC-04 | Live Redis container stopped (`docker stop pgw-redis`) | Health reports `degraded`/`redis_vault: down`; `/api/v1/process` returns `503` fail-closed | **PASS** (Pytest + Live `docker stop pgw-redis` test) |
| SEC-05 | Local PII detector unavailable / exception | Fail-closed (`503`); no external LLM call made | **PASS** (`test_detector_failure_causes_fail_closed_503`) |
| SEC-06 | Policy unavailable / unknown security status (`policy_approved=None`) | Gate returns `UNKNOWN` and blocks outbound transmission | **PASS** (`run_benchmark_suite` fail-closed check #2) |
| SEC-07 | Cross-tenant restoration / vault decryption attempt | Rejected via AAD verification & tenant isolation | **PASS** (`test_consistent_tokenization_and_aes256_ciphertext_in_redis`) |
| SEC-08 | Unauthorized role (`analyst`) attempting PII restoration | Denied (`unauthorized_denied` in `/process`, `403` on `/restore`) | **PASS** (Pytest + Live Docker API `403` check) |
| SEC-09 | Expired mapping TTL restoration attempt | Denied (`mapping_expired_or_missing`); placeholders stay masked | **PASS** (`test_expired_mapping_ttl_cannot_restore`) |
| SEC-10 | Raw PII absence in live Redis ciphertext and PostgreSQL audit tables | Zero raw PII substrings in live Redis blobs (`2898` bytes, `TTL=879s`) or DB audit records | **PASS** (Pytest + Live `pgw-redis` + `pgw-postgres` audit inspection) |
| SEC-11 | User-supplied placeholder collision (`<PERSON_ABCDEF>` in input) | Collision avoided; attacker token cannot hijack vault | **PASS** (`test_user_supplied_placeholder_collision_avoided`) |
| SEC-12 | Unapproved provider / purpose-blocked entity (`AADHAAR` in `marketing_analytics`) | Blocked by allowlist / policy before LLM call (`blocked_policy`) | **PASS** (Pytest + Live Docker API check) |
