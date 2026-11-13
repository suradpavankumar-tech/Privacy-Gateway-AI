import React, { useEffect, useState } from "react";
import { Check, Lock, Save, Shield, Users } from "lucide-react";
import { api } from "../services/api";
import type { PrivacyPolicy } from "../types/api";
import { useAuth } from "../contexts/AuthContext";

const MANDATORY_ENTITIES = ["PERSON", "AADHAAR", "PAN", "GSTIN", "VOTER_ID", "PASSPORT", "ADDRESS"];

export const GovernanceCenter: React.FC = () => {
  const { user } = useAuth();
  const [policies, setPolicies] = useState<PrivacyPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canEdit = user?.permissions.includes("policy:write") ?? false;

  const loadPolicies = async () => {
    setLoading(true);
    try {
      const list = await api.policies();
      setPolicies(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load policies");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPolicies();
  }, []);

  const toggleBlockedEntity = (policyId: string, entity: string) => {
    setPolicies((prev) =>
      prev.map((p) => {
        if (p.id !== policyId) return p;
        const exists = p.blocked_entities.includes(entity);
        return {
          ...p,
          blocked_entities: exists
            ? p.blocked_entities.filter((e) => e !== entity)
            : [...p.blocked_entities, entity],
        };
      })
    );
  };

  const toggleProvider = (policyId: string, prov: string) => {
    setPolicies((prev) =>
      prev.map((p) => {
        if (p.id !== policyId) return p;
        const exists = p.allowed_providers.includes(prov);
        return {
          ...p,
          allowed_providers: exists
            ? p.allowed_providers.filter((x) => x !== prov)
            : [...p.allowed_providers, prov],
        };
      })
    );
  };

  const savePolicy = async (policy: PrivacyPolicy) => {
    setSavingId(policy.id);
    setMessage(null);
    setError(null);
    try {
      const updated = await api.updatePolicy(policy.id, {
        allowed_providers: policy.allowed_providers,
        blocked_entities: policy.blocked_entities,
        allow_restoration_roles: policy.allow_restoration_roles,
        retention_days: policy.retention_days,
        mapping_ttl_seconds: policy.mapping_ttl_seconds,
      });
      setPolicies((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      setMessage(`Updated policy "${updated.name}" to v${updated.version}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update policy");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Privacy Governance Center</h2>
        <p className="text-sm text-slate-500">
          Purpose-based privacy policies, entity-blocking rules, provider allowlists, and role-scoped restoration authority.
        </p>
      </div>

      {message && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-xs font-semibold text-emerald-800 flex items-center gap-2">
          <Check className="w-4 h-4" /> {message}
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs text-rose-700">
          {error}
        </div>
      )}

      {/* RBAC Matrix Summary */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 mb-3">
          <Users className="w-4 h-4 text-indigo-600" />
          <span>Identity-Aware Restoration &amp; RBAC Separation</span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
          <div className="rounded-lg border border-slate-200 p-3">
            <div className="font-bold text-slate-900">Admin / Security Officer</div>
            <div className="text-slate-500 mt-1">Submit, Mask, Restore PII, Manage Policies, Export Audits</div>
          </div>
          <div className="rounded-lg border border-slate-200 p-3">
            <div className="font-bold text-slate-900">Privacy Officer</div>
            <div className="text-slate-500 mt-1">Submit, Authorized Restore, Policy Governance, DPDP Reports</div>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3">
            <div className="font-bold text-amber-900">Analyst / Developer</div>
            <div className="text-amber-800 mt-1">Can submit &amp; process sanitized prompts; <strong>Restoration Denied (403)</strong></div>
          </div>
          <div className="rounded-lg border border-slate-200 p-3">
            <div className="font-bold text-slate-900">Compliance Auditor</div>
            <div className="text-slate-500 mt-1">Read-only Audit Logs, Evaluation Metrics, Evidence Export</div>
          </div>
        </div>
      </div>

      {/* Policy Cards */}
      {loading ? (
        <p className="text-sm text-slate-500">Loading privacy policies...</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {policies.map((pol) => (
            <div key={pol.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-indigo-600" />
                    <h3 className="text-sm font-bold text-slate-900">{pol.name}</h3>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                    <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded">{pol.purpose}</span>
                    <span>Version {pol.version}</span>
                  </div>
                </div>
                <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800">
                  ACTIVE
                </span>
              </div>

              <div>
                <div className="text-xs font-semibold text-slate-600 mb-1.5">
                  Blocked Entities (Fail-Closed Rejection for This Purpose)
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {MANDATORY_ENTITIES.map((ent) => {
                    const blocked = pol.blocked_entities.includes(ent);
                    return (
                      <button
                        key={ent}
                        type="button"
                        disabled={!canEdit}
                        onClick={() => toggleBlockedEntity(pol.id, ent)}
                        className={`rounded-md px-2 py-1 text-[11px] font-semibold border transition ${
                          blocked
                            ? "border-rose-300 bg-rose-100 text-rose-800"
                            : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100"
                        } disabled:cursor-default`}
                      >
                        {blocked ? `BLOCKED: ${ent}` : ent}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="font-semibold text-slate-600 mb-1">Allowed LLM Providers</div>
                  <div className="flex gap-2">
                    {["gemini", "openai"].map((prov) => {
                      const active = pol.allowed_providers.includes(prov);
                      return (
                        <button
                          key={prov}
                          type="button"
                          disabled={!canEdit}
                          onClick={() => toggleProvider(pol.id, prov)}
                          className={`rounded px-2.5 py-1 font-semibold uppercase border ${
                            active
                              ? "border-indigo-300 bg-indigo-50 text-indigo-800"
                              : "border-slate-200 bg-slate-50 text-slate-400"
                          }`}
                        >
                          {prov}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <div className="font-semibold text-slate-600 mb-1">Vault TTL / Audit Retention</div>
                  <div className="text-slate-700 font-mono">
                    TTL: {pol.mapping_ttl_seconds}s • Audit: {pol.retention_days}d
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                <div className="text-[11px] text-slate-500 flex items-center gap-1">
                  <Lock className="w-3 h-3" />
                  Restore Roles: {pol.allow_restoration_roles.join(", ")}
                </div>
                {canEdit && (
                  <button
                    type="button"
                    disabled={savingId === pol.id}
                    onClick={() => void savePolicy(pol)}
                    className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
                  >
                    <Save className="w-3.5 h-3.5" />
                    {savingId === pol.id ? "Saving..." : "Save Policy"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
