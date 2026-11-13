/**
 * ==============================================================================
 * Privacy Gateway AI (MINEARENA PS-02) — Master Enterprise Dashboard Shell
 * ==============================================================================
 * Tech Stack:
 *  - React 19 + TypeScript
 *  - Tailwind CSS: Custom multi-stop pastel gradient, floating rounded canvas,
 *    pitch-black vertical sidebar (`#0e1117`), electric blue highlights (`#168FF0`)
 *  - Lucide React: Modern minimalist iconography
 *
 * Responsibilities:
 *  - Renders the reference-inspired outer frame with pastel background gradient.
 *  - Houses the sleek vertical sidebar with icon-only navigation, active indicator,
 *    hover tooltips, and bottom settings / logout controls.
 *  - Houses the top bar: Active page title, organization tag, dark pill search bar,
 *    live "Zero-Leak Armed" health badge, notification drawer, and profile switcher.
 *  - Renders child workspace pages (`CommandCenter`, `ProcessingCenter`, etc.).
 * ==============================================================================
 */

import React, { useState } from "react";
import {
  Activity,
  Bell,
  CheckCircle2,
  ChevronDown,
  FileSearch,
  FlaskConical,
  LayoutDashboard,
  Layers,
  Lock,
  LogOut,
  Menu,
  MessageSquare,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  Sliders,
  UserCheck,
  X,
} from "lucide-react";
import { DEMO_ACCOUNTS } from "./LoginView";
import type { HealthResponse, UserProfile } from "../types/api";

export type WorkspaceTab = "command" | "studio" | "benchmark" | "governance";

