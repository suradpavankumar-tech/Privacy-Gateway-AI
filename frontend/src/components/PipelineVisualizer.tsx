/**
 * ==============================================================================
 * Privacy Gateway AI (MINEARENA PS-02) — Live 5-Stage Zero-Leak Visualizer
 * ==============================================================================
 * Tech Stack:
 *  - React 19 + TypeScript
 *  - Tailwind CSS: Floating white cards, stage indicators, animated status pills
 *  - Lucide React: Stage and provider icons (Cloud, Cpu, Database, KeyRound, Shield)
 *
 * Architecture & 5-Stage Pipeline Flow:
 *  - Stage 1: Local NER & Document Intake
 *             Local Presidio + Indic NER scan (Aadhaar, PAN, GSTIN, Voter, etc.)
 *  - Stage 2: DPDP Policy Binding & AES-256-GCM Vault
 *             Checks purpose policy allowlist, mints cryptographic random tokens,
 *             and seals original plaintext in memory/Redis vault with tenant AAD.
 *  - Stage 3: Outbound Security Gate & Post-Masking Re-Check
 *             Executes 3 independent checks (Known Guard, Token Integrity, Re-Scan)
 *             and issues HMAC-SHA256 authorization ticket.
 *  - Stage 4: Dispatch & Intelligent Fallback Routing
 *             Dispatches sanitized payload to Cloud LLM (Gemini/OpenAI) or seamlessly
 *             falls back to On-Prem Local SLM (Ollama/Qwen 2.5 3B) upon outage.
 *  - Stage 5: RBAC Output Restoration & Anti-Hallucination Guard
 *             Flags forged tokens and new LLM PII; safely unmasks plaintext only for
 *             authorized enterprise roles.
 * ==============================================================================
 */

