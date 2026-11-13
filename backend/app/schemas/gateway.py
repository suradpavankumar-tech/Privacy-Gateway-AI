from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CategoryTier(str, Enum):
    MANDATORY = "mandatory"
    EXTENDED = "extended"


class SecurityDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class TokenizationMode(str, Enum):
    CRYPTOGRAPHIC_RANDOM = "cryptographic_random"
    TYPED_SEQUENTIAL = "typed_sequential"
    FORMAT_PRESERVING = "format_preserving"


# ---- Auth ----
class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    org_id: str
    org_name: str
    department: str
    permissions: list[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


# ---- Detection ----
class DetectedEntitySchema(BaseModel):
    entity_type: str
    category_tier: CategoryTier
    start: int
    end: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    recognizer: str
    normalized_value: str | None = None
    # Note: raw matched text is ONLY returned for local inspection/UI highlighting,
    # NEVER stored in PostgreSQL audit logs or sent to outbound LLM payloads.
    matched_text: str | None = None


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=120000)
    document_category: str = Field(default="general", max_length=100)
    purpose: str = Field(default="document_summarization", max_length=100)
    entities: list[str] | None = None


class AnalyzeResponse(BaseModel):
    request_id: str
    entity_count: int
    mandatory_entity_types: list[str]
    extended_entity_types: list[str]
    detections: list[DetectedEntitySchema]
    processing_ms: float


# ---- Masking & Vault Metadata ----
class PlaceholderSummary(BaseModel):
    placeholder: str
    entity_type: str
    category_tier: CategoryTier
    occurrence_count: int
    confidence: float
    recognizer: str


class VaultEntryMetadata(BaseModel):
    """Safe, non-PII cryptographic metadata for AES-256-GCM vault inspection in UI."""
    placeholder: str
    entity_type: str
    nonce_hex: str
    ciphertext_preview_hex: str
    auth_tag_hex: str
    aad_scope: str
    expires_at: datetime


class MaskRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=120000)
    document_category: str = Field(default="general", max_length=100)
    purpose: str = Field(default="document_summarization", max_length=100)
    tokenization_mode: TokenizationMode = Field(default=TokenizationMode.CRYPTOGRAPHIC_RANDOM)
    ttl_seconds: int | None = Field(default=None, ge=60, le=86400)


class MaskResponse(BaseModel):
    request_id: str
    tokenization_mode: TokenizationMode
    sanitized_text: str
    placeholders: list[PlaceholderSummary]
    vault_metadata: list[VaultEntryMetadata] = Field(default_factory=list)
    detected_entity_counts: dict[str, int]
    mapping_expires_at: datetime
    processing_ms: float


# ---- Security Verification ----
class GateCheckItem(BaseModel):
    name: str
    passed: bool
    detail: str


class OutboundPayloadSchema(BaseModel):
    request_id: str
    organization_id: str
    provider: str
    model: str
    purpose: str
    system_prompt: str
    user_prompt: str
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    tool_definitions: list[dict[str, Any]] = Field(default_factory=list)
    tool_arguments: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityVerifyRequest(BaseModel):
    payload: OutboundPayloadSchema
    known_sensitive_values: list[str] = Field(default_factory=list)
    allowed_placeholders: list[str] = Field(default_factory=list)


class SecurityVerifyResponse(BaseModel):
    request_id: str
    decision: SecurityDecision
    reason: str
    payload_sha256: str
    raw_pii_leak_count: int = 0
    checks: dict[str, Any]
    gate_checks: list[GateCheckItem] = Field(default_factory=list)
    ticket_id: str | None = None


# ---- Process (Full Workflow) ----
class ProcessRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=120000)
    task: str = Field(
        default="Summarize this enterprise document clearly and extract the key action items while preserving all placeholder tokens verbatim.",
        min_length=3,
        max_length=2000,
    )
    document_category: str = Field(default="loan_application", max_length=100)
    purpose: str = Field(default="loan_underwriting", max_length=100)
    tokenization_mode: TokenizationMode = Field(default=TokenizationMode.CRYPTOGRAPHIC_RANDOM)
    provider: str | None = Field(default=None, max_length=50)
    model: str | None = Field(default=None, max_length=100)
    restore_response: bool = Field(default=True)
    enable_fallback: bool = Field(default=True)
    # Non-production demonstration flags only
    simulate_tampered_outbound: bool = Field(default=False)
    simulate_provider_offline: bool = Field(default=False)
    simulate_forged_token: bool = Field(default=False)


