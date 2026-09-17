"use client";

import React, { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/authContext";
import { mockSettings } from "@/lib/mockData";
import { SystemSettings } from "@/types";
import {
  Sliders,
  ShieldCheck,
  Lock,
  Save,
  Cpu,
  CheckCircle,
} from "lucide-react";

export default function SettingsPage() {
  const { isAdmin, userRole, switchRole } = useAuth();
  const [settings, setSettings] = useState<SystemSettings>(mockSettings);
  const [savedMessage, setSavedMessage] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedMessage(true);
    setTimeout(() => setSavedMessage(false), 3000);
  };

  // Role Gate: If non-admin, render Access Denied guard
  if (!isAdmin) {
    return (
      <AppShell>
        <div className="max-w-xl mx-auto my-auto py-16 text-center space-y-4 font-mono">
          <div className="inline-flex p-4 rounded-2xl bg-red-950/60 border border-red-800 text-red-400">
            <Lock className="w-8 h-8" />
          </div>
          <h1 className="text-xl font-bold text-white uppercase tracking-wider">
            ADMINISTRATOR PRIVILEGES REQUIRED
          </h1>
          <p className="text-xs text-slate-400 leading-relaxed">
            System parameter tuning is restricted exclusively to operators with the{" "}
            <span className="text-amber-400 font-bold">Administrator</span> role. Your active role is{" "}
            <span className="text-cyan-400 font-bold">{userRole}</span>.
          </p>

          <div className="pt-4">
            <button
              onClick={() => switchRole("Administrator")}
              className="px-4 py-2 rounded-lg bg-slate-900 border border-amber-700 hover:border-amber-500 text-amber-300 text-xs font-semibold transition"
            >
              Switch Role to Administrator (Dev Test)
            </button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6 font-mono max-w-3xl mx-auto">
        {/* Title */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
              <Sliders className="w-5 h-5 text-cyan-400" />
              SYSTEM DETECTION PARAMETERS
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Configure acoustic thresholds, audio windowing lengths, and neural inference modes.
            </p>
          </div>

          <span className="text-[10px] px-2.5 py-1 rounded bg-amber-950/80 border border-amber-800 text-amber-400 font-bold">
            ADMINISTRATOR ACCESS ACTIVE
          </span>
        </div>

        {/* Settings Form Card */}
        <form onSubmit={handleSave} className="bg-[#0b101d] border border-slate-800 rounded-xl p-6 space-y-6">
          {/* Detection Threshold */}
          <div className="space-y-2 pb-4 border-b border-slate-800/80">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-slate-200">
                DEEPFAKE DETECTION THRESHOLD
              </label>
              <span className="text-cyan-400 font-bold text-sm">
                {(settings.detection_threshold * 100).toFixed(0)}% ({settings.detection_threshold})
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-normal">
              Acoustic synthetic probability required to trigger DEEPFAKE classification and automated session restriction.
            </p>
            <input
              type="range"
              min="0.50"
              max="0.95"
              step="0.05"
              value={settings.detection_threshold}
              onChange={(e) =>
                setSettings({ ...settings, detection_threshold: parseFloat(e.target.value) })
              }
              className="w-full accent-cyan-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>0.50 (Permissive)</span>
              <span>0.75 (Recommended Standard)</span>
              <span>0.95 (High Precision)</span>
            </div>
          </div>

          {/* Audio Window Length */}
          <div className="space-y-2 pb-4 border-b border-slate-800/80">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-slate-200">
                ROLLING AUDIO WINDOW DURATION
              </label>
              <span className="text-cyan-400 font-bold text-sm">
                {settings.audio_window_length.toFixed(1)} Seconds
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-normal">
              Duration of continuous speech audio sliced into each log-Mel-spectrogram window for model inference.
            </p>
            <div className="grid grid-cols-3 gap-3 pt-1">
              {[1.0, 1.5, 2.0].map((val) => (
                <button
                  type="button"
                  key={val}
                  onClick={() => setSettings({ ...settings, audio_window_length: val })}
                  className={`py-2 rounded-lg text-xs font-semibold border transition ${
                    settings.audio_window_length === val
                      ? "bg-cyan-950 text-cyan-300 border-cyan-500"
                      : "bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  {val.toFixed(1)}s Window
                </button>
              ))}
            </div>
          </div>

          {/* VAD Sensitivity Mode */}
          <div className="space-y-2 pb-4 border-b border-slate-800/80">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-slate-200">
                VOICE ACTIVITY DETECTION (VAD) SENSITIVITY
              </label>
              <span className="text-cyan-400 font-bold text-sm">
                Mode {settings.vad_sensitivity}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-normal">
              Controls silence dropping aggressiveness. Higher modes filter more background noise and breathing pauses.
            </p>
            <div className="grid grid-cols-4 gap-2 pt-1">
              {[
                { mode: 0, label: "0 (Permissive)" },
                { mode: 1, label: "1 (Standard)" },
                { mode: 2, label: "2 (Balanced)" },
                { mode: 3, label: "3 (Aggressive)" },
              ].map((item) => (
                <button
                  type="button"
                  key={item.mode}
                  onClick={() => setSettings({ ...settings, vad_sensitivity: item.mode })}
                  className={`py-2 px-1 text-center rounded-lg text-xs font-semibold border transition ${
                    settings.vad_sensitivity === item.mode
                      ? "bg-cyan-950 text-cyan-300 border-cyan-500"
                      : "bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {/* Demo / ML Mode Toggle */}
          <div className="space-y-2 pb-4 border-b border-slate-800/80">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-slate-200 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-amber-400" />
                <span>INFERENCE ENGINE MODE</span>
              </label>
              <span className={`text-xs font-bold ${settings.demo_mode ? "text-amber-400" : "text-emerald-400"}`}>
                {settings.demo_mode ? "DEMO MODE (SYNTHETIC)" : "PRODUCTION ML MODE"}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-normal">
              When Demo Mode is enabled, the system uses the deterministic synthetic fallback. Toggle off to require loaded ResNet-18 weights.
            </p>
            <div className="flex items-center gap-3 pt-1">
              <button
                type="button"
                onClick={() => setSettings({ ...settings, demo_mode: true })}
                className={`flex-1 py-2 rounded-lg text-xs font-semibold border transition ${
                  settings.demo_mode
                    ? "bg-amber-950/80 text-amber-300 border-amber-600"
                    : "bg-slate-950 text-slate-500 border-slate-800"
                }`}
              >
                Demo Mode (Synthetic Fallback)
              </button>
              <button
                type="button"
                onClick={() => setSettings({ ...settings, demo_mode: false })}
                className={`flex-1 py-2 rounded-lg text-xs font-semibold border transition ${
                  !settings.demo_mode
                    ? "bg-emerald-950/80 text-emerald-300 border-emerald-600"
                    : "bg-slate-950 text-slate-500 border-slate-800"
                }`}
              >
                Production ML (PyTorch ResNet-18)
              </button>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="submit"
              className="py-2.5 px-6 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs flex items-center gap-2 transition shadow-lg shadow-cyan-950"
            >
              <Save className="w-4 h-4" />
              <span>Save System Settings</span>
            </button>

            {savedMessage && (
              <span className="text-xs text-emerald-400 flex items-center gap-1.5 animate-pulse">
                <CheckCircle className="w-4 h-4" />
                <span>Settings applied successfully!</span>
              </span>
            )}
          </div>
        </form>
      </div>
    </AppShell>
  );
}
