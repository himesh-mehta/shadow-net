"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { api } from "@/lib/api";
import {
  KeyRound,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Send,
  Info,
  Unlock,
  RefreshCw,
} from "lucide-react";

function VerifyContent() {
  const searchParams = useSearchParams();
  const initialSessionId = searchParams.get("session_id") || "sess-demo-restricted";

  const [sessionId, setSessionId] = useState(initialSessionId);
  const [sessionStatus, setSessionStatus] = useState<"restricted" | "active">("restricted");
  const [otpCode, setOtpCode] = useState("");
  const [generatedOtp, setGeneratedOtp] = useState<string | null>(null);
  const [disclaimer, setDisclaimer] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);

  // Check session status from API
  useEffect(() => {
    api.getSessionStatus()
      .then((res) => {
        if (res?.session_id) {
          setSessionId(res.session_id);
          setSessionStatus(res.status === "restricted" ? "restricted" : "active");
        }
      })
      .catch(() => {});
  }, []);

  const handleRequestOtp = async () => {
    setIsLoading(true);
    setFeedback(null);
    try {
      const res = await api.requestOtp({ session_id: sessionId });
      const code = res.prototype_otp || res.otp_code || res.otp;
      if (code) {
        setGeneratedOtp(code);
        setOtpCode(code);
      }
      setDisclaimer(res.disclaimer || res.simulation_notice || null);
      setFeedback({
        type: "info",
        msg: `[PROTOTYPE SIMULATION] Verification OTP generated: ${res.prototype_otp || res.otp}. (In production, dispatched via OOB telecom channel).`,
      });
    } catch (err: any) {
      setFeedback({
        type: "error",
        msg: err.message || "Failed to request OTP from backend.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode || otpCode.length < 6) {
      setFeedback({ type: "error", msg: "Please enter a valid 6-digit verification code." });
      return;
    }

    setIsLoading(true);
    setFeedback(null);
    try {
      const res = await api.verifyOtp({ session_id: sessionId, code: otpCode });
      setSessionStatus("active");
      setFeedback({
        type: "success",
        msg: res.message || "Identity successfully verified via prototype MFA simulation. Session restriction lifted back to ACTIVE.",
      });
    } catch (err: any) {
      setFeedback({
        type: "error",
        msg: err.message || "Invalid or expired verification code.",
      });
    } finally {
      setIsLoading(false);
    }
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
            {disclaimer ||
              "This verification flow is an experimental security demonstration running in a controlled test bench. It simulates carrier-grade out-of-band challenge response and does not dispatch real cellular SMS or voice calls."}
          </p>
        </div>

        {/* Verification Card */}
        <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6 space-y-6 shadow-2xl">
          {/* Current Session State Box */}
          <div className="flex justify-between items-center p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 text-xs">
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Target Controlled Session</div>
              <input
                type="text"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                className="bg-transparent text-cyan-300 font-bold mt-0.5 focus:outline-none border-b border-dashed border-cyan-800"
              />
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
                  disabled={isLoading}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 text-xs font-semibold flex items-center gap-2 transition"
                >
                  {isLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
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
                  disabled={isLoading}
                  className="w-full py-2.5 px-4 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs tracking-wider uppercase transition flex items-center justify-center gap-2 shadow-lg shadow-amber-950"
                >
                  {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Unlock className="w-4 h-4" />}
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

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <AppShell>
          <div className="flex items-center justify-center min-h-[50vh] text-cyan-400 font-mono text-xs">
            Loading MFA verification protocol...
          </div>
        </AppShell>
      }
    >
      <VerifyContent />
    </Suspense>
  );
}
