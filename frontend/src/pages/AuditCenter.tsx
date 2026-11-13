import React, { useEffect, useState } from "react";
import { BarChart3, Download, FileCheck2, Play, Search, ShieldCheck } from "lucide-react";
import { api, getStoredToken } from "../services/api";
import type { AuditDetail, AuditSummary, EvaluationReport } from "../types/api";

export const AuditCenter: React.FC = () => {
  const [audits, setAudits] = useState<AuditSummary[]>([]);
  const [selectedDetail, setSelectedDetail] = useState<AuditDetail | null>(null);
  const [evalReport, setEvalReport] = useState<EvaluationReport | null>(null);
  const [runningEval, setRunningEval] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [auditList, metrics] = await Promise.all([api.audits(), api.metrics()]);
      setAudits(auditList);
      if (metrics.latest_evaluation) {
        const payload = metrics.latest_evaluation.report_payload || metrics.latest_evaluation;
        setEvalReport(payload);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit & intelligence data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const handleRunBenchmark = async () => {
    setRunningEval(true);
    setError(null);
    try {
      const rep = await api.runEvaluation();
      setEvalReport(rep);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Benchmark execution failed");
    } finally {
      setRunningEval(false);
    }
  };

  const handleInspect = async (requestId: string) => {
    try {
      const detail = await api.auditDetail(requestId);
      setSelectedDetail(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load audit detail");
    }
  };

  const handleExport = async (format: "json" | "csv") => {
    const token = getStoredToken();
    const res = await fetch(api.exportAuditUrl(format), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dpdp_privacy_audit_evidence.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Audit &amp; Intelligence Center</h2>
          <p className="text-sm text-slate-500">
            DPDP-oriented zero-raw-PII audit trail, evidence export, and 50-document Indian enterprise benchmark.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void handleExport("csv")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
          <button
            onClick={() => void handleExport("json")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <Download className="w-3.5 h-3.5" /> Export JSON
          </button>
          <button
            onClick={() => void handleRunBenchmark()}
            disabled={runningEval}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            {runningEval ? "Running 50-Doc Benchmark..." : "Run 50-Doc Benchmark"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-700">
          {error}
        </div>
      )}

      {/* Benchmark Evaluation Summary */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <BarChart3 className="w-4 h-4 text-indigo-600" />
            <span>Reproducible Indian Enterprise Benchmark ({evalReport?.dataset_version || "indian-enterprise-50-v1.0"})</span>
          </div>
          {evalReport && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
              <ShieldCheck className="w-3.5 h-3.5" />
              Outbound Leakage: {evalReport.outbound_leakage_count}
            </span>
          )}
        </div>

        {!evalReport ? (
          <p className="text-xs text-slate-500 py-4">
            Click &quot;Run 50-Doc Benchmark&quot; to measure real entity-wise Precision, Recall, F1, outbound leakage, reinsertion accuracy, and p50/p95 latency across the 50 synthetic documents.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-[11px] text-slate-500 font-semibold">Precision</div>
                <div className="text-lg font-bold text-slate-900">{(evalReport.overall_precision * 100).toFixed(2)}%</div>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-[11px] text-slate-500 font-semibold">Recall</div>
                <div className="text-lg font-bold text-slate-900">{(evalReport.overall_recall * 100).toFixed(2)}%</div>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-[11px] text-slate-500 font-semibold">F1 Score</div>
                <div className="text-lg font-bold text-indigo-700">{(evalReport.overall_f1 * 100).toFixed(2)}%</div>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-[11px] text-slate-500 font-semibold">Reinsertion Acc</div>
                <div className="text-lg font-bold text-emerald-700">{(evalReport.reinsertion_accuracy * 100).toFixed(2)}%</div>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-[11px] text-slate-500 font-semibold">p50 / p95 Overhead</div>
                <div className="text-lg font-bold text-slate-900">
                  {evalReport.p50_latency_ms} / {evalReport.p95_latency_ms} ms
                </div>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-[11px] text-slate-500 font-semibold">Fail-Closed Rate</div>
                <div className="text-lg font-bold text-emerald-700">{(evalReport.fail_closed_pass_rate * 100).toFixed(0)}%</div>
              </div>
            </div>

            {evalReport.entity_metrics && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 text-slate-500">
                    <tr>
                      <th className="py-2 pr-3">Entity Type</th>
                      <th className="py-2 pr-3">Tier</th>
                      <th className="py-2 pr-3">TP</th>
                      <th className="py-2 pr-3">FP</th>
                      <th className="py-2 pr-3">FN</th>
                      <th className="py-2 pr-3">Precision</th>
                      <th className="py-2 pr-3">Recall</th>
                      <th className="py-2">F1</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {Object.entries(evalReport.entity_metrics).map(([ent, m]) => (
                      <tr key={ent}>
                        <td className="py-1.5 pr-3 font-mono font-semibold text-slate-800">{ent}</td>
                        <td className="py-1.5 pr-3">
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                              m.tier === "mandatory"
                                ? "bg-indigo-100 text-indigo-800"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {m.tier}
                          </span>
                        </td>
                        <td className="py-1.5 pr-3">{m.tp}</td>
                        <td className="py-1.5 pr-3">{m.fp}</td>
                        <td className="py-1.5 pr-3">{m.fn}</td>
                        <td className="py-1.5 pr-3 font-semibold">{(m.precision * 100).toFixed(1)}%</td>
                        <td className="py-1.5 pr-3 font-semibold">{(m.recall * 100).toFixed(1)}%</td>
                        <td className="py-1.5 font-semibold text-indigo-700">{(m.f1 * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      {/* Audit Records + Request Inspector */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs lg:col-span-2">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-3">
            <FileCheck2 className="w-4 h-4 text-indigo-600" />
            <span>Request Audit Trail (No Raw PII Stored)</span>
          </div>
          {loading ? (
            <p className="text-xs text-slate-500">Loading audit logs...</p>
          ) : audits.length === 0 ? (
            <p className="text-xs text-slate-500 py-6 text-center">No audit records available yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-200 text-slate-500">
                  <tr>
                    <th className="py-2 pr-3">Request ID</th>
                    <th className="py-2 pr-3">Purpose</th>
                    <th className="py-2 pr-3">Provider</th>
                    <th className="py-2 pr-3">Decision</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {audits.map((a) => (
                    <tr key={a.request_id} className="hover:bg-slate-50">
                      <td className="py-2 pr-3 font-mono text-[11px] text-slate-600">
                        {a.request_id.slice(0, 8)}...
                      </td>
                      <td className="py-2 pr-3 font-medium text-slate-800">{a.purpose}</td>
                      <td className="py-2 pr-3 uppercase">{a.provider}</td>
                      <td className="py-2 pr-3">
                        <span
                          className={`rounded px-1.5 py-0.5 font-semibold ${
                            a.security_decision === "PASS"
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-rose-100 text-rose-800"
                          }`}
                        >
                          {a.security_decision || "N/A"}
                        </span>
                      </td>
                      <td className="py-2 pr-3 text-slate-600">{a.status}</td>
                      <td className="py-2">
                        <button
                          onClick={() => void handleInspect(a.request_id)}
                          className="inline-flex items-center gap-1 text-indigo-600 font-semibold hover:text-indigo-800"
                        >
                          <Search className="w-3 h-3" /> View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Selected Audit Detail Inspector */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 mb-3">Request Evidence Inspector</h3>
          {!selectedDetail ? (
            <p className="text-xs text-slate-400 py-8 text-center">
              Select a request from the audit table to inspect its SHA-256 outbound digest, entity metadata, and restoration audit.
            </p>
          ) : (
            <div className="space-y-3 text-xs">
              <div className="rounded-lg bg-slate-50 p-2.5 font-mono text-[11px] break-all">
                <div><strong>ID:</strong> {selectedDetail.request_id}</div>
                <div><strong>Policy v:</strong> {selectedDetail.policy_version}</div>
                <div><strong>SHA-256:</strong> {selectedDetail.outbound_audit?.sanitized_payload_hash || "N/A"}</div>
              </div>
              {selectedDetail.outbound_audit && (
                <div>
                  <div className="font-semibold text-slate-700 mb-1">Verified Outbound Payload</div>
                  <pre className="max-h-36 overflow-y-auto whitespace-pre-wrap rounded bg-slate-900 p-2.5 font-mono text-[11px] text-emerald-300">
                    {selectedDetail.outbound_audit.sanitized_payload_text}
                  </pre>
                </div>
              )}
              {selectedDetail.response_audit && (
                <div className="rounded-lg border border-slate-200 p-2.5 space-y-1">
                  <div className="font-semibold text-slate-800">Response Integrity</div>
                  <div>Restoration: {selectedDetail.response_audit.restoration_status}</div>
                  <div>Restored Count: {selectedDetail.response_audit.restored_count}</div>
                  <div>Unknown Tokens: {selectedDetail.response_audit.unknown_placeholders.length}</div>
                  <div>New PII Flagged: {selectedDetail.response_audit.newly_generated_pii_count}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
