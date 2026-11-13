/**
 * =========================================================================================
 * GovernanceAuditCenter.tsx — Enterprise Privacy Policy & Immutable Compliance Audit Engine
 * =========================================================================================
 * 
 * Tech Stack:
 *  - React 19 / TypeScript (Strict typing, functional state, memoized computed sets)
 *  - Tailwind CSS (Enterprise white cards, subtle borders, slate badge palettes)
 *  - Lucide React (Contextual compliance icons: ShieldCheck, FileSpreadsheet, Lock, Eye)
 *  - Privacy Gateway REST Client (Policy CRUD, audit history queries, cryptographic export)
 * 
 * Key Architectural Responsibilities:
 *  1. Purpose-Bound Governance Policies:
 *     - Configures strict privacy policies (e.g., KYC verification, Loan Underwriting, Dispute Analysis).
 *     - Dictates allowed LLM providers (Gemini, OpenAI, Local SLM) and retention TTLs (1h - 30d).
 *     - Sets entity classification tiers (HIGH: Aadhaar/PAN, MEDIUM: Names/Phones, LOW: Addresses).
 * 
 *  2. Role-Based Restoration Matrix (RBAC):
 *     - Governs which roles (Admin, Privacy Officer, Loan Underwriter, Analyst, Support Agent)
 *       possess cryptographic authorization to reveal specific masked PII categories.
 *     - Enforces the principle of least privilege required by India's DPDP Act 2023.
 * 
 *  3. Immutable Cryptographic Audit Trail:
 *     - Displays zero-PII audit event records for every single gateway dispatch.
 *     - Inspects verification hashes, security gate verdicts, latency metrics, and masked payloads.
 *     - Supports one-click CSV and JSON export for regulatory audits and CERT-In compliance.
 * =========================================================================================
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  CheckSquare,
  Download,
  Eye,
  FileJson,
  FileSpreadsheet,
  Lock,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
} from "lucide-react";
import { api, ApiError } from "../services/api";
import type {
  AuditDetail,
  AuditSummary,
  PrivacyPolicy,
  UserProfile,
} from "../types/api";

interface GovernanceAuditCenterProps {
  user: UserProfile;
  searchFilter?: string;
}

const ALL_ROLES = [
  { id: "admin", label: "Admin" },
  { id: "privacy_officer", label: "Privacy Officer" },
  { id: "security_officer", label: "Security Officer" },
  { id: "loan_underwriter", label: "Loan Underwriter" },
  { id: "analyst", label: "Analyst" },
  { id: "support_agent", label: "Support Agent" },
];

const ALL_PROVIDERS = [
  { id: "gemini", label: "Google Gemini" },
  { id: "openai", label: "OpenAI" },
  { id: "local_slm", label: "On-Prem Local SLM" },
];

export const GovernanceAuditCenter: React.FC<GovernanceAuditCenterProps> = ({
  user,
  searchFilter = "",
}) => {
  const [policies, setPolicies] = useState<PrivacyPolicy[]>([]);
  const [audits, setAudits] = useState<AuditSummary[]>([]);
  const [selectedAudit, setSelectedAudit] = useState<AuditDetail | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [savingPolicyId, setSavingPolicyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const canWritePolicy = user.permissions.includes("policies:write");
  const canExportAudit = user.permissions.includes("audit:export");

  const loadData = async () => {
    setLoading(true);
    try {
      const [pols, logs] = await Promise.all([
        api.policies(),
        api.audits(50, statusFilter || undefined),
      ]);
      setPolicies(pols);
      setAudits(logs);
    } catch (err) {
      setBanner({
        type: "err",
        text: err instanceof ApiError ? err.message : "Failed to load governance records",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const toggleRoleOnPolicy = async (policy: PrivacyPolicy, roleId: string) => {
    if (!canWritePolicy) return;
    const exists = policy.allow_restoration_roles.includes(roleId);
    const updatedRoles = exists
      ? policy.allow_restoration_roles.filter((r) => r !== roleId)
      : [...policy.allow_restoration_roles, roleId];

    setSavingPolicyId(policy.id);
    setBanner(null);
    try {
      const saved = await api.updatePolicy(policy.id, {
        allow_restoration_roles: updatedRoles,
      });
      setPolicies((prev) => prev.map((p) => (p.id === saved.id ? saved : p)));
      setBanner({
        type: "ok",
        text: `Updated "${saved.name}" (v${saved.version}) restoration matrix. Allowed roles: ${saved.allow_restoration_roles.join(", ")}.`,
      });
    } catch (err) {
      setBanner({
        type: "err",
        text: err instanceof ApiError ? err.message : "Failed to update policy",
      });
    } finally {
      setSavingPolicyId(null);
    }
  };

  const toggleProviderOnPolicy = async (policy: PrivacyPolicy, providerId: string) => {
    if (!canWritePolicy) return;
    const exists = policy.allowed_providers.includes(providerId);
    const updatedProviders = exists
      ? policy.allowed_providers.filter((p) => p !== providerId)
      : [...policy.allowed_providers, providerId];
    if (updatedProviders.length === 0) {
      setBanner({ type: "err", text: "At least one allowed LLM provider must remain selected." });
      return;
    }

    setSavingPolicyId(policy.id);
    setBanner(null);
    try {
      const saved = await api.updatePolicy(policy.id, {
        allowed_providers: updatedProviders,
      });
      setPolicies((prev) => prev.map((p) => (p.id === saved.id ? saved : p)));
      setBanner({
        type: "ok",
        text: `Updated "${saved.name}" (v${saved.version}) allowed providers: ${saved.allowed_providers.join(", ")}.`,
      });
    } catch (err) {
      setBanner({
        type: "err",
        text: err instanceof ApiError ? err.message : "Failed to update provider allowlist",
      });
    } finally {
      setSavingPolicyId(null);
    }
  };

  const openAuditDetail = async (requestId: string) => {
    try {
      const detail = await api.auditDetail(requestId);
      setSelectedAudit(detail);
    } catch (err) {
      setBanner({
        type: "err",
        text: err instanceof ApiError ? err.message : "Unable to load audit details",
      });
    }
  };

  const handleExport = async (format: "json" | "csv") => {
    try {
      await api.downloadAuditExport(format);
    } catch (err) {
      setBanner({
        type: "err",
        text: err instanceof ApiError ? err.message : "Export failed",
      });
    }
  };

  const filteredAudits = useMemo(() => {
    if (!searchFilter.trim()) return audits;
    const q = searchFilter.toLowerCase();
    return audits.filter(
      (a) =>
        a.request_id.toLowerCase().includes(q) ||
        a.user_role.toLowerCase().includes(q) ||
        a.purpose.toLowerCase().includes(q) ||
        a.provider.toLowerCase().includes(q)
    );
  }, [audits, searchFilter]);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white border border-slate-150 rounded-2xl p-6 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shadow-2xs">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <span>DPDP Governance, Role Restoration Matrix & Zero-PII Audit Log</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-3xl">
            Configure live purpose-bound policies stored in PostgreSQL/SQLite and inspect cryptographic gate decisions.
            Audit rows store SHA-256 hashes, entity offsets, and masked payloads — zero raw PII is persisted.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 shadow-2xs transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-blue-600" : ""}`} />
            <span>Refresh</span>
          </button>
          {canExportAudit && (
            <>
              <button
                onClick={() => handleExport("json")}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 shadow-2xs transition cursor-pointer"
              >
                <FileJson className="w-3.5 h-3.5 text-blue-600" />
                <span>Export JSON</span>
              </button>
              <button
                onClick={() => handleExport("csv")}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#168FF0] hover:bg-blue-600 text-xs font-bold text-white shadow-md shadow-blue-500/25 transition cursor-pointer"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </button>
            </>
          )}
        </div>
      </div>

      {banner && (
        <div
          className={`p-4 rounded-2xl text-xs border flex items-center gap-2.5 shadow-2xs ${
            banner.type === "ok"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-rose-50 border-rose-200 text-rose-800"
          }`}
        >
          {banner.type === "ok" ? (
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
          )}
          <span>{banner.text}</span>
        </div>
      )}

      {/* Interactive Policy & Role Restoration Matrix */}
      <div className="bg-white border border-slate-150 rounded-2xl p-6 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-blue-600" />
              <span>Purpose-Bound Role Restoration &amp; Provider Matrix</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Changes take effect immediately on <code className="text-blue-700 font-mono font-semibold">POST /api/v1/process</code> and{" "}
              <code className="text-blue-700 font-mono font-semibold">POST /api/v1/restore</code> (versioned per save).
            </p>
          </div>
          {!canWritePolicy && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-xs font-semibold">
              <Lock className="w-3 h-3" /> Read-only view for role: {user.role}
            </span>
          )}
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px]">
                <th className="py-3 px-4 font-bold">Policy &amp; Purpose</th>
                {ALL_ROLES.map((r) => (
                  <th key={r.id} className="py-3 px-2 text-center font-bold">
                    {r.label}
                  </th>
                ))}
                <th className="py-3 px-4 font-bold">Allowed LLM Providers</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {policies.map((pol) => (
                <tr key={pol.id} className="hover:bg-slate-50/70 transition">
                  <td className="py-3.5 px-4">
                    <div className="font-bold text-slate-900 text-xs">{pol.name}</div>
                    <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                      purpose: {pol.purpose} • v{pol.version} • TTL {pol.mapping_ttl_seconds}s
                    </div>
                  </td>
                  {ALL_ROLES.map((r) => {
                    const checked = pol.allow_restoration_roles.includes(r.id);
                    return (
                      <td key={r.id} className="py-3.5 px-2 text-center">
                        <button
                          type="button"
                          disabled={!canWritePolicy || savingPolicyId === pol.id}
                          onClick={() => toggleRoleOnPolicy(pol, r.id)}
                          className={`inline-flex items-center justify-center w-8 h-8 rounded-xl border transition shadow-2xs ${
                            checked
                              ? "bg-blue-50 border-blue-300 text-blue-700 shadow-xs"
                              : "bg-slate-50 border-slate-200 text-slate-300 hover:text-slate-500"
                          } ${canWritePolicy ? "hover:border-blue-400 cursor-pointer" : "opacity-50 cursor-not-allowed"}`}
                          title={
                            checked
                              ? `${r.label} CAN restore PII under ${pol.purpose}`
                              : `${r.label} receives masked output only`
                          }
                        >
                          {checked ? <CheckSquare className="w-4 h-4 text-blue-600" /> : <Shield className="w-3.5 h-3.5" />}
                        </button>
                      </td>
                    );
                  })}
                  <td className="py-3.5 px-4">
                    <div className="flex flex-wrap gap-1.5">
                      {ALL_PROVIDERS.map((prov) => {
                        const active = pol.allowed_providers.includes(prov.id);
                        return (
                          <button
                            key={prov.id}
                            type="button"
                            disabled={!canWritePolicy || savingPolicyId === pol.id}
                            onClick={() => toggleProviderOnPolicy(pol, prov.id)}
                            className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border transition shadow-2xs ${
                              active
                                ? "bg-blue-50 border-blue-300 text-blue-700 shadow-xs"
                                : "bg-white border-slate-200 text-slate-400 hover:text-slate-700"
                            } ${canWritePolicy ? "hover:border-blue-400 cursor-pointer" : "opacity-50 cursor-not-allowed"}`}
                          >
                            {prov.label}
                          </button>
                        );
                      })}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Zero-PII Audit Log & Detail Inspector */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-white border border-slate-150 rounded-2xl p-6 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-slate-900">Zero-PII Gateway Audit Trail</h3>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 shadow-2xs cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="">All Statuses</option>
              <option value="completed">completed</option>
              <option value="blocked_security_gate">blocked_security_gate</option>
              <option value="blocked_policy">blocked_policy</option>
              <option value="provider_error">provider_error</option>
              <option value="failed_closed">failed_closed</option>
            </select>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px]">
                  <th className="py-2.5 px-3">Request ID</th>
                  <th className="py-2.5 px-2">Role / Purpose</th>
                  <th className="py-2.5 px-2">Mode / Provider</th>
                  <th className="py-2.5 px-2">Gate Decision</th>
                  <th className="py-2.5 px-2 text-right">Entities</th>
                  <th className="py-2.5 px-2 text-right">Latency</th>
                  <th className="py-2.5 px-3 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredAudits.map((row) => (
                  <tr key={row.request_id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-3">
                      <div className="font-mono text-xs font-bold text-blue-600">{row.request_id.slice(0, 8)}...</div>
                      <div className="text-[10px] text-slate-400">
                        {new Date(row.created_at).toLocaleTimeString()}
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="text-slate-900 font-semibold text-xs">{row.user_role}</div>
                      <div className="text-[10px] text-slate-500">{row.purpose}</div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="text-slate-800 font-medium">{row.provider}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{row.tokenization_mode}</div>
                    </td>
                    <td className="py-3 px-2">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                          row.security_decision === "PASS" && row.raw_pii_leak_count === 0
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-rose-50 text-rose-700 border-rose-200"
                        }`}
                      >
                        {row.security_decision || row.status} • Leak:{row.raw_pii_leak_count}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-right text-slate-800 font-bold">{row.detected_entity_count}</td>
                    <td className="py-3 px-2 text-right text-slate-500 font-mono">{row.total_latency_ms.toFixed(0)}ms</td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => openAuditDetail(row.request_id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-[11px] font-semibold shadow-2xs cursor-pointer"
                      >
                        <Eye className="w-3 h-3 text-blue-600" />
                        <span>Detail</span>
                      </button>
                    </td>
                  </tr>
                ))}
                {filteredAudits.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-slate-400">
                      No audit logs match current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Audit Record Inspector Column */}
        <div className="bg-white border border-slate-150 rounded-2xl p-6 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900">Audit Record Inspector</h3>
            {canExportAudit && selectedAudit && (
              <button
                onClick={() => handleExport("json")}
                className="text-xs font-bold text-blue-600 hover:text-blue-700 inline-flex items-center gap-1 cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Evidence</span>
              </button>
            )}
          </div>

          {!selectedAudit ? (
            <div className="py-16 text-center text-xs text-slate-400">
              Select any request row to inspect its SHA-256 outbound digest, entity metadata, and security gate checks.
            </div>
          ) : (
            <div className="space-y-3.5 text-xs">
              <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5 space-y-1">
                <div className="text-[10px] uppercase font-bold text-slate-400">Request ID</div>
                <div className="font-mono font-bold text-blue-600 break-all">{selectedAudit.request_id}</div>
                <div className="text-[11px] text-slate-600 pt-1">
                  Status: <span className="text-slate-900 font-bold">{selectedAudit.status}</span> • Policy v
                  {selectedAudit.policy_version}
                </div>
              </div>

              {selectedAudit.outbound_audit && (
                <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5 space-y-1.5">
                  <div className="text-[10px] uppercase text-emerald-700 font-bold">
                    Outbound Gate ({selectedAudit.outbound_audit.security_decision})
                  </div>
                  <div className="text-slate-800 font-medium">{selectedAudit.outbound_audit.decision_reason}</div>
                  <div className="text-[10px] text-slate-500 font-mono break-all">
                    SHA-256: {selectedAudit.outbound_audit.sanitized_payload_hash}
                  </div>
                  <pre className="mt-1.5 p-2.5 rounded-lg bg-white border border-slate-200 text-[11px] text-slate-800 whitespace-pre-wrap max-h-36 overflow-auto font-mono">
                    {selectedAudit.outbound_audit.sanitized_payload_text}
                  </pre>
                </div>
              )}

              {selectedAudit.response_audit && (
                <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5 space-y-1">
                  <div className="text-[10px] uppercase text-blue-700 font-bold">
                    Response &amp; Restoration Audit
                  </div>
                  <div className="text-slate-800">
                    Restoration: <span className="font-mono font-bold">{selectedAudit.response_audit.restoration_status}</span> (
                    {selectedAudit.response_audit.restored_count} restored)
                  </div>
                  {selectedAudit.response_audit.unknown_placeholders.length > 0 && (
                    <div className="text-rose-700 text-xs font-semibold">
                      Blocked Forged Tokens: {selectedAudit.response_audit.unknown_placeholders.join(", ")}
                    </div>
                  )}
                </div>
              )}

              <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5 space-y-1.5">
                <div className="text-[10px] uppercase text-slate-400 font-bold">
                  Entity Offsets (Zero Plaintext)
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {selectedAudit.detected_entities_metadata.map((m, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 font-mono text-[10px] text-slate-700 shadow-2xs font-semibold"
                    >
                      {m.entity_type} → {m.placeholder}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
