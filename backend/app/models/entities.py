from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    members: Mapped[list[OrganizationMember]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    memberships: Mapped[list[OrganizationMember]] = relationship(back_populates="user")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    department: Mapped[str] = mapped_column(String(100), default="enterprise", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    organization: Mapped[Organization] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class PrivacyPolicy(Base):
    __tablename__ = "privacy_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allowed_providers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    blocked_entities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    mask_entities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    allow_restoration_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    mapping_ttl_seconds: Mapped[int] = mapped_column(Integer, default=900, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class GatewayRequest(Base):
    __tablename__ = "requests"
    __table_args__ = (Index("ix_requests_org_created", "organization_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_role: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    document_category: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("privacy_policies.id", ondelete="SET NULL"), nullable=True
    )
    policy_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tokenization_mode: Mapped[str] = mapped_column(String(50), default="cryptographic_random", nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fallback_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_pii_leak_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    detected_entity_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    detected_entity_types: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    local_processing_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mapping_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DetectedEntityAudit(Base):
    """Stores metadata about detected entities only — NEVER raw original PII values."""

    __tablename__ = "detected_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    category_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    placeholder: Mapped[str] = mapped_column(String(120), nullable=False)
    start_pos: Mapped[int] = mapped_column(Integer, nullable=False)
    end_pos: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    recognizer: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class OutboundAudit(Base):
    """Stores exact sanitized outbound payload & SHA-256 hash + security gate decision."""

    __tablename__ = "outbound_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    security_decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    sanitized_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sanitized_payload_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    transmitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_pii_leak_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checks_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ResponseAudit(Base):
    __tablename__ = "response_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider_status: Mapped[str] = mapped_column(String(50), nullable=False)
    restoration_status: Mapped[str] = mapped_column(String(50), nullable=False)
    restored_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missing_placeholders: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    unknown_placeholders: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    newly_generated_pii_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    newly_generated_pii_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ProviderUsage(Base):
    __tablename__ = "provider_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_version: Mapped[str] = mapped_column(String(50), nullable=False)
    detector_version: Mapped[str] = mapped_column(String(50), nullable=False)
    total_documents: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_precision: Mapped[float] = mapped_column(Float, nullable=False)
    overall_recall: Mapped[float] = mapped_column(Float, nullable=False)
    overall_f1: Mapped[float] = mapped_column(Float, nullable=False)
    outbound_leakage_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reinsertion_accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    p50_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    p95_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    fail_closed_pass_rate: Mapped[float] = mapped_column(Float, nullable=False)
    report_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
