# Comparative Audit & Design Synthesis: `minearena` vs `minearena2` -> `mine_arena`

## 1. Executive Comparison

| Dimension | `minearena` (FastAPI + Presidio + PG + Redis) | `minearena2` (Node/Express + React/Vite) | Winner & Decision for `mine_arena` |
|---|---|---|---|
| **Detection Accuracy** | Microsoft Presidio + spaCy NER + mathematical Verhoeff (Aadhaar), Mod-36 (GSTIN), PAN 4th-char, Luhn + Hinglish context recognizers + doc-level person propagation | Pure JS regexes + ~20 hardcoded Indian names; no Verhoeff/Mod-36/Luhn checks | **`minearena`** + enhancement: fallback context recognizer for labeled malformed 12-digit UIDs (`1234-5678-9012` under explicit `aadhaar`/`uidai` cue) |
| **Vault Encryption** | Real `cryptography.hazmat.primitives.ciphers.aead.AESGCM` (AES-256-GCM), `os.urandom(12)` nonce, AAD `(org_id, request_id)`, Redis TTL | Homemade XOR cipher (`xorCipherBytes`) + non-cryptographic 32-bit FNV hash; hardcoded fallback key; in-memory `Map` | **`minearena`** + expose non-PII `VaultEntryMetadata` (hex nonce, ciphertext prefix, AAD scope, TTL) for UI inspection |
| **Outbound Security Gate** | Independent canonical-JSON inspector, fail-closed `PASS`/`FAIL`/`UNKNOWN`, HMAC-SHA256 `SecurityGateTicket` enforced at transport boundary | Deterministic leakage scan in TS, but no HMAC ticket binding and no `UNKNOWN` failure state | **`minearena`** + adopt `minearena2`'s itemized `checks` UI breakdown + fix surrogate-aware validation |
| **Tokenization Flexibility** | Single mode (`<TYPE_6CHAR>`) via `secrets.choice` | 3 modes: typed sequential, cryptographic bracket, format-preserving synthetic surrogates | **Both**: support `cryptographic_random`, `typed_sequential`, `format_preserving` inside collision-checked tokenizer + AES-256-GCM vault |
| **LLM Transport & Fallback** | Live Gemini Interactions API (`store=False`, deprecated model substitution, failover) + OpenAI adapter; no local SLM fallback | Mock/simulated Gemini + built-in `local-slm-indic-v1` offline fallback + outage simulation toggle | **Both**: preserve live Gemini/OpenAI adapters and add policy-gated `local_slm` (`local-slm-indic-v1`) + non-prod outage toggle |
| **RBAC & Auth** | Real JWT + bcrypt password verification + org membership DB table + `403` enforcement | Zero auth; spoofable `userRole` dropdown passed in JSON request body | **`minearena`** + add `loan_underwriter` & `support_agent` demo accounts and Quick Role Switcher calling real `/api/v1/auth/login` |
| **Persistence & Audit** | PostgreSQL + Alembic migrations, zero raw PII persisted, JSON/CSV audit export | Ephemeral in-memory arrays lost on restart | **`minearena`** + store `tokenization_mode`, `fallback_triggered`, `raw_pii_leak_count`, `restored_count`, `forged_count` |
| **Frontend UX & Demo Lab** | Light clean UI, lacks inline span `<mark>` highlights, corpus browser, judge scenarios, ciphertext proof | Dark cyber control plane with judge scenarios, `<mark>` spans, vault proof drawer, 50-doc Benchmark Lab, role matrix UI | **`minearena2` UX** wired 100% cleanly to `minearena`'s authenticated FastAPI backend |

## 2. Critical Security Flaws Fixed from `minearena2`
1. Replaced homemade XOR + 32-bit FNV hashing with genuine `AESGCM` (AES-256-GCM) authenticated encryption and per-entry 96-bit CSPRNG nonces.
2. Replaced spoofable client-sent `userRole` with JWT authentication and server-side RBAC policy resolution.
3. Enforced cryptographic HMAC-SHA256 `SecurityGateTicket` verification at `LLMOrchestrationEngine.dispatch()` so no adapter (cloud or local SLM) can execute without Security Gate `PASS`.
4. Replaced in-memory `Map`/`Array` storage with Redis TTL vault (strictly failing closed `503` on Redis outage) + SQLAlchemy/PostgreSQL persistence.

## 3. Usability & Feature Gaps Fixed from `minearena`
1. Added 3 selectable tokenization modes (`cryptographic_random`, `typed_sequential`, `format_preserving`).
2. Added `LocalSLMAdapter` (`local_slm` / `local-slm-indic-v1`) + policy-gated offline fallback + non-prod outage & forged-token simulation switches.
3. Added itemized Security Gate checks (`GateCheckItem`) and safe `VaultEntryMetadata` hex proof drawer.
4. Added full 50-document corpus endpoint (`GET /api/v1/dataset`) and interactive **Benchmark Lab (50 Docs)** UI with category filtering, ground-truth span inspection, per-doc precision/recall metrics, and "Load in Studio".
5. Added interactive **Role Restoration Matrix** controls in Governance & Audit Center backed by `PATCH /api/v1/policies/{policy_id}`.
