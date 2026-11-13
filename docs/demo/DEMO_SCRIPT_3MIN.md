# 3-Minute Hackathon Demonstration Script — Privacy Gateway AI

**Total Time:** 3:00  
**Primary Screen:** Workspace 2 — Privacy Processing Center (Three-Panel Interface)

---

### 0:00 – 0:30 | Problem & Architecture Hook
- Sign in on the Control Plane using **Admin (`admin@bharatfin.in`)**.
- Explain: *"Indian enterprises processing loan applications, KYC, and claims with Gemini or OpenAI risk leaking Aadhaar, PAN, and addresses. Privacy Gateway AI enforces local detection, AES-256-GCM Redis tokenization, an independent outbound security gate, and identity-aware local restoration."*

### 0:30 – 1:15 | Live 3-Panel Processing (Steps 1–6)
- Select a synthetic Indian **Loan Application** in **Panel A (Original Input)** showing name (`Aarav Sharma`), Verhoeff-valid Aadhaar (`2345 6789 0125`), PAN (`ABCPS1020A`), address (`Davangere, Karnataka - 577005`), phone, and bank details.
- Click **Detect PII Locally** → show instant mandatory vs extended entity breakdown (<35 ms).
- Click **Run Privacy Gateway** (Provider: Google Gemini):
  - Point to **Panel B (Sanitized Outbound Payload)**: show exact payload sent to Gemini with unpredictable placeholders (`<PERSON_...>`, `<AADHAAR_...>`, `<PAN_...>`), `GATE: PASS`, and SHA-256 payload digest. Zero raw PII leaves the network.
  - Point to **Panel C (Final Restored Response)**: toggle **"Inspect Raw LLM"** to show Gemini only saw and returned placeholders, then toggle back to show **Locally Restored Enterprise Output** with original values cleanly restored.

### 1:15 – 2:00 | Live Security Failure & Policy Blocking (Step 7)
1. **Post-Masking Tampering Attack:** Check **"Simulate Post-Masking Tamper"** and click **Run Privacy Gateway**.
   - Show **Panel B** turns **`GATE: FAIL`** and **Panel C** blocks the external LLM call fail-closed (*"Known original sensitive value detected in final outbound payload"*). Zero outbound network request made.
2. **Purpose-Based DPDP Blocking:** Uncheck tamper, switch **Purpose** to `Marketing Analytics (Blocks Aadhaar)`, and submit → immediately blocked under DPDP purpose limitation.
3. **RBAC Restoration Control:** Sign out, quick-login as **Loan Analyst (`analyst@bharatfin.in`)**, submit a loan doc → Gemini processes sanitized text, but **Panel C** shows `unauthorized_denied` (placeholders stay masked because Analysts cannot unmask raw PII).

### 2:00 – 3:00 | Evidence, Audit & 50-Doc Benchmark (Step 8)
- Open **Audit & Intelligence Center**:
  - Click **Inspect** on a request to show the SHA-256 outbound digest and zero-raw-PII PostgreSQL audit record, plus **Export CSV / JSON** DPDP evidence.
  - Show the **50-Document Indian Enterprise Benchmark** results: **0 outbound leaks**, **100% precision/recall/F1 on the 50-doc synthetic corpus**, **100% placeholder reinsertion accuracy**, and **~34 ms p95 local overhead**.
