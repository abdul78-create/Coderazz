"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Users,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  Copy,
  Check,
  Plus,
  RefreshCw,
  BookOpen,
  Clock,
  ShieldAlert,
  FileCode,
  CheckSquare,
  XCircle,
  ArrowRight,
  Filter,
  Sparkles,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  LineChart,
  Line,
} from "recharts";
import { authStorage } from "@/lib/auth";
import {
  apiClient,
  ClassGroup,
  ClassMisconceptionAnalyticsResponse,
  ClassRosterResponse,
  ClassStruggleTrendsResponse,
  AnnotationTask,
  UserProfile,
} from "@/lib/api";

const TAXONOMY_OPTIONS = [
  { code: "A1", name: "Off-by-one index bound (len(arr) instead of len(arr)-1)" },
  { code: "A2", name: "Negative step range omitted (range(n, 0) instead of range(n, 0, -1))" },
  { code: "A3", name: "Exclusive upper bound confusion in range()" },
  { code: "A5", name: "Empty range iteration" },
  { code: "B1", name: "Assignment instead of comparison in conditional" },
  { code: "B2", name: "Chained inequality logic error" },
  { code: "C1", name: "Infinite loop with non-advancing counter" },
  { code: "D2", name: "Variable shadowing in nested scope" },
  { code: "D4", name: "Return statement placed inside accumulator loop" },
  { code: "E1", name: "Unintended list alias / reference mutation" },
  { code: "E2", name: "List index modification during iteration" },
  { code: "F1", name: "Type mismatch in string/integer concatenation" },
  { code: "G1", name: "Mutable default argument retention across calls" },
  { code: "S1", name: "Syntax or unparseable malformed code" },
  { code: "S2", name: "Novel or unclassified emerging misconception" },
];

