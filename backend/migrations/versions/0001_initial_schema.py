"""Initial PostgreSQL schema for Privacy Gateway AI

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-12 18:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "organization_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )
    op.create_index("ix_organization_members_organization_id", "organization_members", ["organization_id"])
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])

    op.create_table(
        "privacy_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("purpose", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("allowed_providers", sa.JSON(), nullable=False),
        sa.Column("blocked_entities", sa.JSON(), nullable=False),
        sa.Column("mask_entities", sa.JSON(), nullable=False),
        sa.Column("allow_restoration_roles", sa.JSON(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("mapping_ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_privacy_policies_organization_id", "privacy_policies", ["organization_id"])
    op.create_index("ix_privacy_policies_purpose", "privacy_policies", ["purpose"])

    op.create_table(
        "requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("purpose", sa.String(length=100), nullable=False),
        sa.Column("document_category", sa.String(length=100), nullable=False),
        sa.Column("policy_id", sa.String(length=36), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("detected_entity_count", sa.Integer(), nullable=False),
        sa.Column("detected_entity_types", sa.JSON(), nullable=False),
        sa.Column("local_processing_ms", sa.Float(), nullable=False),
        sa.Column("total_latency_ms", sa.Float(), nullable=False),
        sa.Column("mapping_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["privacy_policies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_requests_org_created", "requests", ["organization_id", "created_at"])
    op.create_index("ix_requests_organization_id", "requests", ["organization_id"])
    op.create_index("ix_requests_user_id", "requests", ["user_id"])
    op.create_index("ix_requests_status", "requests", ["status"])

    op.create_table(
        "detected_entities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("category_tier", sa.String(length=20), nullable=False),
        sa.Column("placeholder", sa.String(length=80), nullable=False),
        sa.Column("start_pos", sa.Integer(), nullable=False),
        sa.Column("end_pos", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("recognizer", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_detected_entities_request_id", "detected_entities", ["request_id"])
    op.create_index("ix_detected_entities_entity_type", "detected_entities", ["entity_type"])

    op.create_table(
        "outbound_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("security_decision", sa.String(length=20), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("sanitized_payload_hash", sa.String(length=64), nullable=False),
        sa.Column("sanitized_payload_text", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("transmitted", sa.Boolean(), nullable=False),
        sa.Column("checks_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_outbound_audits_organization_id", "outbound_audits", ["organization_id"])
    op.create_index("ix_outbound_audits_security_decision", "outbound_audits", ["security_decision"])

    op.create_table(
        "response_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("provider_status", sa.String(length=50), nullable=False),
        sa.Column("restoration_status", sa.String(length=50), nullable=False),
        sa.Column("restored_count", sa.Integer(), nullable=False),
        sa.Column("missing_placeholders", sa.JSON(), nullable=False),
        sa.Column("unknown_placeholders", sa.JSON(), nullable=False),
        sa.Column("newly_generated_pii_count", sa.Integer(), nullable=False),
        sa.Column("newly_generated_pii_types", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_response_audits_organization_id", "response_audits", ["organization_id"])

    op.create_table(
        "security_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_events_request_id", "security_events", ["request_id"])
    op.create_index("ix_security_events_organization_id", "security_events", ["organization_id"])
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_severity", "security_events", ["severity"])

    op.create_table(
        "provider_usage",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_usage_request_id", "provider_usage", ["request_id"])
    op.create_index("ix_provider_usage_organization_id", "provider_usage", ["organization_id"])

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_version", sa.String(length=50), nullable=False),
        sa.Column("detector_version", sa.String(length=50), nullable=False),
        sa.Column("total_documents", sa.Integer(), nullable=False),
        sa.Column("overall_precision", sa.Float(), nullable=False),
        sa.Column("overall_recall", sa.Float(), nullable=False),
        sa.Column("overall_f1", sa.Float(), nullable=False),
        sa.Column("outbound_leakage_count", sa.Integer(), nullable=False),
        sa.Column("reinsertion_accuracy", sa.Float(), nullable=False),
        sa.Column("p50_latency_ms", sa.Float(), nullable=False),
        sa.Column("p95_latency_ms", sa.Float(), nullable=False),
        sa.Column("fail_closed_pass_rate", sa.Float(), nullable=False),
        sa.Column("report_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("evaluation_results")
    op.drop_table("provider_usage")
    op.drop_table("security_events")
    op.drop_table("response_audits")
    op.drop_table("outbound_audits")
    op.drop_table("detected_entities")
    op.drop_table("requests")
    op.drop_table("privacy_policies")
    op.drop_table("organization_members")
    op.drop_table("users")
    op.drop_table("organizations")
