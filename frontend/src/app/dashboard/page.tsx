"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  User,
  LogOut,
  CheckCircle,
  XCircle,
  Terminal,
  Key,
  GraduationCap,
  School,
  FileCheck,
  Crown,
  RefreshCw,
  Clock,
} from "lucide-react";
import { api, UserProfile, UserRole } from "@/lib/api";
import { authStorage } from "@/lib/auth";

interface ProbeResult {
  role: string;
  success: boolean;
  message: string;
  timestamp: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [probeLoading, setProbeLoading] = useState<string | null>(null);
  const [probeResults, setProbeResults] = useState<Record<string, ProbeResult>>({});

  useEffect(() => {
    const storedToken = authStorage.getAccessToken();
    const storedUser = authStorage.getUser();

    if (!storedToken || !storedUser) {
      router.push("/login");
      return;
    }

    setToken(storedToken);
    setUser(storedUser);

    // Refresh profile in background
    api
      .getMe(storedToken)
      .then((updatedUser) => {
        setUser(updatedUser);
        authStorage.setUser(updatedUser);
      })
      .catch(() => {
        // Token might have expired
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [router]);

  const handleLogout = async () => {
    const refreshToken = authStorage.getRefreshToken();
    try {
      await api.logout(refreshToken, token);
    } catch {
      // Ignore network errors on logout
    } finally {
      authStorage.clearAuth();
      router.push("/login");
    }
  };

  const handleTestRole = async (targetRole: "student" | "teacher" | "annotator" | "admin") => {
    if (!token) return;
    setProbeLoading(targetRole);

    try {
      const res = await api.testRoleProbe(targetRole, token);
      setProbeResults((prev) => ({
        ...prev,
        [targetRole]: {
          role: targetRole.toUpperCase(),
          success: true,
          message: res.message,
          timestamp: new Date().toLocaleTimeString(),
        },
      }));
    } catch (err: unknown) {
      const errorMsg =
        err && typeof err === "object" && "message" in err
          ? (err as { message: string }).message
          : "Access Denied";
      setProbeResults((prev) => ({
        ...prev,
        [targetRole]: {
          role: targetRole.toUpperCase(),
          success: false,
          message: errorMsg,
          timestamp: new Date().toLocaleTimeString(),
        },
      }));
    } finally {
      setProbeLoading(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <div className="h-8 w-8 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
        <p className="text-sm text-slate-400">Verifying session credentials...</p>
      </div>
    );
  }

  if (!user) return null;

  const roleBadgeConfig: Record<
    UserRole,
    { label: string; bg: string; border: string; text: string; icon: React.ReactNode }
  > = {
    ADMIN: {
      label: "Administrator",
      bg: "bg-purple-500/10",
      border: "border-purple-500/30",
      text: "text-purple-400",
      icon: <Crown className="h-4 w-4 text-purple-400" />,
    },
    TEACHER: {
      label: "Teacher / Faculty",
      bg: "bg-amber-500/10",
      border: "border-amber-500/30",
      text: "text-amber-400",
      icon: <School className="h-4 w-4 text-amber-400" />,
    },
    ANNOTATOR: {
      label: "Dataset Annotator",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/30",
      text: "text-emerald-400",
      icon: <FileCheck className="h-4 w-4 text-emerald-400" />,
    },
    STUDENT: {
      label: "Student Learner",
      bg: "bg-blue-500/10",
      border: "border-blue-500/30",
      text: "text-blue-400",
      icon: <GraduationCap className="h-4 w-4 text-blue-400" />,
    },
  };

  const currentRoleConfig = roleBadgeConfig[user.role] || roleBadgeConfig.STUDENT;

  return (
    <div className="space-y-8 pb-16">
      {/* User Header Profile */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 sm:p-8 backdrop-blur-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/5 rounded-full blur-3xl -z-10" />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="flex items-start sm:items-center gap-4">
            <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 shrink-0">
              <User className="h-7 w-7" />
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-bold text-white tracking-tight">{user.full_name}</h1>
                <div
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-semibold ${currentRoleConfig.bg} ${currentRoleConfig.border} ${currentRoleConfig.text}`}
                >
                  {currentRoleConfig.icon}
                  <span>{currentRoleConfig.label}</span>
                </div>
              </div>
              <p className="text-sm text-slate-400 mt-1 flex items-center gap-2">
                <span>{user.email}</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-500 font-mono">ID: {user.id.slice(0, 8)}...</span>
              </p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="self-start sm:self-center flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 hover:text-white hover:border-red-500/40 hover:bg-red-500/10 text-xs font-medium transition-all"
          >
            <LogOut className="h-4 w-4 text-slate-400" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Grid: Permissions & Interactive Probes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Card 1: Role Permissions & Capabilities */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Shield className="h-5 w-5 text-indigo-400" />
              <h2 className="text-lg font-semibold text-white">Active RBAC Permissions</h2>
            </div>
            <p className="text-xs text-slate-400 mb-6">
              CodeRazz enforces Role-Based Access Control on backend FastAPI endpoints. Below are your assigned privileges:
            </p>

            <ul className="space-y-3">
              <li className="flex items-start gap-3 text-xs">
                <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-white">Solve Programming Challenges</span>
                  <p className="text-slate-400">Execute code inside isolated Docker sandbox runners</p>
                </div>
              </li>
              <li className="flex items-start gap-3 text-xs">
                <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-white">Receive Progressive 5-Tier Hints</span>
                  <p className="text-slate-400">Nudge, Conceptual, Counter-example, Worked Analogue, Targeted Pointer</p>
                </div>
              </li>
              <li className="flex items-start gap-3 text-xs">
                {user.role === "TEACHER" || user.role === "ADMIN" ? (
                  <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="h-4 w-4 text-slate-600 shrink-0 mt-0.5" />
                )}
                <div>
                  <span className={user.role === "TEACHER" || user.role === "ADMIN" ? "font-semibold text-white" : "text-slate-500"}>
                    Class Misconception Heatmaps & Analytics
                  </span>
                  <p className="text-slate-500">View diagnostic aggregation across student cohort</p>
                </div>
              </li>
              <li className="flex items-start gap-3 text-xs">
                {user.role === "ANNOTATOR" || user.role === "ADMIN" ? (
                  <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="h-4 w-4 text-slate-600 shrink-0 mt-0.5" />
                )}
                <div>
                  <span className={user.role === "ANNOTATOR" || user.role === "ADMIN" ? "font-semibold text-white" : "text-slate-500"}>
                    Curate Ground Truth Taxonomy
                  </span>
                  <p className="text-slate-500">Label student misconceptions across A1–G3 categories</p>
                </div>
              </li>
              <li className="flex items-start gap-3 text-xs">
                {user.role === "ADMIN" ? (
                  <CheckCircle className="h-4 w-4 text-purple-400 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="h-4 w-4 text-slate-600 shrink-0 mt-0.5" />
                )}
                <div>
                  <span className={user.role === "ADMIN" ? "font-semibold text-purple-300" : "text-slate-500"}>
                    Administrator Role Management
                  </span>
                  <p className="text-slate-500">Promote users, configure sandbox quotas, inspect database</p>
                </div>
              </li>
            </ul>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Key className="h-3.5 w-3.5 text-blue-400" />
              Argon2id + JWT Bearer Auth Active
            </span>
            <span>PostgreSQL 16 Storage</span>
          </div>
        </div>

        {/* Card 2: Live RBAC Endpoint Verification Probes */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Terminal className="h-5 w-5 text-blue-400" />
              <h2 className="text-lg font-semibold text-white">Live Backend RBAC Probes</h2>
            </div>
            <span className="text-[10px] font-mono text-slate-500 uppercase px-2 py-0.5 rounded bg-slate-950 border border-slate-800">
              Interactive Test
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            Click each button below to probe real FastAPI endpoints with your Bearer token.
            The backend verifies your role and returns either <strong>HTTP 200 OK</strong> or <strong>HTTP 403 Forbidden</strong>.
          </p>

          <div className="space-y-3">
            {(["student", "teacher", "annotator", "admin"] as const).map((r) => {
              const result = probeResults[r];
              const isProbing = probeLoading === r;

              return (
                <div
                  key={r}
                  className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col gap-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-medium text-slate-300">
                      GET /api/v1/auth/role-test/{r}
                    </span>
                    <button
                      type="button"
                      disabled={isProbing}
                      onClick={() => handleTestRole(r)}
                      className="px-3 py-1 rounded-lg bg-blue-600/10 border border-blue-500/20 text-blue-400 hover:bg-blue-600 hover:text-white text-xs font-medium transition-all disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {isProbing ? (
                        <>
                          <RefreshCw className="h-3 w-3 animate-spin" />
                          <span>Testing...</span>
                        </>
                      ) : (
                        <span>Test Access</span>
                      )}
                    </button>
                  </div>

                  {result && (
                    <div
                      className={`text-xs p-2.5 rounded-lg border flex items-start gap-2 ${
                        result.success
                          ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
                          : "bg-red-500/10 border-red-500/20 text-red-300"
                      }`}
                    >
                      {result.success ? (
                        <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1 font-mono text-[11px]">
                        <span className="font-bold">{result.success ? "200 OK: " : "403 Forbidden: "}</span>
                        <span>{result.message}</span>
                        <div className="text-[10px] text-slate-500 mt-1 flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          <span>{result.timestamp}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

