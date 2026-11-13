# Privacy Gateway AI

**Detect the sensitive. Mask the personal. Verify before sending. Restore locally.**

Privacy Gateway AI is a provider-independent, DPDP-ready AI privacy and governance control plane built for **MINEARENA 1.0 (PS-02 — DPDP-Ready Privacy Gateway for Enterprise LLMs)**.

It sits between enterprise applications and external LLM providers (Google Gemini primary, OpenAI secondary) and enforces the 8-stage pipeline:

`DETECT → CLASSIFY → MASK → VERIFY → FORWARD → INSPECT → RESTORE → AUDIT`

---

## Key Capabilities

1. **Local Indian PII Detection Engine:** Microsoft Presidio + spaCy NER (`en_core_web_sm`) + custom Indian recognizers with mathematical checksum validation:
   - **Mandatory Entities:** `PERSON`, `AADHAAR` (Verhoeff checksum), `PAN` (4th-char entity code), `GSTIN` (Mod-36 checksum + embedded PAN), `VOTER_ID`, `PASSPORT`, `ADDRESS` (Indian PIN codes, street/locality markers, Hinglish cues).
   - **Extended Entities:** `PHONE_NUMBER`, `EMAIL_ADDRESS`, `BANK_ACCOUNT`, `IFSC`, `DATE_OF_BIRTH`, `CREDIT_CARD` (Luhn), `CUSTOMER_ID`, `UPI_ID`.
   - Zero outbound network calls during detection (`UrlRecognizer` / `tldextract` excluded).
2. **AES-256-GCM Encrypted Privacy Vault (Redis):**
   - Cryptographically random 6-character typed placeholders (`<AADHAAR_7K2P9X>`), consistent within request scope, collision-checked against user input.
   - Encrypted with `AES-256-GCM` and AAD bound to `(org_id, request_id)` with separate `MAPPING_ENCRYPTION_KEY` and short TTL.
3. **Independent Outbound Security Gate (Fail-Closed):**
   - Inspects the complete canonical JSON provider payload right at the transport boundary (`PASS` / `FAIL` / `UNKNOWN`).
   - Blocks `FAIL` and `UNKNOWN` (missing policy, detector unavailable, Redis unavailable, post-masking PII injection, unapproved provider, leaked secrets).
   - Cryptographic HMAC-SHA256 `SecurityGateTicket` binds the inspected payload hash to the LLM transport adapter.
4. **Authorized Local Response Restoration:**
   - Exact case-sensitive placeholder lookup (never fuzzy matching or guessing).
   - Handles reordered, repeated, paraphrased, dropped/missing, and forged placeholders.
   - RBAC separates submission (`analyst`/`developer`) from restoration (`admin`/`privacy_officer`/`security_officer`).
   - Scans final output for newly generated LLM PII.
5. **Enterprise Governance, DPDP Audit Evidence & 50-Doc Benchmark:**
   - PostgreSQL schema via SQLAlchemy 2.0 + Alembic migrations storing zero raw PII in audit records.
   - Purpose-based policies (e.g., `marketing_analytics` blocks `AADHAAR`).
   - 50 synthetic Indian enterprise documents (`15` loan, `15` KYC, `10` support, `10` insurance) with 442 ground-truth spans and a reproducible benchmark runner.

---

## Quick Start

### Option 1: Docker Compose (Recommended for Production / Demo)

```bash
cp .env.example .env
# Edit .env and set JWT_SECRET, MAPPING_ENCRYPTION_KEY (32-byte base64 or 64-char hex), GEMINI_API_KEY
docker compose up --build
```

- Frontend UI: `http://localhost:5173`
- Backend FastAPI + OpenAPI Docs: `http://localhost:8000/docs`

### Option 2: Local Development (Backend + Frontend)

1. **Backend:**
   ```bash
   cd backend
   python -m venv .venv
   # Activate venv (.venv\Scripts\activate on Windows or source .venv/bin/activate on Linux)
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   cp .env.example .env
   # Start PostgreSQL and Redis (or update DATABASE_URL / REDIS_URL in .env)
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```
2. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## Seeded Demo Accounts (RBAC Verification)

| Role | Email | Password | Capabilities |
|---|---|---|---|
| `admin` | `admin@bharatfin.in` | `Admin@2026!` | Full access + Local PII Restoration |
| `privacy_officer` | `privacy@bharatfin.in` | `Privacy@2026!` | Governance Policies + Restoration + Audit Export |
| `analyst` | `analyst@bharatfin.in` | `Analyst@2026!` | Submit & Mask only (**Restoration Denied 403**) |
| `auditor` | `auditor@bharatfin.in` | `Auditor@2026!` | Read-only Audits, Metrics & DPDP Evidence Export |

---

## Running Tests & Benchmark

```bash
# Run full unit, integration, and fail-closed security test suite
backend\.venv\Scripts\pytest.exe backend\tests -v

# Regenerate 50 synthetic documents + ground-truth annotations
backend\.venv\Scripts\python.exe dataset\benchmark\generate_dataset.py
```

---

## Repository Layout

- `backend/` — FastAPI application, 8 modular engines, Alembic migrations, pytest suite
- `frontend/` — React + TypeScript + Tailwind CSS 4-workspace control plane
- `dataset/` — 50 synthetic Indian enterprise documents, exact span annotations, benchmark generator
- `docs/` — Architecture, Competitive Gap Analysis, Security Design, Evaluation Report, 3-Min Demo Script
