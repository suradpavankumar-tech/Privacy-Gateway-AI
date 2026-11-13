/**
 * ==============================================================================
 * Privacy Gateway AI (MINEARENA PS-02) — Root Application Orchestrator
 * ==============================================================================
 * Tech Stack:
 *  - React 19 (Functional Components, Hooks: useState, useEffect)
 *  - TypeScript: Type safety with strict interfaces (`UserProfile`, `HealthResponse`)
 *  - Tailwind CSS: Layout, pastel gradients, and dark/light responsive styling
 *  - REST API Client (`services/api.ts`): JWT session restoration and role switching
 *
 * Architecture & Flow:
 *  1. Session Bootstrapping: Checks backend `/health` and stored JWT via `/auth/me`.
 *  2. Unauthenticated State: Renders `LoginView` with 1-click RBAC demo accounts.
 *  3. Authenticated State: Wraps the active view in `DashboardLayout` (pitch-black
 *     sidebar, pastel canvas, top search & notifications pill).
 *  4. Workspaces Supported:
 *     - "command"    -> CommandCenter (Executive Dashboard & Telemetry)
 *     - "studio"     -> ProcessingCenter (PII Masking, OCR, Outbound Gate & SLM)
 *     - "benchmark"  -> BenchmarkLab (50-Doc Indian Corpus Precision/Recall/F1)
 *     - "governance" -> GovernanceAuditCenter (Policies, RBAC Matrix & Audit Log)
 * ==============================================================================
 */

import React, { useEffect, useState } from "react";
import { DashboardLayout, type WorkspaceTab } from "./components/DashboardLayout";
import { DEMO_ACCOUNTS, LoginView } from "./components/LoginView";
import { BenchmarkLab } from "./pages/BenchmarkLab";
import { CommandCenter } from "./pages/CommandCenter";
import { GovernanceAuditCenter } from "./pages/GovernanceAuditCenter";
import { ProcessingCenter } from "./pages/ProcessingCenter";
import { api, getStoredToken, setStoredToken } from "./services/api";
import type { DatasetDocument, HealthResponse, UserProfile } from "./types/api";

export const App: React.FC = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("command");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadedDocument, setLoadedDocument] = useState<DatasetDocument | null>(null);
  const [switchingRole, setSwitchingRole] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    const restoreSession = async () => {
      try {
        const h = await api.health();
        setHealth(h);
      } catch {
        // Ignore initial health fetch failure
      }
      if (getStoredToken()) {
        try {
          const me = await api.me();
          setUser(me);
          if (!me.permissions.includes("process:submit")) {
            setActiveTab("governance");
          }
        } catch {
          setStoredToken(null);
        }
      }
      setBootstrapping(false);
    };
    restoreSession();
  }, []);

  const handleAuthenticated = (authedUser: UserProfile) => {
    setUser(authedUser);
    if (!authedUser.permissions.includes("process:submit")) {
      setActiveTab("governance");
    } else {
      setActiveTab("command");
    }
  };

  const handleRoleSwitch = async (email: string) => {
    const account = DEMO_ACCOUNTS.find((a) => a.email === email);
    if (!account) return;
    setSwitchingRole(true);
    try {
      const res = await api.login(account.email, account.pwd);
      setUser(res.user);
      if (!res.user.permissions.includes("process:submit") && activeTab === "studio") {
        setActiveTab("governance");
      }
    } finally {
      setSwitchingRole(false);
    }
  };

  const handleLogout = () => {
    setStoredToken(null);
    setUser(null);
  };

  const handleLoadDocumentToStudio = (doc: DatasetDocument) => {
    setLoadedDocument(doc);
    setActiveTab("studio");
  };

  if (bootstrapping) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#ffdbe6] via-[#e2e8f0] to-[#cbe2fe] flex items-center justify-center p-6 font-sans">
        <div className="bg-white rounded-3xl p-8 shadow-xl border border-white/60 flex items-center gap-4">
          <div className="w-8 h-8 rounded-full border-3 border-blue-500 border-t-transparent animate-spin" />
          <div>
            <div className="text-sm font-bold text-slate-900">Privacy Gateway AI</div>
            <div className="text-xs text-slate-500">Initializing DPDP Control Plane...</div>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginView onAuthenticated={handleAuthenticated} />;
  }

  const canProcess = user.permissions.includes("process:submit");

  return (
    <DashboardLayout
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      user={user}
      health={health}
      onLogout={handleLogout}
      onRoleSwitch={handleRoleSwitch}
      switchingRole={switchingRole}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
      canProcess={canProcess}
    >
      {activeTab === "command" && (
        <CommandCenter
          onNavigateStudio={() => setActiveTab("studio")}
          searchFilter={searchQuery}
        />
      )}
      {activeTab === "studio" && canProcess && (
        <ProcessingCenter
          user={user}
          loadedDocument={loadedDocument}
          onClearLoadedDocument={() => setLoadedDocument(null)}
          searchFilter={searchQuery}
        />
      )}
      {activeTab === "benchmark" && (
        <BenchmarkLab
          user={user}
          onLoadDocument={handleLoadDocumentToStudio}
          searchFilter={searchQuery}
        />
      )}
      {activeTab === "governance" && (
        <GovernanceAuditCenter
          user={user}
          searchFilter={searchQuery}
        />
      )}
    </DashboardLayout>
  );
};

export default App;
