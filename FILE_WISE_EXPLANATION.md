# Privacy Gateway AI — File-Wise Technical Explanation & Tech Stack Document

**Project:** Privacy Gateway AI (MINEARENA 1.0 — Problem Statement PS-02: DPDP-Ready Privacy Gateway for Enterprise LLMs)  
**Version:** 1.0.0 (DPDP-Ready Architecture)  
**Target:** High-concurrency, fail-closed privacy reverse-proxy sitting between enterprise applications and external LLM providers (Google Gemini primary, OpenAI secondary).

---

## 1. Technology Stack Overview

| Layer / Domain | Technologies & Libraries | Version / Specifics | Role in System |
|---|---|---|---|
| **Programming Languages** | **Python**, **TypeScript** | Python 3.12+, TypeScript 5.5+ | Backend service engines, data pipelines, and strongly typed frontend application. |
| **Backend Framework & Server** | **FastAPI**, **Uvicorn**, **Starlette** | FastAPI 0.115+, Uvicorn (ASGI) | High-concurrency async REST API, CORS middleware, dependency injection, and health endpoints. |
| **Data Validation & Schemas** | **Pydantic** | Pydantic v2 | Request/response data validation, serialization, settings management, and type safety. |
| **PII Detection & NLP** | **Microsoft Presidio Analyzer**, **spaCy** | Presidio 2.2+, `en_core_web_sm` | Local, offline entity identification; orchestrates custom Indian recognizers and NER. |
| **Mathematical Checksums** | Custom Algorithmic Implementations | Dihedral Group $D_5$ Verhoeff, Modulo-36 Radix, Luhn ($Mod\text{-}10$) | Non-linear checksum validation for 12-digit Aadhaar, 15-char GSTIN, and credit cards with 0 network calls. |
| **Cryptographic Vault** | **cryptography** (PyCA), **Python `secrets`** | AES-256-GCM AEAD, CSPRNG | Authenticated symmetric encryption with 96-bit nonce and Additional Authenticated Data (AAD) bound to `(org_id, request_id)`. |
| **In-Memory Cache & Vault Store** | **Redis**, **redis-py** | Redis 7 Alpine, `redis>=5.0` | Ephemeral storage for encrypted token mappings with strict Time-To-Live (default 900s) auto-expungement. |
| **Database & ORM** | **PostgreSQL**, **SQLAlchemy**, **Alembic** | PostgreSQL 16 Alpine, SQLAlchemy 2.0, Alembic 1.13+ | Relational persistence for zero-raw-PII audit logs, security events, governance policies, and evaluation records. |
| **Security & Auth** | **PyJWT**, **passlib** (bcrypt), **hmac / hashlib** | HMAC-SHA256, bcrypt | Role-Based Access Control (RBAC), password hashing, and cryptographic `SecurityGateTicket` minting. |
| **Structured Logging** | **structlog** | structlog 24.1+ | Contextual JSON logging with `pii_scrubber_processor` redacting secrets, keys, and PII before log emission. |
| **LLM Provider Integration** | **Google Gemini Interactions API**, **httpx** | `POST /v1beta/interactions`, `Api-Revision: 2026-05-20`, `store=False` | Stateless zero-retention model inference; `gemini-3.8-flash` with graceful fallback to `gemini-3.5-flash-lite`. |
| **Frontend Framework & Styling** | **React 18**, **Tailwind CSS**, **Lucide React** | React 18, Tailwind CSS 3.4, Lucide Icons | 4-workspace enterprise control plane (Processing, Command, Governance, Audit). |
| **Frontend Build & Server** | **Vite**, **Nginx** | Vite 5, Nginx Alpine | Lightning-fast ESM builds and production container reverse proxy routing `/api/` to FastAPI. |
| **Containerization & DevOps** | **Docker**, **Docker Compose** | Compose v2 (`pgw-backend`, `pgw-frontend`, `pgw-postgres`, `pgw-redis`) | One-command full-stack containerized deployment with volume isolation and network bridging. |
| **Testing & Verification** | **pytest**, **pytest-asyncio**, **fakeredis**, **SQLite** | pytest 9.2+, anyio 4.16+ | 17 automated tests verifying checksums, AES-256-GCM ciphertexts, wire security gates, and fail-closed behaviors. |

---

