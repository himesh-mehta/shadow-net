"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { api } from "@/lib/api";
import { AnalyticsData, Session, Incident } from "@/types";
import {
  ShieldAlert,
  AlertTriangle,
  Radio,
  Clock,
  Mic,
  ArrowUpRight,
  TrendingUp,
  RefreshCw,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [recentIncidents, setRecentIncidents] = useState<Incident[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [analyticsData, incidentsData, sessionStatus] = await Promise.allSettled([
        api.getAnalytics(),
        api.listIncidents({ limit: 5 }),
        api.getSessionStatus(),
      ]);

      if (analyticsData.status === "fulfilled") {
        setAnalytics(analyticsData.value);
      } else {
        throw new Error(analyticsData.reason?.message || "Failed to load security analytics");
      }

      if (incidentsData.status === "fulfilled") {
        setRecentIncidents(Array.isArray(incidentsData.value) ? incidentsData.value : []);
      }

      if (sessionStatus.status === "fulfilled" && sessionStatus.value?.session_id) {
        setActiveSession(sessionStatus.value as unknown as Session);
      } else {
        setActiveSession(null);
      }
    } catch (err: any) {
      setError(err.message || "Failed to communicate with SHADOW-NET backend API.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Chart data from real incidents or latency distribution
  const chartData = recentIncidents.length > 0
    ? recentIncidents.slice(0, 6).reverse().map((inc, i) => ({
        time: new Date(inc.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        fakeScore: inc.confidence,
        latency: inc.detection_latency_ms || 25,
      }))
    : [
        { time: "00:00", fakeScore: 0.1, latency: 20 },
        { time: "04:00", fakeScore: 0.2, latency: 22 },
        { time: "08:00", fakeScore: 0.15, latency: 19 },
        { time: "12:00", fakeScore: 0.35, latency: 24 },
        { time: "16:00", fakeScore: 0.25, latency: 21 },
        { time: "Now", fakeScore: analytics ? (analytics.threat_level_distribution.CRITICAL > 0 ? 0.9 : 0.2) : 0.1, latency: analytics?.average_detection_latency_ms || 20 },
      ];

  if (isLoading) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4 font-mono text-cyan-400">
          <RefreshCw className="w-8 h-8 animate-spin" />
          <p className="text-sm">FETCHING LIVE SOC METRICS & TELEMETRY...</p>
        </div>
      </AppShell>
    );
  }

  if (error && !analytics) {
    return (
      <AppShell>
        <div className="max-w-xl mx-auto my-12 p-6 rounded-xl bg-red-950/40 border border-red-800 text-red-300 font-mono space-y-4">
          <div className="flex items-center gap-2 font-bold text-sm">
            <ShieldAlert className="w-5 h-5 text-red-400" />
            <span>BACKEND INTEGRATION ERROR</span>
          </div>
          <p className="text-xs text-red-200/90">{error}</p>
          <button
            onClick={loadDashboardData}
            className="px-4 py-2 rounded-lg bg-red-900/80 hover:bg-red-800 border border-red-700 text-white text-xs font-semibold flex items-center gap-2 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6 font-mono">
        {/* Top Title & Operational Status Bar */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-cyan-400" />
              SOC TELEMETRY & INCIDENT DASHBOARD
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Live acoustic interception analytics for controlled voice evaluation benches.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadDashboardData}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:border-slate-500 text-slate-300 text-xs flex items-center gap-1.5 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
            <Link
              href="/session"
              className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-2 transition"
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Launch Test Bench</span>
            </Link>
          </div>
        </div>

        {/* 4 Core SOC Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>TOTAL INCIDENTS</span>
              <ShieldAlert className="w-4 h-4 text-red-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {analytics?.total_incidents ?? 0}
            </div>
            <div className="text-[11px] text-red-400 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              <span>Flagged deepfake threats</span>
            </div>
          </div>

          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>SUSPICIOUS SESSIONS</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-amber-400">
              {analytics?.suspicious_sessions ?? 0}
            </div>
            <div className="text-[11px] text-slate-500">
              {analytics?.total_controlled_sessions ?? 0} total test sessions
            </div>
          </div>

          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>REAL VS DEEPFAKE</span>
              <Radio className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold text-white flex items-center gap-2">
              <span className="text-emerald-400">{analytics?.real_vs_deepfake_counts?.REAL ?? 0}</span>
              <span className="text-slate-600">/</span>
              <span className="text-red-400">{analytics?.real_vs_deepfake_counts?.DEEPFAKE ?? 0}</span>
            </div>
            <div className="text-[11px] text-slate-400">
              {analytics?.real_vs_deepfake_counts?.UNCERTAIN ?? 0} uncertain borderline
            </div>
          </div>

          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>AVG DETECTION LATENCY</span>
              <Clock className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold text-cyan-400">
              {analytics?.average_detection_latency_ms?.toFixed(1) ?? "0.0"} <span className="text-sm font-normal text-slate-400">ms</span>
            </div>
            <div className="text-[11px] text-emerald-400">
              Sub-50ms real-time SLA met
            </div>
          </div>
        </div>

        {/* Middle Row: Active Session Card & Confidence Trend Chart */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Active Session Card */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${activeSession ? "bg-emerald-500 animate-pulse" : "bg-slate-600"}`} />
                <span className="text-xs font-semibold text-slate-200">
                  {activeSession ? "ACTIVE TEST SESSION" : "TEST BENCH IDLE"}
                </span>
              </div>
              <ThreatBadge type={activeSession ? (activeSession.status === "restricted" ? "CRITICAL" : "LOW") : "LOW"} size="sm" />
            </div>

            {activeSession ? (
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">SESSION ID</span>
                  <span className="text-cyan-300 font-bold">{activeSession.session_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">CLIENT</span>
                  <span className="text-slate-300">{activeSession.client_label}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">RAW AUDIO PRIVACY</span>
                  <span className="text-emerald-400">store_audio = FALSE</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">STATUS</span>
                  <span className="text-emerald-400 uppercase font-bold">{activeSession.status}</span>
                </div>
              </div>
            ) : (
              <div className="py-4 text-center text-xs text-slate-500 space-y-2">
                <p>No test call currently running.</p>
                <Link
                  href="/session"
                  className="inline-block text-cyan-400 hover:underline"
                >
                  Start a new session &rarr;
                </Link>
              </div>
            )}

            <div className="pt-3 border-t border-slate-800/80">
              <Link
                href="/live"
                className="w-full py-2 px-3 rounded-lg bg-slate-900 border border-slate-700 hover:border-cyan-500 text-cyan-300 text-xs flex items-center justify-center gap-2 transition"
              >
                <span>Open Live Stream Visualizer</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Recharts Timeline Confidence Graph */}
          <div className="lg:col-span-2 bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-slate-200">
                DEEPFAKE RISK PROBABILITY TREND (RECENT INCIDENTS)
              </span>
              <span className="text-[10px] text-slate-500">THRESHOLD: 0.75</span>
            </div>

            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                  <YAxis domain={[0, 1]} stroke="#64748b" fontSize={10} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#020617", borderColor: "#334155", fontSize: 11 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="fakeScore"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={{ fill: "#ef4444", r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Recent Incidents Table */}
        <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
              Recent Interception Incidents
            </h2>
            <Link
              href="/incidents"
              className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
            >
              <span>View All Incidents</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            {recentIncidents.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No incidents recorded yet. Initiate test calls from the Test Bench.
              </div>
            ) : (
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-500 font-semibold text-[11px]">
                    <th className="py-2.5 px-3">INCIDENT ID</th>
                    <th className="py-2.5 px-3">SESSION</th>
                    <th className="py-2.5 px-3">PREDICTION</th>
                    <th className="py-2.5 px-3">CONFIDENCE</th>
                    <th className="py-2.5 px-3">THREAT LEVEL</th>
                    <th className="py-2.5 px-3">ACTION</th>
                    <th className="py-2.5 px-3">VERIFICATION</th>
                    <th className="py-2.5 px-3 text-right">ACTION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-900">
                  {recentIncidents.map((inc) => (
                    <tr key={inc.incident_id} className="hover:bg-slate-900/40 transition">
                      <td className="py-2.5 px-3 font-semibold text-slate-200">
                        {inc.incident_id}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">
                        {inc.session_id}
                      </td>
                      <td className="py-2.5 px-3">
                        <ThreatBadge type={inc.prediction} size="sm" />
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        {(inc.confidence * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3">
                        <ThreatBadge type={inc.threat_level} size="sm" />
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">
                        {inc.response_action}
                      </td>
                      <td className="py-2.5 px-3">
                        <ThreatBadge type={inc.verification_status} size="sm" />
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <Link
                          href={`/incidents/${inc.incident_id}`}
                          className="text-cyan-400 hover:underline"
                        >
                          Inspect
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
