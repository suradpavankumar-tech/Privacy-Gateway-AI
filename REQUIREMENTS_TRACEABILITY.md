# Requirements Traceability Matrix — Privacy Gateway AI (MINEARENA 1.0 PS-02)

**Source of Truth:** Official MINEARENA 1.0 PS-02 PDF (*PS-02: DPDP-Ready Privacy Gateway for Enterprise LLMs*) + Master Implementation Specification.

## A. Official Mandatory Requirements (PS-02 PDF)

| ID | Requirement | Implemented Module | Verification Method & Scope | Status |
|---|---|---|---|---|
| **PS02-1** | Local PII detection layer using Microsoft Presidio | `backend/app/services/detection/engine.py` | Pytest unit suite + 50-doc benchmark (`1.000` P/R/F1) | **Completed** |
| **PS02-2** | India-specific recognizers: Aadhaar, PAN, GSTIN, Voter ID, Passport | `backend/app/services/detection/indian_recognizers.py`, `indian_validators.py` | Pytest Verhoeff/Mod-36/Luhn/format tests | **Completed** |
| **PS02-3** | Local NER / SLM for PERSON and ADDRESS in Indian English & code-mixed text | `backend/app/services/detection/indian_recognizers.py`, `engine.py` | spaCy NER + Indian context/address recognizers + 50-doc benchmark | **Completed** |
| **PS02-4** | Consistent typed placeholders within request scope (`<PERSON_...>`, `<AADHAAR_...>`, etc.) | `backend/app/services/tokenization/tokenizer.py` | Repeat-entity consistency & collision tests | **Completed** |
| **PS02-5** | Secure local mapping between placeholders and original values | `backend/app/services/privacy_vault/vault.py` | AES-256-GCM + AAD + TTL tests (verified against `fakeredis`) | **Completed** |
| **PS02-6** | Ensure original PII is not included in sanitized outbound payload | `backend/app/services/security_gate/gate.py` | Independent boundary serialization inspection + leak tests | **Completed** |
| **PS02-7** | FastAPI Gateway implementing Detect → Classify → Mask → Verify → Forward → Inspect → Restore → Audit | `backend/app/api/v1/gateway.py`, `backend/app/services/pipeline.py` | End-to-end API integration tests (`TestClient` + stubbed LLM) | **Completed** |
| **PS02-8** | Pluggable external LLM backend (Gemini primary, OpenAI secondary) | `backend/app/services/llm/base.py`, `gemini_adapter.py`, `openai_adapter.py`, `orchestrator.py` | Live Gemini Interactions API (`store=False`) verified on `LOAN-001`; OpenAI unverified (no API key set) | **Completed (Live Gemini Verified)** |
| **PS02-9** | Local placeholder reinsertion handling paraphrasing, reordering, dropped/missing, unknown/forged tokens | `backend/app/services/restoration/restorer.py` | Adversarial restoration test suite | **Completed** |
| **PS02-10** | Three-panel Demo UI: Original Input, Sanitized Outbound Payload, Final Restored Response | `frontend/src/pages/ProcessingCenter.tsx` | TypeScript + Vite production build (`dist/` clean) | **Completed** |
| **PS02-11** | ~50 synthetic Indian enterprise documents (15 Loan, 15 KYC, 10 Support, 10 Insurance) with labeled ground truth | `dataset/synthetic_documents/indian_enterprise_50.json`, `dataset/annotations/ground_truth_50.json` | Generator + exact span validation (442 spans) | **Completed** |
| **PS02-12** | Metrics & Performance Report: PII leakage count, entity-wise precision/recall, reinsertion accuracy, processing latency | `backend/app/services/evaluation/benchmark.py`, `/api/v1/metrics` | Reproducible benchmark + API tests | **Completed** |
| **PS02-13** | Audit record per request: detected entity types, exact sanitized payload/hash, external model used | `backend/app/services/audit/audit_service.py`, `backend/migrations/versions/0001_initial_schema.py` | Audit DB & export tests (SQLite tested; Alembic verified) | **Completed** |

## B. Recommended Engineering & Security Improvements

| ID | Improvement | Module | Verification | Status |
|---|---|---|---|---|
| **ENG-1** | Cryptographically unpredictable placeholder suffixes (`<AADHAAR_7K2P9X>`) with user-collision guard | `backend/app/services/tokenization/tokenizer.py` | Collision + entropy tests | **Completed** |
| **ENG-2** | Independent Outbound Security Enforcement Engine at transport boundary (`PASS`/`FAIL`/`UNKNOWN`, fail-closed) | `backend/app/services/security_gate/gate.py` | Post-masking tampering & egress tests | **Completed** |
| **ENG-3** | AES-256-GCM encrypted Redis vault with separate `MAPPING_ENCRYPTION_KEY`, tenant isolation, TTL | `backend/app/services/privacy_vault/vault.py` | Cross-tenant & expired-TTL tests (`fakeredis`) | **Completed** |
| **ENG-4** | Purpose-based & RBAC privacy policies (separate restoration permission from submission permission) | `backend/app/services/policies/policy_service.py`, `backend/app/core/security.py` | RBAC & unauthorized restoration `403` tests | **Completed** |
| **ENG-5** | Response scanning for newly generated PII in LLM output | `backend/app/services/restoration/restorer.py` | Newly-generated PII scanner test | **Completed** |
| **ENG-6** | DPDP-oriented audit evidence export (CSV/JSON) without persisting raw PII in audit logs | `backend/app/services/audit/audit_service.py` | Audit log PII-absence + export tests | **Completed** |

## C. Additional Features (PS-02 Section 5 & Enterprise Workspaces)

| ID | Feature | Module | Status |
|---|---|---|---|
| **OPT-1** | Purpose-based blocking rules (e.g., block Aadhaar for marketing) | `backend/app/services/policies/policy_service.py` | **Completed** |
| **OPT-2** | Format-preserving tokenization option for downstream validators | `backend/app/services/tokenization/tokenizer.py` | **Completed (Schema + Metadata Hook; `<ENTITY_6CHAR>` Active Default)** |
| **OPT-3** | Local rule/SLM fallback hook when external LLM is unavailable (policy-gated) | `backend/app/services/llm/orchestrator.py` | **Completed (Explicit Policy-Gated Hook)** |
| **OPT-4** | Full 4-workspace Enterprise UI (Command Center, Processing Center, Governance Center, Audit & Intelligence Center) | `frontend/src/pages/*` | **Completed** |

## D. Future Roadmap Items (Explicitly Scoped Out of MVP Claims)

- Streaming SSE placeholder boundary buffering across partial chunks.
- OCR pipeline for scanned Aadhaar/PAN PDFs/images using local Tesseract/PaddleOCR.
- MCP tool-call argument & multi-turn conversation history vaulting across long-lived sessions.
- Hardware Security Module (HSM) / KMS envelope key rotation.
