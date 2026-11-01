"use client";

import React from "react";
import { Clock, TrendingUp, AlertTriangle, CheckCircle, HelpCircle, Zap } from "lucide-react";
import { formatScore } from "@/lib/scoreFormatting";

export interface TimelineEvent {
  event_id: string;
  session_id: string;
  timestamp: string;
  prediction: "REAL" | "DEEPFAKE" | "UNCERTAIN";
  confidence: number;
  fake_probability: number;
  threat_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  response_action: string;
  detection_latency_ms: number;
  num_windows: number;
  deepfake_window_count: number;
  top_reason?: string;
  mode: string;
}

interface AnalysisTimelineProps {
  events: TimelineEvent[];
  isLoading?: boolean;
}

const PREDICTION_CONFIG = {
  REAL: {
    icon: CheckCircle,
    color: "text-emerald-400",
    bg: "bg-emerald-950/40",
    border: "border-emerald-800/50",
    bar: "bg-emerald-500",
    dot: "bg-emerald-400",
  },
  DEEPFAKE: {
    icon: AlertTriangle,
    color: "text-red-400",
    bg: "bg-red-950/40",
    border: "border-red-800/60",
    bar: "bg-red-500",
    dot: "bg-red-400",
  },
  UNCERTAIN: {
    icon: HelpCircle,
    color: "text-amber-400",
    bg: "bg-amber-950/30",
    border: "border-amber-800/50",
    bar: "bg-amber-500",
    dot: "bg-amber-400",
  },
};

const THREAT_COLORS: Record<string, string> = {
  LOW: "text-emerald-400",
  MEDIUM: "text-amber-400",
  HIGH: "text-orange-400",
  CRITICAL: "text-red-400",
};

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return iso;
  }
}

function ConfidenceBar({ value, prediction }: { value: number; prediction: keyof typeof PREDICTION_CONFIG }) {
  const cfg = PREDICTION_CONFIG[prediction];
  return (
    <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${cfg.bar}`}
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

export function AnalysisTimeline({ events, isLoading }: AnalysisTimelineProps) {
  if (isLoading) {
    return (
      <div className="space-y-2 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-lg bg-slate-900/60 border border-slate-800" />
        ))}
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center text-slate-500 space-y-2">
        <Clock className="w-8 h-8 text-slate-700" />
        <p className="text-sm">No analysis events yet.</p>
        <p className="text-xs">Upload a WAV file or start the microphone feed to see results here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {events.map((ev, idx) => {
        const cfg = PREDICTION_CONFIG[ev.prediction] ?? PREDICTION_CONFIG.UNCERTAIN;
        const Icon = cfg.icon;
        const isFirst = idx === 0;

        return (
          <div
            key={ev.event_id}
            className={`relative rounded-lg border p-3 transition-all ${cfg.bg} ${cfg.border} ${
              isFirst ? "ring-1 ring-slate-600/50" : ""
            }`}
          >
            {/* Timeline connector dot */}
            <div className="flex items-start gap-3">
              <div className="flex flex-col items-center pt-0.5 shrink-0">
                <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${cfg.dot} ${isFirst ? "animate-pulse" : ""}`} />
                {idx < events.length - 1 && (
                  <div className="w-px flex-1 bg-slate-800 mt-1 min-h-[12px]" />
                )}
              </div>

              <div className="flex-1 min-w-0 space-y-2">
                {/* Header row */}
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    <Icon className={`w-3.5 h-3.5 shrink-0 ${cfg.color}`} />
                    <span className={`text-xs font-bold tracking-wide ${cfg.color}`}>
                      {ev.prediction}
                    </span>
                    <span className={`text-[10px] font-semibold uppercase ${THREAT_COLORS[ev.threat_level]}`}>
                      [{ev.threat_level}]
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-slate-500">
                    <span className="flex items-center gap-1">
                      <Zap className="w-3 h-3 text-cyan-600" />
                      {ev.detection_latency_ms.toFixed(1)}ms
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTimestamp(ev.timestamp)}
                    </span>
                  </div>
                </div>

                {/* Confidence bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>Confidence</span>
                    <span className="font-mono text-slate-300">{(ev.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <ConfidenceBar value={ev.confidence} prediction={ev.prediction} />
                </div>

                {/* Stats row */}
                <div className="flex gap-4 text-[10px] text-slate-500">
                  <span>
                    AI score:{" "}
                    <span className="text-slate-300 font-mono">{formatScore(ev.fake_probability)}</span>
                  </span>
                  <span>
                    windows:{" "}
                    <span className="text-slate-300 font-mono">
                      {ev.deepfake_window_count}/{ev.num_windows}
                    </span>{" "}
                    <span className="text-slate-600">deepfake</span>
                  </span>
                  <span className={`uppercase font-mono ${ev.mode === "ml" ? "text-emerald-500" : "text-amber-600"}`}>
                    [{ev.mode}]
                  </span>
                </div>

                {/* Top reason */}
                {ev.top_reason && ev.prediction !== "REAL" && (
                  <p className="text-[10px] text-slate-400 leading-relaxed border-t border-slate-800/60 pt-1.5 line-clamp-2">
                    ⚑ {ev.top_reason}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
