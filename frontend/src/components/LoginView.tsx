/**
 * ==============================================================================
 * Privacy Gateway AI (MINEARENA PS-02) — Enterprise Login & Role Selector
 * ==============================================================================
 * Tech Stack:
 *  - React 19 + TypeScript
 *  - JWT + bcrypt RBAC: Server-verified role authentication
 *  - Tailwind CSS: Floating white card, multi-stop pastel backdrop
 *  - Lucide React: Security shield and lock iconography
 *
 * Responsibilities:
 *  - Provides secure enterprise email & password sign-in form.
 *  - Supplies instant 1-click Quick Demo Role cards to simulate all 6 DPDP personas:
 *     1. Admin (`admin@bharatfin.in`) - Full access, policy editing & restoration
 *     2. Privacy Officer (`privacy@bharatfin.in`) - DPO governance & evaluation
 *     3. Loan Underwriter (`underwriter@bharatfin.in`) - Authorized KYC restoration
 *     4. Analyst (`analyst@bharatfin.in`) - Process allowed; restoration denied (RBAC proof)
 *     5. Support Agent (`support@bharatfin.in`) - Customer support triage
 *     6. Auditor (`auditor@bharatfin.in`) - Read-only compliance logs & CSV export
 * ==============================================================================
 */

import React, { useState } from "react";
import { AlertCircle, KeyRound, Lock, ShieldCheck } from "lucide-react";
import { api, ApiError } from "../services/api";
import type { UserProfile } from "../types/api";

export const DEMO_ACCOUNTS = [
  {
    email: "admin@bharatfin.in",
    pwd: "Admin@2026!",
    role: "admin",
    label: "Admin",
    desc: "Full access, policy editing & PII restoration",
  },
  {
    email: "privacy@bharatfin.in",
    pwd: "Privacy@2026!",
    role: "privacy_officer",
    label: "Privacy Officer",
    desc: "DPO governance, evaluation, audit & restoration",
  },
  {
    email: "underwriter@bharatfin.in",
    pwd: "Underwriter@2026!",
    role: "loan_underwriter",
    label: "Loan Underwriter",
    desc: "Authorized restoration for underwriting/KYC",
  },
  {
    email: "analyst@bharatfin.in",
    pwd: "Analyst@2026!",
    role: "analyst",
    label: "Analyst",
    desc: "Process allowed; restoration denied by default (RBAC proof)",
  },
  {
    email: "support@bharatfin.in",
    pwd: "Support@2026!",
    role: "support_agent",
    label: "Support Agent",
    desc: "Support triage allowed; restricted for loan docs",
  },
  {
    email: "auditor@bharatfin.in",
    pwd: "Auditor@2026!",
    role: "auditor",
    label: "Auditor",
    desc: "Read-only compliance logs & CSV/JSON evidence export",
  },
] as const;

interface LoginViewProps {
  onAuthenticated: (user: UserProfile) => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onAuthenticated }) => {
  const [email, setEmail] = useState("admin@bharatfin.in");
  const [password, setPassword] = useState("Admin@2026!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.login(email, password);
      onAuthenticated(res.user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = async (demoEmail: string, demoPwd: string) => {
    setEmail(demoEmail);
    setPassword(demoPwd);
    setError(null);
    setLoading(true);
    try {
      const res = await api.login(demoEmail, demoPwd);
      onAuthenticated(res.user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#ffdbe6] via-[#e2e8f0] to-[#cbe2fe] flex items-center justify-center p-4 sm:p-6 lg:p-8 font-sans antialiased text-slate-800">
      <div className="max-w-5xl w-full grid grid-cols-1 lg:grid-cols-2 rounded-[2.25rem] bg-white shadow-2xl overflow-hidden border border-white/80">
        {/* Left Informational Panel */}
        <div className="p-8 sm:p-10 bg-slate-50/60 border-b lg:border-b-0 lg:border-r border-slate-100 flex flex-col justify-between">
          <div>
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-bold mb-6 shadow-2xs">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              <span>MINEARENA 1.0 • PS-02 DPDP Control Plane</span>
            </div>

            <h1 className="text-3xl font-extrabold tracking-tight mb-3 text-slate-900">
              Privacy Gateway AI
            </h1>

            <p className="text-slate-600 text-sm leading-relaxed mb-6 font-medium">
              Enterprise-grade privacy control plane enforcing local Presidio + Indian PII detection,
              AES-256-GCM Redis vault isolation, HMAC-verified fail-closed outbound gates, and RBAC-gated restoration.
            </p>

            <div className="space-y-2.5 text-xs text-slate-700 bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
              <div className="font-bold text-blue-700 uppercase tracking-wider text-[11px]">
                Verified Security Guarantees
              </div>
              <p className="flex items-center gap-2 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                <span>Verhoeff Aadhaar, Mod-36 GSTIN, PAN Entity Code &amp; Luhn Checksums</span>
              </p>
              <p className="flex items-center gap-2 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
                <span>AES-256-GCM Encrypted Vault with Tenant AAD &amp; Automatic TTL Expiry</span>
              </p>
              <p className="flex items-center gap-2 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span>HMAC-SHA256 Security Gate Ticket Enforced at LLM Transport Boundary</span>
              </p>
              <p className="flex items-center gap-2 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                <span>Policy-Gated On-Prem Local SLM Fallback &amp; Zero-PII Audit Trail</span>
              </p>
            </div>
          </div>

          <div className="mt-8 text-xs text-slate-500">
            Organization: <span className="text-slate-900 font-bold">BharatFin Enterprise Ltd</span>
          </div>
        </div>

        {/* Right Form & Demo Logins */}
        <div className="p-8 sm:p-10 flex flex-col justify-center bg-white">
          <h2 className="text-2xl font-bold text-slate-900 mb-1 flex items-center gap-2">
            <Lock className="w-5 h-5 text-blue-600" />
            <span>Sign In to Control Plane</span>
          </h2>
          <p className="text-xs text-slate-500 mb-6">
            Authenticates with JWT &amp; bcrypt RBAC — all actions are bound to server-verified roles.
          </p>

          {error && (
            <div className="mb-4 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                Enterprise Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-50/70 border border-slate-200 text-slate-900 text-sm font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition shadow-2xs"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-50/70 border border-slate-200 text-slate-900 text-sm font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition shadow-2xs"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl bg-[#168FF0] hover:bg-blue-600 text-white font-bold text-sm shadow-md shadow-blue-500/25 transition cursor-pointer disabled:opacity-50"
            >
              {loading ? "Verifying Credentials..." : "Sign In to Gateway"}
            </button>
          </form>

          {/* Quick RBAC Role Demo Login */}
          <div className="mt-8 pt-6 border-t border-slate-100">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-blue-600" />
              <span>Quick Demo Roles (1-Click Instant Sign-In)</span>
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => quickLogin(acc.email, acc.pwd)}
                  className="text-left p-3 rounded-xl border border-slate-200 bg-slate-50/60 hover:border-blue-300 hover:bg-blue-50/40 transition cursor-pointer shadow-2xs"
                >
                  <div className="text-xs font-bold text-slate-900">{acc.label}</div>
                  <div className="text-[10px] text-slate-500 line-clamp-1 mt-0.5">{acc.desc}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
