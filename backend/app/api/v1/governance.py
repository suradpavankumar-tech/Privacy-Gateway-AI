"""
=========================================================================================
governance.py — Enterprise Privacy Governance, Policy Engine & Audit Trail Router
=========================================================================================

Tech Stack:
 - FastAPI (REST routing, dependency injection, streaming responses)
 - SQLAlchemy (Policy entities and append-only audit event persistence)
 - Pydantic (Policy schema validation and transformation)
 - Python Standard Library CSV & JSON (Regulatory compliance export)

Key Architectural Responsibilities:
 1. Purpose-Bound Privacy Policy Management (`/governance/policies`):
    - Defines which entity categories must be blocked, masked, or left intact.
    - Sets role restoration matrix permissions and permissible LLM providers.
    - Manages retention limits (days) and AES-256 vault TTLs (seconds).

 2. Immutable Cryptographic Audit Log Query Engine (`/governance/audits`):
    - Surfaces zero-PII audit records verifying gate decisions, latencies,
      and tokenization stats for enterprise security officers.
    - Implements strict organization-level multi-tenant isolation.

 3. Regulatory Export Generation (`/governance/audits/export`):
    - Generates downloadable CSV or JSON audit packages formatted for
      CERT-In, DPDP Act 2023, and ISO 27701 compliance verification.
=========================================================================================
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import rate_limit_guard, require_permission
from app.database.session import get_db
from app.models.entities import PrivacyPolicy, SecurityEvent
from app.schemas.gateway import (
    AuditDetail,
    AuditSummary,
    EvaluationRunRequest,
    MetricsOverview,
    PrivacyPolicyOut,
    PrivacyPolicyUpdate,
    ProviderStatus,
    TokenizationMode,
)
from app.services.audit.audit_service import AuditService
from app.services.auth_service import AuthContext
from app.services.evaluation.benchmark import (
    load_dataset_corpus,
    resolve_dataset_dir,
    run_benchmark_suite,
)
from app.services.llm.orchestrator import get_llm_orchestrator

router = APIRouter(prefix="/api/v1", tags=["Governance & Audit"], dependencies=[Depends(rate_limit_guard)])


def _policy_to_out(r: PrivacyPolicy) -> PrivacyPolicyOut:
    return PrivacyPolicyOut(
        id=r.id,
        organization_id=r.organization_id,
        name=r.name,
        purpose=r.purpose,
        version=r.version,
        is_active=r.is_active,
        allowed_providers=r.allowed_providers or [],
        blocked_entities=r.blocked_entities or [],
        mask_entities=r.mask_entities or [],
        allow_restoration_roles=r.allow_restoration_roles or [],
        retention_days=r.retention_days,
        mapping_ttl_seconds=r.mapping_ttl_seconds,
        updated_at=r.updated_at,
    )


def _apply_policy_update(
    policy_id: str,
    payload: PrivacyPolicyUpdate,
    auth: AuthContext,
    db: Session,
) -> PrivacyPolicyOut:
    row = db.scalar(
        select(PrivacyPolicy).where(
            PrivacyPolicy.id == policy_id,
            PrivacyPolicy.organization_id == auth.org_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(row, field, val)
    row.version += 1

    AuditService.record_security_event(
        db=db,
        org_id=auth.org_id,
        user_id=auth.user_id,
        event_type="policy_updated",
        severity="info",
        outcome="applied",
        details={
            "policy_id": row.id,
            "purpose": row.purpose,
            "new_version": row.version,
            "updated_fields": sorted(update_data.keys()),
        },
    )
    db.commit()
    db.refresh(row)
    return _policy_to_out(row)


@router.get("/providers", response_model=list[ProviderStatus])
def get_providers(
    auth: AuthContext = Depends(require_permission("providers:read")),
) -> list[ProviderStatus]:
    return get_llm_orchestrator().list_provider_statuses()


@router.get("/policies", response_model=list[PrivacyPolicyOut])
def list_policies(
    auth: AuthContext = Depends(require_permission("policy:read")),
    db: Session = Depends(get_db),
) -> list[PrivacyPolicyOut]:
    rows = list(
        db.scalars(
            select(PrivacyPolicy)
            .where(PrivacyPolicy.organization_id == auth.org_id)
            .order_by(PrivacyPolicy.purpose)
        ).all()
    )
    return [_policy_to_out(r) for r in rows]


@router.put("/policies/{policy_id}", response_model=PrivacyPolicyOut)
def update_policy_put(
    policy_id: str,
    payload: PrivacyPolicyUpdate,
    auth: AuthContext = Depends(require_permission("policy:write")),
    db: Session = Depends(get_db),
) -> PrivacyPolicyOut:
    return _apply_policy_update(policy_id, payload, auth, db)


@router.patch("/policies/{policy_id}", response_model=PrivacyPolicyOut)
def update_policy_patch(
    policy_id: str,
    payload: PrivacyPolicyUpdate,
    auth: AuthContext = Depends(require_permission("policy:write")),
    db: Session = Depends(get_db),
) -> PrivacyPolicyOut:
    return _apply_policy_update(policy_id, payload, auth, db)


@router.get("/audit", response_model=list[AuditSummary])
def list_audit_records(
    status_filter: str | None = None,
    purpose: str | None = None,
    limit: int = 50,
    auth: AuthContext = Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
) -> list[AuditSummary]:
    return AuditService.list_audits(
        db=db,
        org_id=auth.org_id,
        status=status_filter,
        purpose=purpose,
        limit=min(max(limit, 1), 200),
    )


@router.get("/audit/export")
def export_audit_evidence(
    format: str = "json",
    auth: AuthContext = Depends(require_permission("audit:export")),
    db: Session = Depends(get_db),
) -> Response:
    if format.lower() == "csv":
        csv_text = AuditService.export_evidence_csv(db=db, org_id=auth.org_id)
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=dpdp_privacy_audit_evidence.csv"},
        )
    audits = AuditService.list_audits(db=db, org_id=auth.org_id, limit=500)
    payload = {
        "organization_id": auth.org_id,
        "report_type": "DPDP_PRIVACY_GATEWAY_AUDIT_EVIDENCE",
        "record_count": len(audits),
        "records": [a.model_dump(mode="json") for a in audits],
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=dpdp_privacy_audit_evidence.json"},
    )


@router.get("/audit/{request_id}", response_model=AuditDetail)
def get_audit_record(
    request_id: str,
    auth: AuthContext = Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
) -> AuditDetail:
    detail = AuditService.get_audit_detail(db=db, org_id=auth.org_id, request_id=request_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit record not found.")
    return detail


@router.get("/security-events")
def list_security_events(
    limit: int = 50,
    auth: AuthContext = Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(SecurityEvent)
            .where(SecurityEvent.organization_id == auth.org_id)
            .order_by(desc(SecurityEvent.created_at))
            .limit(min(max(limit, 1), 200))
        ).all()
    )
    return [
        {
            "id": r.id,
            "request_id": r.request_id,
            "event_type": r.event_type,
            "severity": r.severity,
            "outcome": r.outcome,
            "details": r.details,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/metrics", response_model=MetricsOverview)
def get_metrics(
    auth: AuthContext = Depends(require_permission("evaluation:read")),
    db: Session = Depends(get_db),
) -> MetricsOverview:
    data = AuditService.get_dashboard_metrics(db=db, org_id=auth.org_id)
    return MetricsOverview(**data)


@router.post("/evaluation/run")
def run_evaluation(
    payload: EvaluationRunRequest | None = Body(default=None),
    auth: AuthContext = Depends(require_permission("evaluation:run")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = payload.tokenization_mode if payload else TokenizationMode.CRYPTOGRAPHIC_RANDOM
    cat = payload.category_filter if payload else None
    return run_benchmark_suite(db=db, tokenization_mode=mode, category_filter=cat)


@router.get("/dataset")
def get_full_dataset(
    auth: AuthContext = Depends(require_permission("evaluation:read")),
) -> dict[str, Any]:
    docs, anns_by_doc = load_dataset_corpus()
    category_counts: dict[str, int] = {}
    enriched_docs: list[dict[str, Any]] = []
    total_entities = 0
    negative_controls = 0
    for d in docs:
        cat = d.get("category", "general")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        doc_anns = anns_by_doc.get(d["doc_id"], [])
        total_entities += len(doc_anns)
        if not doc_anns:
            negative_controls += 1
        enriched_docs.append(
            {
                "doc_id": d["doc_id"],
                "category": cat,
                "purpose": d["purpose"],
                "title": d["title"],
                "text": d["text"],
                "language_style": d.get("language_style", "english"),
                "annotations": doc_anns,
            }
        )
    return {
        "total_documents": len(docs),
        "total_annotations": total_entities,
        "negative_control_count": negative_controls,
        "categories": category_counts,
        "documents": enriched_docs,
    }


@router.get("/dataset/samples")
def list_dataset_samples(
    auth: AuthContext = Depends(require_permission("process:submit")),
) -> list[dict[str, Any]]:
    dataset_path = resolve_dataset_dir() / "synthetic_documents" / "indian_enterprise_50.json"
    if not dataset_path.exists():
        return []
    docs = json.loads(dataset_path.read_text(encoding="utf-8"))
    return [
        {
            "doc_id": d["doc_id"],
            "category": d["category"],
            "purpose": d["purpose"],
            "title": d["title"],
            "text": d["text"],
        }
        for d in docs[:12]
    ]