interface DashboardLayoutProps {
  activeTab: WorkspaceTab;
  onSelectTab: (tab: WorkspaceTab) => void;
  user: UserProfile;
  health: HealthResponse | null;
  onLogout: () => void;
  onRoleSwitch: (email: string) => void;
  switchingRole: boolean;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  canProcess: boolean;
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  activeTab,
  onSelectTab,
  user,
  health,
  onLogout,
  onRoleSwitch,
  switchingRole,
  searchQuery,
  onSearchChange,
  canProcess,
  children,
}) => {
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const navItems: Array<{
    id: WorkspaceTab;
    label: string;
    icon: React.ReactNode;
    disabled?: boolean;
    tooltip: string;
  }> = [
    {
      id: "command",
      label: "Dashboard",
      icon: <LayoutDashboard className="w-5 h-5" />,
      tooltip: "Executive Overview & Telemetry",
    },
    {
      id: "studio",
      label: "Processing Center",
      icon: <Layers className="w-5 h-5" />,
      disabled: !canProcess,
      tooltip: canProcess ? "Privacy Processing Studio" : "Read-Only for Auditor Role",
    },
    {
      id: "benchmark",
      label: "Benchmark Lab",
      icon: <FlaskConical className="w-5 h-5" />,
      tooltip: "50-Document Evaluation Benchmark",
    },
    {
      id: "governance",
      label: "Governance & Audit",
      icon: <Sliders className="w-5 h-5" />,
      tooltip: "DPDP Policies, RBAC & Audit Trails",
    },
  ];

  const currentAccount = DEMO_ACCOUNTS.find((a) => a.email === user.email);

  // Tab Title mapping
  const getPageTitle = () => {
    switch (activeTab) {
      case "command":
        return "Dashboard";
      case "studio":
        return "Privacy Processing Center";
      case "benchmark":
        return "Benchmark Lab (50 Docs)";
      case "governance":
        return "Governance & Audit Center";
      default:
        return "Dashboard";
    }
  };

  return (
    <div className="min-h-screen p-2 sm:p-4 lg:p-6 bg-gradient-to-br from-[#ffdbe6] via-[#e2e8f0] to-[#cbe2fe] flex items-center justify-center font-sans antialiased text-slate-800">
      {/* Main Floating Rounded Application Frame */}
      <div className="w-full max-w-[1720px] min-h-[92vh] rounded-[2.25rem] bg-white shadow-2xl flex overflow-hidden border border-white/60 relative">
        {/* ================= LEFT BLACK SIDEBAR ================= */}
        <aside className="w-18 sm:w-20 md:w-22 bg-[#0e1117] flex flex-col items-center py-7 px-2 border-r border-slate-800/50 shrink-0 select-none justify-between z-30">
          {/* Top: Menu / Brand Logo */}
          <div className="flex flex-col items-center gap-7 w-full">
            <button
              type="button"
              onClick={() => onSelectTab("command")}
              className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-500 text-white flex items-center justify-center shadow-lg shadow-blue-500/30 hover:scale-105 transition cursor-pointer"
              title="Privacy Gateway AI"
            >
              <ShieldCheck className="w-6 h-6 text-white" />
            </button>

            {/* Vertical Navigation Icons */}
            <nav aria-label="Main Navigation" className="flex flex-col items-center gap-3 w-full">
              {navItems.map((item) => {
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    disabled={item.disabled}
                    onClick={() => onSelectTab(item.id)}
                    title={item.tooltip}
                    className={`relative w-12 h-12 rounded-2xl flex items-center justify-center transition-all cursor-pointer group ${
                      isActive
                        ? "bg-[#168FF0] text-white shadow-lg shadow-blue-500/40 scale-105"
                        : "text-slate-400 hover:text-white hover:bg-white/10"
                    } ${item.disabled ? "opacity-35 cursor-not-allowed" : ""}`}
                  >
                    {item.icon}

                    {/* Tooltip on hover */}
                    <div className="absolute left-full ml-3.5 px-3 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-medium whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-xl border border-slate-800">
                      {item.label}
                    </div>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Bottom Sidebar: Role Switcher Settings & Logout */}
          <div className="flex flex-col items-center gap-3 w-full pt-4 border-t border-slate-800/70">
            <button
              type="button"
              onClick={() => setShowRoleModal(true)}
              className="w-11 h-11 rounded-2xl text-slate-400 hover:text-white hover:bg-white/10 flex items-center justify-center transition cursor-pointer group relative"
              title="Switch Demo Role"
            >
              <Settings className="w-5 h-5" />
              <div className="absolute left-full ml-3 px-2.5 py-1 rounded-lg bg-slate-900 text-white text-xs font-medium whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 border border-slate-800">
                Switch Role ({user.role})
              </div>
            </button>

            <button
              type="button"
              onClick={onLogout}
              className="w-11 h-11 rounded-2xl text-rose-400/80 hover:text-rose-300 hover:bg-rose-500/10 flex items-center justify-center transition cursor-pointer group relative"
              title="Sign Out"
            >
              <LogOut className="w-5 h-5" />
              <div className="absolute left-full ml-3 px-2.5 py-1 rounded-lg bg-slate-900 text-rose-300 text-xs font-medium whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 border border-slate-800">
                Sign Out
              </div>
            </button>
          </div>
        </aside>

        {/* ================= MAIN WHITE WORKSPACE ================= */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#f8fafc] overflow-hidden">
          {/* Top Navigation Bar */}
          <header className="h-20 bg-white border-b border-slate-100 px-6 sm:px-8 flex items-center justify-between gap-4 sticky top-0 z-20 shrink-0">
            {/* Left: Page Title */}
            <div className="flex items-center gap-3 min-w-0">
              <div>
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 truncate">
                  {getPageTitle()}
                </h1>
                <div className="text-[11px] text-slate-400 hidden sm:flex items-center gap-2">
                  <span>{user.org_name}</span>
                  <span>•</span>
                  <span className="text-emerald-600 font-semibold">DPDP PS-02 Control Plane</span>
                </div>
              </div>
            </div>

            {/* Center: Sleek Dark Search Bar Pill */}
            <div className="hidden md:flex items-center justify-center flex-1 max-w-md mx-4">
              <div className="bg-[#0e1117] text-white rounded-full px-4 py-2 text-xs flex items-center gap-3 w-full border border-slate-800/80 focus-within:ring-2 focus-within:ring-blue-500/40 transition-all shadow-inner">
                <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <input
                  type="text"
                  placeholder="Search documents, entities, policies..."
                  value={searchQuery}
                  onChange={(e) => onSearchChange(e.target.value)}
                  className="bg-transparent text-white placeholder-slate-500 text-xs focus:outline-none w-full"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => onSearchChange("")}
                    className="text-slate-400 hover:text-white"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>

            {/* Right: Notifications, Role & Profile Dropdown */}
            <div className="flex items-center gap-3 shrink-0">
              {/* System Health Pill */}
              {health && (
                <div
                  title={`Gateway Health: ${health.status}`}
                  className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200/80 text-[11px] text-emerald-700 font-semibold"
                >
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Zero-Leak Armed</span>
                </div>
              )}

              {/* Notification Bell */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setNotificationsOpen(!notificationsOpen)}
                  className="w-10 h-10 rounded-full border border-slate-200 hover:border-slate-300 bg-white flex items-center justify-center text-slate-600 hover:text-slate-900 transition cursor-pointer relative"
                  title="Notifications & Alerts"
                >
                  <Bell className="w-4 h-4" />
                  <span className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-blue-500 ring-2 ring-white" />
                </button>

                {notificationsOpen && (
                  <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-white border border-slate-150 shadow-2xl p-4 z-50 text-xs animate-in fade-in slide-in-from-top-2">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                      <span className="font-bold text-slate-800">Security Gate Alerts</span>
                      <span className="text-[10px] text-slate-400">All Systems Normal</span>
                    </div>
                    <div className="py-3 space-y-2 text-[11px] text-slate-600">
                      <div className="flex items-start gap-2 p-2 rounded-xl bg-emerald-50/70 border border-emerald-100">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                        <div>
                          <p className="font-semibold text-emerald-900">Zero Leakage Enforced</p>
                          <p className="text-emerald-700">AES-256-GCM vault isolation active.</p>
                        </div>
                      </div>
                      <div className="flex items-start gap-2 p-2 rounded-xl bg-blue-50/70 border border-blue-100">
                        <Shield className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                        <div>
                          <p className="font-semibold text-blue-900">Local SLM Engine Ready</p>
                          <p className="text-blue-700">Offline fallback enabled on port 11434.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Quick Role Switcher Pill */}
              <div className="hidden sm:flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-full px-3 py-1 text-xs">
                <UserCheck className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                <select
                  aria-label="Quick Role Switcher"
                  disabled={switchingRole}
                  value={user.email}
                  onChange={(e) => onRoleSwitch(e.target.value)}
                  className="bg-transparent text-xs font-semibold text-slate-800 focus:outline-none cursor-pointer max-w-[140px] truncate"
                >
                  {DEMO_ACCOUNTS.map((acc) => (
                    <option key={acc.email} value={acc.email}>
                      {acc.label} ({acc.role})
                    </option>
                  ))}
                </select>
              </div>

              {/* User Profile Avatar */}
              <div
                onClick={() => setShowRoleModal(true)}
                className="flex items-center gap-2 pl-1 cursor-pointer group"
                title={`${user.full_name} (${user.role}) - Click to Switch Account`}
              >
                <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-slate-800 to-slate-900 text-white flex items-center justify-center font-bold text-xs shadow-md border-2 border-white ring-1 ring-slate-200">
                  {user.full_name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")
                    .slice(0, 2)}
                </div>
                <div className="hidden xl:block text-left text-xs">
                  <div className="font-bold text-slate-900 group-hover:text-blue-600 transition truncate max-w-[120px]">
                    {user.full_name}
                  </div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono tracking-wider font-semibold">
                    {user.role}
                  </div>
                </div>
              </div>
            </div>
          </header>

          {/* Workspace Body Content */}
          <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-[#f8fafc]">
            {children}
          </main>
        </div>
      </div>

      {/* Role Switcher Modal */}
      {showRoleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-3xl border border-slate-150 shadow-2xl p-6 max-w-lg w-full animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900">Switch Demo Account</h3>
                <p className="text-xs text-slate-500">Test different DPDP role permissions</p>
              </div>
              <button
                type="button"
                onClick={() => setShowRoleModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-4">
              {DEMO_ACCOUNTS.map((acc) => {
                const isCurrent = acc.email === user.email;
                return (
                  <button
                    key={acc.email}
                    type="button"
                    onClick={() => {
                      onRoleSwitch(acc.email);
                      setShowRoleModal(false);
                    }}
                    className={`p-3 rounded-2xl text-left border transition ${
                      isCurrent
                        ? "bg-blue-50/70 border-blue-300 ring-2 ring-blue-500/20"
                        : "bg-slate-50/60 border-slate-200 hover:border-slate-300 hover:bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 text-xs">{acc.label}</span>
                      {isCurrent && <span className="w-2 h-2 rounded-full bg-blue-600" />}
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5">{acc.email}</div>
                    <div className="text-[10px] text-slate-600 mt-1 line-clamp-2">{acc.desc}</div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
