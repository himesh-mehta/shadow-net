"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { WaveformVisualizer } from "@/components/ui/WaveformVisualizer";
import { AnalysisTimeline, TimelineEvent } from "@/components/ui/AnalysisTimeline";
import { SegmentTimeline, AudioSegment } from "@/components/ui/SegmentTimeline";
import { api } from "@/lib/api";
import { Session, DetectionAnalysis } from "@/types";
import {
  Mic,
  Square,
  Play,
  Upload,
  Clock,
  Shield,
  FileAudio,
  Radio,
  AlertOctagon,
  Zap,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";

export default function SessionPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("Ready. Start a test session or ingest WAV audio to analyze.");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [lastAnalysis, setLastAnalysis] = useState<DetectionAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [segments, setSegments] = useState<AudioSegment[]>([]);
  const [totalDuration, setTotalDuration] = useState(0);
  const [isStreamAnalyzing, setIsStreamAnalyzing] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);

  const fetchTimeline = useCallback(async (sessionId: string) => {
    try {
      setTimelineLoading(true);
      const token = typeof window !== "undefined" ? localStorage.getItem("shadow_net_token") : null;
      if (!token) return;
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/session/timeline?session_id=${sessionId}&limit=50`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setTimelineEvents(data as TimelineEvent[]);
      }
    } catch {
      // non-critical, swallow
    } finally {
      setTimelineLoading(false);
    }
  }, []);

  // Check initial active session
  useEffect(() => {
    let isMounted = true;
    api.getSessionStatus()
      .then((res) => {
        if (isMounted && res?.session_id) {
          setSession(res as unknown as Session);
          setStatusMessage(`Active session ${res.session_id} resumed.`);
        }
      })
      .catch(() => {
        // Backend not ready or unauthorized
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Duration timer
  useEffect(() => {
    if (!session || session.status !== "active") return;
    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [session]);

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const handleToggleSession = async () => {
    setError(null);
    if (session && session.status === "active") {
      try {
        const stopped = await api.stopSession(session.session_id);
        setSession(stopped);
        if (isRecording) {
          stopRecording();
        }
        setStatusMessage(`Session ${stopped.session_id} stopped.`);
      } catch (err: any) {
        setError(err.message || "Failed to stop session");
      }
    } else {
      try {
        const newSession = await api.startSession({
          client_label: "test-eval-bench",
          store_audio: false,
        });
        setSession(newSession);
        setElapsedSeconds(0);
        setStatusMessage(`New test session ${newSession.session_id} started.`);
      } catch (err: any) {
        setError(err.message || "Failed to start session. Check backend connectivity.");
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((track) => track.stop());
      audioStreamRef.current = null;
    }
    setIsRecording(false);
    setIsStreamAnalyzing(false);
  };

  const startRecording = async () => {
    if (!session || session.status !== "active") {
      setError("Please start a test session before capturing microphone audio.");
      return;
    }

    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      setSegments([]);
      setTotalDuration(0);
      setIsStreamAnalyzing(true);

      mediaRecorder.ondataavailable = async (event) => {
        if (event.data && event.data.size > 0 && session?.session_id) {
          try {
            const reader = new FileReader();
            reader.readAsDataURL(event.data);
            reader.onloadend = async () => {
              const base64Data = (reader.result as string)?.split(",")[1];
              if (base64Data) {
                try {
                  const res = await api.analyzeAudioChunk({
                    session_id: session.session_id,
                    audio_base64: base64Data,
                  });
                  setLastAnalysis(res);
                  setStatusMessage(`Live window analyzed: ${res.prediction} (${(res.confidence * 100).toFixed(1)}%) in ${res.detection_latency_ms?.toFixed(1) ?? 20}ms`);
                  
                  // Append to live segment timeline
                  setSegments((prev) => {
                    const idx = prev.length;
                    return [
                      ...prev,
                      {
                        window_index: idx,
                        start_sec: idx * 2.0,
                        end_sec: (idx + 1) * 2.0,
                        fake_probability: res.fake_probability ?? res.confidence ?? 0.5,
                        prediction: res.prediction,
                        confidence: res.confidence,
                        threat_level: res.threat_level,
                      },
                    ];
                  });
                  setTotalDuration((prev) => prev + 2.0);

                  // Refresh timeline after each mic chunk analysis
                  fetchTimeline(session.session_id);
                } catch {
                  // Fallback or ignore streaming chunk error
                }
              }
            };
          } catch {
            // ignore
          }
        }
      };

      // Emit chunk every 2000ms
      mediaRecorder.start(2000);
      setIsRecording(true);
      setStatusMessage("Microphone stream active. Analyzing 2.0s rolling acoustic windows.");
    } catch (err: any) {
      setIsStreamAnalyzing(false);
      setError("Could not access microphone: " + (err.message || "Permission denied"));
    }
  };

  const handleToggleMic = () => {
    if (isRecording) {
      stopRecording();
      setStatusMessage("Microphone capture paused.");
    } else {
      startRecording();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedFile(file.name);
    setError(null);
    setIsAnalyzing(true);
    setIsStreamAnalyzing(true);
    setSegments([]);
    setTotalDuration(0);
    setStatusMessage(`Streaming segment-level analysis for ${file.name}…`);

    try {
      let activeSessionId = session?.session_id;
      if (!activeSessionId || session?.status !== "active") {
        const tempSession = await api.startSession({
          client_label: "wav-stream-eval",
          store_audio: false,
        });
        setSession(tempSession);
        activeSessionId = tempSession.session_id;
      }

      const token = api.getToken();
      const formData = new FormData();
      formData.append("file", file);
      if (activeSessionId) formData.append("session_id", activeSessionId);

      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_BASE}/audio/analyze/stream`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!res.ok || !res.body) {
        throw new Error(`Stream request failed: ${res.statusText}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE lines
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));

            if (event.type === "pipeline_start") {
              setTotalDuration(event.original_duration_sec || 0);
              setStatusMessage(`Analysing ${event.total_windows} windows over ${(event.original_duration_sec || 0).toFixed(1)}s…`);
            }

            if (event.type === "window") {
              setSegments((prev) => [...prev, event as AudioSegment]);
            }

            if (event.type === "session_verdict") {
              setLastAnalysis({
                mode: event.mode,
                model_name: event.model_name,
                prediction: event.prediction,
                confidence: event.confidence,
                threat_level: event.threat_level,
                response_action: event.response_action,
                detection_latency_ms: event.detection_latency_ms,
                windows: [],
              } as any);
              setStatusMessage(
                `Stream complete: ${event.prediction} (${(event.confidence * 100).toFixed(1)}% confidence, ${event.detection_latency_ms?.toFixed(1)}ms)`
              );
              if (activeSessionId) fetchTimeline(activeSessionId);
            }

            if (event.type === "error") {
              setError(event.message);
            }
          } catch {
            // malformed SSE line, ignore
          }
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to stream audio analysis. Ensure WAV format is used.");
      setStatusMessage("Streaming analysis failed.");
    } finally {
      setIsAnalyzing(false);
      setIsStreamAnalyzing(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6 font-mono">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
              <Mic className="w-5 h-5 text-cyan-400" />
              CONTROLLED TEST BENCH & AUDIO INGESTION
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Initiate controlled call sessions, capture microphone audio, or ingest WAV files for real-time deepfake analysis.
            </p>
            {/* Transparent Model Status Badges */}
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded font-mono text-[10px] font-bold tracking-wider bg-purple-950/70 border border-purple-700 text-purple-300 uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                MODEL STATUS: NOT TRAINED
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded font-mono text-[10px] font-bold tracking-wider bg-amber-950/70 border border-amber-700 text-amber-300 uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                DETECTION: EXPERIMENTAL
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 flex items-center gap-1.5 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span>CALL DURATION:</span>
              <span className="text-white font-bold">{formatTimer(elapsedSeconds)}</span>
            </span>

            <button
              onClick={handleToggleSession}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition ${
                session && session.status === "active"
                  ? "bg-red-950/80 text-red-300 border border-red-800 hover:bg-red-900"
                  : "bg-emerald-600 text-white hover:bg-emerald-500"
              }`}
            >
              {session && session.status === "active" ? (
                <>
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>STOP SESSION</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>START NEW SESSION</span>
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Live Audio Telemetry & Controls Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Waveform & Recording Canvas */}
          <div className="lg:col-span-2 bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
                Real-Time Audio Ingestion Feed
              </span>
              <span className="text-[10px] text-slate-500">RESAMPLED: 16kHz MONO</span>
            </div>

            {/* Canvas Oscilloscope */}
            <WaveformVisualizer isActive={Boolean(session && session.status === "active" && isRecording)} height={120} />

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={handleToggleMic}
                disabled={!session || session.status !== "active"}
                className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
                  !session || session.status !== "active"
                    ? "bg-slate-900 text-slate-600 border border-slate-800 cursor-not-allowed"
                    : isRecording
                    ? "bg-red-600 hover:bg-red-500 text-white animate-pulse"
                    : "bg-cyan-600 hover:bg-cyan-500 text-white"
                }`}
              >
                <Mic className="w-4 h-4" />
                <span>{isRecording ? "Stop Microphone Feed" : "Capture Live Microphone"}</span>
              </button>

              <label className="px-4 py-2 rounded-lg bg-slate-900 border border-slate-700 hover:border-slate-500 text-slate-200 text-xs font-semibold flex items-center gap-2 cursor-pointer transition">
                <Upload className="w-4 h-4 text-cyan-400" />
                <span>{isAnalyzing ? "Processing WAV..." : "Upload Test WAV File"}</span>
                <input
                  type="file"
                  accept="audio/wav,audio/x-wav,.wav"
                  disabled={isAnalyzing}
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>

              {selectedFile && (
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <FileAudio className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{selectedFile}</span>
                </span>
              )}
            </div>

            {/* Status ticker */}
            <div className="p-3 rounded bg-slate-950/80 border border-slate-800/80 text-xs text-slate-400 flex items-center gap-2">
              <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse shrink-0" />
              <span>{statusMessage}</span>
            </div>

            {/* Real Detection Result Card if available */}
            {lastAnalysis && (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                <div className="flex flex-wrap justify-between items-center gap-2">
                  <span className="text-xs font-semibold text-slate-300 uppercase flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-cyan-400" />
                    Latest Acoustic Pipeline Result
                  </span>
                  <div className="flex items-center gap-2">
                    <ThreatBadge type={lastAnalysis.model_status || "NOT_TRAINED"} size="sm" />
                    <ThreatBadge type="EXPERIMENTAL" size="sm" />
                    <ThreatBadge type={lastAnalysis.threat_level || "LOW"} size="sm" />
                  </div>
                </div>

                {/* Untrained Model Plain Disclosure Banner */}
                {(lastAnalysis.model_status !== "TRAINED") && (
                  <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/60 text-xs flex items-start gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <div className="space-y-0.5">
                      <div className="font-semibold text-amber-300 flex items-center gap-2">
                        <span>MODEL STATUS: NOT TRAINED</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-900/60 border border-amber-700 text-amber-200">
                          DETECTION: EXPERIMENTAL
                        </span>
                      </div>
                      <p className="text-[11px] text-amber-300/80">
                        This pipeline is running in untrained prototype mode. Audio ingestion, waveform extraction, and Mel-spectrogram processing are active, but model weights are not trained on a deepfake dataset. Probabilities are heuristic placeholders and must NOT be used for real verification.
                      </p>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-2.5 rounded bg-[#0b101d] border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase">Classification Verdict</div>
                    <div className="mt-1">
                      <ThreatBadge
                        type={lastAnalysis.display_verdict || "UNCERTAIN (MODEL NOT TRAINED)"}
                        size="sm"
                      />
                    </div>
                  </div>
                  <div className="p-2.5 rounded bg-[#0b101d] border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase">AI Prob (Heuristic)</div>
                    <div className="text-sm font-bold text-white mt-1">
                      {(((lastAnalysis.ai_probability !== undefined ? lastAnalysis.ai_probability : lastAnalysis.confidence)) * 100).toFixed(1)}%
                    </div>
                    <div className="text-[9px] text-amber-400/90 font-mono">Uncalibrated Placeholder</div>
                  </div>
                  <div className="p-2.5 rounded bg-[#0b101d] border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase">Detection Latency</div>
                    <div className="text-sm font-bold text-cyan-400 mt-1">
                      {lastAnalysis.detection_latency_ms?.toFixed(1) ?? 20} ms
                    </div>
                    <div className="text-[9px] text-slate-500 font-mono">{lastAnalysis.num_windows ?? 0} windows</div>
                  </div>
                  <div className="p-2.5 rounded bg-[#0b101d] border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase">Model Target</div>
                    <div className="text-xs text-slate-200 font-mono font-semibold mt-1 truncate">
                      {lastAnalysis.model_name || "shadownet-detector"}
                    </div>
                    <div className="text-[9px] text-purple-400 font-mono">Version: {lastAnalysis.model_version || "v1"}</div>
                  </div>
                </div>

                {/* Acoustic Explanation (Why) */}
                {lastAnalysis.explanation?.top_reason && (
                  <div className="p-3 rounded-lg bg-[#070d18] border border-cyan-900/40 text-xs space-y-1">
                    <div className="text-[10px] text-cyan-400 font-semibold uppercase tracking-wider flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                      Acoustic Forensic Attribution (Why)
                    </div>
                    <p className="text-slate-200 font-medium text-xs">
                      {lastAnalysis.explanation.top_reason}
                    </p>
                    {lastAnalysis.explanation.details && lastAnalysis.explanation.details.length > 0 && (
                      <div className="text-[11px] text-slate-400 pt-1 flex flex-wrap gap-x-3 gap-y-1">
                        {lastAnalysis.explanation.details.map((detail, idx) => (
                          <span key={idx} className="inline-block bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800">
                            &bull; {detail}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Segment Timeline */}
                {segments.length > 0 && (
                  <div className="pt-2 space-y-1.5">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider">Segment Timeline</div>
                    <SegmentTimeline
                      segments={segments}
                      totalDuration={totalDuration}
                      isStreaming={isStreamAnalyzing}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Live segment view while streaming and no final result yet */}
            {isStreamAnalyzing && !lastAnalysis && segments.length > 0 && (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                <span className="text-xs font-semibold text-slate-300 uppercase flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  Streaming Segment Analysis
                </span>
                <SegmentTimeline
                  segments={segments}
                  totalDuration={totalDuration}
                  isStreaming={true}
                />
              </div>
            )}
          </div>

          {/* Session Metadata & Privacy Policy Card */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-200">SESSION METADATA</span>
              <ThreatBadge type={session ? (session.status === "active" ? "LOW" : "HIGH") : "LOW"} size="sm" />
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Session Identifier</div>
                <div className="text-cyan-300 font-bold break-all mt-0.5">
                  {session?.session_id || "NO ACTIVE SESSION"}
                </div>
              </div>

              <div>
                <div className="text-[10px] text-slate-500 uppercase">Client Ingest Label</div>
                <div className="text-slate-200 mt-0.5">
                  {session?.client_label || "test-bench-standby"}
                </div>
              </div>

              <div>
                <div className="text-[10px] text-slate-500 uppercase">Operational State</div>
                <div className="text-emerald-400 font-semibold uppercase mt-0.5">
                  {session?.status || "STANDBY"}
                </div>
              </div>

              {/* Privacy Notice Required by Spec */}
              <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/50 space-y-1">
                <div className="text-[10px] text-emerald-400 font-bold uppercase flex items-center gap-1">
                  <Shield className="w-3 h-3" />
                  <span>Audio Privacy Protocol Active</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Raw voice recordings are NOT stored to disk (store_audio = FALSE). Only temporary acoustic feature arrays (MFCCs & Mel-Spectrograms) are extracted for model inference.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/50 space-y-1">
                <div className="text-[10px] text-amber-400 font-bold uppercase flex items-center gap-1">
                  <AlertOctagon className="w-3 h-3" />
                  <span>Self-Owned Test Scope</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-normal">
                  This prototype operates exclusively in user-initiated test calls. It does not interface with third-party carrier telephony, Zoom, or Teams.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Analysis Timeline History */}
        <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Session Analysis Timeline
            </span>
            <span className="text-[10px] text-slate-500 font-mono">
              {timelineEvents.length} event{timelineEvents.length !== 1 ? "s" : ""}
            </span>
          </div>
          <AnalysisTimeline events={timelineEvents} isLoading={timelineLoading} />
        </div>
      </div>
    </AppShell>
  );
}
