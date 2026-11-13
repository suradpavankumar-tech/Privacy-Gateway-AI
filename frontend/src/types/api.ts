/**
 * =========================================================================================
 * types/api.ts — Enterprise Privacy Gateway TypeScript Schema & Domain Contracts
 * =========================================================================================
 * 
 * Tech Stack:
 *  - TypeScript (Type safety, discriminated unions, immutable interfaces)
 * 
 * Key Architectural Responsibilities:
 *  1. Backend Parity:
 *     - Mirrors backend Pydantic models with 100% type fidelity, ensuring compile-time safety
 *       across all API responses and request payloads.
 * 
 *  2. Domain Schema Coverage:
 *     - Identity & RBAC: User profiles, roles (Admin, Privacy Officer, etc.), JWT contracts.
 *     - Entity Detection (NER): PII spans, confidence levels, category tiers (Mandatory vs Extended).
 *     - Cryptographic Vault: Nonces, authentication tags, ciphertext metadata, AES-256-GCM tokens.
 *     - Outbound Security Gate: Decisions (PASS/FAIL/UNKNOWN), signed security tickets, re-scan verdicts.
 *     - Gateway Pipeline: Request payloads, response envelopes, unmasking/restoration receipts.
 *     - Document Intelligence: Multipart file metadata, OCR tokens, character limits.
 *     - Evaluation & Benchmarking: Precision, Recall, F1-Score, Zero-Leak validation, Latency metrics.
 *     - Governance & Audits: Purpose-bound privacy policies and immutable zero-PII audit events.
 * =========================================================================================
 */

export type TokenizationMode =
  | "cryptographic_random"
  | "typed_sequential"
  | "format_preserving";

