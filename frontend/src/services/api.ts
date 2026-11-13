/**
 * =========================================================================================
 * api.ts — Enterprise Privacy Gateway HTTP Client & API Service Layer
 * =========================================================================================
 * 
 * Tech Stack:
 *  - TypeScript (Strict type contracts matching backend Pydantic models)
 *  - Native Fetch API (Lightweight, zero-overhead browser HTTP client)
 *  - LocalStorage (Stateless JWT token caching across page refreshes)
 *  - Multipart FormData (Binary document/image uploads for RapidOCR processing)
 * 
 * Key Architectural Responsibilities:
 *  1. Centralized HTTP Dispatcher:
 *     - Coordinates all communication with the FastAPI backend at `/api/v1/*`.
 *     - Automatically injects `Authorization: Bearer <token>` into outgoing requests.
 * 
 *  2. Robust Error Normalization:
 *     - Normalizes standard FastAPI/Pydantic validation errors (`422 Unprocessable Entity`),
 *       authentication errors (`401 Unauthorized`), and service outages (`503 Service Unavailable`).
 * 
 *  3. Comprehensive API Coverage:
 *     - Auth: Login, session verification (`/auth/login`, `/auth/me`).
 *     - Core Privacy Pipeline: Ingest, masking, outbound security gate, restoration (`/gateway/*`).
 *     - Document Intelligence: Multi-format PDF/image extraction & RapidOCR OCR (`/gateway/extract`).
 *     - Analytics & Telemetry: Zero-leak metrics, provider status, latency waterfalls (`/gateway/metrics`).
 *     - Benchmarking: 50-sample enterprise benchmark corpus execution (`/gateway/benchmark/*`).
 *     - Governance: Purpose-bound policy CRUD & immutable zero-PII audit trail (`/governance/*`).
 * =========================================================================================
 */

import type {
  AnalyzeResponse,
  AuditDetail,
  AuditSummary,
  DatasetDocument,
  DocumentEvaluationReport,
  DocumentExtractResponse,
  DocumentProcessResponse,
  EvaluationReport,
  FullDatasetResponse,
  HealthResponse,
  MetricsOverview,
  PrivacyPolicy,
  ProcessRequestPayload,
  ProcessResponse,
  ProviderStatus,
  RestoreResponse,
  SecurityEventRow,
  TokenizationMode,
  TokenResponse,
  UserProfile,
} from "../types/api";

const TOKEN_KEY = "pgw_access_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function parseErrorDetail(resp: Response): Promise<string> {
  let detail = `HTTP ${resp.status}`;
  try {
    const data = await resp.json();
    const raw = data?.detail ?? data?.message;
    if (typeof raw === "string") {
      detail = raw;
    } else if (Array.isArray(raw)) {
      detail = raw.map((item) => item?.msg || JSON.stringify(item)).join("; ");
    } else if (raw != null) {
      detail = JSON.stringify(raw);
    }
  } catch {
    detail = (await resp.text()) || detail;
  }
  return detail;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const resp = await fetch(path, { ...init, headers });
  if (!resp.ok) {
    throw new ApiError(resp.status, await parseErrorDetail(resp));
  }
  return (await resp.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/api/v1/health"),

  login: async (email: string, password: string): Promise<TokenResponse> => {
    const res = await request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setStoredToken(res.access_token);
    return res;
  },

  me: () => request<UserProfile>("/api/v1/auth/me"),

  analyze: (text: string, purpose: string, documentCategory: string) =>
    request<AnalyzeResponse>("/api/v1/analyze", {
      method: "POST",
      body: JSON.stringify({ text, purpose, document_category: documentCategory }),
    }),

  process: (payload: ProcessRequestPayload) =>
    request<ProcessResponse>("/api/v1/process", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  restore: (requestId: string, responseText: string) =>
    request<RestoreResponse>("/api/v1/restore", {
      method: "POST",
      body: JSON.stringify({ request_id: requestId, response_text: responseText }),
    }),

  providers: () => request<ProviderStatus[]>("/api/v1/providers"),
  policies: () => request<PrivacyPolicy[]>("/api/v1/policies"),

  updatePolicy: (policyId: string, patch: Partial<PrivacyPolicy>) =>
    request<PrivacyPolicy>(`/api/v1/policies/${policyId}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  audits: (limit = 50, statusFilter?: string) => {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (statusFilter) qs.set("status_filter", statusFilter);
    return request<AuditSummary[]>(`/api/v1/audit?${qs.toString()}`);
  },

  auditDetail: (requestId: string) => request<AuditDetail>(`/api/v1/audit/${requestId}`),
  securityEvents: (limit = 50) => request<SecurityEventRow[]>(`/api/v1/security-events?limit=${limit}`),
  metrics: () => request<MetricsOverview>("/api/v1/metrics"),

  runEvaluation: (tokenizationMode: TokenizationMode = "cryptographic_random", categoryFilter?: string) =>
    request<EvaluationReport>("/api/v1/evaluation/run", {
      method: "POST",
      body: JSON.stringify({
        tokenization_mode: tokenizationMode,
        category_filter: categoryFilter && categoryFilter !== "all" ? categoryFilter : null,
      }),
    }),

  dataset: () => request<FullDatasetResponse>("/api/v1/dataset"),
  datasetSamples: () => request<DatasetDocument[]>("/api/v1/dataset/samples"),

  extractDocument: async (file: File): Promise<DocumentExtractResponse> => {
    const token = getStoredToken();
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch("/api/v1/documents/extract", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!resp.ok) {
      throw new ApiError(resp.status, await parseErrorDetail(resp));
    }
    return (await resp.json()) as DocumentExtractResponse;
  },

  processUploadedDocument: async (
    file: File,
    options: {
      task?: string;
      documentCategory?: string;
      purpose?: string;
      tokenizationMode?: TokenizationMode;
      provider?: string;
      restoreResponse?: boolean;
      enableFallback?: boolean;
    } = {}
  ): Promise<DocumentProcessResponse> => {
    const token = getStoredToken();
    const form = new FormData();
    form.append("file", file);
    if (options.task) form.append("task", options.task);
    if (options.documentCategory) form.append("document_category", options.documentCategory);
    if (options.purpose) form.append("purpose", options.purpose);
    if (options.tokenizationMode) form.append("tokenization_mode", options.tokenizationMode);
    if (options.provider) form.append("provider", options.provider);
    form.append("restore_response", String(options.restoreResponse ?? true));
    form.append("enable_fallback", String(options.enableFallback ?? true));

    const resp = await fetch("/api/v1/documents/process", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!resp.ok) {
      throw new ApiError(resp.status, await parseErrorDetail(resp));
    }
    return (await resp.json()) as DocumentProcessResponse;
  },

  evaluateDocument: async (file: File): Promise<DocumentEvaluationReport> => {
    const token = getStoredToken();
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch("/api/v1/documents/evaluate", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!resp.ok) {
      throw new ApiError(resp.status, await parseErrorDetail(resp));
    }
    return (await resp.json()) as DocumentEvaluationReport;
  },

  exportAuditUrl: (format: "json" | "csv") => `/api/v1/audit/export?format=${format}`,

  downloadAuditExport: async (format: "json" | "csv") => {
    const token = getStoredToken();
    const resp = await fetch(`/api/v1/audit/export?format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!resp.ok) {
      throw new ApiError(resp.status, "Audit export failed");
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = format === "csv" ? "dpdp_privacy_audit_evidence.csv" : "dpdp_privacy_audit_evidence.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
