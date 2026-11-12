import React from "react";
import Link from "next/link";
import { Terminal, Shield, Sparkles, BookOpen, BarChart3 } from "lucide-react";

export function Navbar() {
  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white">CodeRazz</span>
              <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                Phase 1 MVP
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              Misconception-Aware Programming Tutor
            </p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-1 sm:gap-4 text-sm font-medium text-slate-300">
          <Link
            href="/"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-white hover:bg-slate-900 transition-colors"
          >
            <Sparkles className="h-4 w-4 text-blue-400" />
            <span>Overview</span>
          </Link>
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-slate-500 cursor-not-allowed">
            <BookOpen className="h-4 w-4" />
            <span>Problem Library</span>
          </span>
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-slate-500 cursor-not-allowed">
            <BarChart3 className="h-4 w-4" />
            <span>Teacher Heatmap</span>
          </span>
        </nav>

        {/* Right Badges */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
            <Shield className="h-3.5 w-3.5" />
            <span>₹0 Budget Architecture</span>
          </div>
        </div>
      </div>
    </header>
  );
}

