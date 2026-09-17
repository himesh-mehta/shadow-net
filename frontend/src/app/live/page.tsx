"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { SpectrogramMatrix } from "@/components/ui/SpectrogramMatrix";
import { useDetectionWebSocket } from "@/lib/useWebSocket";
import { api } from "@/lib/api";
import { DetectionAnalysis, PredictionType, ThreatLevel, WindowResult } from "@/types";
import {
  Radio,
  Clock,
  Cpu,
  Layers,
  Activity,
  AlertTriangle,
  Zap,
  Wifi,
  WifiOff,
  RefreshCw,
  ExternalLink,
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
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeAlert, setActiveAlert] = useState<{
    incident_id?: string;
    message: string;
    requires_verification: boolean;
  } | null>(null);

  const [analysis, setAnalysis] = useState<DetectionAnalysis>({
    session_id: "standby-eval",
    mode: "demo",
    model_name: "ResNet18Classifier (Demo Fallback)",
    prediction: "REAL",
    confidence: 0.12,
    threat_level: "LOW",
    response_action: "LOG_ONLY",
    detection_latency_ms: 18.5,
    windows: [],
    spectrogram_shape: [128, 64],
  });

  const [rollingHistory, setRollingHistory] = useState<Array<{ window: string; fakeScore: number }>>([
    { window: "W-0", fakeScore: 0.1 },
  ]);

  // Query active session ID on mount
  useEffect(() => {
    let isMounted = true;
    api.getSessionStatus()
      .then((res) => {
        if (isMounted) {
          if (res?.session_id) {
            setSessionId(res.session_id);
          } else {
            setSessionId("test-session-live");
          }
        }
      })
      .catch(() => {
        if (isMounted) setSessionId("test-session-live");
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Connect WebSocket to real backend
  const { status: wsStatus, lastMessage, connectionError, reconnect } = useDetectionWebSocket(sessionId);

  // Process live WebSocket stream updates
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === "connection_established") {
      setAnalysis((prev) => ({
        ...prev,
        mode: lastMessage.mode || prev.mode,
        model_name: lastMessage.model_name || prev.model_name,
      }));
    } else if (lastMessage.type === "prediction_update") {
      const pred = lastMessage.prediction as PredictionType;
      const conf = lastMessage.confidence as number;
      const threat = lastMessage.threat_level as ThreatLevel;
      const latency = lastMessage.latency_ms as number;
      const mode = lastMessage.mode || "demo";
      const wins = (lastMessage.windows || []) as WindowResult[];

      setAnalysis((prev) => ({
        ...prev,
        prediction: pred,
        confidence: conf,
        threat_level: threat,
        detection_latency_ms: latency,
        mode,
        response_action: lastMessage.response_action || prev.response_action,
        windows: wins,
      }));

      // Append to rolling chart
      setRollingHistory((prev) => {
        const nextIdx = prev.length;
        const updated = [
          ...prev.slice(-9),
          { window: `W-${nextIdx}`, fakeScore: parseFloat(conf.toFixed(2)) },
        ];
        return updated;
      });

      if (pred === "DEEPFAKE") {
        setActiveAlert({
          message: `Deepfake acoustic signature intercepted with ${(conf * 100).toFixed(1)}% confidence.`,
          requires_verification: true,
        });
      }
    } else if (lastMessage.type === "alert") {
      setActiveAlert({
        incident_id: lastMessage.incident_id,
        message: lastMessage.message || "Deepfake voice anomaly detected. Session restricted.",
        requires_verification: Boolean(lastMessage.requires_verification),
      });
      setAnalysis((prev) => ({
        ...prev,
        prediction: "DEEPFAKE",
        threat_level: (lastMessage.threat_level as ThreatLevel) || "CRITICAL",
        confidence: lastMessage.confidence || 0.95,
      }));
    }
  }, [lastMessage]);

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
            {/* WebSocket Connection Status */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[11px]">
              {wsStatus === "OPEN" ? (
                <>
                  <Wifi className="w-3 h-3 text-emerald-400" />
                  <span className="text-emerald-400 font-semibold">STREAM LIVE</span>
                </>
              ) : wsStatus === "CONNECTING" ? (
                <>
                  <RefreshCw className="w-3 h-3 text-amber-400 animate-spin" />
                  <span className="text-amber-400">CONNECTING...</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3 h-3 text-red-400" />
                  <span className="text-red-400 font-semibold">DISCONNECTED</span>
                </>
              )}
            </div>

            <ThreatBadge type={analysis.mode} size="sm" />
            <ThreatBadge type={analysis.threat_level} size="sm" />
          </div>
        </div>

        {/* Visible Alert if ML Service is Unavailable */}
        {wsStatus === "UNAVAILABLE" && (
          <div className="p-4 rounded-xl bg-red-950/70 border border-red-800 text-red-300 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
              <div>
                <div className="font-bold text-sm text-white">
                  ML TELEMETRY SERVICE UNAVAILABLE
                </div>
                <div className="text-xs text-red-300/80">
                  {connectionError || "WebSocket server connection dropped. Ensure FastAPI backend is running on port 8000."}
                </div>
              </div>
            </div>
            <button
              onClick={reconnect}
              className="px-3 py-1.5 rounded-lg bg-red-900 hover:bg-red-800 border border-red-700 text-white text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reconnect Stream</span>
            </button>
          </div>
        )}

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
                  Acoustic artifact confidence: {(analysis.confidence * 100).toFixed(1)}%. Mitigation: {analysis.response_action}.
                  {activeAlert?.message && ` (${activeAlert.message})`}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded bg-red-900 border border-red-600 text-xs font-bold text-white">
                SESSION RESTRICTED
              </span>
              <Link
                href={`/verify?session_id=${sessionId || "active"}`}
                className="px-3 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold flex items-center gap-1 transition shadow-lg shadow-amber-950"
              >
                <span>MFA Recovery</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
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
                style={{ width: `${Math.min(100, analysis.confidence * 100)}%` }}
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
              {analysis.detection_latency_ms?.toFixed(1) ?? "20.0"} <span className="text-xs font-normal text-slate-500">ms</span>
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
              MODE: {analysis.mode}
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
              label={analysis.windows.length > 0 ? `WINDOW #${analysis.windows[0].window_index} (ACTIVE SPEECH)` : "STREAM STANDBY"}
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

          {analysis.windows.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No audio windows processed yet for active stream. Start a call or upload audio in the Test Bench.
            </div>
          ) : (
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
                    <span className="text-slate-200">[{win.start_sec?.toFixed(1) ?? 0}s &rarr; {win.end_sec?.toFixed(1) ?? 2}s]</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Synthetic Prob:</span>
                    <span className={win.fake_probability >= 0.75 ? "text-red-400 font-bold" : "text-emerald-400"}>
                      {(win.fake_probability * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Spectrogram Shape:</span>
                    <span className="text-slate-300">({win.mel_shape?.join(", ") ?? "128, 64"})</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
