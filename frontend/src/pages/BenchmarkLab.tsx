/**
 * ==============================================================================
 * Privacy Gateway AI (MINEARENA PS-02) — Benchmark & 50-Document Evaluation Lab
 * ==============================================================================
 * Tech Stack:
 *  - React 19 + TypeScript (useMemo, useState, useEffect)
 *  - Tailwind CSS: Floating white cards, clean tabular data grids, pastel badges
 *  - Lucide React: Testing and evaluation iconography
 *
 * Responsibilities:
 *  - Executes live precision, recall, and F1 benchmarks across the 50-document
 *    synthetic Indian enterprise corpus (442 annotated spans, negative controls).
 *  - Displays 6 macro KPIs: Overall Precision, Recall, F1, Outbound Leak Count,
 *    Reinsertion Accuracy, and P50/P95 Latency.
 *  - Renders itemized entity-level performance table across all 14 entity types
 *    (`AADHAAR`, `PAN`, `GSTIN`, `PROPERTY_LEGAL_ID`, `PASSPORT`, etc.).
 *  - Corpus Explorer: Category filters (Loan Applications, KYC Documents, Support
 *    Tickets, Insurance Claims), full-text search, and 1-click "Load in Studio".
 * ==============================================================================
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Database,
  FileSearch,
  FlaskConical,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { api, ApiError } from "../services/api";
import type {
  DatasetDocument,
  EvaluationReport,
  FullDatasetResponse,
  PerDocEvalResult,
  TokenizationMode,
  UserProfile,
} from "../types/api";

interface BenchmarkLabProps {
  user: UserProfile;
  onLoadDocument: (doc: DatasetDocument) => void;
  searchFilter?: string;
}

const CATEGORIES = [
  { id: "all", label: "All Categories" },
  { id: "loan_application", label: "Loan Applications" },
  { id: "kyc_document", label: "KYC Documents" },
  { id: "support_ticket", label: "Support Tickets" },
  { id: "insurance_claim", label: "Insurance Claims" },
];

export const BenchmarkLab: React.FC<BenchmarkLabProps> = ({
  user,
  onLoadDocument,
  searchFilter = "",
}) => {
  const [dataset, setDataset] = useState<FullDatasetResponse | null>(null);
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [mode, setMode] = useState<TokenizationMode>("cryptographic_random");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [loadingDataset, setLoadingDataset] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const canRunEval = user.permissions.includes("evaluation:run");

  useEffect(() => {
    const init = async () => {
      setLoadingDataset(true);
      try {
        const [ds, metrics] = await Promise.all([api.dataset(), api.metrics()]);
        setDataset(ds);
        if (metrics.latest_evaluation) {
          setReport(metrics.latest_evaluation);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load benchmark dataset");
      } finally {
        setLoadingDataset(false);
      }
    };
    init();
  }, []);

  const handleRunEvaluation = async () => {
    if (!canRunEval) return;
    setRunning(true);
    setError(null);
    try {
      const res = await api.runEvaluation(mode);
      setReport(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Live evaluation run failed");
    } finally {
      setRunning(false);
    }
  };

  const perDocMap = useMemo(() => {
    const map = new Map<string, PerDocEvalResult>();
    if (!report?.per_doc_results) return map;
    for (const r of report.per_doc_results) {
      map.set(r.doc_id, r);
    }
    return map;
  }, [report]);

  const entityMetrics = useMemo(() => {
    return report?.entity_metrics || report?.report_payload?.entity_metrics || {};
  }, [report]);

  const effectiveSearch = searchQuery.trim() || searchFilter.trim();

  const filteredDocs = useMemo(() => {
    if (!dataset) return [];
    return dataset.documents.filter((doc) => {
      if (categoryFilter !== "all" && doc.category !== categoryFilter) return false;
      if (effectiveSearch) {
        const q = effectiveSearch.toLowerCase();
        return (
          doc.doc_id.toLowerCase().includes(q) ||
          doc.title.toLowerCase().includes(q) ||
          doc.text.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [dataset, categoryFilter, effectiveSearch]);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white border border-slate-150 rounded-2xl p-6 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shadow-2xs">
              <FlaskConical className="w-4 h-4" />
            </div>
            <span>Benchmark & 50-Document Evaluation Lab</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-3xl">
            Live precision/recall/F1, zero-leakage gate validation, and multi-mode reinsertion verification across{" "}
            {dataset?.total_documents ?? 50} synthetic Indian enterprise records ({dataset?.total_annotations ?? 442}{" "}
            annotated spans, {dataset?.negative_control_count ?? 5} negative controls).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as TokenizationMode)}
            className="px-3.5 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 shadow-2xs cursor-pointer"
          >
            <option value="cryptographic_random">Cryptographic Random (&lt;TYPE_RAND&gt;)</option>
            <option value="typed_sequential">Typed Sequential (&lt;TYPE_1&gt;)</option>
            <option value="format_preserving">Format Preserving (Synthetic Surrogates)</option>
          </select>

          <button
            onClick={handleRunEvaluation}
            disabled={running || !canRunEval}
            title={canRunEval ? "Run live benchmark over selected corpus" : "Role lacks evaluation:run permission"}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-[#168FF0] hover:bg-blue-600 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-blue-500/25 transition cursor-pointer"
          >
            {running ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
            <span>{running ? "Running Benchmark..." : "Run Live Benchmark"}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2.5 shadow-2xs">
          <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {report ? (
        <div className="space-y-6">
          {/* 6 Key Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="bg-white border border-slate-150 rounded-2xl p-4 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col justify-between">
              <div className="text-[10px] uppercase font-bold text-slate-400">Overall Precision</div>
              <div className="text-2xl font-extrabold text-blue-600 mt-2">
                {(report.overall_precision * 100).toFixed(1)}%
              </div>
              <div className="text-[11px] text-slate-500 mt-1">{report.total_documents} docs evaluated</div>
            </div>

            <div className="bg-white border border-slate-150 rounded-2xl p-4 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col justify-between">
              <div className="text-[10px] uppercase font-bold text-slate-400">Overall Recall</div>
              <div className="text-2xl font-extrabold text-teal-600 mt-2">
                {(report.overall_recall * 100).toFixed(1)}%
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                {report.total_ground_truth_entities ?? dataset?.total_annotations ?? 0} GT spans
              </div>
            </div>

            <div className="bg-white border border-slate-150 rounded-2xl p-4 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col justify-between">
              <div className="text-[10px] uppercase font-bold text-slate-400">Overall F1</div>
              <div className="text-2xl font-extrabold text-slate-900 mt-2">
                {(report.overall_f1 * 100).toFixed(1)}%
              </div>
              <div className="text-[11px] text-slate-500 mt-1">Mode: {report.tokenization_mode || mode}</div>
            </div>

            <div className="bg-white border border-slate-150 rounded-2xl p-4 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col justify-between">
              <div className="text-[10px] uppercase font-bold text-slate-400">Outbound Leaks</div>
              <div
                className={`text-2xl font-extrabold mt-2 ${
                  report.outbound_leakage_count === 0 ? "text-emerald-600" : "text-rose-600"
                }`}
              >
                {report.outbound_leakage_count}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Pass rate {(report.fail_closed_pass_rate * 100).toFixed(0)}%
              </div>
            </div>

            <div className="bg-white border border-slate-150 rounded-2xl p-4 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col justify-between">
              <div className="text-[10px] uppercase font-bold text-slate-400">Reinsertion</div>
              <div className="text-2xl font-extrabold text-purple-600 mt-2">
                {(report.reinsertion_accuracy * 100).toFixed(1)}%
              </div>
              <div className="text-[11px] text-slate-500 mt-1">AES-256-GCM vault</div>
            </div>

            <div className="bg-white border border-slate-150 rounded-2xl p-4 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex flex-col justify-between">
              <div className="text-[10px] uppercase font-bold text-slate-400">P50 / P95 Latency</div>
              <div className="text-2xl font-extrabold text-amber-600 mt-2">
                {report.p50_latency_ms.toFixed(1)}ms
              </div>
              <div className="text-[11px] text-slate-500 mt-1">P95: {report.p95_latency_ms.toFixed(1)}ms</div>
            </div>
          </div>

          {/* Entity-Level Table Card */}
          {Object.keys(entityMetrics).length > 0 && (
            <div className="bg-white border border-slate-150 rounded-2xl p-6 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)]">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-slate-900">Entity-Level Precision / Recall / F1</h3>
                <span className="text-xs font-semibold text-slate-500 font-mono">
                  Detector {report.detector_version} • Dataset {report.dataset_version}
                </span>
              </div>
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Entity Type</th>
                      <th className="py-2.5 px-3">Tier</th>
                      <th className="py-2.5 px-3 text-right">TP</th>
                      <th className="py-2.5 px-3 text-right">FP</th>
                      <th className="py-2.5 px-3 text-right">FN</th>
                      <th className="py-2.5 px-3 text-right">Precision</th>
                      <th className="py-2.5 px-3 text-right">Recall</th>
                      <th className="py-2.5 pl-3 text-right">F1</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                    {Object.entries(entityMetrics).map(([entityType, m]) => (
                      <tr key={entityType} className="hover:bg-slate-50/80 transition">
                        <td className="py-2.5 px-3 font-bold text-slate-800">{entityType}</td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                              m.tier === "mandatory"
                                ? "bg-rose-50 text-rose-700 border border-rose-200"
                                : "bg-blue-50 text-blue-700 border border-blue-200"
                            }`}
                          >
                            {m.tier}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-slate-700 font-semibold">{m.tp}</td>
                        <td className="py-2.5 px-3 text-right text-amber-600 font-semibold">{m.fp}</td>
                        <td className="py-2.5 px-3 text-right text-rose-600 font-semibold">{m.fn}</td>
                        <td className="py-2.5 px-3 text-right text-blue-600 font-bold">
                          {(m.precision * 100).toFixed(1)}%
                        </td>
                        <td className="py-2.5 px-3 text-right text-teal-600 font-bold">
                          {(m.recall * 100).toFixed(1)}%
                        </td>
                        <td className="py-2.5 pl-3 text-right text-slate-900 font-bold">
                          {(m.f1 * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white border border-dashed border-slate-200 rounded-2xl p-8 text-center text-xs text-slate-500 shadow-2xs">
          No persisted evaluation run yet. Click <span className="text-blue-600 font-bold">Run Live Benchmark</span>{" "}
          to execute full precision/recall/zero-leak scoring across the corpus.
        </div>
      )}

      {/* 50-Document Benchmark Corpus Section */}
      <div className="bg-white border border-slate-150 rounded-2xl p-6 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
              <Database className="w-3.5 h-3.5" />
            </div>
            <span className="text-sm font-bold text-slate-900">50-Document Benchmark Corpus</span>
            <div className="flex flex-wrap gap-1.5 ml-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setCategoryFilter(cat.id)}
                  className={`px-3 py-1 rounded-xl text-xs font-semibold transition cursor-pointer shadow-2xs ${
                    categoryFilter === cat.id
                      ? "bg-[#168FF0] text-white shadow-xs"
                      : "bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200"
                  }`}
                >
                  {cat.label}
                  {dataset && cat.id !== "all" ? ` (${dataset.categories[cat.id] ?? 0})` : ""}
                </button>
              ))}
            </div>
          </div>

          <div className="relative w-full md:w-72">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search doc ID, title, text..."
              className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-slate-50/80 border border-slate-200 text-xs font-medium text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 shadow-2xs"
            />
          </div>
        </div>

        {loadingDataset ? (
          <div className="py-12 text-center text-xs text-slate-400">Loading 50-document corpus...</div>
        ) : (
          <div className="space-y-3">
            {filteredDocs.map((doc) => {
              const evalRow = perDocMap.get(doc.doc_id);
              const isExpanded = expandedDocId === doc.doc_id;
              const isNegativeControl = (doc.annotations?.length ?? 0) === 0;
              return (
                <div
                  key={doc.doc_id}
                  className="bg-slate-50/60 border border-slate-200/80 rounded-2xl p-4 hover:bg-white hover:border-slate-300 hover:shadow-xs transition"
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                    <div className="space-y-1.5 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold text-blue-600">{doc.doc_id}</span>
                        <span className="text-sm font-bold text-slate-900">{doc.title}</span>
                        <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-bold uppercase border border-slate-200">
                          {doc.category}
                        </span>
                        {doc.language_style && (
                          <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-semibold">
                            {doc.language_style}
                          </span>
                        )}
                        {isNegativeControl && (
                          <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-semibold">
                            Negative Control (0 PII)
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">{doc.text}</p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2.5 shrink-0">
                      {evalRow && (
                        <div className="flex items-center gap-2 text-[11px] bg-white border border-slate-200 px-3 py-1.5 rounded-xl shadow-2xs font-mono font-semibold">
                          <span className="text-emerald-700">TP:{evalRow.tp}</span>
                          <span className="text-amber-700">FP:{evalRow.fp}</span>
                          <span className="text-rose-700">FN:{evalRow.fn}</span>
                          <span
                            className={
                              evalRow.outbound_leaks === 0 ? "text-emerald-700 font-bold" : "text-rose-700 font-bold"
                            }
                          >
                            Leak:{evalRow.outbound_leaks}
                          </span>
                          <span className="text-slate-500">{evalRow.latency_ms.toFixed(1)}ms</span>
                          {evalRow.gate_decision === "PASS" && evalRow.reinsertion_passed && (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          )}
                        </div>
                      )}

                      <button
                        onClick={() => setExpandedDocId(isExpanded ? null : doc.doc_id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 shadow-2xs cursor-pointer"
                      >
                        <FileSearch className="w-3.5 h-3.5 text-slate-500" />
                        <span>GT ({doc.annotations?.length ?? 0})</span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
                      </button>

                      <button
                        onClick={() => onLoadDocument(doc)}
                        className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-50 border border-blue-200 hover:bg-blue-100 text-blue-700 text-xs font-bold transition cursor-pointer shadow-2xs"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                        <span>Load in Studio</span>
                      </button>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-3.5 pt-3.5 border-t border-slate-200/80 space-y-2">
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                        Ground-Truth Annotations ({doc.annotations?.length ?? 0})
                      </div>
                      {doc.annotations && doc.annotations.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {doc.annotations.map((ann, idx) => (
                            <span
                              key={`${doc.doc_id}-${idx}`}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-xs shadow-2xs font-mono"
                            >
                              <span className="font-bold text-blue-700">{ann.entity_type}</span>
                              <span className="text-slate-400">
                                [{ann.start}:{ann.end}]
                              </span>
                              <span className="text-slate-800 font-semibold">{ann.expected_value}</span>
                            </span>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-amber-800 bg-amber-50 border border-amber-200 p-2.5 rounded-xl">
                          Negative control document containing invalid/decoy patterns (0 PII expected).
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
