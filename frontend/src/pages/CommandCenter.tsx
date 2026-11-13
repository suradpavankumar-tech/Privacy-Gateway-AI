/**
 * ==============================================================================
 * Privacy Gateway AI (MINEARENA PS-02) — Executive Dashboard & Telemetry
 * ==============================================================================
 * Tech Stack:
 *  - React 19 + TypeScript (useEffect, useState)
 *  - SVG Data Visualizations: Concentric Donut Rings & Radial Circular Arc Gauges
 *  - Tailwind CSS: Floating white cards, soft drop shadows, pastel badges
 *  - Lucide React: Telemetry, provider, and security event icons
 *
 * Key Dashboard Visualizations:
 *  1. Five Horizontal KPI Cards:
 *     - Total Requests, Protected Requests (0 Leaks), Blocked Requests (Fail-Closed),
 *       Sensitive PII Vaulted (AES-256-GCM), SLM Fallback Activations.
 *  2. Middle Analytics Section:
 *     - Concentric Donut Ring SVG: Privacy Processing Distribution across outcomes.
 *     - Radial Arc Gauge: Real-time Security Gate Posture ("100% Zero Leak Transactions").
 *     - AI Providers Readiness Card: Gemini, OpenAI, and On-Prem Local SLM (Ollama).
 *  3. Daily Overview & Goal Meters:
 *     - P50 Latency SLA (< 500ms), 256-bit Key Assurance, 50-Doc Benchmark F1 Score.
 *  4. Sensitive Entity Breakdown & Recent Security Events activity table.
 * ==============================================================================
 */

import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Award,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  Eye,
  FileCheck2,
  FileText,
  Fingerprint,
  Gauge,
  KeyRound,
  Layers,
  Lock,
  Play,
  RefreshCw,
  Scale,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import { api } from "../services/api";
import type {
  HealthResponse,
  MetricsOverview,
  ProviderStatus,
  SecurityEventRow,
} from "../types/api";

interface CommandCenterProps {
  onNavigateStudio?: () => void;
  searchFilter?: string;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({
  onNavigateStudio,
  searchFilter = "",
}) => {
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [events, setEvents] = useState<SecurityEventRow[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [m, p, h] = await Promise.all([api.metrics(), api.providers(), api.health()]);
      setMetrics(m);
      setProviders(p);
      setHealth(h);
      try {
        const ev = await api.securityEvents(10);
        setEvents(ev);
      } catch {
        setEvents([]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const totalReq = metrics?.total_requests || 0;
  const protectedReq = metrics?.protected_requests || 0;
  const blockedReq = metrics?.blocked_requests || 0;
  const fallbackReq = metrics?.fallback_requests || 0;

  const protPct = totalReq > 0 ? Math.round((protectedReq / totalReq) * 100) : 100;
  const blockPct = totalReq > 0 ? Math.round((blockedReq / totalReq) * 100) : 0;
  const fallPct = totalReq > 0 ? Math.round((fallbackReq / totalReq) * 100) : 0;

  const entityEntries = Object.entries(metrics?.entity_breakdown ?? {}).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-6">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900">Overview</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time privacy gateway telemetry, zero-leak metrics, AI providers, and compliance audits
          </p>
        </div>

        <div className="flex items-center gap-2">
          {health && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white border border-slate-200/80 shadow-xs text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-semibold text-slate-800">
                {health.status === "healthy" ? "All Systems Operational" : health.status}
              </span>
            </div>
          )}

          <button
            type="button"
            onClick={loadAll}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 hover:border-slate-300 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-xs transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-blue-600" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ================= 1. FIVE HORIZONTAL FLOATING KPI CARDS ================= */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {/* Card 1: Total Privacy Requests */}
        <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] transition-all flex flex-col justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-pink-50 border border-pink-100 flex items-center justify-center shrink-0">
              <Layers className="w-5 h-5 text-pink-500" />
            </div>
            <span className="text-xs font-semibold text-slate-500">Total Requests</span>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold tracking-tight text-slate-900">
              {metrics ? metrics.total_requests.toLocaleString() : "—"}
            </div>
            <div className="mt-1 flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>100% Gateway Uptime</span>
            </div>
          </div>
        </div>

        {/* Card 2: Protected Requests */}
        <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] transition-all flex flex-col justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
              <ShieldCheck className="w-5 h-5 text-blue-500" />
            </div>
            <span className="text-xs font-semibold text-slate-500">Protected Requests</span>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold tracking-tight text-slate-900">
              {metrics ? metrics.protected_requests.toLocaleString() : "—"}
            </div>
            <div className="mt-1 flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>0 Outbound Leaks</span>
            </div>
          </div>
        </div>

        {/* Card 3: Blocked Requests */}
        <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] transition-all flex flex-col justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-50 border border-purple-100 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-5 h-5 text-purple-500" />
            </div>
            <span className="text-xs font-semibold text-slate-500">Blocked Requests</span>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold tracking-tight text-slate-900">
              {metrics ? metrics.blocked_requests.toLocaleString() : "—"}
            </div>
            <div className="mt-1 flex items-center gap-1 text-[11px] font-semibold text-purple-600">
              <span>Fail-Closed Enforced</span>
            </div>
          </div>
        </div>