export type SecurityDecision = "PASS" | "FAIL" | "UNKNOWN";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  org_id: string;
  org_name: string;
  department: string;
  permissions: string[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface DetectedEntity {
  entity_type: string;
  category_tier: "mandatory" | "extended";
  start: number;
  end: number;
  confidence: number;
  recognizer: string;
  normalized_value?: string | null;
  matched_text?: string | null;
}

export interface PlaceholderSummary {
  placeholder: string;
  entity_type: string;
  category_tier: "mandatory" | "extended";
  occurrence_count: number;
  confidence: number;
  recognizer: string;
}

export interface VaultEntryMetadata {
  placeholder: string;
  entity_type: string;
  nonce_hex: string;
  ciphertext_preview_hex: string;
  auth_tag_hex: string;
  aad_scope: string;
  expires_at: string;
}

export interface GateCheckItem {
  name: string;
  passed: boolean;
  detail: string;
}

export interface RestorationReport {
  restoration_status: string;
  authorized: boolean;
  restored_count: number;
  valid_placeholders_found: string[];
  missing_placeholders: string[];
  unknown_or_forged_placeholders: string[];
  newly_generated_pii_count: number;
  newly_generated_pii_types: string[];
}

export interface ProcessRequestPayload {
  text: string;
  task: string;
  document_category: string;
  purpose: string;
  tokenization_mode: TokenizationMode;
  provider?: string;
  model?: string;
  restore_response: boolean;
  enable_fallback: boolean;
  simulate_tampered_outbound?: boolean;
  simulate_provider_offline?: boolean;
  simulate_forged_token?: boolean;
}

export interface ProcessResponse {
  request_id: string;
  status: string;
  document_category: string;
  purpose: string;
  tokenization_mode: TokenizationMode;
  provider: string;
  model: string;
  fallback_triggered: boolean;
  fallback_reason?: string | null;
  policy_version: number;
  security_decision: SecurityDecision;
  security_reason: string;
  raw_pii_leak_count: number;
  gate_checks: GateCheckItem[];
  sanitized_outbound_payload: string;
  outbound_payload_sha256: string;
  detections: DetectedEntity[];
  placeholders: PlaceholderSummary[];
  vault_metadata: VaultEntryMetadata[];
  detected_entity_counts: Record<string, number>;
  raw_llm_response?: string | null;
  final_response?: string | null;
  restoration?: RestorationReport | null;
  execution_trace: string[];
  mapping_expires_at?: string | null;
  local_processing_ms: number;
  llm_latency_ms: number;
  total_latency_ms: number;
}

export interface AnalyzeResponse {
  request_id: string;
  entity_count: number;
  mandatory_entity_types: string[];
  extended_entity_types: string[];
  detections: DetectedEntity[];
  processing_ms: number;
}

export interface RestoreResponse {
  request_id: string;
  restored_text: string;
  report: RestorationReport;
}

export interface PrivacyPolicy {
  id: string;
  organization_id: string;
  name: string;
  purpose: string;
  version: number;
  is_active: boolean;
  allowed_providers: string[];
  blocked_entities: string[];
  mask_entities: string[];
  allow_restoration_roles: string[];
  retention_days: number;
  mapping_ttl_seconds: number;
  updated_at: string;
}

export interface AuditSummary {
  request_id: string;
  organization_id: string;
  user_id?: string | null;
  user_role: string;
  purpose: string;
  document_category: string;
  tokenization_mode: string;
  provider: string;
  model: string;
  status: string;
  fallback_triggered: boolean;
  security_decision?: string | null;
  raw_pii_leak_count: number;
  detected_entity_count: number;
  detected_entity_types: Record<string, number>;
  local_processing_ms: number;
  total_latency_ms: number;
  created_at: string;
}

export interface AuditDetail extends AuditSummary {
  policy_id?: string | null;
  policy_version: number;
  mapping_expires_at?: string | null;
  outbound_audit?: {
    security_decision: string;
    decision_reason: string;
    sanitized_payload_hash: string;
    sanitized_payload_text: string;
    transmitted: boolean;
    raw_pii_leak_count: number;
    checks_summary: Record<string, boolean>;
  } | null;
  response_audit?: {
    provider_status: string;
    restoration_status: string;
    restored_count: number;
    missing_placeholders: string[];
    unknown_placeholders: string[];
    newly_generated_pii_count: number;
    newly_generated_pii_types: string[];
  } | null;
  detected_entities_metadata: Array<{
    entity_type: string;
    category_tier: string;
    placeholder: string;
    start: number;
    end: number;
    confidence: number;
    recognizer: string;
  }>;
  security_events: Array<{
    id: string;
    event_type: string;
    severity: string;
    outcome: string;
    details: Record<string, unknown>;
    created_at: string;
  }>;
}

export interface SecurityEventRow {
  id: string;
  request_id?: string | null;
  event_type: string;
  severity: string;
  outcome: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface ProviderStatus {
  name: string;
  configured: boolean;
  allowlisted: boolean;
  default_model: string;
  status: string;
}

export interface EvaluationEntityMetric {
  tier: "mandatory" | "extended";
  tp: number;
  fp: number;
  fn: number;
  precision: number;
  recall: number;
  f1: number;
}

export interface PerDocEvalResult {
  doc_id: string;
  title: string;
  category: string;
  gt_count: number;
  detected_count: number;
  tp: number;
  fp: number;
  fn: number;
  outbound_leaks: number;
  gate_decision: string;
  reinsertion_passed: boolean;
  latency_ms: number;
}

export interface EvaluationReport {
  id?: string;
  dataset_version: string;
  detector_version: string;
  tokenization_mode?: string;
  category_filter?: string;
  total_documents: number;
  total_ground_truth_entities?: number;
  overall_precision: number;
  overall_recall: number;
  overall_f1: number;
  outbound_leakage_count: number;
  reinsertion_accuracy: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  fail_closed_pass_rate: number;
  entity_metrics?: Record<string, EvaluationEntityMetric>;
  per_doc_results?: PerDocEvalResult[];
  report_payload?: EvaluationReport;
  created_at?: string;
}

export interface MetricsOverview {
  total_requests: number;
  protected_requests: number;
  blocked_requests: number;
  fallback_requests: number;
  zero_leak_rate: number;
  total_entities_detected: number;
  entity_breakdown: Record<string, number>;
  security_events_count: number;
  avg_local_processing_ms: number;
  p95_local_processing_ms: number;
  latest_evaluation?: EvaluationReport | null;
}

export interface DatasetAnnotation {
  doc_id: string;
  category: string;
  entity_type: string;
  start: number;
  end: number;
  expected_value: string;
}

export interface DatasetDocument {
  doc_id: string;
  category: string;
  purpose: string;
  title: string;
  text: string;
  language_style?: string;
  annotations?: DatasetAnnotation[];
}

export interface FullDatasetResponse {
  total_documents: number;
  total_annotations: number;
  negative_control_count: number;
  categories: Record<string, number>;
  documents: DatasetDocument[];
}

export interface HealthResponse {
  status: string;
  environment: string;
  components: {
    database: string;
    redis_vault: string;
    local_pii_detector: string;
  };
}

export interface DocumentUploadMeta {
  filename: string;
  file_extension: string;
  file_size_bytes: number;
  page_count?: number | null;
  char_count: number;
  word_count: number;
  extraction_method: string;
  ocr_used?: boolean;
  ocr_confidence?: number | null;
  ocr_line_count?: number | null;
  ocr_processing_ms?: number | null;
  image_dimensions?: string | null;
  truncated_for_gateway: boolean;
  suggested_category: string;
  suggested_purpose: string;
  suggested_task: string;
  classification_signals: string[];
}

export interface DocumentExtractResponse {
  request_id: string;
  document: DocumentUploadMeta;
  extracted_text: string;
  entity_count: number;
  detected_entity_counts: Record<string, number>;
  mandatory_entity_types: string[];
  extended_entity_types: string[];
  detections: DetectedEntity[];
  processing_ms: number;
}

export interface DocumentProcessResponse {
  document: DocumentUploadMeta;
  gateway_result: ProcessResponse;
}

export interface ChecksumValidationItem {
  entity_type: string;
  value_preview: string;
  algorithm: string;
  is_valid: boolean;
  detail: string;
}

export interface EntityEvaluationItem {
  entity_type: string;
  tier: "mandatory" | "extended";
  matched_text: string;
  start: number;
  end: number;
  confidence: number;
  recognizer: string;
  checksum_validation?: ChecksumValidationItem | null;
}

export interface DocumentEvaluationReport {
  request_id: string;
  document_name: string;
  char_count: number;
  word_count: number;
  extraction_method: string;
  ocr_used?: boolean;
  ocr_confidence?: number | null;
  ocr_processing_ms?: number | null;

  // Privacy & Security Gate Metrics
  zero_leak_score: number;
  outbound_leak_count: number;
  security_decision: SecurityDecision;
  gate_checks_passed: number;
  gate_checks_total: number;
  gate_checks: GateCheckItem[];

  // Detection Quality Metrics
  total_entities_detected: number;
  mean_detection_confidence: number;
  mandatory_tier_count: number;
  extended_tier_count: number;
  entity_counts: Record<string, number>;
  detections: EntityEvaluationItem[];
  checksum_validations: ChecksumValidationItem[];

  // Tokenization & Vault Cryptography Metrics
  vault_token_count: number;
  tokenization_mode: TokenizationMode;
  encryption_algorithm: string;
  key_size_bits: number;
  entropy_assurance: string;

  // Restoration & Integrity Metrics
  restoration_fidelity_pct: number;
  restored_tokens_count: number;
  total_tokens_count: number;
  forged_tokens_detected: number;
  hallucinated_pii_count: number;

  // Ground Truth Comparison Metrics
  ground_truth_matched: boolean;
  ground_truth_count: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1_score: number;

  // Latency Performance Metrics (ms)
  ocr_latency_ms: number;
  local_detection_ms: number;
  security_gate_ms: number;
  llm_latency_ms: number;
  total_latency_ms: number;

  // Overall Summary
  overall_grade: string;
  overall_score: number;
  dpdp_compliance_status: string;
  evaluated_at: string;
}

