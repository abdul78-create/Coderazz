"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Terminal,
  Shield,
  Sparkles,
  LayoutDashboard,
  LogIn,
  UserPlus,
  LogOut,
  User,
  BarChart3,
} from "lucide-react";
import { authStorage } from "@/lib/auth";
import { UserProfile } from "@/lib/api";

export function Navbar() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    setUser(authStorage.getUser());
    const unsubscribe = authStorage.subscribe(() => {
      setUser(authStorage.getUser());
    });
    return unsubscribe;
  }, []);

  const handleLogout = () => {
    authStorage.clearAuth();
    setUser(null);
    router.push("/login");
  };

  const roleColor = (role?: string) => {
    switch (role) {
      case "ADMIN":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      case "TEACHER":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "ANNOTATOR":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      default:
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
    }
  };

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 group-hover:scale-105 transition-transform">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white">CodeRazz</span>
              <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                Phase 2 Auth
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              Misconception-Aware Programming Tutor
            </p>
          </div>
        </Link>

        {/* Navigation */}
        <nav className="flex items-center gap-1 sm:gap-3 text-sm font-medium text-slate-300">
          <Link
            href="/"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-900 transition-colors"
          >
            <Sparkles className="h-4 w-4 text-blue-400" />
            <span>Overview</span>
          </Link>

          <Link
            href="/problems"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-900 transition-colors"
          >
            <Terminal className="h-4 w-4 text-emerald-400" />
            <span>Problem Library</span>
          </Link>

          {user && (
            <Link
              href="/dashboard"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-900 transition-colors"
            >
              <LayoutDashboard className="h-4 w-4 text-indigo-400" />
              <span>Dashboard</span>
            </Link>
          )}

          {user && (user.role === "TEACHER" || user.role === "ADMIN") && (
            <Link
              href="/teacher/dashboard"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-amber-300 hover:text-white hover:bg-amber-500/10 transition-colors border border-amber-500/20"
            >
              <BarChart3 className="h-4 w-4 text-amber-400" />
              <span>Teacher Analytics</span>
            </Link>
          )}
        </nav>

        {/* Right Action / Auth Area */}
        <div className="flex items-center gap-3">
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
            <Shield className="h-3.5 w-3.5" />
            <span>₹0 FOSS</span>
          </div>

          {user ? (
            <div className="flex items-center gap-2">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-colors"
              >
                <div className="h-6 w-6 rounded-lg bg-blue-600/20 text-blue-400 flex items-center justify-center">
                  <User className="h-3.5 w-3.5" />
                </div>
                <div className="text-left hidden sm:block">
                  <div className="text-xs font-medium text-white leading-tight">
                    {user.full_name.split(" ")[0]}
                  </div>
                  <div
                    className={`text-[9px] uppercase font-semibold px-1 rounded border inline-block ${roleColor(
                      user.role
                    )}`}
                  >
                    {user.role}
                  </div>
                </div>
              </Link>
              <button
                onClick={handleLogout}
                title="Sign Out"
                className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-900 transition-colors"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login"
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-900 transition-colors"
              >
                <LogIn className="h-3.5 w-3.5" />
                <span>Sign In</span>
              </Link>
              <Link
                href="/register"
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-medium text-white bg-blue-600 hover:bg-blue-500 transition-colors shadow-sm shadow-blue-500/20"
              >
                <UserPlus className="h-3.5 w-3.5" />
                <span>Register</span>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
