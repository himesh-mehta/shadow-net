"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { SpectrogramMatrix } from "@/components/ui/SpectrogramMatrix";
import { mockLiveAnalysis } from "@/lib/mockData";
import {
  Radio,
  Clock,
  Cpu,
  Layers,
  Activity,
  AlertTriangle,
  Zap,
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

export default function LiveDetectionPage() {
  const [analysis, setAnalysis] = useState(mockLiveAnalysis);
  const [rollingHistory, setRollingHistory] = useState([
    { window: "W-0", fakeScore: 0.15 },
    { window: "W-1", fakeScore: 0.28 },
    { window: "W-2", fakeScore: 0.35 },
    { window: "W-3", fakeScore: 0.62 },
    { window: "W-4", fakeScore: 0.88 },
    { window: "W-5", fakeScore: 0.94 },
  ]);

  // Periodic simulation of live rolling window update
  useEffect(() => {
    const interval = setInterval(() => {
      const nextScore = Math.max(0.1, Math.min(0.98, 0.85 + (Math.random() * 0.2 - 0.1)));
      setRollingHistory((prev) => {
        const nextIdx = prev.length;
        const updated = [...prev.slice(1), { window: `W-${nextIdx}`, fakeScore: parseFloat(nextScore.toFixed(2)) }];
        return updated;
      });
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <AppShell>
      <div className="space-y-6 font-mono">
        {/* Top Title Bar */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
              <Radio className="w-5 h-5 text-red-500 animate-pulse" />
              LIVE DEEPFAKE INTERCEPTION TELEMETRY
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              High-frequency spectral analysis and neural classifier probability stream.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <ThreatBadge type={analysis.mode} size="sm" />
            <ThreatBadge type={analysis.threat_level} size="sm" />
          </div>
        </div>

        {/* Primary Alert Banner if DEEPFAKE flagged */}
        {analysis.prediction === "DEEPFAKE" && (
          <div className="p-4 rounded-xl bg-red-950/60 border border-red-700 text-red-300 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 animate-bounce" />
              <div>
                <div className="font-bold text-sm text-red-200">
                  CRITICAL SYNTHETIC SIGNATURE INTERCEPTED
                </div>
                <div className="text-xs text-red-300/80">
                  Acoustic artifact confidence exceeds {analysis.confidence * 100}%. Mitigation: {analysis.response_action}.
                </div>
              </div>
            </div>

            <span className="px-3 py-1 rounded bg-red-900 border border-red-600 text-xs font-bold text-white">
              SESSION RESTRICTED
            </span>
          </div>
        )}

        {/* 4 Core Real-Time Readout Tiles */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Classification Verdict */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="text-xs text-slate-500 uppercase">CLASSIFICATION VERDICT</div>
            <div className="flex items-center gap-2">
              <ThreatBadge type={analysis.prediction} size="lg" />
            </div>
            <div className="text-[10px] text-slate-500">Three-state decision engine</div>
          </div>

          {/* Confidence Gauge */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between text-xs text-slate-500 uppercase">
              <span>CONFIDENCE GAUGE</span>
              <span>{(analysis.confidence * 100).toFixed(1)}%</span>
            </div>
            <div className="text-2xl font-bold text-white">
              {(analysis.confidence * 100).toFixed(1)}%
            </div>
            {/* Progress bar */}
            <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
              <div
                className={`h-full transition-all duration-500 ${
                  analysis.prediction === "DEEPFAKE" ? "bg-red-500" : "bg-emerald-500"
                }`}
                style={{ width: `${analysis.confidence * 100}%` }}
              />
            </div>
          </div>

          {/* Measured Detection Latency */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between text-xs text-slate-500 uppercase">
              <span>MEASURED LATENCY</span>
              <Clock className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold text-cyan-400">
              {analysis.detection_latency_ms} <span className="text-xs font-normal text-slate-500">ms</span>
            </div>
            <div className="text-[10px] text-slate-500">Fast Fourier & tensor forward pass</div>
          </div>

          {/* Active Model / Mode */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between text-xs text-slate-500 uppercase">
              <span>INFERENCE ENGINE</span>
              <Cpu className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-sm font-bold text-amber-300 truncate">
              {analysis.model_name}
            </div>
            <div className="text-[10px] text-amber-400 font-semibold uppercase">
              MODE: {analysis.mode} (SYNTHETIC FALLBACK)
            </div>
          </div>
        </div>

        {/* Middle Section: Mel-Spectrogram Heatmap & Rolling History */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Mel-Spectrogram Heatmap Canvas */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                Live Mel-Spectrogram Spectral Heatmap
              </span>
              <span className="text-[10px] text-slate-500">128 MEL BANDS</span>
            </div>

            <SpectrogramMatrix
              matrix={analysis.windows[0]?.visual_matrix}
              height={180}
              label="WINDOW #2 (ACTIVE SPEECH INTERVAL)"
            />
          </div>

          {/* Rolling Prediction History Graph */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-red-400" />
                Rolling Deepfake Risk Probability
              </span>
              <span className="text-[10px] text-red-400">THRESHOLD: 0.75</span>
            </div>

            <div className="h-52 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rollingHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="window" stroke="#64748b" fontSize={10} />
                  <YAxis domain={[0, 1]} stroke="#64748b" fontSize={10} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#020617", borderColor: "#334155", fontSize: 11 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="fakeScore"
                    stroke="#ef4444"
                    strokeWidth={2.5}
                    dot={{ fill: "#ef4444", r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Window-by-Window Detailed Readout */}
        <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
            Rolling Window Inference Timeline
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {analysis.windows.map((win) => (
              <div
                key={win.window_index}
                className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2 text-xs"
              >
                <div className="flex justify-between items-center pb-2 border-b border-slate-800/80">
                  <span className="text-slate-400 font-bold">WINDOW #{win.window_index}</span>
                  <ThreatBadge type={win.threat_level} size="sm" />
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Timestamp Span:</span>
                  <span className="text-slate-200">[{win.start_sec}s &rarr; {win.end_sec}s]</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Synthetic Prob:</span>
                  <span className={win.fake_probability >= 0.75 ? "text-red-400 font-bold" : "text-emerald-400"}>
                    {(win.fake_probability * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Spectrogram Shape:</span>
                  <span className="text-slate-300">({win.mel_shape.join(", ")})</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
