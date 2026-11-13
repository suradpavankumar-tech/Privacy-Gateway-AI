# Security Design Document — Privacy Gateway AI

## 1. Threat Model & Core Invariant

**Invariant:** Original personal information (`PERSON`, `AADHAAR`, `PAN`, `GSTIN`, `VOTER_ID`, `PASSPORT`, `ADDRESS`, etc.) and reversible vault mappings must never cross the external LLM boundary or appear in normal application logs or PostgreSQL audit records.

## 2. Cryptographic & Vault Controls

- **Cipher:** AES-256-GCM (`cryptography.hazmat.primitives.ciphers.aead.AESGCM`) with 96-bit random nonce per write.
- **Additional Authenticated Data (AAD):** `"{org_id}|{request_id}"` bound into the GCM tag, preventing cross-tenant or cross-request ciphertext transplantation.
- **Key Separation:** `MAPPING_ENCRYPTION_KEY` resides exclusively in server environment secrets and is never persisted in Redis or PostgreSQL.
- **Token Unpredictability & Collision Guard:** Placeholders (`<ENTITY_6CHAR>`) use `secrets.choice` CSPRNG suffixes and verify non-existence in the source text so user input cannot hijack or collide with vault placeholders.
- **Retention & TTL:** Temporary mappings auto-expire in Redis (`MAPPING_TTL_SECONDS`, default 900s).

## 3. Transport-Boundary Outbound Security Gate

- Implemented at the final dispatch boundary (`LLMOrchestrationEngine.dispatch`).
- `OutboundSecurityGate.inspect_and_authorize()` inspects the full canonical serialized JSON payload (`system_prompt`, `user_prompt`, `conversation_history`, `tool_definitions`, `tool_arguments`, `metadata`).
- Mints a short-lived HMAC-SHA256 `SecurityGateTicket` bound to `(ticket_id, request_id, org_id, provider, model, sha256(serialized_payload))`.
- Any `FAIL` or `UNKNOWN` decision, or post-inspection payload modification, causes immediate fail-closed blocking before any HTTP request is initiated.

## 4. Access Control & Purpose Limitation

- JWT authentication with `bcrypt`-hashed credentials.
- RBAC cleanly separates document submission (`analyst`, `developer`) from PII restoration (`admin`, `privacy_officer`, `security_officer`).
- Purpose-based policies enforce entity blocking (e.g., `marketing_analytics` blocks `AADHAAR`, `PASSPORT`, `VOTER_ID`, `BANK_ACCOUNT`).

## 5. Log & Audit Hygiene

- `structlog` processor (`pii_scrubber_processor`) redacts sensitive keys (`api_key`, `password`, `original_value`, `mapping_encryption_key`) and regex-matches Aadhaar, PAN, GSTIN, Bearer tokens, and provider API keys before emission.
- PostgreSQL audit tables store entity types, offsets, confidence, SHA-256 of the sanitized outbound payload, and sanitized preview text—never raw PII.
