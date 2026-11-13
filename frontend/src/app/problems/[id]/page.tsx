"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import {
  Play,
  Send,
  RotateCcw,
  Terminal,
  FileCode2,
  History,
  AlertCircle,
  Shield,
  ChevronRight,
  Sparkles,
  BookOpen,
  Lightbulb,
  Lock,
  Unlock,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  api,
  ProblemDetail,
  CodeRunResult,
  SubmissionRecord,
  SubmissionListItem,
  SubmissionVerdict,
  DiagnosisResult,
  HintRecord,
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

const HINT_TIER_META = [
  {
    level: 1,
    name: "Nudge",
    penalty: 0.0,
    penaltyLabel: "Free (0%)",
    teaser: "A directional Socratic question guiding your intuition without giving anything away.",
  },
  {
    level: 2,
    name: "Conceptual Explanation",
    penalty: 0.05,
    penaltyLabel: "+5% penalty",
    teaser: "Clarifies the core language mechanics, boundary rules, and execution invariants at play.",
  },
  {
    level: 3,
    name: "Minimal Counter-Example",
    penalty: 0.10,
    penaltyLabel: "+10% penalty",
    teaser: "Provides a minimal, tangible input boundary where your current logic breaks down.",
  },
  {
    level: 4,
    name: "Worked Analogue",
    penalty: 0.15,
    penaltyLabel: "+15% penalty",
    teaser: "Demonstrates the correct architectural pattern on a completely different, unrelated problem.",
  },
  {
    level: 5,
    name: "Targeted Pointer",
    penalty: 0.25,
    penaltyLabel: "+25% penalty",
    teaser: "Pinpoints the exact code line and construct requiring remediation with tactical advice.",
  },
];

function HintContentRenderer({ content }: { content: string }) {
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className="space-y-2.5 text-xs text-slate-200 leading-relaxed font-sans">
      {parts.map((part, idx) => {
        if (part.startsWith("```")) {
          const lines = part.slice(3, -3).trim().split("\n");
          const lang = lines[0].trim();
          const codeLines = lang === "python" ? lines.slice(1).join("\n") : lines.join("\n");
          return (
            <div
              key={idx}
              className="my-2 rounded-lg bg-slate-950 border border-slate-800 overflow-hidden font-mono text-[11px]"
            >
              <div className="bg-slate-900/80 px-3 py-1 border-b border-slate-800 text-[10px] text-slate-400 flex items-center justify-between">
                <span>{lang || "python"}</span>
                <span className="text-[9px] text-slate-500">Read-only analogue</span>
              </div>
              <pre className="p-3 overflow-x-auto text-emerald-300">
                <code>{codeLines}</code>
              </pre>
            </div>
          );
        }

        const paragraphs = part.split("\n\n").filter(Boolean);
        return paragraphs.map((para, pIdx) => {
          if (para.startsWith("> ")) {
            return (
              <blockquote
                key={`${idx}-${pIdx}`}
                className="border-l-2 border-indigo-500 pl-3 py-1 my-1 italic text-indigo-300 bg-indigo-950/20 rounded-r"
              >
                {para.slice(2)}
              </blockquote>
            );
          }
          if (para.startsWith("### ")) {
            return (
              <h4 key={`${idx}-${pIdx}`} className="font-semibold text-white text-xs mt-2 mb-1">
                {para.slice(4)}
              </h4>
            );
          }
          return (
            <p key={`${idx}-${pIdx}`} className="whitespace-pre-line text-slate-300">
              {para}
            </p>
          );
        });
      })}
    </div>
  );
}

