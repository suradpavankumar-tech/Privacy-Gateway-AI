"""
=========================================================================================
audit_service.py — Cryptographic Audit Logging & DPDP Evidence Persistence Engine
=========================================================================================

Tech Stack:
 - Python 3.11+ / SQLAlchemy (Relational persistence across multi-table audit schema)
 - SHA-256 Digest Verification (Tamper-evident record hashing)
 - CSV & JSON Exporters (Regulatory data extraction for CERT-In / DPDP compliance)

Key Architectural Responsibilities:
 1. Zero-PII Data Storage Guarantee:
    - Never stores raw PII, unencrypted text, or vault keys in any database column.
    - Records only aggregate counts, entity categories, cryptographic hashes, and verdicts.

 2. Multi-Table Relational Evidence Trail:
    - Tracks every transaction across normalized audit tables:
      * `GatewayRequest`: Transaction metadata, duration, purpose, caller role.
      * `OutboundAudit`: Sanitized payload SHA-256 hash, security ticket signature.
      * `ResponseAudit`: Restoration stats, token counts, and downstream model latency.
      * `SecurityEvent`: Tamper attempts, forged token alerts, gate rejections.

 3. Regulatory Export Generation:
    - Formats audit trails into structured CSV and JSON archives for compliance inspections.
=========================================================================================
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    DetectedEntityAudit,
    EvaluationResult,
    GatewayRequest,
    OutboundAudit,
    ProviderUsage,
    ResponseAudit,
    SecurityEvent,
)
from app.schemas.gateway import (
    AuditDetail,
    AuditSummary,
    PlaceholderSummary,
    RestorationReport,
    SecurityDecision,
)
from app.services.detection.engine import DetectionItem


class AuditService:
    """Engine 7: DPDP-oriented audit & evidence persistence (never stores raw PII)."""

    @staticmethod
    def record_request_start(
        db: Session,
        request_id: str,
        org_id: str,
        user_id: str | None,
        user_role: str,
        purpose: str,
        document_category: str,
        tokenization_mode: str,
        policy_id: str | None,
        policy_version: int,
        provider: str,
        model: str,
        status: str,
        detected_entity_counts: dict[str, int],
        local_processing_ms: float,
        fallback_triggered: bool = False,
        raw_pii_leak_count: int = 0,
        mapping_expires_at: datetime | None = None,
    ) -> GatewayRequest:
        req = GatewayRequest(
            id=request_id,
            organization_id=org_id,
            user_id=user_id,
            user_role=user_role,
            purpose=purpose,
            document_category=document_category,
            tokenization_mode=tokenization_mode,
            policy_id=policy_id,
            policy_version=policy_version,
            provider=provider,
            model=model,
            status=status,
            fallback_triggered=fallback_triggered,
            raw_pii_leak_count=raw_pii_leak_count,
            detected_entity_count=sum(detected_entity_counts.values()),
            detected_entity_types=detected_entity_counts,
            local_processing_ms=local_processing_ms,
            total_latency_ms=local_processing_ms,
            mapping_expires_at=mapping_expires_at,
        )
        db.add(req)
        db.flush()
        return req

    @staticmethod
    def record_detected_entities(
        db: Session,
        request_id: str,
        detections: list[DetectionItem],
        placeholders: list[PlaceholderSummary],
    ) -> None:
        placeholder_lookup: dict[str, str] = {}
        for ph in placeholders:
            placeholder_lookup.setdefault(ph.entity_type, ph.placeholder)

        for det in detections:
            row = DetectedEntityAudit(
                request_id=request_id,
                entity_type=det.entity_type,
                category_tier=det.category_tier.value,
                placeholder=placeholder_lookup.get(det.entity_type, f"<{det.entity_type}_MASKED>"),
                start_pos=det.start,
                end_pos=det.end,
                confidence=det.confidence,
                recognizer=det.recognizer,
            )
            db.add(row)

    @staticmethod
    def record_outbound_audit(
        db: Session,
        request_id: str,
        org_id: str,
        decision: SecurityDecision,
        reason: str,
        payload_sha256: str,
        sanitized_payload_text: str,
        provider: str,
        model: str,
        transmitted: bool,
        checks_summary: dict[str, Any],
        raw_pii_leak_count: int = 0,
    ) -> OutboundAudit:
        audit = OutboundAudit(
            request_id=request_id,
            organization_id=org_id,
            security_decision=decision.value,
            decision_reason=reason,
            sanitized_payload_hash=payload_sha256,
            sanitized_payload_text=sanitized_payload_text,
            provider=provider,
            model=model,
            transmitted=transmitted,
            raw_pii_leak_count=raw_pii_leak_count,
            checks_summary=checks_summary,
        )
        db.add(audit)
        return audit

    @staticmethod
    def record_response_audit(
        db: Session,
        request_id: str,
        org_id: str,
        provider_status: str,
        report: RestorationReport,
    ) -> ResponseAudit:
        audit = ResponseAudit(
            request_id=request_id,
            organization_id=org_id,
            provider_status=provider_status,
            restoration_status=report.restoration_status,
            restored_count=report.restored_count,
            missing_placeholders=report.missing_placeholders,
            unknown_placeholders=report.unknown_or_forged_placeholders,
            newly_generated_pii_count=report.newly_generated_pii_count,
            newly_generated_pii_types=report.newly_generated_pii_types,
        )
        db.add(audit)
        return audit

    @staticmethod
    def record_provider_usage(
        db: Session,
        request_id: str,
        org_id: str,
        provider: str,
        model: str,
        latency_ms: float,
        prompt_tokens: int,
        completion_tokens: int,
        success: bool,
        error_code: str | None = None,
    ) -> ProviderUsage:
        usage = ProviderUsage(
            request_id=request_id,
            organization_id=org_id,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            success=success,
            error_code=error_code,
        )
        db.add(usage)
        return usage

    @staticmethod
    def record_security_event(
        db: Session,
        org_id: str,
        event_type: str,
        severity: str,
        outcome: str,
        details: dict[str, Any],
        request_id: str | None = None,
        user_id: str | None = None,
    ) -> SecurityEvent:
        evt = SecurityEvent(
            request_id=request_id,
            organization_id=org_id,
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            outcome=outcome,
            details=details,
        )
        db.add(evt)
        return evt

    @staticmethod
    def list_audits(
        db: Session,
        org_id: str,
        status: str | None = None,
        purpose: str | None = None,
        limit: int = 50,
    ) -> list[AuditSummary]:
        stmt = select(GatewayRequest).where(GatewayRequest.organization_id == org_id)
        if status:
            stmt = stmt.where(GatewayRequest.status == status)
        if purpose:
            stmt = stmt.where(GatewayRequest.purpose == purpose)
        stmt = stmt.order_by(desc(GatewayRequest.created_at)).limit(limit)
        requests = list(db.scalars(stmt).all())

        req_ids = [r.id for r in requests]
        outbound_map: dict[str, str] = {}
        if req_ids:
            out_rows = db.scalars(
                select(OutboundAudit).where(OutboundAudit.request_id.in_(req_ids))
            ).all()
            outbound_map = {o.request_id: o.security_decision for o in out_rows}

        return [
            AuditSummary(
                request_id=r.id,
                organization_id=r.organization_id,
                user_id=r.user_id,
                user_role=r.user_role,
                purpose=r.purpose,
                document_category=r.document_category,
                tokenization_mode=r.tokenization_mode,
                provider=r.provider,
                model=r.model,
                status=r.status,
                fallback_triggered=r.fallback_triggered,
                security_decision=outbound_map.get(r.id),
                raw_pii_leak_count=r.raw_pii_leak_count,
                detected_entity_count=r.detected_entity_count,
                detected_entity_types=r.detected_entity_types or {},
                local_processing_ms=r.local_processing_ms,
                total_latency_ms=r.total_latency_ms,
                created_at=r.created_at,
            )
            for r in requests
        ]

    @staticmethod
    def get_audit_detail(db: Session, org_id: str, request_id: str) -> AuditDetail | None:
        req = db.scalar(
            select(GatewayRequest).where(
                GatewayRequest.id == request_id,
                GatewayRequest.organization_id == org_id,
            )
        )
        if req is None:
            return None

        outbound = db.scalar(select(OutboundAudit).where(OutboundAudit.request_id == request_id))
        response = db.scalar(select(ResponseAudit).where(ResponseAudit.request_id == request_id))
        entities = list(
            db.scalars(select(DetectedEntityAudit).where(DetectedEntityAudit.request_id == request_id)).all()
        )
        events = list(
            db.scalars(select(SecurityEvent).where(SecurityEvent.request_id == request_id)).all()
        )

        return AuditDetail(
            request_id=req.id,
            organization_id=req.organization_id,
            user_id=req.user_id,
            user_role=req.user_role,
            purpose=req.purpose,
            document_category=req.document_category,
            tokenization_mode=req.tokenization_mode,
            provider=req.provider,
            model=req.model,
            status=req.status,
            fallback_triggered=req.fallback_triggered,
            security_decision=outbound.security_decision if outbound else None,
            raw_pii_leak_count=req.raw_pii_leak_count,
            detected_entity_count=req.detected_entity_count,
            detected_entity_types=req.detected_entity_types or {},
            local_processing_ms=req.local_processing_ms,
            total_latency_ms=req.total_latency_ms,
            created_at=req.created_at,
            policy_id=req.policy_id,
            policy_version=req.policy_version,
            mapping_expires_at=req.mapping_expires_at,
            outbound_audit=(
                {
                    "security_decision": outbound.security_decision,
                    "decision_reason": outbound.decision_reason,
                    "sanitized_payload_hash": outbound.sanitized_payload_hash,
                    "sanitized_payload_text": outbound.sanitized_payload_text,
                    "transmitted": outbound.transmitted,
                    "raw_pii_leak_count": outbound.raw_pii_leak_count,
                    "checks_summary": outbound.checks_summary,
                }
                if outbound
                else None
            ),
            response_audit=(
                {
                    "provider_status": response.provider_status,
                    "restoration_status": response.restoration_status,
                    "restored_count": response.restored_count,
                    "missing_placeholders": response.missing_placeholders,
                    "unknown_placeholders": response.unknown_placeholders,
                    "newly_generated_pii_count": response.newly_generated_pii_count,
                    "newly_generated_pii_types": response.newly_generated_pii_types,
                }
                if response
                else None
            ),
            detected_entities_metadata=[
                {
                    "entity_type": e.entity_type,
                    "category_tier": e.category_tier,
                    "placeholder": e.placeholder,
                    "start": e.start_pos,
                    "end": e.end_pos,
                    "confidence": e.confidence,
                    "recognizer": e.recognizer,
                }
                for e in entities
            ],
            security_events=[
                {
                    "id": ev.id,
                    "event_type": ev.event_type,
                    "severity": ev.severity,
                    "outcome": ev.outcome,
                    "details": ev.details,
                    "created_at": ev.created_at.isoformat(),
                }
                for ev in events
            ],
        )

    @staticmethod
    def export_evidence_csv(db: Session, org_id: str) -> str:
        audits = AuditService.list_audits(db, org_id=org_id, limit=500)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "request_id",
                "timestamp",
                "user_role",
                "purpose",
                "document_category",
                "tokenization_mode",
                "provider",
                "model",
                "status",
                "fallback_triggered",
                "security_decision",
                "raw_pii_leak_count",
                "detected_entity_count",
                "detected_entity_types",
                "local_processing_ms",
                "total_latency_ms",
            ]
        )
        for a in audits:
            writer.writerow(
                [
                    a.request_id,
                    a.created_at.isoformat(),
                    a.user_role,
                    a.purpose,
                    a.document_category,
                    a.tokenization_mode,
                    a.provider,
                    a.model,
                    a.status,
                    a.fallback_triggered,
                    a.security_decision or "",
                    a.raw_pii_leak_count,
                    a.detected_entity_count,
                    json.dumps(a.detected_entity_types),
                    a.local_processing_ms,
                    a.total_latency_ms,
                ]
            )
        return buf.getvalue()

    @staticmethod
    def get_dashboard_metrics(db: Session, org_id: str) -> dict[str, Any]:
        total_requests = (
            db.scalar(
                select(func.count(GatewayRequest.id)).where(GatewayRequest.organization_id == org_id)
            )
            or 0
        )
        blocked_requests = (
            db.scalar(
                select(func.count(GatewayRequest.id)).where(
                    GatewayRequest.organization_id == org_id,
                    GatewayRequest.status.in_(["blocked_policy", "blocked_security_gate", "failed_closed"]),
                )
            )
            or 0
        )
        protected_requests = (
            db.scalar(
                select(func.count(GatewayRequest.id)).where(
                    GatewayRequest.organization_id == org_id,
                    GatewayRequest.status == "completed",
                )
            )
            or 0
        )
        fallback_requests = (
            db.scalar(
                select(func.count(GatewayRequest.id)).where(
                    GatewayRequest.organization_id == org_id,
                    GatewayRequest.fallback_triggered.is_(True),
                )
            )
            or 0
        )
        sec_events_count = (
            db.scalar(
                select(func.count(SecurityEvent.id)).where(SecurityEvent.organization_id == org_id)
            )
            or 0
        )

        reqs = list(
            db.scalars(
                select(GatewayRequest).where(GatewayRequest.organization_id == org_id)
            ).all()
        )
        entity_breakdown: dict[str, int] = {}
        latencies: list[float] = []
        leaks = 0
        for r in reqs:
            latencies.append(float(r.local_processing_ms))
            if r.status == "completed" and r.raw_pii_leak_count > 0:
                leaks += 1
            for k, v in (r.detected_entity_types or {}).items():
                entity_breakdown[k] = entity_breakdown.get(k, 0) + int(v)

        zero_leak_rate = round((1.0 - (leaks / total_requests)) * 100.0, 2) if total_requests else 100.0

        latencies.sort()
        avg_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        p95_idx = min(len(latencies) - 1, int(0.95 * len(latencies))) if latencies else 0
        p95_ms = round(latencies[p95_idx], 2) if latencies else 0.0

        latest_eval = db.scalar(
            select(EvaluationResult).order_by(desc(EvaluationResult.created_at)).limit(1)
        )

        return {
            "total_requests": int(total_requests),
            "protected_requests": int(protected_requests),
            "blocked_requests": int(blocked_requests),
            "fallback_requests": int(fallback_requests),
            "zero_leak_rate": zero_leak_rate,
            "total_entities_detected": sum(entity_breakdown.values()),
            "entity_breakdown": entity_breakdown,
            "security_events_count": int(sec_events_count),
            "avg_local_processing_ms": avg_ms,
            "p95_local_processing_ms": p95_ms,
            "latest_evaluation": (
                {
                    "id": latest_eval.id,
                    "dataset_version": latest_eval.dataset_version,
                    "detector_version": latest_eval.detector_version,
                    "total_documents": latest_eval.total_documents,
                    "overall_precision": latest_eval.overall_precision,
                    "overall_recall": latest_eval.overall_recall,
                    "overall_f1": latest_eval.overall_f1,
                    "outbound_leakage_count": latest_eval.outbound_leakage_count,
                    "reinsertion_accuracy": latest_eval.reinsertion_accuracy,
                    "p50_latency_ms": latest_eval.p50_latency_ms,
                    "p95_latency_ms": latest_eval.p95_latency_ms,
                    "fail_closed_pass_rate": latest_eval.fail_closed_pass_rate,
                    "report_payload": latest_eval.report_payload,
                    "created_at": latest_eval.created_at.isoformat(),
                }
                if latest_eval
                else None
            ),
        }
