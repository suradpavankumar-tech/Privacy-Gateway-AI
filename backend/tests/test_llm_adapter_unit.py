from __future__ import annotations

import pytest

from app.schemas.gateway import OutboundPayloadSchema, SecurityDecision
from app.services.llm.gemini_adapter import GeminiAdapter, resolve_gemini_model
from app.services.llm.local_slm_adapter import LocalSLMAdapter


def test_deprecated_gemini_model_substitution():
    assert resolve_gemini_model("gemini-2.5-flash") == "gemini-3.5-flash-lite"
    assert resolve_gemini_model("models/gemini-2.5-flash") == "gemini-3.5-flash-lite"
    assert resolve_gemini_model("gemini-2.5-flash-lite") == "gemini-3.5-flash-lite"
    assert resolve_gemini_model("gemini-3.8-flash") == "gemini-3.5-flash-lite"


def test_gemini_interactions_request_body_stateless_and_clean():
    payload = OutboundPayloadSchema(
        request_id="req-g1",
        organization_id="org-1",
        provider="gemini",
        model="gemini-3.8-flash",
        purpose="loan_underwriting",
        system_prompt="Preserve placeholders verbatim.",
        user_prompt="Summarize <PERSON_A1B2C3> with PAN <PAN_X9Y8Z7>.",
    )
    body = GeminiAdapter.build_request_body(payload, model="gemini-3.8-flash")
    assert body["model"] == "gemini-3.8-flash"
    assert body["store"] is False
    assert body["system_instruction"] == "Preserve placeholders verbatim."
    assert body["input"] == "Summarize <PERSON_A1B2C3> with PAN <PAN_X9Y8Z7>."
    assert body["generation_config"]["max_output_tokens"] == 1024


@pytest.mark.asyncio
async def test_local_slm_preserves_placeholders_offline():
    adapter = LocalSLMAdapter()
    assert adapter.is_configured() is True
    assert adapter.default_model() == "local-slm-indic-v1"

    payload = OutboundPayloadSchema(
        request_id="req-slm-1",
        organization_id="org-1",
        provider="local_slm",
        model="local-slm-indic-v1",
        purpose="loan_underwriting",
        system_prompt="System",
        user_prompt="Task: Summarize\n\nMasked Document Content:\nName: <PERSON_K8P2M4>\nPAN: <PAN_N7R3Q9>",
        metadata={"registered_placeholders": ["<PERSON_K8P2M4>", "<PAN_N7R3Q9>"]},
    )
    res = await adapter.generate(payload)
    assert res.provider == "local_slm"
    assert "<PERSON_K8P2M4>" in res.content
    assert "<PAN_N7R3Q9>" in res.content


@pytest.mark.asyncio
async def test_local_slm_structured_property_and_legal_analysis():
    adapter = LocalSLMAdapter()

    prop_payload = OutboundPayloadSchema(
        request_id="req-slm-prop",
        organization_id="org-1",
        provider="local_slm",
        model="local-slm-indic-v1",
        purpose="property_verification",
        system_prompt="System",
        user_prompt=(
            "Task: Analyze deed\n\nMasked Document Content:\n"
            "DEED OF ABSOLUTE SALE\n"
            "Sale Deed Reg No: <PROPERTY_LEGAL_ID_A1B2C3> | Survey No: <PROPERTY_LEGAL_ID_D4E5F6>\n"
            "Vendor: Shri <PERSON_X1Y2Z3> | PAN: <PAN_P9Q8R7>\n"
            "Vendee: Smt. <PERSON_M4N5B6>\n"
            "Consideration Value: INR 1,45,00,000 paid via RTGS with Nil Encumbrance Certificate.\n"
        ),
        metadata={
            "registered_placeholders": [
                "<PROPERTY_LEGAL_ID_A1B2C3>",
                "<PROPERTY_LEGAL_ID_D4E5F6>",
                "<PERSON_X1Y2Z3>",
                "<PAN_P9Q8R7>",
                "<PERSON_M4N5B6>",
            ]
        },
    )
    prop_res = await adapter.generate(prop_payload)
    assert "1. Ownership Chain / Parties:" in prop_res.content
    assert "2. Deed, Survey & CNR IDs:" in prop_res.content
    assert "3. Financial Consideration & Deadlines:" in prop_res.content
    assert "4. Risk & Red-Flag Clauses:" in prop_res.content
    assert "<PERSON_X1Y2Z3>" in prop_res.content
    assert "<PROPERTY_LEGAL_ID_A1B2C3>" in prop_res.content
    assert "INR 1,45,00,000" in prop_res.content
    assert "Nil Encumbrance" in prop_res.content

    legal_payload = OutboundPayloadSchema(
        request_id="req-slm-legal",
        organization_id="org-1",
        provider="local_slm",
        model="local-slm-indic-v1",
        purpose="legal_review",
        system_prompt="System",
        user_prompt=(
            "Task: Analyze notice\n\nMasked Document Content:\n"
            "LEGAL NOTICE UNDER SECTION 138 & ARBITRATION CLAUSE\n"
            "CNR No: <PROPERTY_LEGAL_ID_L1M2N3>\n"
            "Petitioner: <PERSON_A9B8C7> | Respondent: Horizon Buildcon LLP\n"
            "Claim Amount: INR 38,75,000 security deposit refund within 15 days.\n"
        ),
        metadata={"registered_placeholders": ["<PROPERTY_LEGAL_ID_L1M2N3>", "<PERSON_A9B8C7>"]},
    )
    legal_res = await adapter.generate(legal_payload)
    assert "1. Ownership Chain / Parties:" in legal_res.content
    assert "2. Deed, Survey & CNR IDs:" in legal_res.content
    assert "3. Financial Consideration & Deadlines:" in legal_res.content
    assert "4. Risk & Red-Flag Clauses:" in legal_res.content
    assert "within 15 days" in legal_res.content
    assert "<PERSON_A9B8C7>" in legal_res.content
