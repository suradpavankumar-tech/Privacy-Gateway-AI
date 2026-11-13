from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Role
from app.models.entities import PrivacyPolicy
from app.services.detection.engine import ALL_SUPPORTED_ENTITIES, DetectionItem

DEFAULT_POLICY_TEMPLATES = [
    {
        "name": "Loan Underwriting Privacy Policy",
        "purpose": "loan_underwriting",
        "allowed_providers": ["gemini", "openai", "local_slm"],
        "blocked_entities": [],
        "mask_entities": ALL_SUPPORTED_ENTITIES,
        "allow_restoration_roles": [
            Role.ADMIN.value,
            Role.SECURITY_OFFICER.value,
            Role.PRIVACY_OFFICER.value,
            Role.LOAN_UNDERWRITER.value,
        ],
        "retention_days": 90,
        "mapping_ttl_seconds": 900,
    },
    {
        "name": "KYC Verification Privacy Policy",
        "purpose": "kyc_verification",
        "allowed_providers": ["gemini", "openai", "local_slm"],
        "blocked_entities": [],
        "mask_entities": ALL_SUPPORTED_ENTITIES,
        "allow_restoration_roles": [
            Role.ADMIN.value,
            Role.SECURITY_OFFICER.value,
            Role.PRIVACY_OFFICER.value,
            Role.LOAN_UNDERWRITER.value,
        ],
        "retention_days": 180,
        "mapping_ttl_seconds": 900,
    },
    {
        "name": "Customer Support Triage Policy",
        "purpose": "customer_support",
        "allowed_providers": ["gemini", "openai", "local_slm"],
        "blocked_entities": [],
        "mask_entities": ALL_SUPPORTED_ENTITIES,
        "allow_restoration_roles": [
            Role.ADMIN.value,
            Role.SECURITY_OFFICER.value,
            Role.PRIVACY_OFFICER.value,
            Role.SUPPORT_AGENT.value,
        ],
        "retention_days": 60,
        "mapping_ttl_seconds": 600,
    },
    {
        "name": "Insurance Claims Processing Policy",
        "purpose": "insurance_claims",
        "allowed_providers": ["gemini", "openai", "local_slm"],
        "blocked_entities": [],
        "mask_entities": ALL_SUPPORTED_ENTITIES,
        "allow_restoration_roles": [
            Role.ADMIN.value,
            Role.SECURITY_OFFICER.value,
            Role.PRIVACY_OFFICER.value,
            Role.LOAN_UNDERWRITER.value,
        ],
        "retention_days": 180,
        "mapping_ttl_seconds": 900,
    },
    {
        "name": "Marketing Analytics Strict Policy (Blocks Aadhaar & Passport)",
        "purpose": "marketing_analytics",
        "allowed_providers": ["gemini", "local_slm"],
        "blocked_entities": ["AADHAAR", "PASSPORT", "VOTER_ID", "BANK_ACCOUNT"],
        "mask_entities": ALL_SUPPORTED_ENTITIES,
        "allow_restoration_roles": [Role.ADMIN.value, Role.PRIVACY_OFFICER.value],
        "retention_days": 30,
        "mapping_ttl_seconds": 300,
    },
    {
        "name": "Property & Title Verification Policy",
        "purpose": "property_verification",
        "allowed_providers": ["gemini", "openai", "local_slm"],
        "blocked_entities": [],
        "mask_entities": ALL_SUPPORTED_ENTITIES,
        "allow_restoration_roles": [
            Role.ADMIN.value,
            Role.SECURITY_OFFICER.value,
            Role.PRIVACY_OFFICER.value,
            Role.LOAN_UNDERWRITER.value,
        ],
        "retention_days": 180,
        "mapping_ttl_seconds": 900,
    },
    {
        "name": "Legal & Contract Review Policy",
        "purpose": "legal_review",
        "allowed_providers": ["gemini", "openai", "local_slm"],
        "blocked_entities": [],
        "mask_entities": ALL_SUPPORTED_ENTITIES,
        "allow_restoration_roles": [
            Role.ADMIN.value,
            Role.SECURITY_OFFICER.value,
            Role.PRIVACY_OFFICER.value,
        ],
        "retention_days": 365,
        "mapping_ttl_seconds": 900,
    },
    {
        "name": "General Document Summarization Policy",
        "purpose": "document_summarization",
        "allowed_providers": ["gemini", "openai", "local_slm"],
        "blocked_entities": [],
        "mask_entities": ALL_SUPPORTED_ENTITIES,
        "allow_restoration_roles": [
            Role.ADMIN.value,
            Role.SECURITY_OFFICER.value,
            Role.PRIVACY_OFFICER.value,
            Role.LOAN_UNDERWRITER.value,
        ],
        "retention_days": 90,
        "mapping_ttl_seconds": 900,
    },
]


