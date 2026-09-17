"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { mockIncidentDetail } from "@/lib/mockData";
import {
  ShieldAlert,
  ArrowLeft,
  Clock,
  KeyRound,
  FileText,
  Activity,
  AlertTriangle,
} from "lucide-react";

export default function IncidentDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [incident] = useState({
    ...mockIncidentDetail,
    incident_id: id || mockIncidentDetail.incident_id,
  });

  return (
    <AppShell>
      <div className="space-y-6 font-mono">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-3">
          <Link
            href="/incidents"
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-cyan-400 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Incidents</span>
          </Link>
          <span className="text-slate-600">/</span>
          <span className="text-xs text-cyan-400 font-bold">{incident.incident_id}</span>
        </div>

        {/* Top Header Card */}
        <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <ThreatBadge type={incident.threat_level} size="lg" />
              <ThreatBadge type={incident.prediction} size="lg" />
              <ThreatBadge type={incident.verification_status} size="sm" />
            </div>
            <h1 className="text-lg font-bold text-white tracking-wide">
              INCIDENT RECORD: <span className="text-cyan-400">{incident.incident_id}</span>
            </h1>
            <p className="text-xs text-slate-400">
              Triggered on {new Date(incident.timestamp).toUTCString()} across session {incident.session_id}
            </p>
          </div>

          {incident.verification_status === "PENDING" && (
            <Link
              href="/verify"
              className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs flex items-center gap-2 transition shadow-lg shadow-amber-950"
            >
              <KeyRound className="w-4 h-4" />
              <span>Initiate Prototype MFA Unlock</span>
            </Link>
          )}
        </div>

        {/* Incident Summary Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-[#0b101d] border border-slate-800 space-y-1">
            <div className="text-[10px] text-slate-500 uppercase">Detection Confidence</div>
            <div className="text-xl font-bold text-red-400">
              {(incident.confidence * 100).toFixed(2)}%
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0b101d] border border-slate-800 space-y-1">
            <div className="text-[10px] text-slate-500 uppercase">Detection Latency</div>
            <div className="text-xl font-bold text-cyan-400">
              {incident.detection_latency} ms
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0b101d] border border-slate-800 space-y-1">
            <div className="text-[10px] text-slate-500 uppercase">Response Action</div>
            <div className="text-sm font-bold text-amber-400 mt-1">
              {incident.response_action}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0b101d] border border-slate-800 space-y-1">
            <div className="text-[10px] text-slate-500 uppercase">Audio Privacy Flag</div>
            <div className="text-sm font-bold text-emerald-400 mt-1">
              store_audio = FALSE
            </div>
          </div>
        </div>

        {/* Chronological Detection Timeline (Window Breakdown) */}
        <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex justify-between items-center pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
                Chronological Detection Timeline (Acoustic Window Progression)
              </span>
            </div>
            <span className="text-[10px] text-slate-500">2.0s WINDOWS / 1.0s HOP</span>
          </div>

          <div className="space-y-3 pt-2">
            {incident.timeline.map((item, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3.5 rounded-lg bg-slate-950/80 border border-slate-800/80 text-xs"
              >
                <div className="flex items-center gap-4">
                  <span className="w-6 h-6 rounded bg-slate-900 border border-slate-700 flex items-center justify-center font-bold text-cyan-400 text-[10px]">
                    #{item.window_index}
                  </span>
                  <div>
                    <div className="text-slate-300 font-semibold">
                      Window Interval: [{item.start_sec}s &rarr; {item.end_sec}s]
                    </div>
                    <div className="text-[10px] text-slate-500">
                      Sample rate 16kHz &bull; 128 Mel frequency bins
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500 uppercase">Synthetic Prob</div>
                    <div className={item.fake_probability >= 0.75 ? "text-red-400 font-bold" : "text-emerald-400 font-semibold"}>
                      {(item.fake_probability * 100).toFixed(1)}%
                    </div>
                  </div>
                  <ThreatBadge type={item.threat_level} size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