## 2. Root Project & Infrastructure Files

- [docker-compose.yml](file:///c:/antigravity_projects/minearena/docker-compose.yml): Orchestrates the multi-container production deployment. Deploys four services: `pgw-backend` (FastAPI at port 8000), `pgw-frontend` (Nginx + React at port 5173), `pgw-postgres` (PostgreSQL 16 on port 5432), and `pgw-redis` (Redis 7 on port 6379). Sets environment variables, volume persistence, and dependency health checks.
- [.env.example](file:///c:/antigravity_projects/minearena/.env.example) / [.env](file:///c:/antigravity_projects/minearena/.env): Configuration templates defining environment secrets: `JWT_SECRET`, `MAPPING_ENCRYPTION_KEY` (32-byte base64/hex key), `GEMINI_API_KEY`, `DATABASE_URL`, and `REDIS_URL`.
- [.gitignore](file:///c:/antigravity_projects/minearena/.gitignore): Specifies file patterns ignored by Git (e.g. `.venv`, `node_modules`, `__pycache__`, `.env`, temporary test databases).
- [README.md](file:///c:/antigravity_projects/minearena/README.md): Primary repository landing page. Explains core capabilities, 8-stage pipeline, quick start steps (Docker Compose & Local Dev), seeded demo accounts, and testing instructions.
- [IMPLEMENTATION_STATUS.md](file:///c:/antigravity_projects/minearena/IMPLEMENTATION_STATUS.md): Tracking document logging the execution status of Phases 0 through 11, including live fixes applied for Gemini Interactions API migration and Nginx proxy routing.
- [KNOWN_LIMITATIONS.md](file:///c:/antigravity_projects/minearena/KNOWN_LIMITATIONS.md): Transparent disclosure of architectural boundaries: probabilistic unstructured NER for rare names, synchronous request scope, typed pseudonymization visibility to LLMs, and host port collision considerations.
- [REQUIREMENTS_TRACEABILITY.md](file:///c:/antigravity_projects/minearena/REQUIREMENTS_TRACEABILITY.md): Maps official MINEARENA PS-02 requirements (PS02-1 through PS02-13, ENG-1 through ENG-6, OPT-1 through OPT-4) to concrete code files and test validations.
- [SECURITY_TEST_REPORT.md](file:///c:/antigravity_projects/minearena/SECURITY_TEST_REPORT.md): Audit report detailing the execution of 12 security failure and attack test scenarios (SEC-01 to SEC-12), including live container outage resilience tests.
- [generate_ieee_report.py](file:///c:/antigravity_projects/minearena/generate_ieee_report.py): Python automation script that builds the comprehensive, publication-grade IEEE style research report (`Privacy_Gateway_AI_IEEE_Report.docx`).
- [generate_pitch_deck.py](file:///c:/antigravity_projects/minearena/generate_pitch_deck.py): Automation script generating the 16-slide widescreen presentation deck (`Privacy_Gateway_AI_Pitch_Deck.pptx`).
- [generate_5slide_pitch_deck.py](file:///c:/antigravity_projects/minearena/generate_5slide_pitch_deck.py): Automation script generating the structured 5-slide pitch presentation deck (`Privacy_Gateway_AI_5_Slide_Presentation.pptx`).

---

## 3. Backend Core & Configuration (`backend/app/core/` & `backend/app/database/`)

- [backend/Dockerfile](file:///c:/antigravity_projects/minearena/backend/Dockerfile): Container build definition for the FastAPI backend. Uses Python 3.12-slim, installs build dependencies, downloads spaCy's `en_core_web_sm` model, and runs Uvicorn.
- [backend/requirements.txt](file:///c:/antigravity_projects/minearena/backend/requirements.txt): Declares Python package dependencies: `fastapi`, `uvicorn`, `pydantic`, `presidio-analyzer`, `spacy`, `cryptography`, `redis`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `httpx`, `structlog`, `pytest`, `pytest-asyncio`, `python-docx`, `python-pptx`.
- [backend/app/main.py](file:///c:/antigravity_projects/minearena/backend/app/main.py): Application entrypoint. Creates the FastAPI instance, mounts CORS middleware, executes lifespan startup events (initializes Engine 1 PII detector and validates DB connection), registers API routers (`auth`, `gateway`, `governance`), and defines the `/health` endpoint.
- [backend/app/core/config.py](file:///c:/antigravity_projects/minearena/backend/app/core/config.py): Pydantic BaseSettings class managing environment variables, encryption key validation, database connection strings, Redis URLs, model provider allowlists, and default parameters.
- [backend/app/core/security.py](file:///c:/antigravity_projects/minearena/backend/app/core/security.py): Cryptographic security primitives: bcrypt password hashing and verification, JWT token creation (`create_access_token`) and decoding (`verify_token`) with role claims.
- [backend/app/core/logging.py](file:///c:/antigravity_projects/minearena/backend/app/core/logging.py): Configures `structlog` with `pii_scrubber_processor`. Intercepts log event dictionaries and replaces sensitive keys (passwords, tokens, encryption keys, raw PII regexes) with `[REDACTED]` prior to console/file output.
- [backend/app/database/session.py](file:///c:/antigravity_projects/minearena/backend/app/database/session.py): Manages SQLAlchemy database engine and session factory (`sessionmaker`). Exposes the `get_db` FastAPI dependency for database transaction lifecycle management.

---

## 4. Backend Database Models & Schemas (`backend/app/models/` & `schemas/`)

- [backend/app/models/entities.py](file:///c:/antigravity_projects/minearena/backend/app/models/entities.py): SQLAlchemy declarative models:
  - `Organization`: Enterprise tenant record with subscription tier and settings.
  - `User`: User accounts with bcrypt hashed passwords, assigned roles (`admin`, `privacy_officer`, `analyst`, `auditor`), and organization foreign key.
  - `PrivacyPolicy`: Purpose-based governance policies specifying allowed entity sets, blocked entity sets, allowed LLM providers, and active versions.
  - `AuditRecord`: Immutable compliance record per request. Stores request UUID, user/org IDs, detected entity frequencies (JSON), SHA-256 hash of the sanitized wire payload, sanitized preview, gate decision, model used, and latency breakdown. **Contains zero raw PII.**
  - `SecurityEvent`: Security incident log capturing blocked payloads, tampering attempts, detector errors, and failed authorization attempts.
  - `EvaluationRun`: Historical benchmark execution results, overall F1 score, leakage counts, and entity metrics.
- [backend/app/schemas/gateway.py](file:///c:/antigravity_projects/minearena/backend/app/schemas/gateway.py): Pydantic v2 data models for API communication:
  - `ProcessRequest`: Input schema for `/api/v1/process` (raw text, business purpose, selected LLM provider, target model).
  - `ProcessResponse`: Full pipeline response schema (request ID, sanitized text, final restored text, gate decision, restoration report, latencies).
  - `OutboundPayloadSchema`: Canonical JSON wire payload schema evaluated by the Outbound Security Gate.
  - `RestorationReport`: Detailed restoration audit (valid tokens restored, missing tokens, unknown/forged tokens, newly generated PII count).
  - `ProviderStatus` & `BenchmarkRunResponse`: Schemas for telemetry, provider readiness, and benchmark execution results.

---

## 5. Backend API Endpoints & Dependencies (`backend/app/api/`)

- [backend/app/api/deps.py](file:///c:/antigravity_projects/minearena/backend/app/api/deps.py): FastAPI dependency injection providers:
  - `get_current_user`: Extracts and validates the Bearer JWT token from HTTP Authorization headers; retrieves the user from DB.
  - `require_role(...)`: Role-Based Access Control dependency factory that restricts sensitive endpoints to specific roles (e.g. `admin` or `privacy_officer`).
- [backend/app/api/v1/auth.py](file:///c:/antigravity_projects/minearena/backend/app/api/v1/auth.py): Authentication router (`POST /api/v1/auth/login`). Validates email/password credentials against bcrypt hashes and returns a signed JWT token along with user profile metadata.
- [backend/app/api/v1/gateway.py](file:///c:/antigravity_projects/minearena/backend/app/api/v1/gateway.py): Core processing endpoints:
  - `POST /api/v1/process`: Primary entrypoint executing the full 8-stage privacy pipeline.
  - `POST /api/v1/restore`: Dedicated unmasking endpoint allowing authorized roles to decrypt and restore placeholders for a prior request ID.
  - `GET /api/v1/providers`: Returns availability and allowlist status of configured LLM backends.
- [backend/app/api/v1/governance.py](file:///c:/antigravity_projects/minearena/backend/app/api/v1/governance.py): Enterprise governance endpoints:
  - `GET/POST /api/v1/governance/policies`: Retrieve and create purpose-based privacy policies.
  - `GET /api/v1/governance/audits`: Paginated search and request-level investigation of zero-PII audit trails.
  - `GET /api/v1/governance/dpdp-evidence`: Automated export of compliance audit evidence in structured JSON and CSV formats.
  - `POST /api/v1/governance/benchmark`: Triggers execution of the 50-document Indian enterprise evaluation suite.

---

## 6. Backend Service Engines (`backend/app/services/`)

- [backend/app/services/pipeline.py](file:///c:/antigravity_projects/minearena/backend/app/services/pipeline.py): Central orchestrator for the 8-stage workflow:
  1. `DETECT` (Local Presidio + Indian Checksums)
  2. `CLASSIFY` (PBAC Purpose & Policy Evaluation)
  3. `MASK` (Tokenization & AES-256-GCM Vault Write)
  4. `VERIFY` (Outbound Security Gate & Ticket Minting)
  5. `FORWARD` (LLM Dispatch with Transport Guard)
  6. `INSPECT` (Model Response Token Categorization)
  7. `RESTORE` (RBAC-Gated Local Unmasking & Hallucination Scan)
  8. `AUDIT` (PostgreSQL Zero-PII Audit Record & Metrics)
- [backend/app/services/auth_service.py](file:///c:/antigravity_projects/minearena/backend/app/services/auth_service.py): Business logic for user credential authentication, token generation, and user role lookup.

### Engine 1: Detection Intelligence (`backend/app/services/detection/`)
- [backend/app/services/detection/engine.py](file:///c:/antigravity_projects/minearena/backend/app/services/detection/engine.py): Coordinates Presidio Analyzer, spaCy English pipeline, and Indian recognizers. Implements:
  - `_resolve_overlaps`: Priority-driven conflict resolution preventing entity cannibalization (e.g. GSTIN absorbing embedded PAN).
  - `_filter_result`: False-positive suppression filter discarding banking keywords and malformed tokens.
  - `_propagate_known_persons`: Re-identifies bare last-names across a document once a multi-word person name is identified.
- [backend/app/services/detection/indian_validators.py](file:///c:/antigravity_projects/minearena/backend/app/services/detection/indian_validators.py): Pure mathematical checksum algorithms:
  - `validate_aadhaar_verhoeff`: Dihedral group $D_5$ non-linear permutation checksum for 12-digit Aadhaar cards + UIDAI prefix checks.
  - `validate_gstin`: Modulo-36 weighted radix algorithm for 15-character GSTIN + state code set + embedded PAN validation.
  - `validate_pan`: Structural entity code validation (4th char in `ABCFGHLJPT`) + alphanumeric format.
  - `validate_luhn`: Modulo-10 checksum for credit and debit cards.
  - `validate_ifsc`, `validate_voter_id`, `validate_indian_passport`: RBI and Election Commission format validators.
- [backend/app/services/detection/indian_recognizers.py](file:///c:/antigravity_projects/minearena/backend/app/services/detection/indian_recognizers.py): Presidio `PatternRecognizer` subclasses binding regexes, Indian context words, and mathematical validators into Presidio's engine.

### Engine 2: Tokenization & Privacy Vault (`backend/app/services/tokenization/` & `privacy_vault/`)
- [backend/app/services/tokenization/tokenizer.py](file:///c:/antigravity_projects/minearena/backend/app/services/tokenization/tokenizer.py): Generates cryptographically unpredictable typed placeholders (`<ENTITY_6CHAR>`) using CSPRNG seeds (`secrets.choice`). Ensures request-scoped consistency (same entity gets same token) and executes collision detection against user input.
- [backend/app/services/privacy_vault/vault.py](file:///c:/antigravity_projects/minearena/backend/app/services/privacy_vault/vault.py): Ephemeral mapping store backed by Redis. Encrypts plaintext mapping envelopes using **AES-256-GCM** with a 96-bit random nonce and Additional Authenticated Data (AAD) bound to `"{org_id}|{request_id}"`. Enforces short TTL (default 900s) for automatic data expungement.

### Engine 3: Outbound Security Gate (`backend/app/services/security_gate/`)
- [backend/app/services/security_gate/gate.py](file:///c:/antigravity_projects/minearena/backend/app/services/security_gate/gate.py): Independent enforcement engine at the transport boundary. Serializes the canonical outbound JSON payload, checks for raw PII substrings, secret patterns, and unapproved providers. Operates on three-valued logic (`PASS`, `FAIL`, `UNKNOWN`). Mints an HMAC-SHA256 `SecurityGateTicket` bound to the payload's SHA-256 hash. Enforces fail-closed blocking.

### Engine 4: LLM Orchestration (`backend/app/services/llm/`)
- [backend/app/services/llm/base.py](file:///c:/antigravity_projects/minearena/backend/app/services/llm/base.py): Abstract base class `BaseLLMProvider` and dataclasses (`LLMGenerationResult`, `LLMProviderError`).
- [backend/app/services/llm/gemini_adapter.py](file:///c:/antigravity_projects/minearena/backend/app/services/llm/gemini_adapter.py): Adapter for Google Gemini Interactions API (`POST /v1beta/interactions`, `Api-Revision: 2026-05-20`, `store=False`). Dispatches to `gemini-3.8-flash` with automatic failover to `gemini-3.5-flash-lite` on transient 429/503/timeout conditions.
- [backend/app/services/llm/openai_adapter.py](file:///c:/antigravity_projects/minearena/backend/app/services/llm/openai_adapter.py): Adapter for OpenAI Chat Completions API.
- [backend/app/services/llm/orchestrator.py](file:///c:/antigravity_projects/minearena/backend/app/services/llm/orchestrator.py): LLM dispatcher. Features a **Transport Boundary Guard** that cryptographically re-verifies the `SecurityGateTicket` signature and payload SHA-256 hash before invoking any provider network client.

### Engine 5: Response Intelligence & Restoration (`backend/app/services/restoration/`)
- [backend/app/services/restoration/restorer.py](file:///c:/antigravity_projects/minearena/backend/app/services/restoration/restorer.py): Extracts placeholder tokens from LLM output. Categorizes tokens into `valid_restored`, `missing_placeholders`, and `unknown_or_forged_placeholders`. If authorized via RBAC, performs exact case-sensitive unmasking. Runs an active PII scanner over the unmasked text to detect newly generated/hallucinated personal data.

### Engine 6: Policy & Access Control (`backend/app/services/policies/`)
- [backend/app/services/policies/policy_service.py](file:///c:/antigravity_projects/minearena/backend/app/services/policies/policy_service.py): Evaluates Purpose-Based Access Control (PBAC). Checks whether detected entities are permitted under the selected business purpose (e.g. blocking `AADHAAR` in `marketing_analytics`).

### Engine 7: Audit & Compliance (`backend/app/services/audit/`)
- [backend/app/services/audit/audit_service.py](file:///c:/antigravity_projects/minearena/backend/app/services/audit/audit_service.py): Records request metadata, payload SHA-256 hashes, and entity frequencies in PostgreSQL. Logs security incidents into `SecurityEvent`. Generates DPDP compliance evidence exports in JSON and CSV.

### Engine 8: Evaluation & Monitoring (`backend/app/services/evaluation/`)
- [backend/app/services/evaluation/benchmark.py](file:///c:/antigravity_projects/minearena/backend/app/services/evaluation/benchmark.py): Automated benchmark runner that evaluates the gateway against 50 synthetic enterprise documents. Calculates TP, FP, FN, Precision, Recall, F1 score, outbound leakage counts, and latency percentiles.

---

## 7. Database Migrations (`backend/migrations/`)

- [backend/alembic.ini](file:///c:/antigravity_projects/minearena/backend/alembic.ini): Configuration for Alembic migration environment and database connection URL.
- [backend/migrations/env.py](file:///c:/antigravity_projects/minearena/backend/migrations/env.py): Migration execution script connecting Alembic to SQLAlchemy models in `app.models.entities`.
- [backend/migrations/versions/0001_initial_schema.py](file:///c:/antigravity_projects/minearena/backend/migrations/versions/0001_initial_schema.py): Initial database migration script that creates the `organizations`, `users`, `privacy_policies`, `audit_records`, `security_events`, and `evaluation_runs` tables with indexes.

---

## 8. Backend Test Suite (`backend/tests/`)

- [backend/tests/conftest.py](file:///c:/antigravity_projects/minearena/backend/tests/conftest.py): Pytest configuration fixtures: initializes in-memory SQLite database, configures `fakeredis`, seeds default tenant organizations, users, and governance policies.
- [backend/tests/test_detection_and_validators.py](file:///c:/antigravity_projects/minearena/backend/tests/test_detection_and_validators.py): Unit tests verifying Verhoeff algorithm, Modulo-36 checksums, Luhn algorithm, PAN entity validation, and Presidio detection of mandatory Indian entities.
- [backend/tests/test_tokenization_and_vault.py](file:///c:/antigravity_projects/minearena/backend/tests/test_tokenization_and_vault.py): Tests verifying typed placeholder entropy, request-scoped consistency, AES-256-GCM ciphertext in Redis, collision avoidance, and fail-closed behavior on Redis unavailability.
- [backend/tests/test_security_gate_and_pipeline.py](file:///c:/antigravity_projects/minearena/backend/tests/test_security_gate_and_pipeline.py): End-to-end integration tests verifying zero outbound PII leakage, fail-closed blocking of tampered payloads, purpose policy blocking (Aadhaar in marketing), unauthorized unmasking restrictions (HTTP 403), and forged placeholder handling.
- [backend/tests/test_governance_and_evaluation_api.py](file:///c:/antigravity_projects/minearena/backend/tests/test_governance_and_evaluation_api.py): Tests verifying governance policy endpoints, DPDP evidence export (CSV/JSON), benchmark API execution, and detector failure handling.
- [backend/tests/test_llm_adapter_unit.py](file:///c:/antigravity_projects/minearena/backend/tests/test_llm_adapter_unit.py): Unit tests verifying Gemini Interactions API request structure (`POST /v1beta/interactions`, `store=False`) and deprecated-model substitution.

---

## 9. Dataset & Synthetic Benchmark (`dataset/`)

- [dataset/synthetic_documents/indian_enterprise_50.json](file:///c:/antigravity_projects/minearena/dataset/synthetic_documents/indian_enterprise_50.json): 50 synthetic Indian enterprise documents across 4 sectors: 15 Loan Underwriting Applications, 15 KYC & Onboarding Records, 10 Customer Support Tickets (with Hinglish), and 10 Insurance Claims.
- [dataset/annotations/ground_truth_50.json](file:///c:/antigravity_projects/minearena/dataset/annotations/ground_truth_50.json): 442 manually validated ground-truth entity spans across 15 entity types with exact character start/end coordinates.
- [dataset/benchmark/generate_dataset.py](file:///c:/antigravity_projects/minearena/dataset/benchmark/generate_dataset.py): Reproducible dataset generation script synthesizing documents with authentic Indian name distributions, valid Verhoeff Aadhaar numbers, Mod-36 GSTINs, and PAN entity codes.

---

## 10. Frontend Architecture & Enterprise Workspaces (`frontend/`)

- [frontend/Dockerfile](file:///c:/antigravity_projects/minearena/frontend/Dockerfile): Multi-stage Dockerfile: builds the React/TypeScript application with Vite and serves production artifacts via Nginx.
- [frontend/nginx.conf](file:///c:/antigravity_projects/minearena/frontend/nginx.conf): Reverse proxy configuration routing frontend asset requests, single-page application fallback (`index.html`), and proxying `/api/` and `/health` requests to `backend:8000`.
- [frontend/package.json](file:///c:/antigravity_projects/minearena/frontend/package.json): Defines frontend npm dependencies: `react`, `react-dom`, `lucide-react`, `tailwindcss`, `vite`, `typescript`.
- [frontend/vite.config.ts](file:///c:/antigravity_projects/minearena/frontend/vite.config.ts): Vite build configuration with development proxy to `http://localhost:8000`.
- [frontend/src/main.tsx](file:///c:/antigravity_projects/minearena/frontend/src/main.tsx): React DOM entrypoint mounting the application with `AuthProvider`.
- [frontend/src/App.tsx](file:///c:/antigravity_projects/minearena/frontend/src/App.tsx): Root application container managing authentication state, navigation header, and tab routing across the four operational workspaces.
- [frontend/src/contexts/AuthContext.tsx](file:///c:/antigravity_projects/minearena/frontend/src/contexts/AuthContext.tsx): React context managing JWT authentication tokens, active user session, and login/logout state.
- [frontend/src/components/LoginView.tsx](file:///c:/antigravity_projects/minearena/frontend/src/components/LoginView.tsx): Sign-in modal featuring one-click quick-login buttons for demonstration roles (`admin`, `privacy_officer`, `analyst`, `auditor`).
- [frontend/src/services/api.ts](file:///c:/antigravity_projects/minearena/frontend/src/services/api.ts): API client wrapper managing HTTP headers, JWT authorization bearer injection, and error handling.
- [frontend/src/types/api.ts](file:///c:/antigravity_projects/minearena/frontend/src/types/api.ts): TypeScript interfaces matching backend models (`ProcessResponse`, `AuditRecord`, `RestorationReport`, `CategoryTier`).

### The Four Operational Workspaces (`frontend/src/pages/`)
1. [frontend/src/pages/ProcessingCenter.tsx](file:///c:/antigravity_projects/minearena/frontend/src/pages/ProcessingCenter.tsx): Core interactive 3-panel console:
   - *Panel A (Original Input)*: Text editor with sample document selector and color-coded entity highlight badges.
   - *Panel B (Sanitized Wire Payload)*: Live preview of the outbound payload showing `<ENTITY_6CHAR>` tokens and `GATE: PASS/FAIL` status.
   - *Panel C (Final Restored Response)*: Restored enterprise response with toggle to inspect raw LLM output, restoration telemetry, and tamper simulation.
2. [frontend/src/pages/CommandCenter.tsx](file:///c:/antigravity_projects/minearena/frontend/src/pages/CommandCenter.tsx): Executive telemetry console presenting real-time system health, provider readiness, p50/p95 latency percentiles, throughput counters, and security block rates.
3. [frontend/src/pages/GovernanceCenter.tsx](file:///c:/antigravity_projects/minearena/frontend/src/pages/GovernanceCenter.tsx): Policy administration console for configuring purpose-based entity blocking rules, provider allowlists, and role matrices.
4. [frontend/src/pages/AuditCenter.tsx](file:///c:/antigravity_projects/minearena/frontend/src/pages/AuditCenter.tsx): Compliance audit explorer with searchable request logs, SHA-256 wire digest verification, security event timeline, and one-click JSON/CSV DPDP evidence export.

---

## 11. Documentation & Architecture Reports (`docs/`)

- [docs/architecture/SYSTEM_ARCHITECTURE.md](file:///c:/antigravity_projects/minearena/docs/architecture/SYSTEM_ARCHITECTURE.md): Comprehensive system architecture specification detailing the modular monolith pattern, sequence diagrams, and data retention schedules.
- [docs/architecture/COMPETITIVE_GAP_ANALYSIS.md](file:///c:/antigravity_projects/minearena/docs/architecture/COMPETITIVE_GAP_ANALYSIS.md): Technical comparison matrix evaluating Privacy Gateway AI against LiteLLM, Cloudflare AI Gateway, Skyflow, and Protecto.
- [docs/architecture/REPOSITORY_AUDIT.md](file:///c:/antigravity_projects/minearena/docs/architecture/REPOSITORY_AUDIT.md): Codebase audit confirming adherence to modularity standards, test coverage, and security invariants.
- [docs/security/SECURITY_DESIGN.md](file:///c:/antigravity_projects/minearena/docs/security/SECURITY_DESIGN.md): Detailed threat model, cryptographic specifications (AES-256-GCM, HMAC tickets), and log scrubbing protocols.
- [docs/evaluation/EVALUATION_REPORT.md](file:///c:/antigravity_projects/minearena/docs/evaluation/EVALUATION_REPORT.md): Benchmark results across the 50-document Indian enterprise corpus documenting 100% precision, 100% recall, 0 outbound leaks, and sub-35 ms latency.
- [docs/demo/DEMO_SCRIPT_3MIN.md](file:///c:/antigravity_projects/minearena/docs/demo/DEMO_SCRIPT_3MIN.md): Concise 3-minute hackathon presentation script detailing the step-by-step demonstration flow.
