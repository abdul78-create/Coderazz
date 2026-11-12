"use client";

import React, { useState, useEffect } from "react";
import { CheckCircle2, AlertCircle, RefreshCw, Database, Server, Clock } from "lucide-react";
import { api, HealthResponse, PingResponse } from "@/lib/api";

export function StatusCard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [ping, setPing] = useState<PingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastCheck, setLastCheck] = useState<string>("");

  const checkStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, pingData] = await Promise.all([
        api.getHealth(),
        api.ping(),
      ]);
      setHealth(healthData);
      setPing(pingData);
      setLastCheck(new Date().toLocaleTimeString());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md shadow-xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <Server className="h-4 w-4 text-blue-400" />
            System Connectivity Status
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time health check verification (FastAPI + Database)
          </p>
        </div>
        <button
          onClick={checkStatus}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Backend Status */}
        <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-950/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Backend API</span>
            {loading ? (
              <span className="text-xs text-slate-400">Checking...</span>
            ) : health ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                200 OK
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-400">
                <AlertCircle className="h-3.5 w-3.5" />
                Offline
              </span>
            )}
          </div>
          <div className="mt-2 text-sm font-semibold text-white">
            {health ? `${health.app} v${health.version}` : "FastAPI Backend"}
          </div>
          <div className="mt-1 text-xs text-slate-500 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {ping ? `Ping: ${ping.message} at ${new Date(ping.timestamp).toLocaleTimeString()}` : "Not reached"}
          </div>
        </div>

        {/* Database Status */}
        <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-950/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Database Engine</span>
            {loading ? (
              <span className="text-xs text-slate-400">Checking...</span>
            ) : health?.database.status === "connected" ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-400">
                <AlertCircle className="h-3.5 w-3.5" />
                Offline / Degraded
              </span>
            )}
          </div>
          <div className="mt-2 text-sm font-semibold text-white flex items-center gap-2">
            <Database className="h-4 w-4 text-indigo-400" />
            {health?.database.dialect ? (
              <span className="capitalize">{health.database.dialect}</span>
            ) : (
              "PostgreSQL 16"
            )}
            {health?.database.fallback_active && (
              <span className="text-[10px] font-normal px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                SQLite Dev Fallback
              </span>
            )}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {health?.database.notice ||
              (health?.database.target
                ? `Target: ${health.database.target}`
                : "PostgreSQL 16 via Docker")}
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3 rounded-lg border border-amber-500/20 bg-amber-500/10 text-xs text-amber-300 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Backend Unreachable on port 8000</p>
            <p className="text-slate-400 mt-0.5">
              Start the backend with: <code className="text-slate-200">.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000</code>
            </p>
          </div>
        </div>
      )}

      {lastCheck && !error && (
        <p className="mt-3 text-[11px] text-right text-slate-500">
          Last verified: {lastCheck}
        </p>
      )}
    </div>
  );
}