export default function ProblemWorkspacePage() {
  const router = useRouter();
  const routeParams = useParams();
  const slugOrId = routeParams?.id as string;

  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [code, setCode] = useState<string>("");
  const [token, setToken] = useState<string | null>(null);
  const [activeLeftTab, setActiveLeftTab] = useState<"description" | "history" | "hints">("description");
  const [activeBottomTab, setActiveBottomTab] = useState<"testcases" | "console" | "custom">("testcases");
  const [selectedTestCaseIndex, setSelectedTestCaseIndex] = useState<number>(0);
  const [customInput, setCustomInput] = useState<string>("");

  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runResult, setRunResult] = useState<CodeRunResult | null>(null);
  const [submissionResult, setSubmissionResult] = useState<SubmissionRecord | null>(null);
  const [submissionsList, setSubmissionsList] = useState<SubmissionListItem[]>([]);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Progressive Hint Drawer State
  const [unlockedHints, setUnlockedHints] = useState<HintRecord[]>([]);
  const [hintPenalty, setHintPenalty] = useState<number>(0);
  const [isUnlockingHint, setIsUnlockingHint] = useState<boolean>(false);
  const [hintError, setHintError] = useState<string | null>(null);
  const [expandedHintLevel, setExpandedHintLevel] = useState<number | null>(null);

  // Monaco Editor references for line decorations and navigation
  const editorRef = useRef<any>(null);
  const monacoRef = useRef<any>(null);
  const decorationsRef = useRef<string[]>([]);

  // Active diagnosed misconception from either interactive run or submission
  const activeDiagnosis: DiagnosisResult | undefined =
    submissionResult?.diagnosis || runResult?.diagnosis;

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

  // Load existing hints whenever the active submission changes
  useEffect(() => {
    const targetSubId = submissionResult?.id || selectedSubmissionId;
    if (token && targetSubId) {
      api
        .getHints(targetSubId, token)
        .then((res) => {
          setUnlockedHints(res.hints || []);
          setHintPenalty(res.total_penalty || 0);
          if (res.hints && res.hints.length > 0) {
            setExpandedHintLevel(res.max_unlocked_level);
          }
        })
        .catch(() => {
          setUnlockedHints([]);
          setHintPenalty(0);
        });
    } else {
      setUnlockedHints([]);
      setHintPenalty(0);
    }
  }, [token, submissionResult, selectedSubmissionId]);

  // Update Monaco line decorations whenever a new diagnosis is emitted
  useEffect(() => {
    if (!editorRef.current || !monacoRef.current) return;
    const editor = editorRef.current;
    const monaco = monacoRef.current;

    if (activeDiagnosis && activeDiagnosis.evidence_lines && activeDiagnosis.evidence_lines.length > 0) {
      const newDecorations = activeDiagnosis.evidence_lines.map((lineNum) => ({
        range: new monaco.Range(lineNum, 1, lineNum, 1),
        options: {
          isWholeLine: true,
          className: "bg-amber-500/15 border-l-4 border-amber-500",
          glyphMarginClassName: "text-amber-400 font-bold",
          hoverMessage: {
            value: `**[${activeDiagnosis.misconception_code}] ${activeDiagnosis.misconception_name || "Misconception Detected"}**\n\n${activeDiagnosis.explanation || ""}\n\n*Confidence: ${(activeDiagnosis.confidence_score * 100).toFixed(0)}%*`,
          },
        },
      }));
      decorationsRef.current = editor.deltaDecorations(decorationsRef.current, newDecorations);
      editor.revealLineInCenter(activeDiagnosis.evidence_lines[0]);
    } else {
      decorationsRef.current = editor.deltaDecorations(decorationsRef.current, []);
    }
  }, [activeDiagnosis]);

  const handleJumpToLine = (lineNum: number) => {
    if (editorRef.current) {
      editorRef.current.revealLineInCenter(lineNum);
      editorRef.current.setPosition({ lineNumber: lineNum, column: 1 });
      editorRef.current.focus();
    }
  };

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
      setRunResult(null);
      setSubmissionResult(null);
      setSelectedSubmissionId(null);
      setUnlockedHints([]);
      setHintPenalty(0);
      if (editorRef.current) {
        decorationsRef.current = editorRef.current.deltaDecorations(decorationsRef.current, []);
      }
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
      setSelectedSubmissionId(result.id);
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

  const handleUnlockHint = async (desiredLevel?: number) => {
    if (!token) {
      router.push("/login");
      return;
    }

    const targetSubId = submissionResult?.id || selectedSubmissionId;
    if (!targetSubId) {
      setActiveLeftTab("hints");
      setHintError("Submit your code first to generate a diagnostic trace before requesting hints.");
      return;
    }

    setHintError(null);
    setIsUnlockingHint(true);
    setActiveLeftTab("hints");

    try {
      const hint = await api.unlockNextHint(targetSubId, token, desiredLevel);
      setUnlockedHints((prev) => {
        const filtered = prev.filter((h) => h.hint_level !== hint.hint_level);
        return [...filtered, hint].sort((a, b) => a.hint_level - b.hint_level);
      });
      setHintPenalty((prev) => Number((prev + hint.penalty_score).toFixed(2)));
      setExpandedHintLevel(hint.hint_level);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? (err as { message: string }).message
          : "Failed to unlock hint.";
      setHintError(msg);
    } finally {
      setIsUnlockingHint(false);
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

  const maxUnlocked = unlockedHints.length > 0
    ? Math.max(...unlockedHints.map((h) => h.hint_level))
    : 0;

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
            data-testid="run-code-button"
            disabled={isRunning || isSubmitting}
            onClick={handleRunCode}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50 transition-all border border-slate-700 cursor-pointer"
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
            data-testid="submit-solution-button"
            disabled={isRunning || isSubmitting}
            onClick={handleSubmitSolution}
            className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm shadow-blue-500/20 disabled:opacity-50 transition-all cursor-pointer"
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

      {/* Main Workspace Split (Left: Problem / Submissions / Hints, Right: Editor + Test Panel) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 min-h-0">
        {/* Left Column: Description, Submissions & Hints Tabs (5 Cols) */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col overflow-hidden backdrop-blur-xl">
          {/* Left Tabs Header */}
          <div className="h-10 border-b border-slate-800 px-4 flex items-center justify-between shrink-0 bg-slate-950/40">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveLeftTab("description")}
                className={`text-xs font-medium pb-2 pt-2 border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
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
                className={`text-xs font-medium pb-2 pt-2 border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
                  activeLeftTab === "history"
                    ? "border-blue-500 text-white"
                    : "border-transparent text-slate-400 hover:text-slate-300"
                }`}
              >
                <History className="h-3.5 w-3.5" />
                <span>Submissions ({submissionsList.length})</span>
              </button>

              <button
                data-testid="hints-tab-button"
                onClick={() => setActiveLeftTab("hints")}
                className={`text-xs font-medium pb-2 pt-2 border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
                  activeLeftTab === "hints"
                    ? "border-amber-500 text-amber-300"
                    : "border-transparent text-slate-400 hover:text-slate-300"
                }`}
              >
                <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
                <span>Hints</span>
                {unlockedHints.length > 0 && (
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                    {unlockedHints.length}/5
                  </span>
                )}
              </button>
            </div>

            <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
              <Shield className="h-3 w-3 text-emerald-400" />
              <span>Docker Runner</span>
            </div>
          </div>

          {/* Left Tabs Content */}
          <div className="flex-1 overflow-y-auto p-5 text-xs text-slate-300 space-y-4">
            {activeLeftTab === "description" && (
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
            )}

            {activeLeftTab === "history" && (
              <div className="space-y-3">
                {submissionsList.length === 0 ? (
                  <div className="text-center py-12 text-slate-500">
                    <History className="h-6 w-6 mx-auto mb-2 opacity-40" />
                    <p className="text-xs">No submissions yet for this problem.</p>
                    <p className="text-[10px] text-slate-600 mt-1">Submit your code to see grading records.</p>
                  </div>
                ) : (
                  submissionsList.map((sub) => (
                    <button
                      key={sub.id}
                      onClick={() => {
                        setSelectedSubmissionId(sub.id);
                        api
                          .getSubmission(sub.id, token || "")
                          .then((fullSub) => {
                            setSubmissionResult(fullSub);
                            setActiveBottomTab("console");
                          })
                          .catch(() => {});
                      }}
                      className={`w-full text-left p-3 rounded-xl border transition-all cursor-pointer ${
                        selectedSubmissionId === sub.id || submissionResult?.id === sub.id
                          ? "bg-slate-900 border-blue-500/50 shadow-sm shadow-blue-500/10"
                          : "bg-slate-950/70 border-slate-800/80 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded border ${verdictBadge(
                              sub.verdict
                            )}`}
                          >
                            {sub.verdict}
                          </span>
                          <span className="text-slate-300 text-[11px]">
                            {sub.test_cases_passed} / {sub.total_test_cases} passed
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {sub.runtime_ms ?? 0}ms
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 mt-1.5">
                        {new Date(sub.created_at).toLocaleString()}
                      </p>
                    </button>
                  ))
                )}
              </div>
            )}

            {/* Progressive 5-Tier Hint Drawer */}
            {activeLeftTab === "hints" && (
              <div className="space-y-4">
                {/* Header Card */}
                <div className="p-3.5 rounded-xl bg-gradient-to-r from-amber-950/30 via-slate-950 to-indigo-950/30 border border-amber-500/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="p-1.5 rounded-lg bg-amber-500/20 text-amber-400">
                        <Lightbulb className="h-4 w-4" />
                      </span>
                      <div>
                        <h3 className="text-xs font-bold text-white">Progressive 5-Tier Hint Ladder</h3>
                        <p className="text-[10px] text-slate-400">Calibrated Socratic guidance without solution leaks</p>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Penalty</span>
                      <span className="font-mono text-xs font-bold text-amber-300">
                        -{(hintPenalty * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  {/* Progress tracker */}
                  <div className="grid grid-cols-5 gap-1 pt-1">
                    {HINT_TIER_META.map((t) => {
                      const isUnlocked = t.level <= maxUnlocked;
                      return (
                        <div
                          key={t.level}
                          className={`h-1.5 rounded-full transition-all ${
                            isUnlocked ? "bg-amber-400" : "bg-slate-800"
                          }`}
                          title={`Level ${t.level}: ${t.name} (${isUnlocked ? "Unlocked" : "Locked"})`}
                        />
                      );
                    })}
                  </div>
                </div>

                {hintError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                    <span>{hintError}</span>
                  </div>
                )}

                {/* 5-Tier Stack */}
                <div className="space-y-2.5">
                  {HINT_TIER_META.map((tier) => {
                    const unlockedHint = unlockedHints.find((h) => h.hint_level === tier.level);
                    const isUnlocked = Boolean(unlockedHint);
                    const isNextToUnlock = tier.level === maxUnlocked + 1;
                    const isExpanded = expandedHintLevel === tier.level;

                    if (isUnlocked && unlockedHint) {
                      return (
                        <div
                          key={tier.level}
                          data-testid={`hint-tier-${tier.level}`}
                          className="rounded-xl border border-amber-500/40 bg-slate-950/80 overflow-hidden shadow-sm"
                        >
                          <button
                            type="button"
                            onClick={() => setExpandedHintLevel(isExpanded ? null : tier.level)}
                            className="w-full p-3 flex items-center justify-between text-left hover:bg-slate-900/60 transition-colors cursor-pointer"
                          >
                            <div className="flex items-center gap-2.5">
                              <span className="p-1 rounded-md bg-amber-500/20 text-amber-300">
                                <Unlock className="h-3.5 w-3.5" />
                              </span>
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-white text-xs">
                                    Level {tier.level}: {tier.name}
                                  </span>
                                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                                    {tier.penaltyLabel}
                                  </span>
                                </div>
                                <span className="text-[10px] text-slate-400">{unlockedHint.hint_title}</span>
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              <span
                                data-testid="leak-guard-badge"
                                className="hidden sm:inline-flex items-center gap-1 text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20"
                                title="Mathematically verified by SolutionLeakGuard"
                              >
                                <ShieldCheck className="h-3 w-3" />
                                <span>Leak Guard OK</span>
                              </span>
                              {isExpanded ? (
                                <ChevronUp className="h-4 w-4 text-slate-400" />
                              ) : (
                                <ChevronDown className="h-4 w-4 text-slate-400" />
                              )}
                            </div>
                          </button>

                          {isExpanded && (
                            <div className="px-3.5 pb-3.5 pt-1 border-t border-slate-900 space-y-3">
                              <HintContentRenderer content={unlockedHint.hint_content} />

                              {tier.level === 5 && activeDiagnosis?.evidence_lines && (
                                <div className="pt-2 border-t border-slate-900 flex justify-end">
                                  <button
                                    type="button"
                                    onClick={() => handleJumpToLine(activeDiagnosis.evidence_lines![0])}
                                    className="px-2.5 py-1 rounded-lg bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 text-xs font-semibold flex items-center gap-1 border border-amber-500/30 cursor-pointer"
                                  >
                                    <span>Focus faulty construct (Line {activeDiagnosis.evidence_lines[0]})</span>
                                    <ChevronRight className="h-3 w-3" />
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    }

                    if (isNextToUnlock) {
                      return (
                        <div
                          key={tier.level}
                          className="rounded-xl border border-dashed border-indigo-500/50 bg-indigo-950/20 p-3.5 space-y-2.5"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="p-1 rounded-md bg-indigo-500/20 text-indigo-400">
                                <Lock className="h-3.5 w-3.5" />
                              </span>
                              <div>
                                <span className="font-bold text-white text-xs">
                                  Level {tier.level}: {tier.name}
                                </span>
                                <span className="ml-2 text-[9px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                                  {tier.penaltyLabel}
                                </span>
                              </div>
                            </div>
                            <span className="text-[10px] text-indigo-300 font-semibold uppercase tracking-wider">
                              Next Available
                            </span>
                          </div>

                          <p className="text-xs text-slate-400 leading-relaxed font-sans">{tier.teaser}</p>

                          <button
                            type="button"
                            disabled={isUnlockingHint}
                            onClick={() => handleUnlockHint(tier.level)}
                            className="w-full py-2 px-3 rounded-lg bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-sm shadow-indigo-500/20 disabled:opacity-50 transition-all cursor-pointer"
                          >
                            {isUnlockingHint ? (
                              <>
                                <span className="h-3 w-3 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                                <span>Validating with SolutionLeakGuard...</span>
                              </>
                            ) : (
                              <>
                                <Unlock className="h-3.5 w-3.5" />
                                <span>Unlock Level {tier.level} ({tier.penaltyLabel})</span>
                              </>
                            )}
                          </button>
                        </div>
                      );
                    }

                    // Future locked tier
                    return (
                      <div
                        key={tier.level}
                        className="rounded-xl border border-slate-800/60 bg-slate-950/40 p-3 flex items-center justify-between opacity-60"
                      >
                        <div className="flex items-center gap-2.5">
                          <span className="p-1 rounded-md bg-slate-800 text-slate-500">
                            <Lock className="h-3.5 w-3.5" />
                          </span>
                          <div>
                            <span className="font-medium text-slate-400 text-xs">
                              Level {tier.level}: {tier.name}
                            </span>
                            <p className="text-[10px] text-slate-600">
                              Unlock Level {tier.level - 1} first to reveal this hint tier.
                            </p>
                          </div>
                        </div>

                        <span className="text-[9px] font-mono text-slate-600">
                          {tier.penaltyLabel}
                        </span>
                      </div>
                    );
                  })}
                </div>
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
                onMount={(editor, monaco) => {
                  editorRef.current = editor;
                  monacoRef.current = monaco;
                  if (typeof window !== "undefined") {
                    (window as any).__coderazz_editor = editor;
                    (window as any).__coderazz_monaco = monaco;
                    (window as any).__coderazz_set_code = (val: string) => {
                      editor.setValue(val);
                      setCode(val);
                    };
                  }
                }}
                onChange={(newVal) => setCode(newVal || "")}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                  wordWrap: "on",
                  automaticLayout: true,
                  padding: { top: 12, bottom: 12 },
                  glyphMargin: true,
                }}
              />
            </div>
          </div>

          {/* Bottom Half: Test Case & Console Results Drawer */}
          <div className="h-72 min-h-[260px] bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col overflow-hidden backdrop-blur-xl shrink-0">
            {/* Drawer Tabs Header */}
            <div className="h-9 border-b border-slate-800 px-4 flex items-center justify-between bg-slate-950/60 shrink-0 text-xs">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setActiveBottomTab("testcases")}
                  className={`font-medium py-1 transition-colors flex items-center gap-1.5 cursor-pointer ${
                    activeBottomTab === "testcases" ? "text-blue-400" : "text-slate-400 hover:text-white"
                  }`}
                >
                  <span>Sample Test Cases</span>
                </button>
                <button
                  onClick={() => setActiveBottomTab("console")}
                  className={`font-medium py-1 transition-colors flex items-center gap-1.5 cursor-pointer ${
                    activeBottomTab === "console" ? "text-blue-400" : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Terminal className="h-3 w-3" />
                  <span>Execution Output</span>
                </button>
                <button
                  onClick={() => setActiveBottomTab("custom")}
                  className={`font-medium py-1 transition-colors flex items-center gap-1.5 cursor-pointer ${
                    activeBottomTab === "custom" ? "text-blue-400" : "text-slate-400 hover:text-white"
                  }`}
                >
                  <span>Custom Input</span>
                </button>

                {/* Misconception Alert Badge */}
                {activeDiagnosis && (
                  <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[10px] font-mono animate-pulse">
                    <AlertCircle className="h-3 w-3 text-amber-400" />
                    <span>Misconception: {activeDiagnosis.misconception_code}</span>
                  </span>
                )}
              </div>

              {/* Status info */}
              <div className="flex items-center gap-2">
                {runResult && (
                  <>
                    <span
                      className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${verdictBadge(
                        runResult.verdict
                      )}`}
                    >
                      {runResult.verdict}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">{runResult.runtime_ms}ms</span>
                  </>
                )}
                {submissionResult && !runResult && (
                  <>
                    <span
                      className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${verdictBadge(
                        submissionResult.verdict
                      )}`}
                    >
                      {submissionResult.verdict}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">{submissionResult.runtime_ms}ms</span>
                  </>
                )}
              </div>
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
                        className={`px-3 py-1 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
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
                <div className="space-y-3 h-full flex flex-col justify-start">
                  {errorBanner && (
                    <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-xs">
                      {errorBanner}
                    </div>
                  )}

                  {/* High-Visibility Misconception Diagnosis Card */}
                  {activeDiagnosis && (
                    <div
                      data-testid="diagnosis-card"
                      className="p-4 rounded-xl bg-gradient-to-br from-amber-950/40 via-slate-900/90 to-purple-950/30 border border-amber-500/40 shadow-lg shadow-amber-950/20 space-y-3"
                    >
                      {/* Card Header */}
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-500/20 pb-2.5">
                        <div className="flex items-center gap-2.5">
                          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30">
                            <Sparkles className="h-4 w-4" />
                          </span>
                          <div>
                            <div className="flex items-center gap-2">
                              <span
                                data-testid="misconception-badge"
                                className="font-mono text-xs font-bold text-amber-300 bg-amber-500/20 px-2 py-0.5 rounded border border-amber-500/30"
                              >
                                {activeDiagnosis.misconception_code}
                              </span>
                              <span className="text-xs font-semibold text-white">
                                {activeDiagnosis.misconception_name || "Misconception Identified"}
                              </span>
                            </div>
                            <span className="text-[10px] text-slate-400">
                              Category: {activeDiagnosis.misconception_category || "General"}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                            {(activeDiagnosis.confidence_score * 100).toFixed(0)}% Confidence
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300">
                            {activeDiagnosis.detector_type.toUpperCase()}
                          </span>
                        </div>
                      </div>

                      {/* Explanation */}
                      {activeDiagnosis.explanation && (
                        <div className="text-xs text-slate-200 leading-relaxed font-sans bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                          <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider block mb-1">
                            Diagnostic Analysis
                          </span>
                          <p>{activeDiagnosis.explanation}</p>
                        </div>
                      )}

                      {/* Pedagogical Remedy */}
                      {activeDiagnosis.pedagogical_remedy && (
                        <div className="text-xs text-indigo-200 leading-relaxed font-sans bg-indigo-950/30 p-3 rounded-lg border border-indigo-500/30">
                          <span className="text-[10px] font-semibold text-indigo-400 uppercase tracking-wider block mb-1 flex items-center gap-1.5">
                            <BookOpen className="h-3.5 w-3.5 text-indigo-400" />
                            How to Think About This (Pedagogical Guidance)
                          </span>
                          <p className="whitespace-pre-line text-slate-300">
                            {activeDiagnosis.pedagogical_remedy}
                          </p>
                        </div>
                      )}

                      {/* Evidence Lines and Action Bar with Hint Ladder Shortcut */}
                      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-amber-500/10">
                        <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                          {activeDiagnosis.evidence_lines && activeDiagnosis.evidence_lines.length > 0 && (
                            <>
                              <span>Faulty line(s):</span>
                              {activeDiagnosis.evidence_lines.map((ln) => (
                                <button
                                  key={ln}
                                  type="button"
                                  onClick={() => handleJumpToLine(ln)}
                                  className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/30 font-bold transition-colors cursor-pointer"
                                  title="Click to jump to line in editor"
                                >
                                  Line {ln}
                                </button>
                              ))}
                            </>
                          )}
                        </div>

                        {/* Hint Ladder Shortcut Button */}
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            data-testid="unlock-hint-button"
                            onClick={() => {
                              setActiveLeftTab("hints");
                              if (unlockedHints.length === 0) {
                                handleUnlockHint(1);
                              }
                            }}
                            className="px-3 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm shadow-amber-500/10"
                          >
                            <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
                            <span>
                              {unlockedHints.length === 0
                                ? "Unlock Hint Level 1 (Free)"
                                : `View Progressive Hints (${unlockedHints.length}/5)`}
                            </span>
                            <ChevronRight className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
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