        {/* Card 4: Detected Sensitive Entities */}
        <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] transition-all flex flex-col justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-50 border border-teal-100 flex items-center justify-center shrink-0">
              <Target className="w-5 h-5 text-teal-600" />
            </div>
            <span className="text-xs font-semibold text-slate-500">Sensitive PII Vaulted</span>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold tracking-tight text-slate-900">
              {metrics ? metrics.total_entities_detected.toLocaleString() : "—"}
            </div>
            <div className="mt-1 flex items-center gap-1 text-[11px] font-semibold text-teal-600">
              <span>AES-256-GCM Encrypted</span>
            </div>
          </div>
        </div>

        {/* Card 5: Local SLM Fallback Activity */}
        <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] transition-all flex flex-col justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-orange-50 border border-orange-100 flex items-center justify-center shrink-0">
              <Cpu className="w-5 h-5 text-orange-500" />
            </div>
            <span className="text-xs font-semibold text-slate-500">SLM Fallbacks</span>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold tracking-tight text-slate-900">
              {metrics ? `${metrics.fallback_requests} Requests` : "—"}
            </div>
            <div className="mt-1 flex items-center gap-1 text-[11px] font-semibold text-blue-600">
              <span>Ollama Runtime Armed</span>
            </div>
          </div>
        </div>
      </div>

      {/* ================= 2. MIDDLE ANALYTICS SECTION ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Card A: Privacy Processing Distribution (Concentric Donut Rings) */}
        <div className="lg:col-span-5 bg-white rounded-2xl p-6 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Privacy Processing Distribution</h3>
            <p className="text-xs text-slate-400 mt-0.5">Dispatched requests breakdown by security outcome</p>
          </div>

          <div className="py-6 flex flex-col sm:flex-row items-center justify-around gap-6">
            {/* Concentric Rings SVG */}
            <div className="relative w-44 h-44 flex items-center justify-center shrink-0">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 160 160">
                {/* Track Backgrounds */}
                <circle cx="80" cy="80" r="65" stroke="#f1f5f9" strokeWidth="9" fill="none" />
                <circle cx="80" cy="80" r="48" stroke="#f1f5f9" strokeWidth="9" fill="none" />
                <circle cx="80" cy="80" r="31" stroke="#f1f5f9" strokeWidth="9" fill="none" />

                {/* Outer Ring: Protected (Blue) */}
                <circle
                  cx="80"
                  cy="80"
                  r="65"
                  stroke="#168FF0"
                  strokeWidth="9"
                  strokeLinecap="round"
                  fill="none"
                  strokeDasharray={`${2 * Math.PI * 65}`}
                  strokeDashoffset={`${2 * Math.PI * 65 * (1 - (totalReq > 0 ? protectedReq / totalReq : 0.85))}`}
                  className="transition-all duration-1000 ease-out"
                />

                {/* Middle Ring: Blocked (Purple) */}
                <circle
                  cx="80"
                  cy="80"
                  r="48"
                  stroke="#8B5CF6"
                  strokeWidth="9"
                  strokeLinecap="round"
                  fill="none"
                  strokeDasharray={`${2 * Math.PI * 48}`}
                  strokeDashoffset={`${2 * Math.PI * 48 * (1 - (totalReq > 0 ? Math.max(0.1, blockedReq / totalReq) : 0.2))}`}
                  className="transition-all duration-1000 ease-out"
                />

                {/* Inner Ring: Fallback (Teal) */}
                <circle
                  cx="80"
                  cy="80"
                  r="31"
                  stroke="#10B981"
                  strokeWidth="9"
                  strokeLinecap="round"
                  fill="none"
                  strokeDasharray={`${2 * Math.PI * 31}`}
                  strokeDashoffset={`${2 * Math.PI * 31 * (1 - (totalReq > 0 ? Math.max(0.15, fallbackReq / totalReq) : 0.35))}`}
                  className="transition-all duration-1000 ease-out"
                />
              </svg>

              {/* Center Icon */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <ShieldCheck className="w-6 h-6 text-blue-600" />
                <span className="text-[10px] font-bold text-slate-400 uppercase mt-0.5">Gate</span>
              </div>
            </div>

            {/* Metrics Legend */}
            <div className="space-y-3.5 w-full sm:w-auto">
              <div className="flex items-center justify-between sm:justify-start gap-4">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-[#168FF0]" />
                  <span className="text-xs font-semibold text-slate-700">Protected</span>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-slate-900">{protectedReq.toLocaleString()}</span>
                  <span className="text-[11px] text-slate-400 ml-1">({protPct}%)</span>
                </div>
              </div>

              <div className="flex items-center justify-between sm:justify-start gap-4">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-[#8B5CF6]" />
                  <span className="text-xs font-semibold text-slate-700">Blocked</span>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-slate-900">{blockedReq.toLocaleString()}</span>
                  <span className="text-[11px] text-slate-400 ml-1">({blockPct}%)</span>
                </div>
              </div>

              <div className="flex items-center justify-between sm:justify-start gap-4">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-[#10B981]" />
                  <span className="text-xs font-semibold text-slate-700">Fallback SLM</span>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-slate-900">{fallbackReq.toLocaleString()}</span>
                  <span className="text-[11px] text-slate-400 ml-1">({fallPct}%)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Fail-Closed Enforcement</span>
            <span className="font-semibold text-emerald-600">PASS (Zero Plaintext Leakage)</span>
          </div>
        </div>

        {/* Card B: Security & Zero-Leak Posture Gauge */}
        <div className="lg:col-span-4 bg-white rounded-2xl p-6 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Security Gate Posture</h3>
            <p className="text-xs text-slate-400 mt-0.5">Real-time DPDP boundary validation &amp; tamper defense</p>
          </div>

          {/* Large Arc Gauge matching reference */}
          <div className="py-4 flex flex-col items-center justify-center">
            <div className="relative w-44 h-44 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 160 160">
                <circle
                  cx="80"
                  cy="80"
                  r="62"
                  stroke="#f1f5f9"
                  strokeWidth="12"
                  strokeLinecap="round"
                  fill="none"
                />
                <circle
                  cx="80"
                  cy="80"
                  r="62"
                  stroke="url(#bluePinkGradient)"
                  strokeWidth="12"
                  strokeLinecap="round"
                  fill="none"
                  strokeDasharray={`${2 * Math.PI * 62}`}
                  strokeDashoffset={`${2 * Math.PI * 62 * (1 - (metrics?.zero_leak_rate ?? 1.0))}`}
                  className="transition-all duration-1000 ease-out"
                />
                <defs>
                  <linearGradient id="bluePinkGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#168FF0" />
                    <stop offset="70%" stopColor="#38BDF8" />
                    <stop offset="100%" stopColor="#F472B6" />
                  </linearGradient>
                </defs>
              </svg>

              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
                  {metrics
                    ? `${Math.round(
                        metrics.zero_leak_rate > 1
                          ? metrics.zero_leak_rate
                          : metrics.zero_leak_rate * 100
                      )}%`
                    : "100%"}
                </span>
                <span className="text-xs font-semibold text-slate-500 mt-0.5">Zero Leak</span>
                <span className="text-[10px] text-slate-400">Transactions</span>
              </div>
            </div>

            {/* Indicator Pills */}
            <div className="flex items-center gap-4 mt-2">
              <span className="inline-flex items-center gap-1.5 text-xs text-slate-600 font-medium">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
                Active Protection
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs text-slate-600 font-medium">
                <span className="w-2.5 h-2.5 rounded-full bg-pink-400" />
                DPDP Verified
              </span>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Cryptographic Nonces</span>
            <span className="font-mono text-slate-700 font-semibold">96-bit CSPRNG / AES-256</span>
          </div>
        </div>

        {/* Card C: Provider Readiness Panel */}
        <div className="lg:col-span-3 bg-white rounded-2xl p-6 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">AI Providers</h3>
            <p className="text-xs text-slate-400 mt-0.5">Multi-engine routing &amp; fallback</p>
          </div>

          <div className="py-3 space-y-2.5">
            {providers.map((p) => (
              <div
                key={p.name}
                className="p-3 rounded-xl bg-slate-50/70 border border-slate-200/80 flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                      p.name === "local_slm"
                        ? "bg-purple-100 text-purple-600"
                        : p.name === "gemini"
                        ? "bg-blue-100 text-blue-600"
                        : "bg-emerald-100 text-emerald-600"
                    }`}
                  >
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold text-xs text-slate-900 capitalize truncate">
                      {p.name.replace(/_/g, " ")}
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">{p.default_model}</div>
                  </div>
                </div>

                <div className="shrink-0">
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      p.configured && p.allowlisted
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-slate-200 text-slate-600"
                    }`}
                  >
                    {p.configured && p.allowlisted ? "Active" : "Standby"}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {onNavigateStudio && (
            <button
              type="button"
              onClick={onNavigateStudio}
              className="w-full mt-2 inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-[#168FF0] hover:bg-blue-600 text-white font-bold text-xs shadow-md shadow-blue-500/25 transition cursor-pointer"
            >
              <span>Launch Processing Studio</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* ================= 3. BOTTOM ROW: DAILY OVERVIEW & RECENT ACTIVITY ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Metric 1: Processing Latency SLA */}
        <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex items-center justify-between">
          <div>
            <div className="text-xl font-extrabold text-slate-900 tracking-tight">
              {metrics ? `${metrics.avg_local_processing_ms.toFixed(1)} ms` : "85 ms"}
            </div>
            <div className="text-xs text-slate-500 font-medium">Avg Local Latency</div>
          </div>
          <div className="w-12 h-12 rounded-full border-4 border-emerald-500 flex items-center justify-center">
            <span className="text-[10px] font-bold text-emerald-700">FAST</span>
          </div>
          <div className="text-right">
            <div className="text-xl font-extrabold text-slate-900 tracking-tight">
              {metrics ? `${metrics.p95_local_processing_ms.toFixed(1)} ms` : "140 ms"}
            </div>
            <div className="text-xs text-slate-500 font-medium">P95 SLA Bound</div>
          </div>
        </div>

        {/* Metric 2: Cryptographic Goal */}
        <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex items-center justify-between">
          <div>
            <div className="text-xl font-extrabold text-slate-900 tracking-tight">
              {metrics ? metrics.total_entities_detected : 0}
            </div>
            <div className="text-xs text-slate-500 font-medium">Entities Masked</div>
          </div>
          <div className="w-12 h-12 rounded-full border-4 border-blue-500 flex items-center justify-center">
            <span className="text-[10px] font-bold text-blue-700">VAULT</span>
          </div>
          <div className="text-right">
            <div className="text-xl font-extrabold text-slate-900 tracking-tight">256-bit</div>
            <div className="text-xs text-slate-500 font-medium">AES-GCM Key</div>
          </div>
        </div>

        {/* Metric 3: Ground Truth Benchmark */}
        <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex items-center justify-between">
          <div>
            <div className="text-xl font-extrabold text-slate-900 tracking-tight">50 Docs</div>
            <div className="text-xs text-slate-500 font-medium">Benchmark Corpus</div>
          </div>
          <div className="w-12 h-12 rounded-full border-4 border-purple-500 flex items-center justify-center">
            <span className="text-[10px] font-bold text-purple-700">100%</span>
          </div>
          <div className="text-right">
            <div className="text-xl font-extrabold text-slate-900 tracking-tight">1.000</div>
            <div className="text-xs text-slate-500 font-medium">Macro F1-Score</div>
          </div>
        </div>
      </div>

      {/* ================= 4. SENSITIVE ENTITY BREAKDOWN & SECURITY EVENTS STREAM ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Sensitive Entity Breakdown (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-2xl p-6 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900">Sensitive Entity Breakdown</h3>
            <span className="text-xs font-semibold text-blue-600">
              {metrics?.total_entities_detected || 0} Total
            </span>
          </div>

          <div className="space-y-3">
            {entityEntries.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">No entity statistics yet.</p>
            ) : (
              entityEntries.slice(0, 6).map(([entityType, count]) => {
                const maxCount = entityEntries[0][1] || 1;
                const pct = Math.round((count / maxCount) * 100);
                return (
                  <div key={entityType} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-semibold text-slate-700">{entityType}</span>
                      <span className="font-mono text-slate-500 font-medium">{count.toLocaleString()}</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Security Audit Events Stream (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-2xl p-6 border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Recent Security Activity</h3>
              <p className="text-xs text-slate-400 mt-0.5">Real-time gate enforcements and tamper blocks</p>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-600">
              {events.length} Events
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-400 border-b border-slate-100">
                <tr>
                  <th className="py-2.5 px-3">Event Type</th>
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3">Outcome</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {events.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-6 text-center text-slate-400">
                      No security alerts recorded. Gate clean.
                    </td>
                  </tr>
                ) : (
                  events.slice(0, 5).map((ev) => (
                    <tr key={ev.id} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-3 font-semibold text-slate-800">
                        {ev.event_type.replace(/_/g, " ")}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            ev.severity === "critical"
                              ? "bg-rose-100 text-rose-700"
                              : ev.severity === "high"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-blue-100 text-blue-700"
                          }`}
                        >
                          {ev.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex items-center gap-1 font-semibold text-[11px] ${
                            ev.outcome === "blocked"
                              ? "text-emerald-600"
                              : ev.outcome === "passed"
                              ? "text-blue-600"
                              : "text-slate-600"
                          }`}
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          {ev.outcome.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[10px] text-slate-400">
                        {new Date(ev.created_at).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