import React, { useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cloud,
  Cpu,
  Database,
  GitBranch,
  KeyRound,
  Lock,
  ScanSearch,
  ServerCrash,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import type { DetectedEntity, ProcessResponse } from "../types/api";

interface PipelineVisualizerProps {
  result: ProcessResponse | null;
  loading: boolean;
  detectionsPreview: DetectedEntity[];
  selectedProvider: string;
  requestedProvider: string;
  enableFallback: boolean;
  simulateOffline: boolean;
  simulateTampered: boolean;
  simulateForged: boolean;
  purpose: string;
  userRole: string;
}

type StageId = "ner" | "vault" | "recheck" | "dispatch" | "restore";

const PROVIDER_DISPLAY: Record<string, string> = {
  gemini: "Google Gemini",
  openai: "OpenAI GPT",
  local_slm: "On-Prem Local SLM",
};

export const PipelineVisualizer: React.FC<PipelineVisualizerProps> = ({
  result,
  loading,
  detectionsPreview,
  selectedProvider,
  requestedProvider,
  enableFallback,
  simulateOffline,
  simulateTampered,
  simulateForged,
  purpose,
  userRole,
}) => {
  const [collapsed, setCollapsed] = useState(false);
  const [focusedStage, setFocusedStage] = useState<StageId | null>(null);

  const activeDetections = result?.detections ?? detectionsPreview;
  const gatePassed = result?.security_decision === "PASS";
  const gateBlocked = result != null && result.security_decision !== "PASS";
  const checksMap = Object.fromEntries(
    (result?.gate_checks ?? []).map((c) => [c.name, c])
  );

  const policyCheck = checksMap["Enterprise Policy Authorization"];
  const knownGuard = checksMap["Known Sensitive Value Guard"];
  const tokenIntegrity = checksMap["Placeholder Token Integrity"];
  const independentRescan = checksMap["Independent Outbound Re-Scan"];

  const effectivePrimaryProvider = result ? requestedProvider : selectedProvider;
  const isFallbackActive = Boolean(result?.fallback_triggered);
  const usedLocalDirectly =
    result != null && gatePassed && !isFallbackActive && result.provider === "local_slm";
  const usedCloudPrimary =
    result != null && gatePassed && !isFallbackActive && result.provider !== "local_slm";

  const statusTone = loading
    ? "border-blue-200 bg-blue-50 text-blue-700"
    : !result
      ? "border-slate-200 bg-slate-50 text-slate-700"
      : gateBlocked
        ? "border-rose-200 bg-rose-50 text-rose-700"
        : isFallbackActive
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : "border-emerald-200 bg-emerald-50 text-emerald-800";

  const statusText = loading
    ? "Executing Pipeline..."
    : !result
      ? "Pipeline Armed"
      : gateBlocked
        ? `Halted at ${policyCheck && !policyCheck.passed ? "Policy Gate" : "Post-Masking Gate"}`
        : isFallbackActive
          ? `Fallback SLM Active (${result.model})`
          : `Verified & Restored (${result.total_latency_ms}ms)`;

  const renderCheckPill = (label: string, item?: { passed: boolean; detail: string }) => {
    if (!result) {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-white border border-slate-200 text-[9px] text-slate-500 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
          {label}
        </span>
      );
    }
    const skipped = item && !item.passed && item.detail?.toLowerCase().includes("not evaluated");
    return (
      <span
        title={item?.detail || label}
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md border text-[9px] font-semibold ${
          item?.passed
            ? "bg-emerald-50 border-emerald-200 text-emerald-700"
            : skipped
              ? "bg-slate-50 border-slate-200 text-slate-500"
              : "bg-rose-50 border-rose-200 text-rose-700"
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            item?.passed ? "bg-emerald-500" : skipped ? "bg-slate-400" : "bg-rose-500"
          }`}
        />
        {label}
      </span>
    );
  };

  const renderFocusedDetail = () => {
    if (!focusedStage) return null;

    let title = "";
    let body = "";
    if (focusedStage === "ner") {
      title = "Stage 1 • Local NER & Document Intake";
      body = result
        ? `Detected ${result.detections.length} sensitive entity span(s) locally in ${result.local_processing_ms}ms before masking (${Object.entries(
            result.detected_entity_counts || {}
          )
            .map(([k, v]) => `${k}: ${v}`)
            .join(", ") || "no PII detected"}).`
        : `Runs locally using Presidio + custom Indian Verhoeff/Mod-36/PAN recognizers. Currently holding ${activeDetections.length} preview span(s).`;
    } else if (focusedStage === "vault") {
      title = "Stage 2 • DPDP Policy Binding & AES-256-GCM Vault";
      body = result
        ? `Policy v${result.policy_version} (${result.purpose}): ${
            policyCheck?.passed ? "APPROVED" : policyCheck?.detail || "BLOCKED"
          }. Minted ${result.vault_metadata.length} cryptographic placeholder(s) (${result.tokenization_mode}) sealed in Redis/memory vault.`
        : `Evaluates organization policy for '${purpose}' and encrypts every sensitive span with AES-256-GCM + tenant AAD.`;
    } else if (focusedStage === "recheck") {
      title = "Stage 3 • Post-Masking Recheck & Outbound Security Gate";
      body = result
        ? `${result.security_decision} (Leaks: ${result.raw_pii_leak_count}) — ${result.security_reason} | Known Guard: ${
            knownGuard?.passed ? "PASS" : "FAIL"
          }, Token Integrity: ${tokenIntegrity?.passed ? "PASS" : "FAIL"}, Independent Re-Scan: ${
            independentRescan?.passed ? "PASS" : "FAIL"
          }.`
        : `Re-scans the sanitized payload AFTER masking across 3 independent post-masking layers (Known Sensitive Value Guard, Placeholder Token Integrity, Independent Outbound Re-Scan) and mints an HMAC-SHA256 ticket before LLM transport.`;
    } else if (focusedStage === "dispatch") {
      title = "Stage 4 • Transport Guard & Fallback SLM Routing";
      body = result
        ? gateBlocked
          ? "Fail-closed halt: Outbound Gate did not issue a PASS ticket, so neither primary LLM nor Fallback SLM received any data."
          : isFallbackActive
            ? `Primary provider (${effectivePrimaryProvider}) failed/unavailable (${
                result.fallback_reason || "outage"
              }). Policy check confirmed 'local_slm' is allowed, re-ran Outbound Gate (PASS), and executed On-Prem Local SLM (${
                result.model
              }) in ${result.llm_latency_ms}ms.`
            : `Verified HMAC ticket at LLM transport boundary and dispatched via ${result.provider} (${result.model}) in ${result.llm_latency_ms}ms.`
        : `Primary provider: ${
            PROVIDER_DISPLAY[selectedProvider] || selectedProvider
          }. Policy-gated On-Prem Local SLM fallback is ${
            enableFallback ? "ARMED (re-checks Outbound Gate automatically on cloud outage)" : "DISABLED"
          }.`;
    } else {
      title = "Stage 5 • Post-LLM Recheck & RBAC Local Restoration";
      body = result?.restoration
        ? `Status: ${result.restoration.restoration_status} | Authorized (${userRole}): ${
            result.restoration.authorized ? "YES" : "NO (kept sealed)"
          } | Restored: ${result.restoration.restored_count}, Forged/Unknown blocked: ${
            result.restoration.unknown_or_forged_placeholders.length
          }, New LLM PII: ${result.restoration.newly_generated_pii_count}.`
        : `Re-scans LLM output for forged placeholder tokens and unmasked new PII, then restores original values locally only if role '${userRole}' is authorized for '${purpose}'.`;
    }

    return (
      <div className="mt-3 p-3.5 rounded-xl bg-blue-50/60 border border-blue-100 text-xs flex items-start justify-between gap-3 shadow-xs">
        <div>
          <span className="font-bold text-blue-900 mr-2">{title}:</span>
          <span className="text-slate-700 leading-relaxed">{body}</span>
        </div>
        <button
          type="button"
          onClick={() => setFocusedStage(null)}
          className="text-slate-400 hover:text-slate-700 text-xs font-semibold shrink-0 cursor-pointer p-0.5"
        >
          Close
        </button>
      </div>
    );
  };

  return (
    <section className="bg-white border border-slate-100 rounded-2xl shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] overflow-hidden">
      {/* Visualizer Header */}
      <div className="px-5 py-3.5 bg-white border-b border-slate-100 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shadow-2xs">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-900 flex items-center gap-2">
              <span>Live Zero-Leak Architecture &amp; Fallback SLM Flow</span>
              {simulateOffline && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-700 font-semibold">
                  Simulating Outage
                </span>
              )}
              {simulateTampered && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-50 border border-rose-200 text-rose-700 font-semibold">
                  Simulating Tamper Leak
                </span>
              )}
              {simulateForged && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-50 border border-purple-200 text-purple-700 font-semibold">
                  Simulating Forged Token
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <span className={`text-[11px] px-3 py-1 rounded-full border font-semibold ${statusTone}`}>
            {statusText}
          </span>
          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs transition"
          >
            <span>{collapsed ? "Show Flow" : "Hide Flow"}</span>
            {collapsed ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="p-4 bg-slate-50/40">
          {/* Horizontal 5-Stage Pipeline with Branched Fallback SLM */}
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_auto_1fr_auto_1.35fr_auto_1.45fr_auto_1fr] gap-2.5 items-stretch">
            {/* STAGE 1: Input & Local NER */}
            <button
              type="button"
              onClick={() => setFocusedStage(focusedStage === "ner" ? null : "ner")}
              className={`text-left p-3.5 rounded-2xl border transition flex flex-col justify-between cursor-pointer ${
                focusedStage === "ner"
                  ? "border-blue-400 bg-blue-50/80 shadow-xs ring-2 ring-blue-500/20"
                  : result
                    ? "border-slate-200 bg-white hover:border-blue-300 hover:shadow-xs"
                    : "border-slate-200/80 bg-white/80 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between gap-1.5">
                <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-blue-600">
                  <ScanSearch className="w-3.5 h-3.5" />
                  1. Local NER
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                  {activeDetections.length} PII
                </span>
              </div>
              <div className="text-xs font-bold text-slate-900 mt-2">
                Presidio + Indic Scan
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                {result ? `${result.local_processing_ms}ms local scan` : "On-prem detection only"}
              </div>
            </button>

            <div className="hidden xl:flex items-center justify-center text-slate-300">
              <ArrowRight className="w-4 h-4" />
            </div>

            {/* STAGE 2: Policy & AES-256-GCM Vault */}
            <button
              type="button"
              onClick={() => setFocusedStage(focusedStage === "vault" ? null : "vault")}
              className={`text-left p-3.5 rounded-2xl border transition flex flex-col justify-between cursor-pointer ${
                focusedStage === "vault"
                  ? "border-amber-400 bg-amber-50/80 shadow-xs ring-2 ring-amber-500/20"
                  : policyCheck && !policyCheck.passed
                    ? "border-rose-300 bg-rose-50/70"
                    : result
                      ? "border-slate-200 bg-white hover:border-amber-300 hover:shadow-xs"
                      : "border-slate-200/80 bg-white/80 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between gap-1.5">
                <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-amber-600">
                  <Database className="w-3.5 h-3.5" />
                  2. Mask &amp; Vault
                </span>
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                    policyCheck && !policyCheck.passed
                      ? "bg-rose-50 border-rose-200 text-rose-700"
                      : "bg-amber-50 border-amber-200 text-amber-700"
                  }`}
                >
                  {result ? `${result.vault_metadata.length} AES` : "AES-256"}
                </span>
              </div>
              <div className="text-xs font-bold text-slate-900 mt-2">
                DPDP Policy &amp; Sealing
              </div>
              <div className="text-[11px] text-slate-500 mt-1 truncate">
                {policyCheck && !policyCheck.passed
                  ? "Blocked by policy"
                  : result
                    ? `Policy v${result.policy_version} approved`
                    : `Purpose: ${purpose.replace(/_/g, " ")}`}
              </div>
            </button>

            <div className="hidden xl:flex items-center justify-center text-slate-300">
              <ArrowRight className="w-4 h-4" />
            </div>

            {/* STAGE 3: Post-Masking Recheck & Outbound Gate */}
            <button
              type="button"
              onClick={() => setFocusedStage(focusedStage === "recheck" ? null : "recheck")}
              className={`text-left p-3.5 rounded-2xl border transition flex flex-col justify-between cursor-pointer ${
                focusedStage === "recheck"
                  ? "border-emerald-400 bg-emerald-50/80 shadow-xs ring-2 ring-emerald-500/20"
                  : gateBlocked
                    ? "border-rose-300 bg-rose-50/70"
                    : gatePassed
                      ? "border-slate-200 bg-white hover:border-emerald-300 hover:shadow-xs"
                      : "border-slate-200/80 bg-white/80 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between gap-1.5">
                <span
                  className={`inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider ${
                    gateBlocked ? "text-rose-600" : "text-emerald-600"
                  }`}
                >
                  {gateBlocked ? (
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                  ) : (
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  )}
                  3. Outbound Gate
                </span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                    !result
                      ? "bg-slate-100 border-slate-200 text-slate-600"
                      : gatePassed
                        ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                        : "bg-rose-50 border-rose-200 text-rose-700"
                  }`}
                >
                  {!result ? "3 Guards" : gatePassed ? "PASS • 0 Leaks" : `FAIL • ${result.raw_pii_leak_count}`}
                </span>
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {renderCheckPill("Known Guard", knownGuard)}
                {renderCheckPill("Token Integrity", tokenIntegrity)}
                {renderCheckPill("Re-Scan", independentRescan)}
              </div>
              <div className="text-[11px] text-slate-500 mt-2 flex items-center justify-between">
                <span>Zero-Leak Enforced</span>
                <span className="font-mono text-[10px] text-slate-400 font-semibold">
                  {gatePassed ? "HMAC Signed" : gateBlocked ? "Halted" : "HMAC SHA-256"}
                </span>
              </div>
            </button>

            <div className="hidden xl:flex items-center justify-center text-slate-300">
              <ArrowRight className={`w-4 h-4 ${gateBlocked ? "text-rose-400" : ""}`} />
            </div>

            {/* STAGE 4: Primary LLM + Branched Fallback SLM */}
            <button
              type="button"
              onClick={() => setFocusedStage(focusedStage === "dispatch" ? null : "dispatch")}
              className={`text-left p-3.5 rounded-2xl border transition flex flex-col justify-between cursor-pointer ${
                focusedStage === "dispatch"
                  ? "border-purple-400 bg-purple-50/80 shadow-xs ring-2 ring-purple-500/20"
                  : gateBlocked
                    ? "border-slate-200 bg-slate-50/60 opacity-75"
                    : isFallbackActive
                      ? "border-amber-300 bg-amber-50/60"
                      : gatePassed
                        ? "border-slate-200 bg-white hover:border-purple-300 hover:shadow-xs"
                        : "border-slate-200/80 bg-white/80 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between gap-1.5">
                <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-purple-600">
                  <GitBranch className="w-3.5 h-3.5" />
                  4. Dispatch &amp; Fallback
                </span>
                <span className="text-[10px] font-mono font-semibold text-slate-500">
                  {result && gatePassed ? `${result.llm_latency_ms}ms` : "Transport"}
                </span>
              </div>

              {/* Dual-Lane Model Route */}
              <div className="mt-2 space-y-1.5">
                {/* Primary Lane */}
                <div
                  className={`flex items-center justify-between gap-1.5 px-2.5 py-1.5 rounded-xl border text-[11px] ${
                    gateBlocked
                      ? "bg-slate-100 border-slate-200 text-slate-500"
                      : isFallbackActive
                        ? "bg-rose-50 border-rose-200 text-rose-700"
                        : usedCloudPrimary || usedLocalDirectly
                          ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                          : "bg-white border-slate-200 text-slate-700"
                  }`}
                >
                  <span className="inline-flex items-center gap-1.5 truncate font-semibold">
                    {effectivePrimaryProvider === "local_slm" ? (
                      <Cpu className="w-3.5 h-3.5 shrink-0 text-blue-600" />
                    ) : (
                      <Cloud className="w-3.5 h-3.5 shrink-0 text-indigo-600" />
                    )}
                    <span className="truncate">
                      Primary: {PROVIDER_DISPLAY[effectivePrimaryProvider] || effectivePrimaryProvider}
                    </span>
                  </span>
                  <span className="text-[10px] font-bold uppercase shrink-0">
                    {gateBlocked
                      ? "Blocked"
                      : isFallbackActive
                        ? "Outage"
                        : usedCloudPrimary || usedLocalDirectly
                          ? "Active"
                          : "Selected"}
                  </span>
                </div>

                {/* Fallback SLM Lane */}
                <div
                  className={`flex items-center justify-between gap-1.5 px-2.5 py-1.5 rounded-xl border text-[11px] ${
                    gateBlocked
                      ? "bg-slate-100 border-slate-200 text-slate-500"
                      : isFallbackActive
                        ? "bg-amber-50 border-amber-300 text-amber-900 font-bold shadow-xs"
                        : !enableFallback
                          ? "bg-slate-50 border-slate-200 text-slate-400"
                          : "bg-white border-slate-200 text-slate-700"
                  }`}
                >
                  <span className="inline-flex items-center gap-1.5 truncate font-semibold">
                    {isFallbackActive ? (
                      <ServerCrash className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    ) : (
                      <Cpu className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                    )}
                    <span className="truncate">Fallback: Local SLM (Indic v1)</span>
                  </span>
                  <span
                    className={`text-[10px] font-bold uppercase shrink-0 ${
                      isFallbackActive
                        ? "text-amber-700"
                        : !enableFallback
                          ? "text-slate-400"
                          : "text-blue-600"
                    }`}
                  >
                    {gateBlocked
                      ? "Standby"
                      : isFallbackActive
                        ? "Engaged"
                        : enableFallback
                          ? "Armed"
                          : "Disabled"}
                  </span>
                </div>
              </div>
            </button>

            <div className="hidden xl:flex items-center justify-center text-slate-300">
              <ArrowRight className={`w-4 h-4 ${gateBlocked ? "text-rose-400" : ""}`} />
            </div>

            {/* STAGE 5: Post-LLM Inspect & RBAC Restoration */}
            <button
              type="button"
              onClick={() => setFocusedStage(focusedStage === "restore" ? null : "restore")}
              className={`text-left p-3.5 rounded-2xl border transition flex flex-col justify-between cursor-pointer ${
                focusedStage === "restore"
                  ? "border-emerald-400 bg-emerald-50/80 shadow-xs ring-2 ring-emerald-500/20"
                  : gateBlocked
                    ? "border-slate-200 bg-slate-50/60"
                    : result?.restoration?.unknown_or_forged_placeholders.length
                      ? "border-amber-300 bg-amber-50/70"
                      : result?.restoration
                        ? "border-slate-200 bg-white hover:border-emerald-300 hover:shadow-xs"
                        : "border-slate-200/80 bg-white/80 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between gap-1.5">
                <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-600">
                  <KeyRound className="w-3.5 h-3.5" />
                  5. RBAC Restore
                </span>
                {result?.restoration ? (
                  result.restoration.unknown_or_forged_placeholders.length > 0 ? (
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  ) : result.restoration.authorized ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  ) : (
                    <Lock className="w-3.5 h-3.5 text-amber-500" />
                  )
                ) : gateBlocked ? (
                  <XCircle className="w-3.5 h-3.5 text-rose-500" />
                ) : null}
              </div>

              <div className="text-xs font-bold text-slate-900 mt-2">
                {gateBlocked
                  ? "Withheld Locally"
                  : result?.restoration
                    ? result.restoration.authorized
                      ? `${result.restoration.restored_count} Restored Locally`
                      : "Sealed (RBAC Denied)"
                    : "Inspect & Unmask"}
              </div>
              <div className="text-[11px] text-slate-500 mt-1 truncate">
                {gateBlocked
                  ? "Zero external leak"
                  : result?.restoration
                    ? `${result.restoration.unknown_or_forged_placeholders.length} forged • ${result.restoration.newly_generated_pii_count} new PII`
                    : `Role: ${userRole}`}
              </div>
            </button>
          </div>

          {renderFocusedDetail()}
        </div>
      )}
    </section>
  );
};
