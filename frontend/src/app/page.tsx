import React from "react";
import Link from "next/link";
import {
  Code2,
  Cpu,
  HelpCircle,
  BarChart,
  Lock,
  Zap,
  Layers,
  ArrowRight,
  UserCheck,
} from "lucide-react";
import { StatusCard } from "@/components/StatusCard";

export default function HomePage() {
  return (
    <div className="space-y-10">
      {/* Hero Section */}
      <div className="relative py-8 md:py-12 text-center max-w-4xl mx-auto space-y-5">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider">
          <Zap className="h-3.5 w-3.5" />
          <span>FOSS Educational AI Infrastructure</span>
        </div>
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-white">
          Don&apos;t just fix the code.{" "}
          <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Understand the thinking behind it.
          </span>
        </h1>
        <p className="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto">
          Unlike traditional online judges that only report Wrong Answer or Runtime Error,
          CodeRazz detects the mental model misconception behind introductory programming mistakes,
          delivers 5 levels of progressive hints, and empowers teachers with diagnostic class heatmaps.
        </p>

        {/* CTA Buttons */}
        <div className="flex items-center justify-center gap-3 pt-2">
          <Link
            href="/login"
            className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 transition-all shadow-lg shadow-blue-500/20 flex items-center gap-2"
          >
            <span>Sign In to Platform</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/register"
            className="px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-300 bg-slate-900 border border-slate-800 hover:border-slate-700 hover:text-white transition-all flex items-center gap-2"
          >
            <UserCheck className="h-4 w-4 text-slate-400" />
            <span>Create Account</span>
          </Link>
        </div>
      </div>

      {/* Real-time Status Verification Card */}
      <div className="max-w-3xl mx-auto">
        <StatusCard />
      </div>

      {/* 4 Pillars of CodeRazz */}
      <div className="pt-6">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-white tracking-tight">
            Core Architectural Subsystems
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Engineered with separation of concerns and ₹0 external tool dependencies.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1: Student Platform */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition-all">
            <div className="h-10 w-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-4">
              <Code2 className="h-5 w-5" />
            </div>
            <h3 className="text-base font-semibold text-white">Student Coding Platform</h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Monaco Editor integration with language syntax highlighting, problem library,
              isolated test execution, and comprehensive execution diagnostics.
            </p>
          </div>

          {/* Card 2: AI Diagnosis Engine */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition-all">
            <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4">
              <Cpu className="h-5 w-5" />
            </div>
            <h3 className="text-base font-semibold text-white">Hybrid Diagnosis Engine</h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Combines Python AST structural visitors, behavioral trace inspection, diagnostic probes,
              and modular Scikit-learn classification across 30 core misconception classes.
            </p>
          </div>

          {/* Card 3: 5-Level Hint Engine */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition-all">
            <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 mb-4">
              <HelpCircle className="h-5 w-5" />
            </div>
            <h3 className="text-base font-semibold text-white">5-Tier Hint Ladder</h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              From Nudge to Conceptual Explanation, Counter-Example, Worked Analogue, and Targeted
              Pointer, with automated SolutionLeakGuard protection.
            </p>
          </div>

          {/* Card 4: Teacher Analytics */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition-all">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4">
              <BarChart className="h-5 w-5" />
            </div>
            <h3 className="text-base font-semibold text-white">Teacher Heatmap</h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Class-level misconception distribution, longitudinal progress trends, student profiles,
              and human-in-the-loop diagnostic review queues.
            </p>
          </div>
        </div>
      </div>

      {/* Security & Zero-Cost Architecture Notice */}
      <div className="mt-8 p-6 rounded-2xl border border-slate-800/80 bg-gradient-to-r from-slate-900/90 via-slate-900/50 to-slate-900/90 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-start gap-4">
          <div className="h-10 w-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
            <Lock className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white">
              Phase 2 Authentication, RBAC & Database Models Active
            </h4>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Argon2id password hashing, JWT bearer tokens, rotating refresh tokens with SHA-256 revocation,
              and 4-tier RBAC (Student, Teacher, Annotator, Admin) are enforced on PostgreSQL 16. Container
              sandboxing and misconception diagnosis will be introduced in subsequent phases.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium text-slate-400 bg-slate-950 px-3 py-2 rounded-xl border border-slate-800 shrink-0">
          <Layers className="h-4 w-4 text-blue-400" />
          <span>Next.js 15 + FastAPI + PostgreSQL 16</span>
        </div>
      </div>
    </div>
  );
}