class RestorationReport(BaseModel):
    restoration_status: str
    authorized: bool
    restored_count: int
    valid_placeholders_found: list[str]
    missing_placeholders: list[str]
    unknown_or_forged_placeholders: list[str]
    newly_generated_pii_count: int
    newly_generated_pii_types: list[str]


class ProcessResponse(BaseModel):
    request_id: str
    status: str
    document_category: str
    purpose: str
    tokenization_mode: TokenizationMode
    provider: str
    model: str
    fallback_triggered: bool = False
    fallback_reason: str | None = None
    policy_version: int
    security_decision: SecurityDecision
    security_reason: str
    raw_pii_leak_count: int = 0
    gate_checks: list[GateCheckItem] = Field(default_factory=list)
    sanitized_outbound_payload: str
    outbound_payload_sha256: str
    detections: list[DetectedEntitySchema] = Field(default_factory=list)
    placeholders: list[PlaceholderSummary]
    vault_metadata: list[VaultEntryMetadata] = Field(default_factory=list)
    detected_entity_counts: dict[str, int]
    raw_llm_response: str | None = None
    final_response: str | None = None
    restoration: RestorationReport | None = None
    execution_trace: list[str] = Field(default_factory=list)
    mapping_expires_at: datetime | None = None
    local_processing_ms: float
    llm_latency_ms: float
    total_latency_ms: float


# ---- Restore ----
class RestoreRequest(BaseModel):
    request_id: str
    response_text: str = Field(..., min_length=1, max_length=100000)


class RestoreResponse(BaseModel):
    request_id: str
    restored_text: str
    report: RestorationReport


# ---- Policies ----
class PrivacyPolicyOut(BaseModel):
    id: str
    organization_id: str
    name: str
    purpose: str
    version: int
    is_active: bool
    allowed_providers: list[str]
    blocked_entities: list[str]
    mask_entities: list[str]
    allow_restoration_roles: list[str]
    retention_days: int
    mapping_ttl_seconds: int
    updated_at: datetime


class PrivacyPolicyUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    allowed_providers: list[str] | None = None
    blocked_entities: list[str] | None = None
    mask_entities: list[str] | None = None
    allow_restoration_roles: list[str] | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    mapping_ttl_seconds: int | None = Field(default=None, ge=60, le=86400)


# ---- Audit, Providers & Evaluation ----
class AuditSummary(BaseModel):
    request_id: str
    organization_id: str
    user_id: str | None
    user_role: str
    purpose: str
    document_category: str
    tokenization_mode: str
    provider: str
    model: str
    status: str
    fallback_triggered: bool
    security_decision: str | None
    raw_pii_leak_count: int
    detected_entity_count: int
    detected_entity_types: dict[str, int]
    local_processing_ms: float
    total_latency_ms: float
    created_at: datetime


class AuditDetail(AuditSummary):
    policy_id: str | None
    policy_version: int
    mapping_expires_at: datetime | None
    outbound_audit: dict[str, Any] | None
    response_audit: dict[str, Any] | None
    detected_entities_metadata: list[dict[str, Any]]
    security_events: list[dict[str, Any]]


class ProviderStatus(BaseModel):
    name: str
    configured: bool
    allowlisted: bool
    default_model: str
    status: str


class EvaluationRunRequest(BaseModel):
    tokenization_mode: TokenizationMode = Field(default=TokenizationMode.CRYPTOGRAPHIC_RANDOM)
    category_filter: str | None = Field(default=None, max_length=100)


