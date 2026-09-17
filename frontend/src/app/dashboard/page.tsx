"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import {
  mockAnalytics,
  mockActiveSession,
  mockIncidents,
} from "@/lib/mockData";
import {
  ShieldAlert,
  AlertTriangle,
  Radio,
  Clock,
  Mic,
  ArrowUpRight,
  TrendingUp,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

export default function DashboardPage() {
  const [analytics] = useState(mockAnalytics);
  const [activeSession] = useState(mockActiveSession);
  const [recentIncidents] = useState(mockIncidents);

  // Recharts timeline mock points
  const chartData = [
    { time: "12:00", fakeScore: 0.12, latency: 21 },
    { time: "13:00", fakeScore: 0.18, latency: 22 },
    { time: "14:00", fakeScore: 0.45, latency: 24 },
    { time: "15:00", fakeScore: 0.25, latency: 19 },
    { time: "16:00", fakeScore: 0.82, latency: 26 },
    { time: "17:00", fakeScore: 0.94, latency: 23 },
  ];

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
              {analytics.total_incidents}
            </div>
            <div className="text-[11px] text-red-400 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              <span>+3 flagged today</span>
            </div>
          </div>

          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>SUSPICIOUS SESSIONS</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-amber-400">
              {analytics.suspicious_sessions}
            </div>
            <div className="text-[11px] text-slate-500">
              {analytics.total_controlled_sessions} total test sessions
            </div>
          </div>

          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>REAL VS DEEPFAKE</span>
              <Radio className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold text-white flex items-center gap-2">
              <span className="text-emerald-400">{analytics.real_vs_deepfake_counts.REAL}</span>
              <span className="text-slate-600">/</span>
              <span className="text-red-400">{analytics.real_vs_deepfake_counts.DEEPFAKE}</span>
            </div>
            <div className="text-[11px] text-slate-400">
              {analytics.real_vs_deepfake_counts.UNCERTAIN} uncertain borderline
            </div>
          </div>

          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span>AVG DETECTION LATENCY</span>
              <Clock className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold text-cyan-400">
              {analytics.average_detection_latency_ms} <span className="text-sm font-normal text-slate-400">ms</span>
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
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-semibold text-slate-200">ACTIVE TEST SESSION</span>
              </div>
              <ThreatBadge type="LOW" size="sm" />
            </div>

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
                DEEPFAKE RISK PROBABILITY TREND (HOURLY)
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
          </div>
        </div>
      </div>
    </AppShell>
  );
}
