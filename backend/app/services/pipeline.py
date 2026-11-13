"""
=========================================================================================
pipeline.py — Master Zero-Leak Privacy Gateway Pipeline Orchestrator
=========================================================================================

Tech Stack:
 - Python 3.11+ / Asyncio (High-throughput asynchronous request pipeline)
 - SQLAlchemy (Database persistence for session state and audit events)
 - Pydantic (Strict schema transformation across pipeline boundaries)
 - High-Precision Time Profiling (`time.perf_counter` latency instrumentation)

Key Architectural Responsibilities:
 1. 5-Stage Zero-Leak Orchestration (`execute_privacy_pipeline`):
    - Stage 1: Local Detection & Ingestion:
      Scans raw input using Indic NER, Presidio, and mathematical checksum validators.
    - Stage 2: Policy-Bound Masking & Vault Storage:
      Evaluates organization privacy policies; stores original PII values inside an
      AES-256-GCM encrypted vault and replaces them with safe placeholder tokens.
    - Stage 3: Outbound Security Gate:
      Executes independent post-masking re-scans. If any residual PII is detected,
      the gate terminates the request immediately (FAIL). On success (PASS), issues a signed HMAC ticket.
    - Stage 4: AI Model Invocation & SLM Fallback:
      Dispatches the verified sanitized payload to primary cloud LLMs (Gemini/OpenAI).
      If cloud providers fail or time out, intelligently routes to local on-premise Ollama SLM.
    - Stage 5: Response Validation & RBAC Restoration:
      Inspects the model response for forged tokens; selectively unmasks entities matching
      the caller's authorized RBAC permissions.

 2. High-Resolution Latency Waterfall:
    - Measures elapsed milliseconds across each stage (detection, vault, gate, model, restorer)
      for real-time dashboard performance visualization.
=========================================================================================
"""

from __future__ import annotations

import time
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.gateway import (
    DetectedEntitySchema,
    OutboundPayloadSchema,
    ProcessRequest,
    ProcessResponse,
    RestorationReport,
    SecurityDecision,
)
from app.services.audit.audit_service import AuditService
from app.services.detection.engine import DetectionEngineError, get_detection_engine
from app.services.llm.base import LLMProviderError
from app.services.llm.orchestrator import get_llm_orchestrator
from app.services.policies.policy_service import evaluate_policy
from app.services.privacy_vault.vault import VaultUnavailableError
from app.services.restoration.restorer import get_response_engine
from app.services.security_gate.gate import SecurityGateViolationError, get_security_gate
from app.services.tokenization.tokenizer import PLACEHOLDER_REGEX, TokenizerEngine

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are an enterprise AI assistant processing a privacy-sanitized document. "
    "Sensitive fields have been replaced with protected placeholder tokens or synthetic surrogates. "
    "Preserve every placeholder token verbatim whenever referencing that entity, and never invent or guess personal details."
)


