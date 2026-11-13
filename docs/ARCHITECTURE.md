# System Architecture (`mine_arena`)

## End-to-End Request Lifecycle

```text
User / Client (JWT Auth)
   │
   ▼
[1. Policy & RBAC Resolution] (PostgreSQL: PrivacyPolicy by org_id + purpose)
   │
   ▼
[2. Local Detection Engine] (Presidio + spaCy + Verhoeff/Mod-36/Luhn/PAN + Hinglish Context)
   │
   ▼
[3. Multi-Mode Tokenizer] (cryptographic_random | typed_sequential | format_preserving)
   │
   ├──► [4. Privacy Vault] (AES-256-GCM with 12-byte nonce + AAD=(org_id, request_id) -> Redis TTL)
   │
   ▼
[5. Outbound Security Gate] (Inspects canonical JSON, excludes issued placeholders, verifies zero raw PII)
   │   ├── FAIL / UNKNOWN ──► Blocked locally + SecurityEvent logged (Zero transmission)
   │   └── PASS ──► Issues HMAC-SHA256 SecurityGateTicket
   │
   ▼
[6. LLM Orchestrator] (Verifies SecurityGateTicket -> Gemini / OpenAI / Local SLM Fallback)
   │
   ▼
[7. Response Inspector & Restorer] (RBAC check + Re-insertion + Forged token detection + New PII scan)
   │
   ▼
[8. Audit & Observability] (PostgreSQL metadata + SHA-256 hash + Sanitized preview; Zero raw PII stored)
```

## Non-Negotiable Security Guarantees
1. **No raw PII persisted in PostgreSQL audit tables:** Only entity types, character offsets, placeholders, confidence scores, recognizer names, SHA-256 hash, and masked payload previews are stored.
2. **Fail-Closed Security Gate:** Any leakage detection, missing policy/provider authorization, or unexpected exception transitions the gate to `FAIL` or `UNKNOWN` and halts outbound dispatch.
3. **Cryptographic Transport Boundary:** `LLMOrchestrationEngine.dispatch()` verifies the HMAC-SHA256 signature and payload hash of `SecurityGateTicket` before invoking any external HTTP client or fallback engine.
4. **Fail-Closed Vault:** In `redis://...` mode, Redis unavailability returns HTTP `503` without forwarding unmasked prompts.