class MetricsOverview(BaseModel):
    total_requests: int
    protected_requests: int
    blocked_requests: int
    fallback_requests: int
    zero_leak_rate: float
    total_entities_detected: int
    entity_breakdown: dict[str, int]
    security_events_count: int
    avg_local_processing_ms: float
    p95_local_processing_ms: float
    latest_evaluation: dict[str, Any] | None = None


# ---- Document Upload & Local Extraction ----
class DocumentUploadMeta(BaseModel):
    filename: str
    file_extension: str
    file_size_bytes: int
    page_count: int | None = None
    char_count: int
    word_count: int
    extraction_method: str
    ocr_used: bool = False
    ocr_confidence: float | None = None
    ocr_line_count: int | None = None
    ocr_processing_ms: float | None = None
    image_dimensions: str | None = None
    truncated_for_gateway: bool = False
    suggested_category: str
    suggested_purpose: str
    suggested_task: str
    classification_signals: list[str] = Field(default_factory=list)


class DocumentExtractResponse(BaseModel):
    request_id: str
    document: DocumentUploadMeta
    extracted_text: str
    entity_count: int
    detected_entity_counts: dict[str, int]
    mandatory_entity_types: list[str]
    extended_entity_types: list[str]
    detections: list[DetectedEntitySchema]
    processing_ms: float


class DocumentProcessResponse(BaseModel):
    document: DocumentUploadMeta
    gateway_result: ProcessResponse


# ---- Document Evaluation Metrics Schemas ----
class ChecksumValidationItem(BaseModel):
    entity_type: str
    value_preview: str
    algorithm: str
    is_valid: bool
    detail: str


class EntityEvaluationItem(BaseModel):
    entity_type: str
    tier: str  # "mandatory" | "extended"
    matched_text: str
    start: int
    end: int
    confidence: float
    recognizer: str
    checksum_validation: ChecksumValidationItem | None = None


class DocumentEvaluationReport(BaseModel):
    request_id: str
    document_name: str
    char_count: int
    word_count: int
    extraction_method: str
    ocr_used: bool = False
    ocr_confidence: float | None = None
    ocr_processing_ms: float | None = None

    # Privacy & Security Gate Metrics
    zero_leak_score: float = 100.0
    outbound_leak_count: int = 0
    security_decision: SecurityDecision = SecurityDecision.PASS
    gate_checks_passed: int = 7
    gate_checks_total: int = 7
    gate_checks: list[GateCheckItem] = Field(default_factory=list)

    # Detection Quality Metrics
    total_entities_detected: int = 0
    mean_detection_confidence: float = 0.0
    mandatory_tier_count: int = 0
    extended_tier_count: int = 0
    entity_counts: dict[str, int] = Field(default_factory=dict)
    detections: list[EntityEvaluationItem] = Field(default_factory=list)
    checksum_validations: list[ChecksumValidationItem] = Field(default_factory=list)

    # Tokenization & Vault Cryptography Metrics
    vault_token_count: int = 0
    tokenization_mode: TokenizationMode = TokenizationMode.CRYPTOGRAPHIC_RANDOM
    encryption_algorithm: str = "AES-256-GCM"
    key_size_bits: int = 256
    entropy_assurance: str = "96-bit CSPRNG Nonce + AAD Integrity"

    # Restoration & Integrity Metrics
    restoration_fidelity_pct: float = 100.0
    restored_tokens_count: int = 0
    total_tokens_count: int = 0
    forged_tokens_detected: int = 0
    hallucinated_pii_count: int = 0

    # Ground Truth Comparison Metrics (when ground truth is matched)
    ground_truth_matched: bool = False
    ground_truth_count: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 1.0
    recall: float = 1.0
    f1_score: float = 1.0

    # Latency Performance Metrics (ms)
    ocr_latency_ms: float = 0.0
    local_detection_ms: float = 0.0
    security_gate_ms: float = 0.0
    llm_latency_ms: float = 0.0
    total_latency_ms: float = 0.0

    # Overall Summary
    overall_grade: str = "A+"
    overall_score: float = 98.5
    dpdp_compliance_status: str = "COMPLIANT"
    evaluated_at: str = ""

