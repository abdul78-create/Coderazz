"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import {
  Play,
  Send,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Clock,
  Terminal,
  FileCode2,
  History,
  AlertCircle,
  HelpCircle,
  Shield,
  Layers,
  ChevronRight,
  Maximize2,
  Sparkles,
} from "lucide-react";
import {
  api,
  ProblemDetail,
  CodeRunResult,
  SubmissionRecord,
  SubmissionListItem,
  SubmissionVerdict,
} from "@/lib/api";
import { authStorage } from "@/lib/auth";

// Dynamically import Monaco Editor to avoid SSR hydration mismatches
const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full bg-slate-950 flex items-center justify-center text-slate-500 text-xs">
      <div className="flex items-center gap-2">
        <span className="h-4 w-4 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
        Loading Monaco Code Editor...
      </div>
    </div>
  ),
});

export default function ProblemWorkspacePage() {
  const router = useRouter();
  const routeParams = useParams();
  const slugOrId = routeParams?.id as string;

  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [code, setCode] = useState<string>("");
  const [token, setToken] = useState<string | null>(null);
  const [activeLeftTab, setActiveLeftTab] = useState<"description" | "history">("description");
  const [activeBottomTab, setActiveBottomTab] = useState<"testcases" | "console" | "custom">("testcases");
  const [selectedTestCaseIndex, setSelectedTestCaseIndex] = useState<number>(0);
  const [customInput, setCustomInput] = useState<string>("");

  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runResult, setRunResult] = useState<CodeRunResult | null>(null);
  const [submissionResult, setSubmissionResult] = useState<SubmissionRecord | null>(null);
  const [submissionsList, setSubmissionsList] = useState<SubmissionListItem[]>([]);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = authStorage.getAccessToken();
    setToken(storedToken);

    if (slugOrId) {
      api
        .getProblem(slugOrId)
        .then((data) => {
          setProblem(data);
          setCode(data.starter_code);
          if (data.sample_test_cases.length > 0) {
            setCustomInput(data.sample_test_cases[0].input_data);
          }
        })
        .catch((err) => {
          setErrorBanner(err.message || "Failed to load problem.");
        });
    }
  }, [slugOrId]);

  useEffect(() => {
    if (token && problem) {
      api
        .getSubmissions(token, problem.id)
        .then((list) => setSubmissionsList(list))
        .catch(() => {});
    }
  }, [token, problem, submissionResult]);

  const handleRunCode = async () => {
    if (!token) {
      router.push("/login");
      return;
    }
    if (!problem) return;

    setErrorBanner(null);
    setIsRunning(true);
    setActiveBottomTab("console");

    try {
      const payload: { code: string; problem_id?: string; custom_input?: string } = {
        code,
        problem_id: problem.id,
      };

      if (activeBottomTab === "custom" && customInput) {
        payload.custom_input = customInput;
      }

      const result = await api.runCode(payload, token);
      setRunResult(result);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? (err as { message: string }).message
          : "Execution failed.";
      setErrorBanner(msg);
    } finally {
      setIsRunning(false);
    }
  };

  const handleResetCode = () => {
    if (problem) {
      setCode(problem.starter_code);
      setErrorBanner(null);
    }
  };

  const handleSubmitSolution = async () => {
    if (!token) {
      router.push("/login");
      return;
    }
    if (!problem) return;

    setErrorBanner(null);
    setIsSubmitting(true);
    setActiveBottomTab("console");

    try {
      const result = await api.submitCode(
        {
          problem_id: problem.id,
          code,
          language: "python",
        },
        token
      );
      setSubmissionResult(result);
      // Also update history tab
      setActiveLeftTab("history");
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? (err as { message: string }).message
          : "Submission failed.";
      setErrorBanner(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const verdictBadge = (verdict?: SubmissionVerdict) => {
    switch (verdict) {
      case "ACCEPTED":
        return "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
      case "WRONG_ANSWER":
        return "bg-rose-500/10 border-rose-500/30 text-rose-400";
      case "TIME_LIMIT_EXCEEDED":
        return "bg-amber-500/10 border-amber-500/30 text-amber-400";
      case "RUNTIME_ERROR":
      case "COMPILATION_ERROR":
        return "bg-purple-500/10 border-purple-500/30 text-purple-400";
      default:
        return "bg-blue-500/10 border-blue-500/30 text-blue-400";
    }
  };

  if (!problem) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="h-8 w-8 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
        <p className="text-xs text-slate-400">Loading problem environment...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-6.5rem)] min-h-[650px] space-y-3">
      {/* Top Action Bar */}
      <div className="h-12 bg-slate-900/70 border border-slate-800 rounded-xl px-4 flex items-center justify-between backdrop-blur-xl shrink-0">
        <div className="flex items-center gap-3">
          <Link
            href="/problems"
            className="text-xs text-slate-400 hover:text-white transition-colors flex items-center gap-1"
          >
            <span>Problems</span>
            <ChevronRight className="h-3 w-3" />
          </Link>
          <span className="text-xs font-bold text-white tracking-tight">{problem.title}</span>
          <span
            className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${verdictBadge(
              problem.difficulty as unknown as SubmissionVerdict
            )}`}
          >
            {problem.difficulty}
          </span>
          <span className="hidden md:inline-block text-[10px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
            {problem.category}
          </span>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleResetCode}
            title="Reset to starter code"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 text-xs transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>

          <button
            type="button"
            disabled={isRunning || isSubmitting}
            onClick={handleRunCode}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50 transition-all border border-slate-700"
          >
            {isRunning ? (
              <>
                <span className="h-3 w-3 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                <span>Running...</span>
              </>
            ) : (
              <>
                <Play className="h-3 w-3 text-emerald-400 fill-emerald-400" />
                <span>Run Code</span>
              </>
            )}
          </button>

          <button
            type="button"
            disabled={isRunning || isSubmitting}
            onClick={handleSubmitSolution}
            className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm shadow-blue-500/20 disabled:opacity-50 transition-all"
          >
            {isSubmitting ? (
              <>
                <span className="h-3 w-3 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                <span>Grading...</span>
              </>
            ) : (
              <>
                <Send className="h-3 w-3" />
                <span>Submit Solution</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Workspace Split (Left: Problem / Submissions, Right: Editor + Test Panel) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 min-h-0">
        {/* Left Column: Description & Submissions Tabs (5 Cols) */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col overflow-hidden backdrop-blur-xl">
          {/* Left Tabs Header */}
          <div className="h-10 border-b border-slate-800 px-4 flex items-center justify-between shrink-0 bg-slate-950/40">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveLeftTab("description")}
                className={`text-xs font-medium pb-2 pt-2 border-b-2 transition-all flex items-center gap-1.5 ${
                  activeLeftTab === "description"
                    ? "border-blue-500 text-white"
                    : "border-transparent text-slate-400 hover:text-slate-300"
                }`}
              >
                <FileCode2 className="h-3.5 w-3.5" />
                <span>Description</span>
              </button>
              <button
                onClick={() => setActiveLeftTab("history")}
                className={`text-xs font-medium pb-2 pt-2 border-b-2 transition-all flex items-center gap-1.5 ${
                  activeLeftTab === "history"
                    ? "border-blue-500 text-white"
                    : "border-transparent text-slate-400 hover:text-slate-300"
                }`}
              >
                <History className="h-3.5 w-3.5" />
                <span>Submissions ({submissionsList.length})</span>
              </button>
            </div>

            <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
              <Shield className="h-3 w-3 text-emerald-400" />
              <span>Docker Runner</span>
            </div>
          </div>

          {/* Left Tabs Content */}
          <div className="flex-1 overflow-y-auto p-5 text-xs text-slate-300 space-y-4">
            {activeLeftTab === "description" ? (
              <div className="space-y-4">
                <div className="prose prose-invert prose-xs max-w-none space-y-3 leading-relaxed whitespace-pre-line">
                  {problem.description}
                </div>

                <div className="pt-4 border-t border-slate-800 space-y-2 text-[11px] text-slate-400">
                  <div className="flex items-center justify-between">
                    <span>CPU Time Ceiling:</span>
                    <span className="font-mono text-white">{problem.time_limit_ms / 1000}s</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Memory Limit:</span>
                    <span className="font-mono text-white">{problem.memory_limit_mb} MB</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Execution Runtime:</span>
                    <span className="font-mono text-emerald-400">Python 3.12 (Isolated Alpine)</span>
                  </div>
                </div>
              </div>
            ) : (
              /* Submissions History Tab */
              <div className="space-y-3">
                {submissionsList.length === 0 ? (
                  <div className="text-center py-12 text-slate-500">
                    <History className="h-6 w-6 mx-auto mb-2 opacity-40" />
                    <p className="text-xs">No submissions yet for this problem.</p>
                    <p className="text-[10px] text-slate-600 mt-1">Submit your code to see grading records.</p>
                  </div>
                ) : (
                  submissionsList.map((sub) => (
                    <div
                      key={sub.id}
                      className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-center justify-between text-xs"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded border ${verdictBadge(
                              sub.verdict
                            )}`}
                          >
                            {sub.verdict}
                          </span>
                          <span className="text-slate-400 text-[11px]">
                            {sub.test_cases_passed} / {sub.total_test_cases} passed
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 mt-1">
                          {new Date(sub.created_at).toLocaleTimeString()} • {sub.runtime_ms ?? 0}ms
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Code Editor & Execution Panel (7 Cols) */}
        <div className="lg:col-span-7 flex flex-col gap-3 min-h-0">
          {/* Top Half: Monaco Code Editor */}
          <div className="flex-1 bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden flex flex-col min-h-[300px] backdrop-blur-xl">
            <div className="h-8 border-b border-slate-800 px-4 flex items-center justify-between bg-slate-950/60 shrink-0 text-xs">
              <span className="font-mono text-slate-400 flex items-center gap-1.5 text-[11px]">
                <span className="h-2 w-2 rounded-full bg-blue-400" />
                solution.py (Python 3.12)
              </span>
              <span className="text-[10px] text-slate-500 font-mono">UTF-8 • Tab: 4 spaces</span>
            </div>

            <div className="flex-1 w-full h-full relative">
              <Editor
                height="100%"
                language="python"
                theme="vs-dark"
                value={code}
                onChange={(newVal) => setCode(newVal || "")}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                  wordWrap: "on",
                  automaticLayout: true,
                  padding: { top: 12, bottom: 12 },
                }}
              />
            </div>
          </div>

          {/* Bottom Half: Test Case & Console Results Drawer */}
          <div className="h-56 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col overflow-hidden backdrop-blur-xl shrink-0">
            {/* Drawer Tabs Header */}
            <div className="h-9 border-b border-slate-800 px-4 flex items-center justify-between bg-slate-950/60 shrink-0 text-xs">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setActiveBottomTab("testcases")}
                  className={`font-medium py-1 transition-colors flex items-center gap-1.5 ${
                    activeBottomTab === "testcases" ? "text-blue-400" : "text-slate-400 hover:text-white"
                  }`}
                >
                  <span>Sample Test Cases</span>
                </button>
                <button
                  onClick={() => setActiveBottomTab("console")}
                  className={`font-medium py-1 transition-colors flex items-center gap-1.5 ${
                    activeBottomTab === "console" ? "text-blue-400" : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Terminal className="h-3 w-3" />
                  <span>Execution Output</span>
                </button>
                <button
                  onClick={() => setActiveBottomTab("custom")}
                  className={`font-medium py-1 transition-colors flex items-center gap-1.5 ${
                    activeBottomTab === "custom" ? "text-blue-400" : "text-slate-400 hover:text-white"
                  }`}
                >
                  <span>Custom Input</span>
                </button>
              </div>

              {/* Status info */}
              {runResult && (
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${verdictBadge(
                      runResult.verdict
                    )}`}
                  >
                    {runResult.verdict}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">{runResult.runtime_ms}ms</span>
                </div>
              )}
            </div>

            {/* Drawer Body */}
            <div className="flex-1 overflow-y-auto p-3 text-xs font-mono">
              {activeBottomTab === "testcases" && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    {problem.sample_test_cases.map((tc, idx) => (
                      <button
                        key={tc.id}
                        onClick={() => setSelectedTestCaseIndex(idx)}
                        className={`px-3 py-1 rounded-lg border text-xs font-medium transition-all ${
                          selectedTestCaseIndex === idx
                            ? "bg-blue-600/20 border-blue-500 text-white"
                            : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        Case {idx + 1}
                      </button>
                    ))}
                  </div>

                  {problem.sample_test_cases[selectedTestCaseIndex] && (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <span className="text-[10px] uppercase text-slate-500 block mb-1">Standard Input:</span>
                        <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">
                          {problem.sample_test_cases[selectedTestCaseIndex].input_data}
                        </pre>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase text-slate-500 block mb-1">Expected Output:</span>
                        <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                          {problem.sample_test_cases[selectedTestCaseIndex].expected_output}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeBottomTab === "console" && (
                <div className="space-y-2 h-full flex flex-col justify-between">
                  {errorBanner && (
                    <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-xs">
                      {errorBanner}
                    </div>
                  )}

                  {runResult ? (
                    <div className="space-y-2">
                      {runResult.error_message && (
                        <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-xs">
                          <span className="font-bold block">Error Traceback:</span>
                          <pre className="whitespace-pre-wrap mt-1 text-[11px]">{runResult.error_message}</pre>
                        </div>
                      )}

                      {runResult.stdout && (
                        <div>
                          <span className="text-[10px] uppercase text-slate-500 block mb-1">Program Output:</span>
                          <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-[11px] overflow-x-auto whitespace-pre-wrap">
                            {runResult.stdout}
                          </pre>
                        </div>
                      )}
                    </div>
                  ) : submissionResult ? (
                    <div className="space-y-2">
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                        <div>
                          <span
                            className={`text-[10px] uppercase font-bold px-2.5 py-1 rounded border inline-block ${verdictBadge(
                              submissionResult.verdict
                            )}`}
                          >
                            {submissionResult.verdict}
                          </span>
                          <p className="text-xs text-slate-300 mt-2">
                            Passed {submissionResult.test_cases_passed} of {submissionResult.total_test_cases} test cases
                          </p>
                        </div>
                        <span className="text-xs text-slate-400 font-mono">{submissionResult.runtime_ms} ms</span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-slate-500 text-center py-8">
                      Click <strong>Run Code</strong> or <strong>Submit Solution</strong> to view container outputs.
                    </div>
                  )}
                </div>
              )}

              {activeBottomTab === "custom" && (
                <div className="space-y-2">
                  <span className="text-[10px] uppercase text-slate-500 block">Custom Standard Input:</span>
                  <textarea
                    rows={4}
                    value={customInput}
                    onChange={(e) => setCustomInput(e.target.value)}
                    placeholder="Provide standard input lines for your program..."
                    className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

