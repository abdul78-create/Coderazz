"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Code2,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  ArrowRight,
  Terminal,
  Shield,
  Layers,
  Sparkles,
} from "lucide-react";
import { api, ProblemListItem, ProblemDifficulty } from "@/lib/api";

export default function ProblemsPage() {
  const [problems, setProblems] = useState<ProblemListItem[]>([]);
  const [filteredProblems, setFilteredProblems] = useState<ProblemListItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    api
      .getProblems()
      .then((data) => {
        setProblems(data);
        setFilteredProblems(data);
      })
      .catch((err) => {
        setErrorMsg(err.message || "Failed to load problem library.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    let result = problems;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.category.toLowerCase().includes(q) ||
          p.slug.toLowerCase().includes(q)
      );
    }

    if (selectedDifficulty !== "ALL") {
      result = result.filter((p) => p.difficulty === selectedDifficulty);
    }

    if (selectedCategory !== "ALL") {
      result = result.filter((p) => p.category === selectedCategory);
    }

    setFilteredProblems(result);
  }, [searchQuery, selectedDifficulty, selectedCategory, problems]);

  const categories = ["ALL", ...Array.from(new Set(problems.map((p) => p.category)))];

  const difficultyBadge = (diff: ProblemDifficulty) => {
    switch (diff) {
      case "EASY":
        return "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
      case "MEDIUM":
        return "bg-amber-500/10 border-amber-500/30 text-amber-400";
      case "HARD":
        return "bg-rose-500/10 border-rose-500/30 text-rose-400";
      default:
        return "bg-blue-500/10 border-blue-500/30 text-blue-400";
    }
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header Banner */}
      <div className="relative p-6 sm:p-8 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-xl overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/5 rounded-full blur-3xl -z-10" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-3">
              <Code2 className="h-3.5 w-3.5" />
              <span>Phase 3 Interactive Workspace</span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white">Problem Library</h1>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Select a programming challenge to write Python code in the Monaco Editor and execute it
              inside our isolated, non-root Docker execution sandbox.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <div className="px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 flex items-center gap-2">
              <Shield className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>Docker Sandboxing Active</span>
            </div>
            <div className="px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 flex items-center gap-2">
              <Layers className="h-4 w-4 text-blue-400 shrink-0" />
              <span>{problems.length} Challenges Available</span>
            </div>
          </div>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
            <Search className="h-4 w-4" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search problems by title, topic, or keyword..."
            className="w-full pl-10 pr-4 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-all"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800 text-xs">
            {["ALL", "EASY", "MEDIUM", "HARD"].map((diff) => (
              <button
                key={diff}
                onClick={() => setSelectedDifficulty(diff)}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${
                  selectedDifficulty === diff
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {diff === "ALL" ? "All Difficulties" : diff.charAt(0) + diff.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs flex items-center gap-2">
          <span>Failed to connect to backend: {errorMsg}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 animate-pulse h-48 flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="h-4 bg-slate-800 rounded w-1/3" />
                <div className="h-6 bg-slate-800 rounded w-3/4" />
                <div className="h-3 bg-slate-800 rounded w-full" />
              </div>
              <div className="h-8 bg-slate-800 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : filteredProblems.length === 0 ? (
        <div className="text-center py-16 bg-slate-900/30 rounded-2xl border border-slate-800/80">
          <Terminal className="h-8 w-8 text-slate-500 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No challenges match your query</h3>
          <p className="text-xs text-slate-400 mt-1">Try clearing filters or search terms.</p>
        </div>
      ) : (
        /* Problem Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProblems.map((prob) => (
            <Link
              key={prob.id}
              href={`/problems/${prob.slug}`}
              className="group p-6 rounded-2xl bg-slate-900/60 border border-slate-800/90 hover:border-blue-500/50 hover:bg-slate-900/90 transition-all flex flex-col justify-between relative overflow-hidden shadow-lg shadow-black/20"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                    {prob.category}
                  </span>
                  <span
                    className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${difficultyBadge(
                      prob.difficulty
                    )}`}
                  >
                    {prob.difficulty}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors">
                  {prob.title}
                </h3>

                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  Solve with Python 3.12. Includes {prob.sample_cases_count} visible test cases and{" "}
                  {prob.total_cases_count - prob.sample_cases_count} evaluation cases.
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-slate-500 flex items-center gap-1 font-mono text-[11px]">
                  <Clock className="h-3.5 w-3.5" />
                  3.0s Timeout
                </span>

                <div className="flex items-center gap-1.5 font-medium text-blue-400 group-hover:translate-x-0.5 transition-transform">
                  <span>Solve Challenge</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

