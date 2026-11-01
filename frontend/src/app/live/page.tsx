"use client";

import { WavRecorder } from "@/lib/wavRecorder";
import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { SpectrogramMatrix } from "@/components/ui/SpectrogramMatrix";
import { useDetectionWebSocket } from "@/lib/useWebSocket";
import { api } from "@/lib/api";
import { formatScore, scoreToWidth, getScoreSublabel } from "@/lib/scoreFormatting";
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
  Mic,
  Square,
  ShieldCheck,
  Info,
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
  const [sessionId, setSessionId] = useState<string>("test-session-live");
  const [activeAlert, setActiveAlert] = useState<{
    incident_id?: string;
    message: string;
    requires_verification: boolean;
  } | null>(null);

  const [isMicStreaming, setIsMicStreaming] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [lastExplanation, setLastExplanation] = useState<{
    top_reason: string;
    details?: string[];
  } | null>(null);

  const mediaRecorderRef = useRef<WavRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);

  const [analysis, setAnalysis] = useState<DetectionAnalysis>({
    session_id: "test-session-live",
    mode: "ml",
    model_name: "Gustking/wav2vec2-large-xlsr-deepfake-audio-classification",
    model_version: "f7050b586236dc910d1157f430def2d0647b02b4",
    model_status: "TRAINED",
    is_heuristic_placeholder: false,
    display_verdict: "STANDBY",
    prediction: "REAL",
    confidence: 0,
    ai_probability: undefined,
    real_probability: undefined,
    threat_level: "LOW",
    response_action: "NONE",
    detection_latency_ms: 0,
    windows: [],
    spectrogram_shape: [128, 64],
  });

  const [rollingHistory, setRollingHistory] = useState<Array<{ window: string; fakeScore: number }>>([]);

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
  const { status: wsStatus, lastMessage, connectionError, reconnect, sendAudioChunk } = useDetectionWebSocket(sessionId);

  // Stop mic streaming
  const stopMicStream = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((track) => track.stop());
      audioStreamRef.current = null;
    }
    setIsMicStreaming(false);
  }, []);

  // Start mic streaming
  const startMicStream = async () => {
    setMicError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;

      const mediaRecorder = new WavRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          const reader = new FileReader();
          reader.readAsDataURL(event.data);
          reader.onloadend = () => {
            const base64 = (reader.result as string)?.split(",")[1];
            if (base64) {
              sendAudioChunk(base64);
            }
          };
        }
      };

      // Emit chunk every 2000ms
      mediaRecorder.start(4000);
      setIsMicStreaming(true);
    } catch (err: any) {
      setMicError("Microphone access failed: " + (err?.message || "Permission denied"));
      setIsMicStreaming(false);
    }
  };

  const handleToggleMic = () => {
    if (isMicStreaming) {
      stopMicStream();
    } else {
      startMicStream();
    }
  };

  // Clean up mic on unmount
  useEffect(() => {
    return () => {
      stopMicStream();
    };
  }, [stopMicStream]);

  // Process live WebSocket stream updates
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === "connection_established") {
      setAnalysis((prev) => ({
        ...prev,
        mode: lastMessage.mode || prev.mode,
        model_name: lastMessage.model_name || prev.model_name,
        model_version: lastMessage.model_version || prev.model_version,
        model_status: lastMessage.model_status || prev.model_status,
        is_heuristic_placeholder: lastMessage.is_heuristic_placeholder ?? prev.is_heuristic_placeholder,
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
        display_verdict: lastMessage.display_verdict || prev.display_verdict,
        confidence: conf,
        ai_probability: typeof lastMessage.ai_probability === "number" ? lastMessage.ai_probability : undefined,
        real_probability: typeof lastMessage.real_probability === "number" ? lastMessage.real_probability : undefined,
        threat_level: threat,
        detection_latency_ms: latency,
        mode,
        model_name: lastMessage.model_name || prev.model_name,
        model_version: lastMessage.model_version || prev.model_version,
        model_status: lastMessage.model_status || prev.model_status,
        is_heuristic_placeholder: lastMessage.is_heuristic_placeholder ?? prev.is_heuristic_placeholder,
        response_action: lastMessage.response_action || prev.response_action,
        sustained_threat_detected: lastMessage.sustained_threat_detected ?? prev.sustained_threat_detected,
        windows: wins,
      }));

      // Update explanation if present
      if (lastMessage.top_reason) {
        setLastExplanation({
          top_reason: lastMessage.top_reason,
          details: lastMessage.explanation?.details,
        });
      }

      // Append to rolling chart using the exact same analysis event ai_probability
      if (typeof lastMessage.ai_probability === "number" && !isNaN(lastMessage.ai_probability)) {
        setRollingHistory((prev) => {
          const nextIdx = prev.length;
          const updated = [
            ...prev.slice(-9),
            { window: `W-${nextIdx}`, fakeScore: lastMessage.ai_probability },
          ];
          return updated;
        });
      }

      if (pred === "DEEPFAKE") {
        setActiveAlert({
          message: `Deepfake acoustic signature intercepted with ${formatScore(lastMessage.ai_probability)} AI score.`,
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
            {/* Transparent Model Status Badges */}
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded font-mono text-[10px] font-bold tracking-wider bg-purple-950/70 border border-purple-700 text-purple-300 uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                MODEL STATUS: {analysis.model_status || "CHECKING"}
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded font-mono text-[10px] font-bold tracking-wider bg-amber-950/70 border border-amber-700 text-amber-300 uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                DETECTION: EXPERIMENTAL
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Live Mic Streaming Toggle */}
            <button
              onClick={handleToggleMic}
              disabled={wsStatus !== "OPEN" && (wsStatus as string) !== "connected"}
              title={
                wsStatus !== "OPEN" && (wsStatus as string) !== "connected"
                  ? "Connecting to WebSocket telemetry server..."
                  : isMicStreaming
                  ? "Click to stop streaming microphone"
                  : "Click to stream microphone to real-time ML detector"
              }
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition disabled:opacity-50 disabled:cursor-not-allowed ${
                isMicStreaming
                  ? "bg-rose-600 hover:bg-rose-500 text-white animate-pulse"
                  : "bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-950/40"
              }`}
            >
              {isMicStreaming ? (
                <>
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>Stop Live Mic</span>
                </>
              ) : (
                <>
                  <Mic className="w-3.5 h-3.5" />
                  <span>Stream Mic to WS</span>
                </>
              )}
            </button>

            {/* WebSocket Connection Status */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[11px]">
              {wsStatus === "OPEN" || (wsStatus as string) === "connected" ? (
                <>
                  <Wifi className="w-3 h-3 text-emerald-400" />
                  <span className="text-emerald-400 font-semibold">WS CONNECTED</span>
                </>
              ) : wsStatus === "CONNECTING" || (wsStatus as string) === "connecting" ? (
                <>
                  <RefreshCw className="w-3 h-3 text-amber-400 animate-spin" />
                  <span className="text-amber-400 font-semibold">CONNECTING...</span>
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

        {/* Mic Error Alert */}
        {micError && (
          <div className="p-3 rounded-xl bg-rose-950/50 border border-rose-800 text-rose-300 text-xs flex items-center justify-between">
            <span>{micError}</span>
            <button onClick={() => setMicError(null)} className="text-slate-400 hover:text-white">&times;</button>
          </div>
        )}

        {/* Streaming Status Banner */}
        {isMicStreaming && (
          <div className="p-3 rounded-xl bg-cyan-950/40 border border-cyan-800/60 text-cyan-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              <span className="font-semibold">Microphone stream transmitting 2.0s audio chunks over WebSocket...</span>
            </div>
            <span className="font-mono text-[11px] text-cyan-400">Session: {sessionId}</span>
          </div>
        )}

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
                  AI score: {formatScore(analysis.ai_probability)} &bull; Real score: {formatScore(analysis.real_probability)}. Mitigation: {analysis.response_action}.
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

        {/* Untrained Model Plain Disclosure Banner */}
        {(analysis.model_status !== "TRAINED") && (
          <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-800/70 text-amber-300 text-xs flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <div className="font-semibold text-amber-200 flex items-center gap-2">
                <span>MODEL STATUS: NOT TRAINED</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-900/60 border border-amber-700 text-amber-200">
                  DETECTION: EXPERIMENTAL
                </span>
              </div>
              <p className="text-[11px] text-amber-300/80">
                Real-time audio ingestion and Mel-spectrogram processing are active. However, this model skeleton is not trained on any deepfake dataset yet. Output probabilities are heuristic spectral placeholders and are displayed for prototyping and pipeline validation only.
              </p>
            </div>
          </div>
        )}

        {/* 4 Core Real-Time Readout Tiles */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Classification Verdict */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="text-xs text-slate-500 uppercase">CLASSIFICATION VERDICT</div>
            <div className="flex items-center gap-2">
              <ThreatBadge type={analysis.display_verdict || "RESULT UNAVAILABLE"} size="lg" />
            </div>
            <div className="text-[10px] text-amber-400/90 font-mono">
              Threshold-based decision
            </div>
          </div>

          {/* AI score Card */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between text-xs text-slate-500 uppercase">
              <span>AI score</span>
              <span>{formatScore(analysis.ai_probability)}</span>
            </div>
            <div className="flex items-baseline justify-between">
              <div className="text-2xl font-bold text-white">
                {formatScore(analysis.ai_probability)}
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Real: {formatScore(analysis.real_probability)}
              </div>
            </div>
            {/* Progress bar */}
            <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
              <div
                className={`h-full transition-all duration-500 ${
                  analysis.prediction === "DEEPFAKE"
                    ? "bg-rose-500"
                    : analysis.prediction === "AI_SUSPECTED"
                    ? "bg-amber-500"
                    : analysis.prediction === "REAL"
                    ? "bg-emerald-500"
                    : "bg-amber-500"
                }`}
                style={{ width: scoreToWidth(analysis.ai_probability) }}
              />
            </div>
            <div className="text-[10px] text-amber-400 font-mono">
              {getScoreSublabel(analysis.mode, analysis.model_status)}
            </div>
          </div>

          {/* Measured Detection Latency */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between text-xs text-slate-500 uppercase">
              <span>MEASURED LATENCY</span>
              <Clock className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold text-cyan-400">
              {typeof analysis.detection_latency_ms === "number" && analysis.detection_latency_ms > 0
                ? `${analysis.detection_latency_ms.toFixed(1)} ms`
                : "Unavailable"}
            </div>
            <div className="text-[10px] text-slate-500">Fast Fourier &amp; tensor forward pass</div>
          </div>

          {/* Active Model / Mode */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex justify-between text-xs text-slate-500 uppercase">
              <span>MODEL TARGET</span>
              <Cpu className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-sm font-bold text-slate-200 font-mono truncate" title={analysis.model_name}>
              {analysis.model_name || "Unavailable"}
            </div>
            <div className="text-[10px] text-purple-400 font-semibold uppercase">
              STATUS: {analysis.model_status || "NOT_TRAINED"} {analysis.model_version ? `(v${analysis.model_version})` : ""}
            </div>
          </div>
        </div>

        {/* Acoustic Observations Panel if Available */}
        {lastExplanation && (
          <div className="p-4 rounded-xl bg-[#09101f] border border-cyan-900/50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                Acoustic observations
              </span>
              <span className="text-[10px] text-slate-500">
                Acoustic observations only; not a model explanation.
              </span>
            </div>
            <p className="text-sm font-medium text-slate-200">
              {lastExplanation.top_reason}
            </p>
            {lastExplanation.details && lastExplanation.details.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-1">
                {lastExplanation.details.map((d, i) => (
                  <span key={i} className="text-[11px] px-2.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                    &bull; {d}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

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
              <span className="text-[10px] text-amber-400 font-mono">
                UNCERTAIN: 35–65% | FAKE: &ge;65%
              </span>
            </div>

            <div className="h-52 w-full pt-2">
              {rollingHistory.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
                  Stream standby. No audio windows analyzed yet.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={rollingHistory}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="window" stroke="#64748b" fontSize={10} />
                    <YAxis domain={[0, 1]} stroke="#64748b" fontSize={10} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#020617", borderColor: "#334155", fontSize: 11 }}
                      formatter={(val: any) => [`${(Number(val) * 100).toFixed(1)}%`, "AI score"]}
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
              )}
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
              No audio windows processed yet for active stream. Start live microphone streaming above or ingest audio in the Test Bench.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {analysis.windows.map((win) => {
                const winAiScore = win.ai_probability !== undefined ? win.ai_probability : win.fake_probability;
                const winRealScore = win.real_probability !== undefined ? win.real_probability : undefined;
                return (
                  <div
                    key={win.window_index}
                    className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2 text-xs"
                  >
                    <div className="flex justify-between items-center pb-2 border-b border-slate-800/80">
                      <span className="text-slate-400 font-bold">WINDOW #{win.window_index}</span>
                      <ThreatBadge type={win.threat_level} size="sm" />
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Window Span:</span>
                      <span className="text-slate-200">[{win.start_sec?.toFixed(1) ?? 0}s &rarr; {win.end_sec?.toFixed(1) ?? 2}s]</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Window AI score:</span>
                      <span className={typeof winAiScore === "number" ? (winAiScore >= 0.65 ? "text-red-400 font-bold" : winAiScore < 0.35 ? "text-emerald-400 font-bold" : "text-amber-400 font-bold") : "text-slate-400"}>
                        {formatScore(winAiScore)}
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Window Real score:</span>
                      <span className="text-slate-300">
                        {formatScore(winRealScore)}
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Spectrogram Shape:</span>
                      <span className="text-slate-300">({win.mel_shape?.join(", ") ?? "128, 64"})</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
