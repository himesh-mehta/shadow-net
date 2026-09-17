"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { mockIncidents } from "@/lib/mockData";
import { Incident, ThreatLevel, PredictionType } from "@/types";
import { ShieldAlert, Filter, Search, ArrowUpRight } from "lucide-react";

export default function IncidentsListPage() {
  const [incidents] = useState<Incident[]>(mockIncidents);
  const [threatFilter, setThreatFilter] = useState<string>("ALL");
  const [predictionFilter, setPredictionFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredIncidents = incidents.filter((inc) => {
    if (threatFilter !== "ALL" && inc.threat_level !== threatFilter) return false;
    if (predictionFilter !== "ALL" && inc.prediction !== predictionFilter) return false;
    if (
      searchQuery &&
      !inc.incident_id.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !inc.session_id.toLowerCase().includes(searchQuery.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  return (
    <AppShell>
      <div className="space-y-6 font-mono">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-red-500" />
              INCIDENT RESPONSE REPOSITORY
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Comprehensive log of flagged voice anomalies, deepfake detections, and mitigation actions.
            </p>
          </div>

          <div className="text-xs text-slate-400">
            TOTAL LOGGED: <span className="text-cyan-400 font-bold">{incidents.length}</span>
          </div>
        </div>

        {/* Filter Controls Bar */}
        <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row gap-4 justify-between items-center text-xs">
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <div className="flex items-center gap-2 text-slate-400">
              <Filter className="w-4 h-4 text-cyan-400" />
              <span>FILTER:</span>
            </div>

            <select
              value={threatFilter}
              onChange={(e) => setThreatFilter(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 focus:border-cyan-500 focus:outline-none"
            >
              <option value="ALL">All Threat Levels</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
            </select>

            <select
              value={predictionFilter}
              onChange={(e) => setPredictionFilter(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 focus:border-cyan-500 focus:outline-none"
            >
              <option value="ALL">All Predictions</option>
              <option value="DEEPFAKE">DEEPFAKE</option>
              <option value="REAL">REAL</option>
              <option value="UNCERTAIN">UNCERTAIN</option>
            </select>
          </div>

          {/* Search Box */}
          <div className="relative w-full md:w-72">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by ID or Session..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 placeholder-slate-600 focus:border-cyan-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Incidents Table */}
        <div className="bg-[#0b101d] border border-slate-800 rounded-xl overflow-hidden">
          {filteredIncidents.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-500 space-y-2">
              <ShieldAlert className="w-8 h-8 text-slate-600 mx-auto" />
              <p>No incidents match the active filter criteria.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-500 font-semibold text-[11px] bg-slate-950/60">
                    <th className="py-3 px-4">INCIDENT ID</th>
                    <th className="py-3 px-4">TIMESTAMP (UTC)</th>
                    <th className="py-3 px-4">SESSION ID</th>
                    <th className="py-3 px-4">PREDICTION</th>
                    <th className="py-3 px-4">CONFIDENCE</th>
                    <th className="py-3 px-4">THREAT LEVEL</th>
                    <th className="py-3 px-4">ACTION</th>
                    <th className="py-3 px-4">STATUS</th>
                    <th className="py-3 px-4 text-right">DETAILS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-900">
                  {filteredIncidents.map((inc) => (
                    <tr key={inc.incident_id} className="hover:bg-slate-900/40 transition">
                      <td className="py-3 px-4 font-bold text-white">
                        {inc.incident_id}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(inc.timestamp).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-cyan-400">
                        {inc.session_id}
                      </td>
                      <td className="py-3 px-4">
                        <ThreatBadge type={inc.prediction} size="sm" />
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-200">
                        {(inc.confidence * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-4">
                        <ThreatBadge type={inc.threat_level} size="sm" />
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {inc.response_action}
                      </td>
                      <td className="py-3 px-4">
                        <ThreatBadge type={inc.verification_status} size="sm" />
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          href={`/incidents/${inc.incident_id}`}
                          className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 hover:border-cyan-500 text-cyan-300 text-xs inline-flex items-center gap-1 transition"
                        >
                          <span>Inspect</span>
                          <ArrowUpRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