export default function TeacherDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const [classes, setClasses] = useState<ClassGroup[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"analytics" | "roster" | "annotations">("analytics");

  const [analyticsData, setAnalyticsData] = useState<ClassMisconceptionAnalyticsResponse | null>(null);
  const [struggleTrends, setStruggleTrends] = useState<ClassStruggleTrendsResponse | null>(null);
  const [rosterData, setRosterData] = useState<ClassRosterResponse | null>(null);
  const [annotationTasks, setAnnotationTasks] = useState<AnnotationTask[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<boolean>(false);

  // Create class modal state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [newClassName, setNewClassName] = useState<string>("");
  const [newClassDesc, setNewClassDesc] = useState<string>("");
  const [creatingClass, setCreatingClass] = useState<boolean>(false);

  // Annotation resolution state
  const [resolvingTaskId, setResolvingTaskId] = useState<string | null>(null);
  const [selectedTaxonomyCode, setSelectedTaxonomyCode] = useState<string>("D4");
  const [annotationNotes, setAnnotationNotes] = useState<string>("");
  const [resolvingSubmitting, setResolvingSubmitting] = useState<boolean>(false);

  // Authentication and RBAC Check
  useEffect(() => {
    const curUser = authStorage.getUser();
    const curToken = authStorage.getAccessToken();

    if (!curUser || !curToken) {
      router.push("/login?redirect=/teacher/dashboard");
      return;
    }

    if (curUser.role !== "TEACHER" && curUser.role !== "ADMIN") {
      router.push("/dashboard");
      return;
    }

    setUser(curUser);
    setToken(curToken);
  }, [router]);

  // Load teacher classes
  const loadClasses = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const classList = await apiClient.getTeacherClasses(token);
      setClasses(classList);

      if (classList.length > 0 && !selectedClassId) {
        setSelectedClassId(classList[0].id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load classes";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [token, selectedClassId]);

  useEffect(() => {
    if (token) {
      loadClasses();
    }
  }, [token, loadClasses]);

  // Load active class data (Analytics, Struggle Trends, Roster)
  const loadClassData = useCallback(async () => {
    if (!token || !selectedClassId) return;
    try {
      setError(null);
      const [analytics, trends, roster, annotations] = await Promise.all([
        apiClient.getClassMisconceptions(selectedClassId, token).catch(() => null),
        apiClient.getClassStruggleTrends(selectedClassId, token, 14).catch(() => null),
        apiClient.getClassRoster(selectedClassId, token).catch(() => null),
        apiClient.getAnnotationQueue(token, "PENDING", 20).catch(() => ({ total_pending: 0, tasks: [] })),
      ]);

      setAnalyticsData(analytics);
      setStruggleTrends(trends);
      setRosterData(roster);
      setAnnotationTasks(annotations.tasks || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load class analytics";
      setError(msg);
    }
  }, [token, selectedClassId]);

  useEffect(() => {
    if (token && selectedClassId) {
      loadClassData();
    }
  }, [token, selectedClassId, loadClassData]);

  // Copy class join code to clipboard
  const handleCopyJoinCode = () => {
    const currentClass = classes.find((c) => c.id === selectedClassId);
    if (!currentClass?.join_code) return;

    navigator.clipboard.writeText(currentClass.join_code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  // Create new class
  const handleCreateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !newClassName.trim()) return;

    try {
      setCreatingClass(true);
      const created = await apiClient.createClass(
        { name: newClassName.trim(), description: newClassDesc.trim() || undefined },
        token
      );
      setClasses((prev) => [created, ...prev]);
      setSelectedClassId(created.id);
      setShowCreateModal(false);
      setNewClassName("");
      setNewClassDesc("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create class";
      alert(msg);
    } finally {
      setCreatingClass(false);
    }
  };

  // Resolve human annotation task
  const handleResolveTask = async (taskId: string) => {
    if (!token) return;
    try {
      setResolvingSubmitting(true);
      await apiClient.resolveAnnotationTask(
        taskId,
        {
          resolved_misconception_code: selectedTaxonomyCode,
          annotator_notes: annotationNotes.trim() || undefined,
        },
        token
      );

      // Remove from pending list
      setAnnotationTasks((prev) => prev.filter((t) => t.id !== taskId));
      setResolvingTaskId(null);
      setAnnotationNotes("");
      // Refresh analytics
      loadClassData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to resolve annotation";
      alert(msg);
    } finally {
      setResolvingSubmitting(false);
    }
  };

  // Dismiss human annotation task
  const handleDismissTask = async (taskId: string) => {
    if (!token) return;
    if (!confirm("Are you sure you want to dismiss this annotation task?")) return;

    try {
      await apiClient.dismissAnnotationTask(taskId, token, "Dismissed by teacher");
      setAnnotationTasks((prev) => prev.filter((t) => t.id !== taskId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to dismiss annotation";
      alert(msg);
    }
  };

  const selectedClass = classes.find((c) => c.id === selectedClassId);

  // Transform data for Recharts
  const misconceptionChartData =
    analyticsData?.misconceptions.map((m) => ({
      name: `${m.misconception_code}`,
      count: m.count,
      students: m.unique_students,
      percentage: m.percentage,
      severity: m.severity,
      fullName: m.name,
    })) || [];

  const struggleTrendsChartData =
    struggleTrends?.trends.map((t) => ({
      date: t.date.slice(5), // MM-DD
      "Total Submissions": t.total_submissions,
      "Failing Submissions": t.failing_submissions,
      "Hints Requested": t.hints_requested,
      "Active Students": t.active_students,
    })) || [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Top Header & Class Switcher */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                Teacher Analytics Hub
              </span>
              <span className="text-xs text-slate-400">Phase 6 Operational</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
              Class Diagnostics & Intervention Queue
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Macroscopic misconception heatmaps, student struggle trajectories, and human ground-truth calibration.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {classes.length > 0 && (
              <select
                aria-label="Select active class"
                value={selectedClassId}
                onChange={(e) => setSelectedClassId(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-white text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
              >
                {classes.map((cls) => (
                  <option key={cls.id} value={cls.id}>
                    {cls.name} ({cls.enrolled_students_count} students)
                  </option>
                ))}
              </select>
            )}

            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-blue-600/20"
            >
              <Plus className="h-4 w-4" />
              <span>New Class</span>
            </button>

            <button
              onClick={loadClassData}
              title="Refresh Analytics"
              className="p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Empty Classes State */}
        {classes.length === 0 && !loading && (
          <div className="p-12 text-center rounded-2xl bg-slate-900/60 border border-slate-800">
            <Users className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white">No Classes Created Yet</h3>
            <p className="text-sm text-slate-400 max-w-md mx-auto mt-1 mb-6">
              Create your first class roster to distribute enrollment join codes and monitor automated misconception analytics.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm rounded-lg transition-colors"
            >
              Create Class Roster
            </button>
          </div>
        )}

        {/* Active Class Overview Cards */}
        {selectedClass && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Enrollment Join Code
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-2xl font-mono font-bold tracking-wider text-blue-400">
                  {selectedClass.join_code}
                </span>
                <button
                  onClick={handleCopyJoinCode}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
                >
                  {copiedCode ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
              <p className="text-xs text-slate-400 mt-2">Share with students to join this class.</p>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Enrolled Students
              </div>
              <div className="text-3xl font-bold text-white mt-2">
                {selectedClass.enrolled_students_count}
              </div>
              <p className="text-xs text-slate-400 mt-2">Active learners in this cohort</p>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Submissions Analyzed
              </div>
              <div className="text-3xl font-bold text-indigo-400 mt-2">
                {analyticsData?.total_submissions_analyzed || 0}
              </div>
              <p className="text-xs text-slate-400 mt-2">
                {analyticsData?.total_struggling_students || 0} students triggered diagnostic probes
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Human Review Queue
              </div>
              <div className="text-3xl font-bold text-amber-400 mt-2">
                {annotationTasks.length}
              </div>
              <p className="text-xs text-slate-400 mt-2">
                Submissions awaiting ground-truth override
              </p>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        {selectedClass && (
          <div className="flex items-center gap-2 border-b border-slate-800">
            <button
              onClick={() => setActiveTab("analytics")}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "analytics"
                  ? "border-blue-500 text-blue-400 bg-blue-500/5"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <BarChart3 className="h-4 w-4" />
              <span>Misconception & Struggle Analytics</span>
            </button>

            <button
              onClick={() => setActiveTab("roster")}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "roster"
                  ? "border-blue-500 text-blue-400 bg-blue-500/5"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Users className="h-4 w-4" />
              <span>Student Roster & Interventions ({rosterData?.total_enrolled || 0})</span>
            </button>

            <button
              onClick={() => setActiveTab("annotations")}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "annotations"
                  ? "border-amber-500 text-amber-400 bg-amber-500/5"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <FileCode className="h-4 w-4" />
              <span>Annotation Review Queue ({annotationTasks.length})</span>
            </button>
          </div>
        )}

        {/* TAB 1: Analytics & Recharts Visualizations */}
        {selectedClass && activeTab === "analytics" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Misconception Frequency Bar Chart */}
              <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-base font-semibold text-white">
                        Misconception Prevalence Distribution
                      </h3>
                      <p className="text-xs text-slate-400">
                        Frequency breakdown by 30-class taxonomy code across student submissions
                      </p>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      AST & Probes
                    </span>
                  </div>

                  {misconceptionChartData.length > 0 ? (
                    <div className="w-full h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={misconceptionChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                          <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                          <YAxis stroke="#94a3b8" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                          <Tooltip
                            contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px", color: "#f8fafc" }}
                            formatter={(value: any, name: any, item: any) => [
                              `${value} occurrences (${item.payload.students} students)`,
                              `${item.payload.name}: ${item.payload.fullName}`,
                            ]}
                          />
                          <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Occurrences" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-64 flex flex-col items-center justify-center text-slate-500">
                      <BarChart3 className="h-10 w-10 mb-2 opacity-50" />
                      <p className="text-sm">No failing submissions diagnosed yet in this cohort.</p>
                    </div>
                  )}
                </div>

                {misconceptionChartData.length > 0 && (
                  <div className="pt-4 border-t border-slate-800 flex flex-wrap gap-2 text-xs">
                    <span className="text-slate-400">Top Class Struggle:</span>
                    <span className="font-semibold text-amber-400">
                      {misconceptionChartData[0]?.name} - {misconceptionChartData[0]?.fullName} (
                      {misconceptionChartData[0]?.percentage}%)
                    </span>
                  </div>
                )}
              </div>

              {/* Multi-line Struggle Trends Chart */}
              <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-base font-semibold text-white">
                        Cohort Struggle Trajectory (14 Days)
                      </h3>
                      <p className="text-xs text-slate-400">
                        Comparing total attempts, failures, hint requests, and active learners
                      </p>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      Time Series
                    </span>
                  </div>

                  {struggleTrendsChartData.length > 0 ? (
                    <div className="w-full h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={struggleTrendsChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                          <XAxis dataKey="date" stroke="#94a3b8" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                          <YAxis stroke="#94a3b8" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                          <Tooltip
                            contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px", color: "#f8fafc" }}
                          />
                          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                          <Line type="monotone" dataKey="Total Submissions" stroke="#3b82f6" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="Failing Submissions" stroke="#ef4444" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="Hints Requested" stroke="#a855f7" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="Active Students" stroke="#10b981" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-64 flex flex-col items-center justify-center text-slate-500">
                      <TrendingUp className="h-10 w-10 mb-2 opacity-50" />
                      <p className="text-sm">Activity trends will populate as students solve problems.</p>
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                  <span>Legend: 🔵 Total Attempts | 🔴 Failures | 🟣 Hint Requests | 🟢 Learners</span>
                </div>
              </div>
            </div>

            {/* Detailed Misconception Table */}
            <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-800">
                <h3 className="text-base font-semibold text-white">Taxonomy Diagnostic Insights</h3>
                <p className="text-xs text-slate-400">
                  Detailed pedagogical breakdown with recommended teaching interventions
                </p>
              </div>

              {analyticsData && analyticsData.misconceptions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-slate-300">
                    <thead className="bg-slate-950/50 text-xs uppercase text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="px-6 py-3">Code</th>
                        <th className="px-6 py-3">Misconception</th>
                        <th className="px-6 py-3">Category</th>
                        <th className="px-6 py-3">Severity</th>
                        <th className="px-6 py-3">Occurrences</th>
                        <th className="px-6 py-3">Affected Students</th>
                        <th className="px-6 py-3">% of Cohort</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {analyticsData.misconceptions.map((m) => (
                        <tr key={m.misconception_code} className="hover:bg-slate-800/40 transition-colors">
                          <td className="px-6 py-4 font-mono font-bold text-blue-400">
                            {m.misconception_code}
                          </td>
                          <td className="px-6 py-4 font-medium text-white max-w-xs">
                            <div>{m.name}</div>
                            <div className="text-xs text-slate-400 truncate">{m.description}</div>
                          </td>
                          <td className="px-6 py-4 text-xs font-mono text-slate-400">{m.category}</td>
                          <td className="px-6 py-4">
                            <span
                              className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${
                                m.severity === "CRITICAL"
                                  ? "bg-red-500/10 text-red-400 border-red-500/30"
                                  : m.severity === "HIGH"
                                  ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                                  : "bg-blue-500/10 text-blue-400 border-blue-500/30"
                              }`}
                            >
                              {m.severity}
                            </span>
                          </td>
                          <td className="px-6 py-4 font-semibold text-white">{m.count}</td>
                          <td className="px-6 py-4">{m.unique_students}</td>
                          <td className="px-6 py-4 font-bold text-indigo-400">{m.percentage}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500 text-sm">
                  No misconception data recorded for this class yet.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: Student Roster & Interventions */}
        {selectedClass && activeTab === "roster" && (
          <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-white">Enrolled Students Roster</h3>
                <p className="text-xs text-slate-400">
                  Cohort members enrolled in {selectedClass.name} via join code {selectedClass.join_code}
                </p>
              </div>
              <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
                {rosterData?.students.length || 0} Registered
              </span>
            </div>

            {rosterData && rosterData.students.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead className="bg-slate-950/50 text-xs uppercase text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="px-6 py-3">Student Name</th>
                      <th className="px-6 py-3">Email Address</th>
                      <th className="px-6 py-3">Enrolled On</th>
                      <th className="px-6 py-3">Intervention Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {rosterData.students.map((student) => (
                      <tr key={student.student_id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="px-6 py-4 font-medium text-white flex items-center gap-2">
                          <div className="h-7 w-7 rounded-full bg-slate-800 flex items-center justify-center text-xs text-slate-300">
                            {student.student_name.charAt(0)}
                          </div>
                          <span>{student.student_name}</span>
                        </td>
                        <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                          {student.student_email}
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-400">
                          {new Date(student.enrolled_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                            Active
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500 text-sm">
                No students enrolled yet. Distribute join code{" "}
                <span className="font-mono font-bold text-blue-400">{selectedClass.join_code}</span> to
                your class.
              </div>
            )}
          </div>
        )}

        {/* TAB 3: Human Annotation Review Queue */}
        {selectedClass && activeTab === "annotations" && (
          <div className="space-y-6">
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm flex items-center gap-3">
              <ShieldAlert className="h-5 w-5 shrink-0 text-amber-400" />
              <div>
                <span className="font-semibold">Human-in-the-Loop Calibration Active:</span> Submissions
                with diagnostic confidence below 0.50 or novel unclassified code patterns (S2) are routed here
                for educator verification and ground-truth updating.
              </div>
            </div>

            {annotationTasks.length > 0 ? (
              <div className="space-y-4">
                {annotationTasks.map((task) => (
                  <div
                    key={task.id}
                    className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-bold text-amber-400">
                            Task #{task.id.slice(0, 8)}
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/30">
                            {task.trigger_reason}
                          </span>
                        </div>
                        <div className="text-xs text-slate-400 mt-1">
                          Problem: <span className="text-white">{task.problem_title || "Unknown"}</span> |
                          Student: <span className="text-white">{task.student_name || "Anonymous"}</span> |
                          Original Detection:{" "}
                          <span className="font-mono font-bold text-blue-400">
                            {task.original_misconception_code}
                          </span>{" "}
                          ({Math.round(task.original_confidence * 100)}% confidence)
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => {
                            setResolvingTaskId(task.id);
                            setSelectedTaxonomyCode(task.original_misconception_code || "D4");
                          }}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors"
                        >
                          Verify / Override
                        </button>
                        <button
                          onClick={() => handleDismissTask(task.id)}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition-colors border border-slate-700"
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>

                    {/* Code Snippet Preview */}
                    {task.submission_code && (
                      <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 font-mono text-xs text-slate-200 overflow-x-auto">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2 font-sans font-bold">
                          Submitted Python Code:
                        </div>
                        <pre>{task.submission_code}</pre>
                      </div>
                    )}

                    {/* Inline Resolution Drawer */}
                    {resolvingTaskId === task.id && (
                      <div className="p-4 rounded-xl bg-slate-950 border border-blue-500/30 space-y-3">
                        <div className="text-xs font-semibold text-white uppercase tracking-wider">
                          Authoritative Misconception Classification Override
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs text-slate-400 mb-1">
                              Select Ground-Truth Taxonomy Code:
                            </label>
                            <select
                              value={selectedTaxonomyCode}
                              onChange={(e) => setSelectedTaxonomyCode(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg px-3 py-2 outline-none"
                            >
                              {TAXONOMY_OPTIONS.map((opt) => (
                                <option key={opt.code} value={opt.code}>
                                  {opt.code} - {opt.name}
                                </option>
                              ))}
                            </select>
                          </div>

                          <div>
                            <label className="block text-xs text-slate-400 mb-1">
                              Annotator Notes (Optional justification):
                            </label>
                            <input
                              type="text"
                              value={annotationNotes}
                              onChange={(e) => setAnnotationNotes(e.target.value)}
                              placeholder="e.g. Premature return inside accumulator loop verified"
                              className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg px-3 py-2 outline-none"
                            />
                          </div>
                        </div>

                        <div className="flex items-center justify-end gap-2 pt-2">
                          <button
                            onClick={() => setResolvingTaskId(null)}
                            className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleResolveTask(task.id)}
                            disabled={resolvingSubmitting}
                            className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5"
                          >
                            <Check className="h-3.5 w-3.5" />
                            <span>
                              {resolvingSubmitting ? "Updating..." : "Commit Ground Truth Override (1.0)"}
                            </span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800">
                <CheckCircle className="h-10 w-10 text-emerald-400 mx-auto mb-3" />
                <h4 className="text-base font-semibold text-white">Annotation Queue Clear</h4>
                <p className="text-xs text-slate-400 mt-1">
                  All low-confidence submissions have been resolved or automated classifications hold high certainty.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Modal: Create Class Roster */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Users className="h-5 w-5 text-blue-500" />
                  <span>Create Class Roster</span>
                </h3>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-slate-400 hover:text-white text-sm"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateClass} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    Class Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={newClassName}
                    onChange={(e) => setNewClassName(e.target.value)}
                    placeholder="e.g. CS101 Introduction to Python"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    Description (Optional)
                  </label>
                  <textarea
                    rows={3}
                    value={newClassDesc}
                    onChange={(e) => setNewClassDesc(e.target.value)}
                    placeholder="e.g. Fall 2026 undergraduate programming lab section"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                  />
                </div>

                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300">
                  A unique 6-character uppercase enrollment code will automatically be generated for students.
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creatingClass}
                    className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    {creatingClass ? "Creating..." : "Create Class"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
