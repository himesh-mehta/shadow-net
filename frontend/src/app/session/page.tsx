"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { WaveformVisualizer } from "@/components/ui/WaveformVisualizer";
import { mockActiveSession } from "@/lib/mockData";
import { Session } from "@/types";
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
} from "lucide-react";

export default function SessionPage() {
  const [session, setSession] = useState<Session>(mockActiveSession);
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(165); // 02:45
  const [selectedFile, setSelectedFile] = useState<string | null>("sample_test.wav");
  const [statusMessage, setStatusMessage] = useState("Controlled audio ingestion active. Analyzing rolling windows.");

  // Duration timer
  useEffect(() => {
    if (session.status !== "active") return;
    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [session.status]);

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const handleToggleSession = () => {
    if (session.status === "active") {
      setSession({
        ...session,
        status: "stopped",
        stopped_at: new Date().toISOString(),
      });
      setIsRecording(false);
      setStatusMessage("Controlled test session terminated.");
    } else {
      setSession({
        ...mockActiveSession,
        session_id: "sess-" + Math.random().toString(36).substring(2, 8),
        status: "active",
        started_at: new Date().toISOString(),
        stopped_at: null,
      });
      setElapsedSeconds(0);
      setStatusMessage("New test session initiated. Audio pipeline online.");
    }
  };

  const handleToggleMic = () => {
    if (session.status !== "active") return;
    setIsRecording(!isRecording);
    setStatusMessage(
      !isRecording
        ? "Microphone live capture active (16kHz PCM stream to VAD)."
        : "Microphone paused. Awaiting WAV or resumed stream."
    );
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file.name);
      setStatusMessage(`Ingested ${file.name} (WAV). Analyzing acoustic features...`);
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
                session.status === "active"
                  ? "bg-red-950/80 text-red-300 border border-red-800 hover:bg-red-900"
                  : "bg-emerald-600 text-white hover:bg-emerald-500"
              }`}
            >
              {session.status === "active" ? (
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
            <WaveformVisualizer isActive={session.status === "active" && isRecording} height={120} />

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={handleToggleMic}
                disabled={session.status !== "active"}
                className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
                  session.status !== "active"
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
                <span>Upload Test WAV File</span>
                <input
                  type="file"
                  accept="audio/wav,audio/x-wav"
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
          </div>

          {/* Session Metadata & Privacy Policy Card */}
          <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-200">SESSION METADATA</span>
              <ThreatBadge type={session.status === "active" ? "LOW" : "HIGH"} size="sm" />
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Session Identifier</div>
                <div className="text-cyan-300 font-bold break-all mt-0.5">{session.session_id}</div>
              </div>

              <div>
                <div className="text-[10px] text-slate-500 uppercase">Client Ingest Label</div>
                <div className="text-slate-200 mt-0.5">{session.client_label}</div>
              </div>

              <div>
                <div className="text-[10px] text-slate-500 uppercase">Operational State</div>
                <div className="text-emerald-400 font-semibold uppercase mt-0.5">
                  {session.status}
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
      </div>
    </AppShell>
  );
}
