"use client";

import React, { useState } from "react";
import type { PredictionType } from "@/types";

export interface AudioSegment {
  window_index: number;
  start_sec: number;
  end_sec: number;
  fake_probability: number;
  ai_probability?: number;
  real_probability?: number;
  prediction: PredictionType;
  threat_level: string;
  confidence: number;
  speaker_id?: string;
  is_sustained_threat?: boolean;
  is_padded?: boolean;
}

interface SegmentTimelineProps {
  segments: AudioSegment[];
  totalDuration: number;       // seconds
  isStreaming?: boolean;        // show pulsing progress indicator
  className?: string;
}

const SEGMENT_COLORS: Record<PredictionType, { bg: string; border: string; label: string; dot: string }> = {
  REAL:         { bg: "bg-emerald-500/80",  border: "border-emerald-400", label: "text-emerald-300", dot: "bg-emerald-400" },
  DEEPFAKE:     { bg: "bg-red-500/80",      border: "border-red-400",     label: "text-red-300",     dot: "bg-red-400"     },
  AI_SUSPECTED: { bg: "bg-amber-500/80",    border: "border-amber-400",   label: "text-amber-300",   dot: "bg-amber-400"   },
  UNCERTAIN:    { bg: "bg-yellow-500/70",   border: "border-yellow-400",  label: "text-yellow-300",  dot: "bg-yellow-400"  },
};

function fmt(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = (sec % 60).toFixed(1).padStart(4, "0");
  return m > 0 ? `${m}:${s}` : `${s}s`;
}

function Tooltip({ segment }: { segment: AudioSegment }) {
  const cfg = SEGMENT_COLORS[segment.prediction] || SEGMENT_COLORS.UNCERTAIN;
  return (
    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 pointer-events-none
                    bg-slate-900 border border-slate-700 rounded-lg p-2.5 shadow-xl w-48
                    text-[10px] font-mono space-y-1">
      <div className="flex items-center justify-between">
        <div className={`font-bold uppercase text-xs ${cfg.label}`}>
          {segment.prediction === "AI_SUSPECTED" ? "AI SUSPECTED" : segment.prediction}
        </div>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
          {segment.speaker_id || "Speaker 1"}
        </span>
      </div>
      <div className="flex justify-between text-slate-400">
        <span>AI score</span>
        <span className="text-slate-200">{(segment.fake_probability * 100).toFixed(1)}%</span>
      </div>
      <div className="flex justify-between text-slate-400">
        <span>Confidence</span>
        <span className="text-slate-200">{(segment.confidence * 100).toFixed(1)}%</span>
      </div>
      <div className="flex justify-between text-slate-400">
        <span>Window Range</span>
        <span className="text-slate-200">{fmt(segment.start_sec)} – {fmt(segment.end_sec)}</span>
      </div>
      {segment.is_sustained_threat && (
        <div className="text-[9px] font-bold text-amber-400 bg-amber-950/70 border border-amber-800 rounded px-1.5 py-0.5 mt-0.5">
          SUSTAINED AI DETECTION CLUSTER
        </div>
      )}
      {segment.is_padded && (
        <div className="text-amber-600 italic">padded window</div>
      )}
      {/* Confidence bar */}
      <div className="w-full bg-slate-800 rounded-full h-1 overflow-hidden mt-1">
        <div
          className={`h-full rounded-full ${cfg.bg}`}
          style={{ width: `${segment.confidence * 100}%` }}
        />
      </div>
    </div>
  );
}

function SegmentBlock({ segment, widthPct }: { segment: AudioSegment; widthPct: number }) {
  const [hovered, setHovered] = useState(false);
  const cfg = SEGMENT_COLORS[segment.prediction];

  return (
    <div
      className="relative h-full cursor-pointer group"
      style={{ width: `${widthPct}%`, minWidth: "4px" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Segment bar */}
      <div
        className={`h-full rounded-sm border-r ${cfg.bg} ${cfg.border}
                    transition-all duration-150
                    ${hovered ? "brightness-125 scale-y-110 shadow-lg" : "brightness-100"}`}
        style={{ borderRightWidth: widthPct > 2 ? "1px" : "0" }}
      />

      {/* Tooltip */}
      {hovered && <Tooltip segment={segment} />}

      {/* Label for wide enough segments */}
      {widthPct > 8 && (
        <div className={`absolute inset-0 flex items-center justify-center
                         text-[8px] font-bold uppercase pointer-events-none select-none
                         ${cfg.label} drop-shadow`}>
          {segment.prediction === "DEEPFAKE" ? "FAKE" : segment.prediction.slice(0, 4)}
        </div>
      )}
    </div>
  );
}

export function SegmentTimeline({
  segments,
  totalDuration,
  isStreaming = false,
  className = "",
}: SegmentTimelineProps) {
  if (!segments || segments.length === 0) {
    if (isStreaming) {
      return (
        <div className={`flex items-center gap-2 text-xs text-slate-500 ${className}`}>
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span>Initialising pipeline…</span>
        </div>
      );
    }
    return null;
  }

  const duration = totalDuration > 0 ? totalDuration : segments[segments.length - 1].end_sec;

  // Summary counts
  const counts: Record<PredictionType, number> = { REAL: 0, DEEPFAKE: 0, AI_SUSPECTED: 0, UNCERTAIN: 0 };
  segments.forEach((s) => {
    if (counts[s.prediction] !== undefined) {
      counts[s.prediction]++;
    }
  });

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Timeline bar */}
      <div className="relative h-8 flex rounded overflow-hidden bg-slate-900/70 border border-slate-800">
        {segments.map((seg) => {
          const segDuration = seg.end_sec - seg.start_sec;
          const widthPct = (segDuration / duration) * 100;
          return (
            <SegmentBlock
              key={seg.window_index}
              segment={seg}
              widthPct={widthPct}
            />
          );
        })}

        {/* Streaming shimmer at the end */}
        {isStreaming && (
          <div className="absolute right-0 top-0 bottom-0 w-6 bg-gradient-to-r from-transparent to-cyan-500/20 animate-pulse" />
        )}
      </div>

      {/* Time ruler */}
      <div className="flex justify-between text-[9px] text-slate-600 font-mono px-0.5">
        <span>0s</span>
        {duration > 4 && <span>{fmt(duration / 4)}</span>}
        {duration > 2 && <span>{fmt(duration / 2)}</span>}
        {duration > 4 && <span>{fmt((duration * 3) / 4)}</span>}
        <span>{fmt(duration)}</span>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-[10px] flex-wrap">
        {(["REAL", "AI_SUSPECTED", "DEEPFAKE", "UNCERTAIN"] as PredictionType[]).map((p) => (
          <div key={p} className="flex items-center gap-1.5 text-slate-400">
            <div className={`w-2.5 h-2.5 rounded-sm ${SEGMENT_COLORS[p].bg}`} />
            <span>{p === "AI_SUSPECTED" ? "AI SUSPECTED" : p}</span>
            <span className="text-slate-600">({counts[p] || 0})</span>
          </div>
        ))}
        {isStreaming && (
          <div className="flex items-center gap-1.5 text-cyan-500 ml-auto">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span>Streaming…</span>
          </div>
        )}
      </div>
    </div>
  );
}
