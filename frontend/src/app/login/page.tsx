"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Lock, Mail, ArrowRight, AlertCircle, ShieldCheck, CheckCircle2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { authStorage } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsLoading(true);

    try {
      const response = await api.login({ email, password });
      authStorage.setAuth(response.access_token, response.refresh_token, response.user);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("An unexpected network error occurred. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleFillDemo = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setErrorMsg(null);
  };

  return (
    <div className="max-w-md mx-auto pt-8 pb-16">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center h-12 w-12 rounded-2xl bg-blue-600/10 border border-blue-500/20 text-blue-400 mb-4 shadow-lg shadow-blue-500/10">
          <Lock className="h-6 w-6" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Welcome back</h1>
        <p className="text-sm text-slate-400 mt-1">
          Sign in to access your CodeRazz learning workspace
        </p>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 sm:p-8 backdrop-blur-xl shadow-xl shadow-black/40">
        {errorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3 text-red-300 text-sm">
            <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold block">Authentication Error</span>
              <span>{errorMsg}</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Mail className="h-4 w-4" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@example.edu"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-2">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Lock className="h-4 w-4" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 py-3 px-4 rounded-xl font-medium text-sm text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                Signing in...
              </span>
            ) : (
              <>
                <span>Sign in</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>

        {/* Demo Quick-Fill */}
        <div className="mt-6 pt-6 border-t border-slate-800/80">
          <p className="text-xs text-slate-400 font-medium mb-3 flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-blue-400" />
            Quick Test Accounts:
          </p>
          <div className="flex flex-col gap-2">
            <button
              type="button"
              onClick={() => handleFillDemo("admin@coderazz.edu", "AdminInitial#2026")}
              className="text-left text-xs px-3 py-2 rounded-lg bg-slate-950/50 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition-colors flex items-center justify-between"
            >
              <span>
                <strong className="text-purple-400">Admin:</strong> admin@coderazz.edu
              </span>
              <span className="text-[10px] text-slate-500">Seed Account</span>
            </button>
          </div>
        </div>
      </div>

      <p className="text-center text-xs text-slate-400 mt-6">
        Don&apos;t have an account yet?{" "}
        <Link href="/register" className="text-blue-400 hover:underline font-medium">
          Create student or teacher account
        </Link>
      </p>
    </div>
  );
}