async def execute_privacy_pipeline(
    db: Session,
    org_id: str,
    user_id: str,
    user_role: str,
    payload_in: ProcessRequest,
) -> ProcessResponse:
    settings = get_settings()
    request_id = str(uuid.uuid4())
    t_total_start = time.perf_counter()
    t_local_start = time.perf_counter()
    trace: list[str] = []

    provider_name = (payload_in.provider or settings.DEFAULT_LLM_PROVIDER).strip().lower()
    orchestrator = get_llm_orchestrator()
    try:
        adapter = orchestrator.get_provider(provider_name)
        model_name = payload_in.model or adapter.default_model()
    except (SecurityGateViolationError, LLMProviderError) as exc:
        AuditService.record_security_event(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            event_type="provider_blocked",
            severity="high",
            outcome="blocked",
            details={"provider": provider_name, "reason": str(exc)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    # Stage 1: DETECT locally (fail-closed if detector fails)
    try:
        detector = get_detection_engine()
        detections, detect_ms = detector.detect(payload_in.text)
        trace.append(f"DETECT({len(detections)} entities in {detect_ms}ms)")
    except DetectionEngineError as exc:
        AuditService.record_security_event(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            event_type="detector_unavailable",
            severity="critical",
            outcome="failed_closed",
            details={"reason": str(exc)},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local PII detection engine unavailable; request blocked fail-closed.",
        ) from exc

    # Stage 2: CLASSIFY & POLICY EVALUATION
    policy_decision = evaluate_policy(
        db=db,
        org_id=org_id,
        purpose=payload_in.purpose,
        role=user_role,
        provider=provider_name,
        detections=detections,
    )
    policy_version = policy_decision.policy.version if policy_decision.policy else 0
    policy_id = policy_decision.policy.id if policy_decision.policy else None
    ttl_seconds = (
        policy_decision.policy.mapping_ttl_seconds
        if policy_decision.policy
        else settings.MAPPING_TTL_SECONDS
    )
    trace.append(
        f"CLASSIFY(policy v{policy_version}: {'APPROVED' if policy_decision.approved else 'BLOCKED'})"
    )

    # Stage 3: MASK & STORE IN AES-256-GCM VAULT (fail-closed if Redis unavailable)
    tokenizer = TokenizerEngine()
    try:
        tok_res = tokenizer.tokenize(
            org_id=org_id,
            request_id=request_id,
            text=payload_in.text,
            detections=detections,
            ttl_seconds=ttl_seconds,
            mode=payload_in.tokenization_mode,
        )
        trace.append(f"MASK({payload_in.tokenization_mode.value}, {len(tok_res.placeholders)} tokens -> AES-256-GCM)")
    except VaultUnavailableError as exc:
        local_ms = round((time.perf_counter() - t_local_start) * 1000.0, 2)
        AuditService.record_request_start(
            db=db,
            request_id=request_id,
            org_id=org_id,
            user_id=user_id,
            user_role=user_role,
            purpose=payload_in.purpose,
            document_category=payload_in.document_category,
            tokenization_mode=payload_in.tokenization_mode.value,
            policy_id=policy_id,
            policy_version=policy_version,
            provider=provider_name,
            model=model_name,
            status="failed_closed",
            detected_entity_counts={},
            local_processing_ms=local_ms,
        )
        AuditService.record_security_event(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            event_type="vault_unavailable",
            severity="critical",
            outcome="failed_closed",
            details={"reason": "Encrypted Redis privacy vault unavailable"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Encrypted privacy vault unavailable; request blocked fail-closed.",
        ) from exc

    outbound_user_prompt = f"Task: {payload_in.task}\n\nMasked Document Content:\n{tok_res.sanitized_text}"

    # Optional non-production adversarial simulation: reintroduce raw PII after masking
    if payload_in.simulate_tampered_outbound and settings.ENVIRONMENT != "production":
        leaked_sample = next(iter(tok_res.placeholder_to_original.values()), "ABCDE1234F")
        outbound_user_prompt += f"\n[TAMPERED_INJECTION]: {leaked_sample}"

    allowed_tokens = [p.placeholder for p in tok_res.placeholders]
    source_literal_tokens = [m.group(0) for m in PLACEHOLDER_REGEX.finditer(payload_in.text)]
    system_prompt = _SYSTEM_PROMPT
    if payload_in.purpose in ("property_verification", "legal_review"):
        system_prompt += (
            " Format your response using these exact numbered sections with '-' bullet points: "
            "1. Ownership Chain / Parties:, 2. Deed, Survey & CNR IDs:, "
            "3. Financial Consideration & Deadlines:, and 4. Risk & Red-Flag Clauses:."
        )

    outbound_payload = OutboundPayloadSchema(
        request_id=request_id,
        organization_id=org_id,
        provider=provider_name,
        model=model_name,
        purpose=payload_in.purpose,
        system_prompt=system_prompt,
        user_prompt=outbound_user_prompt,
        metadata={
            "document_category": payload_in.document_category,
            "policy_version": policy_version,
            "tokenization_mode": payload_in.tokenization_mode.value,
            "registered_placeholders": allowed_tokens,
        },
    )

    # Stage 4: INDEPENDENT OUTBOUND SECURITY VERIFICATION GATE
    gate = get_security_gate()
    gate_res = gate.inspect_and_authorize(
        payload=outbound_payload,
        known_sensitive_values=list(tok_res.placeholder_to_original.values()),
        allowed_placeholders=allowed_tokens,
        policy_approved=policy_decision.approved,
        policy_block_reason=policy_decision.reason,
        preexisting_source_tokens=source_literal_tokens,
    )
    local_ms = round((time.perf_counter() - t_local_start) * 1000.0, 2)
    trace.append(f"VERIFY(Gate={gate_res.decision.value}, leaks={gate_res.raw_pii_leak_count})")

    detection_schemas = [
        DetectedEntitySchema(
            entity_type=d.entity_type,
            category_tier=d.category_tier,
            start=d.start,
            end=d.end,
            confidence=d.confidence,
            recognizer=d.recognizer,
            normalized_value=d.normalized_value,
            matched_text=d.matched_text,
        )
        for d in detections
    ]

    if gate_res.decision != SecurityDecision.PASS or gate_res.ticket is None:
        req_status = (
            "blocked_policy"
            if policy_decision.approved is False
            else "blocked_security_gate"
        )
        trace.append(f"HALT({req_status})")
        AuditService.record_request_start(
            db=db,
            request_id=request_id,
            org_id=org_id,
            user_id=user_id,
            user_role=user_role,
            purpose=payload_in.purpose,
            document_category=payload_in.document_category,
            tokenization_mode=payload_in.tokenization_mode.value,
            policy_id=policy_id,
            policy_version=policy_version,
            provider=provider_name,
            model=model_name,
            status=req_status,
            detected_entity_counts=tok_res.detected_entity_counts,
            local_processing_ms=local_ms,
            raw_pii_leak_count=gate_res.raw_pii_leak_count,
            mapping_expires_at=tok_res.mapping_expires_at,
        )
        AuditService.record_detected_entities(db, request_id, detections, tok_res.placeholders)
        AuditService.record_outbound_audit(
            db=db,
            request_id=request_id,
            org_id=org_id,
            decision=gate_res.decision,
            reason=gate_res.reason,
            payload_sha256=gate_res.payload_sha256,
            sanitized_payload_text=outbound_user_prompt if not payload_in.simulate_tampered_outbound else "[BLOCKED_TAMPERED_PAYLOAD_REDACTED]",
            provider=provider_name,
            model=model_name,
            transmitted=False,
            checks_summary=gate_res.checks,
            raw_pii_leak_count=gate_res.raw_pii_leak_count,
        )
        AuditService.record_security_event(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            event_type="outbound_gate_blocked",
            severity="high",
            outcome=gate_res.decision.value,
            details={"reason": gate_res.reason, "checks": gate_res.checks, "raw_pii_leak_count": gate_res.raw_pii_leak_count},
        )
        db.commit()
        return ProcessResponse(
            request_id=request_id,
            status=req_status,
            document_category=payload_in.document_category,
            purpose=payload_in.purpose,
            tokenization_mode=payload_in.tokenization_mode,
            provider=provider_name,
            model=model_name,
            policy_version=policy_version,
            security_decision=gate_res.decision,
            security_reason=gate_res.reason,
            raw_pii_leak_count=gate_res.raw_pii_leak_count,
            gate_checks=gate_res.gate_checks,
            sanitized_outbound_payload=tok_res.sanitized_text,
            outbound_payload_sha256=gate_res.payload_sha256,
            detections=detection_schemas,
            placeholders=tok_res.placeholders,
            vault_metadata=tok_res.vault_metadata,
            detected_entity_counts=tok_res.detected_entity_counts,
            raw_llm_response=None,
            final_response=None,
            restoration=None,
            execution_trace=trace,
            mapping_expires_at=tok_res.mapping_expires_at,
            local_processing_ms=local_ms,
            llm_latency_ms=0.0,
            total_latency_ms=local_ms,
        )

    # Record allowed request + pre-call audit
    req_row = AuditService.record_request_start(
        db=db,
        request_id=request_id,
        org_id=org_id,
        user_id=user_id,
        user_role=user_role,
        purpose=payload_in.purpose,
        document_category=payload_in.document_category,
        tokenization_mode=payload_in.tokenization_mode.value,
        policy_id=policy_id,
        policy_version=policy_version,
        provider=provider_name,
        model=model_name,
        status="forwarding",
        detected_entity_counts=tok_res.detected_entity_counts,
        local_processing_ms=local_ms,
        raw_pii_leak_count=0,
        mapping_expires_at=tok_res.mapping_expires_at,
    )
    AuditService.record_detected_entities(db, request_id, detections, tok_res.placeholders)
    outbound_row = AuditService.record_outbound_audit(
        db=db,
        request_id=request_id,
        org_id=org_id,
        decision=gate_res.decision,
        reason=gate_res.reason,
        payload_sha256=gate_res.payload_sha256,
        sanitized_payload_text=outbound_user_prompt,
        provider=provider_name,
        model=model_name,
        transmitted=True,
        checks_summary=gate_res.checks,
        raw_pii_leak_count=0,
    )

    # Stage 5: FORWARD VERIFIED SANITIZED PAYLOAD (WITH POLICY-GATED LOCAL SLM FALLBACK)
    fallback_triggered = False
    fallback_reason: str | None = None
    active_provider = provider_name
    active_model = model_name

    async def _try_local_slm_fallback(reason: str):
        nonlocal fallback_triggered, fallback_reason, active_provider, active_model, gate_res
        slm_allowed = (
            payload_in.enable_fallback
            and settings.ENABLE_LOCAL_SLM_FALLBACK
            and policy_decision.policy is not None
            and "local_slm" in [p.lower() for p in (policy_decision.policy.allowed_providers or [])]
        )
        if not slm_allowed:
            return None
        slm_adapter = orchestrator.get_provider("local_slm")
        slm_model = slm_adapter.default_model()
        slm_payload = outbound_payload.model_copy(
            update={"provider": "local_slm", "model": slm_model}
        )
        slm_gate = gate.inspect_and_authorize(
            payload=slm_payload,
            known_sensitive_values=list(tok_res.placeholder_to_original.values()),
            allowed_placeholders=allowed_tokens,
            policy_approved=policy_decision.approved,
            policy_block_reason=policy_decision.reason,
            preexisting_source_tokens=source_literal_tokens,
        )
        if slm_gate.decision != SecurityDecision.PASS or slm_gate.ticket is None:
            return None
        fallback_triggered = True
        fallback_reason = reason
        active_provider = "local_slm"
        active_model = slm_model
        gate_res = slm_gate
        req_row.provider = active_provider
        req_row.model = active_model
        req_row.fallback_triggered = True
        outbound_row.provider = active_provider
        outbound_row.model = active_model
        outbound_row.sanitized_payload_hash = slm_gate.payload_sha256
        AuditService.record_security_event(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            event_type="local_slm_fallback_activated",
            severity="low",
            outcome="fallback_ok",
            details={"primary_provider": provider_name, "reason": reason},
        )
        return await orchestrator.dispatch(slm_payload, slm_gate.ticket)

    try:
        if payload_in.simulate_provider_offline and settings.ENVIRONMENT != "production" and provider_name != "local_slm":
            raise LLMProviderError(
                f"Simulated outage for primary provider '{provider_name}'.",
                error_code="simulated_provider_offline",
                status_code=503,
            )
        llm_res = await orchestrator.dispatch(outbound_payload, gate_res.ticket)
        trace.append(f"FORWARD({llm_res.provider}/{llm_res.model}, {llm_res.latency_ms}ms)")
    except SecurityGateViolationError as exc:
        req_row.status = "blocked_security_gate"
        AuditService.record_security_event(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            event_type="transport_boundary_violation",
            severity="critical",
            outcome="blocked",
            details={"reason": str(exc)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LLMProviderError as exc:
        fallback_res = await _try_local_slm_fallback(reason=str(exc))
        if fallback_res is not None:
            llm_res = fallback_res
            trace.append(f"FALLBACK(local_slm/{llm_res.model}, primary failed: {exc.error_code})")
        else:
            req_row.status = "provider_error"
            req_row.total_latency_ms = round((time.perf_counter() - t_total_start) * 1000.0, 2)
            AuditService.record_provider_usage(
                db=db,
                request_id=request_id,
                org_id=org_id,
                provider=provider_name,
                model=model_name,
                latency_ms=0.0,
                prompt_tokens=0,
                completion_tokens=0,
                success=False,
                error_code=exc.error_code,
            )
            AuditService.record_response_audit(
                db=db,
                request_id=request_id,
                org_id=org_id,
                provider_status=exc.error_code,
                report=RestorationReport(
                    restoration_status="not_executed",
                    authorized=policy_decision.can_restore,
                    restored_count=0,
                    valid_placeholders_found=[],
                    missing_placeholders=[],
                    unknown_or_forged_placeholders=[],
                    newly_generated_pii_count=0,
                    newly_generated_pii_types=[],
                ),
            )
            db.commit()
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    AuditService.record_provider_usage(
        db=db,
        request_id=request_id,
        org_id=org_id,
        provider=llm_res.provider,
        model=llm_res.model,
        latency_ms=llm_res.latency_ms,
        prompt_tokens=llm_res.prompt_tokens,
        completion_tokens=llm_res.completion_tokens,
        success=True,
    )

    llm_raw_content = llm_res.content
    if payload_in.simulate_forged_token and settings.ENVIRONMENT != "production":
        llm_raw_content += "\n[UNVERIFIED_LLM_ARTIFACT]: <PAN_FORGED99>"

    # Stage 6 & 7: INSPECT RESPONSE & AUTHORIZED LOCAL RESTORATION
    restorer = get_response_engine()
    try:
        restoration_outcome = restorer.process_response(
            org_id=org_id,
            request_id=request_id,
            response_text=llm_raw_content,
            authorized_to_restore=policy_decision.can_restore,
            restore_requested=payload_in.restore_response,
        )
    except VaultUnavailableError as exc:
        req_row.status = "failed_closed"
        AuditService.record_security_event(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            event_type="vault_unavailable_during_restore",
            severity="critical",
            outcome="failed_closed",
            details={"reason": "Vault unavailable during response restoration"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Privacy vault unavailable during restoration; response withheld fail-closed.",
        ) from exc

    trace.append(
        f"INSPECT_&_RESTORE({restoration_outcome.report.restoration_status}, restored={restoration_outcome.report.restored_count}, forged={len(restoration_outcome.report.unknown_or_forged_placeholders)})"
    )

    if restoration_outcome.report.unknown_or_forged_placeholders:
        AuditService.record_security_event(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            event_type="unknown_placeholder_in_response",
            severity="medium",
            outcome="flagged",
            details={"tokens": restoration_outcome.report.unknown_or_forged_placeholders},
        )
    if restoration_outcome.report.newly_generated_pii_count > 0:
        AuditService.record_security_event(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            event_type="newly_generated_pii_detected",
            severity="medium",
            outcome="flagged",
            details={"types": restoration_outcome.report.newly_generated_pii_types},
        )

    # Stage 8: FINALIZE AUDIT
    total_ms = round((time.perf_counter() - t_total_start) * 1000.0, 2)
    req_row.status = "completed"
    req_row.total_latency_ms = total_ms
    AuditService.record_response_audit(
        db=db,
        request_id=request_id,
        org_id=org_id,
        provider_status="fallback_ok" if fallback_triggered else "ok",
        report=restoration_outcome.report,
    )
    trace.append(f"AUDIT(completed in {total_ms}ms)")
    db.commit()

    return ProcessResponse(
        request_id=request_id,
        status="completed",
        document_category=payload_in.document_category,
        purpose=payload_in.purpose,
        tokenization_mode=payload_in.tokenization_mode,
        provider=llm_res.provider,
        model=llm_res.model,
        fallback_triggered=fallback_triggered,
        fallback_reason=fallback_reason,
        policy_version=policy_version,
        security_decision=gate_res.decision,
        security_reason=gate_res.reason,
        raw_pii_leak_count=0,
        gate_checks=gate_res.gate_checks,
        sanitized_outbound_payload=outbound_user_prompt,
        outbound_payload_sha256=gate_res.payload_sha256,
        detections=detection_schemas,
        placeholders=tok_res.placeholders,
        vault_metadata=tok_res.vault_metadata,
        detected_entity_counts=tok_res.detected_entity_counts,
        raw_llm_response=llm_raw_content,
        final_response=restoration_outcome.final_text,
        restoration=restoration_outcome.report,
        execution_trace=trace,
        mapping_expires_at=tok_res.mapping_expires_at,
        local_processing_ms=local_ms,
        llm_latency_ms=llm_res.latency_ms,
        total_latency_ms=total_ms,
    )