@dataclass
class PolicyDecision:
    policy: PrivacyPolicy | None
    approved: bool | None
    reason: str
    can_restore: bool


def ensure_default_policies(db: Session, org_id: str) -> list[PrivacyPolicy]:
    existing = list(
        db.scalars(select(PrivacyPolicy).where(PrivacyPolicy.organization_id == org_id)).all()
    )
    existing_purposes = {p.purpose for p in existing}
    created: list[PrivacyPolicy] = []
    for tpl in DEFAULT_POLICY_TEMPLATES:
        if tpl["purpose"] not in existing_purposes:
            pol = PrivacyPolicy(organization_id=org_id, **tpl)
            db.add(pol)
            created.append(pol)
    if created:
        db.commit()
        for pol in created:
            db.refresh(pol)
    return existing + created


def evaluate_policy(
    db: Session,
    org_id: str,
    purpose: str,
    role: str,
    provider: str,
    detections: list[DetectionItem],
) -> PolicyDecision:
    try:
        policy = db.scalar(
            select(PrivacyPolicy)
            .where(
                PrivacyPolicy.organization_id == org_id,
                PrivacyPolicy.purpose == purpose,
                PrivacyPolicy.is_active.is_(True),
            )
            .order_by(PrivacyPolicy.version.desc())
        )
        if policy is None:
            policy = db.scalar(
                select(PrivacyPolicy)
                .where(
                    PrivacyPolicy.organization_id == org_id,
                    PrivacyPolicy.purpose == "document_summarization",
                    PrivacyPolicy.is_active.is_(True),
                )
                .order_by(PrivacyPolicy.version.desc())
            )
    except Exception:
        return PolicyDecision(
            policy=None,
            approved=None,
            reason="Privacy policy lookup failed; failing closed.",
            can_restore=False,
        )

    if policy is None:
        return PolicyDecision(
            policy=None,
            approved=None,
            reason=f"No active privacy policy found for purpose '{purpose}'; failing closed.",
            can_restore=False,
        )

    if provider.lower() not in [p.lower() for p in (policy.allowed_providers or [])]:
        return PolicyDecision(
            policy=policy,
            approved=False,
            reason=f"Provider '{provider}' is prohibited by policy '{policy.name}' for purpose '{purpose}'.",
            can_restore=False,
        )

    blocked_set = set(policy.blocked_entities or [])
    detected_types = {d.entity_type for d in detections}
    violating = sorted(blocked_set & detected_types)
    if violating:
        return PolicyDecision(
            policy=policy,
            approved=False,
            reason=f"Policy '{policy.name}' blocks processing entities {violating} for purpose '{purpose}'.",
            can_restore=False,
        )

    # Auditors are strictly read-only; all other roles obey the active policy matrix
    can_restore = (
        role != Role.AUDITOR.value
        and role in (policy.allow_restoration_roles or [])
    )
    return PolicyDecision(
        policy=policy,
        approved=True,
        reason=f"Approved under policy '{policy.name}' v{policy.version}.",
        can_restore=can_restore,
    )
