"use client";

import React, { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { mockRestrictedSession } from "@/lib/mockData";
import {
  KeyRound,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Send,
  Info,
  Unlock,
} from "lucide-react";

export default function VerifyPage() {
  const [sessionId, setSessionId] = useState(mockRestrictedSession.session_id);
  const [sessionStatus, setSessionStatus] = useState<"restricted" | "active">("restricted");
  const [otpCode, setOtpCode] = useState("");
  const [generatedOtp, setGeneratedOtp] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);

  const handleRequestOtp = () => {
    // Simulate prototype MFA generation
    const mockCode = Math.floor(100000 + Math.random() * 900000).toString();
    setGeneratedOtp(mockCode);
    setOtpCode(mockCode); // Pre-fill for easy demonstration
    setFeedback({
      type: "info",
      msg: `[PROTOTYPE SIMULATION] Verification OTP generated: ${mockCode}. (In production, dispatched via OOB telecom channel).`,
    });
  };

  const handleVerify = (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode || otpCode.length < 6) {
      setFeedback({ type: "error", msg: "Please enter a valid 6-digit verification code." });
      return;
    }

    if (generatedOtp && otpCode !== generatedOtp) {
      setFeedback({ type: "error", msg: "Invalid verification code entered." });
      return;
    }

    setSessionStatus("active");
    setFeedback({
      type: "success",
      msg: "Identity successfully verified via prototype MFA simulation. Session restriction lifted back to ACTIVE.",
    });
  };

  return (
    <AppShell>
      <div className="space-y-6 font-mono max-w-2xl mx-auto py-6">
        {/* Header */}
        <div className="text-center space-y-2 pb-4 border-b border-slate-800">
          <div className="inline-flex p-3 rounded-2xl bg-amber-950/60 border border-amber-800/60 text-amber-400 mb-1">
            <KeyRound className="w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold text-white tracking-wide">
            OUT-OF-BAND IDENTITY VERIFICATION (MFA)
          </h1>
          <p className="text-xs text-slate-400">
            Automated session recovery protocol triggered by deepfake voice anomaly interception.
          </p>
        </div>

        {/* Mandatory Prototype Simulation Warning Banner */}
        <div className="p-4 rounded-xl bg-amber-950/50 border border-amber-700/80 text-amber-300 text-xs space-y-1">
          <div className="flex items-center gap-2 font-bold uppercase tracking-wider">
            <Info className="w-4 h-4 text-amber-400 shrink-0" />
            <span>Prototype Simulation Notice</span>
          </div>
          <p className="text-amber-200/90 leading-relaxed text-[11px]">
            This verification flow is an experimental security demonstration running in a controlled test bench. It simulates carrier-grade out-of-band challenge response and does not dispatch real cellular SMS or voice calls.
          </p>
        </div>

        {/* Verification Card */}
        <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6 space-y-6 shadow-2xl">
          {/* Current Session State Box */}
          <div className="flex justify-between items-center p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 text-xs">
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Target Controlled Session</div>
              <div className="text-cyan-300 font-bold mt-0.5">{sessionId}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase text-right">Current Status</div>
              <div className="mt-0.5 text-right">
                <ThreatBadge
                  type={sessionStatus === "restricted" ? "CRITICAL" : "LOW"}
                  size="sm"
                />
              </div>
            </div>
          </div>

          {sessionStatus === "restricted" ? (
            <div className="space-y-6">
              {/* Step 1: Request OTP */}
              <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-3">
                <div className="text-xs font-semibold text-slate-200 flex items-center justify-between">
                  <span>STEP 1: REQUEST VERIFICATION CHALLENGE</span>
                  <span className="text-[10px] text-cyan-400">DEV MODE</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Generate a one-time passcode (OTP) challenge mapped to the restricted session.
                </p>
                <button
                  type="button"
                  onClick={handleRequestOtp}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 text-xs font-semibold flex items-center gap-2 transition"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Request Prototype OTP Code</span>
                </button>
              </div>

              {/* Step 2: Code Submission */}
              <form onSubmit={handleVerify} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs text-slate-300 font-semibold">
                    STEP 2: ENTER 6-DIGIT VERIFICATION CODE
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    placeholder="000000"
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    className="w-full text-center tracking-[0.5em] text-2xl font-bold py-3 rounded-lg bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:outline-none text-cyan-400"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-2.5 px-4 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs tracking-wider uppercase transition flex items-center justify-center gap-2 shadow-lg shadow-amber-950"
                >
                  <Unlock className="w-4 h-4" />
                  <span>Authenticate & Unlock Session</span>
                </button>
              </form>
            </div>
          ) : (
            /* Unlocked Confirmation */
            <div className="p-6 rounded-xl bg-emerald-950/40 border border-emerald-800 text-center space-y-3">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
              <div className="text-sm font-bold text-emerald-300">
                SESSION UNLOCKED & RESTORED TO ACTIVE
              </div>
              <p className="text-xs text-slate-400">
                Identity was successfully validated. Real-time audio ingestion and live classification may now safely resume.
              </p>
              <button
                type="button"
                onClick={() => setSessionStatus("restricted")}
                className="text-xs text-slate-500 hover:text-slate-300 underline pt-2"
              >
                (Re-simulate Restricted State)
              </button>
            </div>
          )}

          {/* Feedback message banner */}
          {feedback && (
            <div
              className={`p-3 rounded-lg text-xs leading-normal ${
                feedback.type === "success"
                  ? "bg-emerald-950/60 border border-emerald-800 text-emerald-300"
                  : feedback.type === "error"
                  ? "bg-red-950/60 border border-red-800 text-red-300"
                  : "bg-cyan-950/60 border border-cyan-800 text-cyan-300"
              }`}
            >
              {feedback.msg}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
