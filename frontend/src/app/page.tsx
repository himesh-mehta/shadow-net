"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/authContext";
import { UserRole } from "@/types";
import { Shield, KeyRound, ArrowRight, UserCheck } from "lucide-react";
import { ThreatBadge } from "@/components/ui/ThreatBadge";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [username, setUsername] = useState("alex.vance");
  const [password, setPassword] = useState("admin123456");
  const [selectedRole, setSelectedRole] = useState<UserRole>("Administrator");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(selectedRole, username, password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Authentication failed. Ensure backend is running.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickLogin = async (role: UserRole, user: string) => {
    setError(null);
    setSubmitting(true);
    setUsername(user);
    setSelectedRole(role);
    const rolePassMap: Record<string, string> = {
      Administrator: "admin123456",
      "Security Analyst": "analyst123456",
      User: "user123456",
    };
    setPassword(rolePassMap[role] || "admin123456");
    try {
      await login(role);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Quick login failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-screen bg-[#060911] text-slate-100 flex flex-col justify-between p-6 sm:p-12 font-mono selection:bg-cyan-500/20">
      {/* Top SOC Bar */}
      <header className="flex justify-between items-center pb-6 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-xl font-bold tracking-wider text-cyan-400">
            SHADOW<span className="text-white">-NET</span>
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400">
            SOC AUTH GATE
          </span>
        </div>
        <ThreatBadge type="demo" size="sm" />
      </header>

      {/* Main Login Card */}
      <div className="my-auto max-w-md mx-auto w-full">
        <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-8 shadow-2xl space-y-6">
          <div className="space-y-2 text-center">
            <div className="inline-flex p-3 rounded-xl bg-cyan-950/60 border border-cyan-800/50 text-cyan-400 mb-2">
              <Shield className="w-6 h-6" />
            </div>
            <h1 className="text-xl font-bold tracking-wide text-white">
              Operator Access Terminal
            </h1>
            <p className="text-xs text-slate-400 leading-relaxed">
              Controlled deepfake voice interception & telemetry environment.
            </p>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-950/50 border border-red-800 text-red-300 text-xs flex items-center gap-2">
              <span className="font-bold">ERROR:</span> {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs text-slate-400">Operator Handle / ID</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:outline-none text-slate-200 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs text-slate-400">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:outline-none text-slate-200 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs text-slate-400">Assigned Role</label>
              <select
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value as UserRole)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:outline-none text-slate-200 text-sm"
              >
                <option value="Administrator">Administrator (Full Access)</option>
                <option value="Security Analyst">Security Analyst (Triage)</option>
                <option value="User">User (Test Operator)</option>
              </select>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm tracking-wide transition flex items-center justify-center gap-2 shadow-lg shadow-cyan-950"
            >
              <span>Authenticate Session</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Preset Buttons for Easy Dev/Demo Evaluation */}
          <div className="pt-4 border-t border-slate-800/80 space-y-2">
            <div className="text-[10px] uppercase text-slate-500 font-semibold tracking-wider">
              Quick Switch Presets (Dev Mode)
            </div>
            <div className="grid grid-cols-3 gap-2 text-[11px]">
              <button
                type="button"
                onClick={() => handleQuickLogin("Administrator", "alex.vance")}
                className="p-2 rounded bg-slate-900 border border-slate-800 hover:border-amber-600 text-amber-400 text-center transition"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("Security Analyst", "marcus.kane")}
                className="p-2 rounded bg-slate-900 border border-slate-800 hover:border-cyan-600 text-cyan-400 text-center transition"
              >
                Analyst
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("User", "elena.rostova")}
                className="p-2 rounded bg-slate-900 border border-slate-800 hover:border-slate-600 text-slate-300 text-center transition"
              >
                Standard
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="text-center text-[11px] text-slate-600 border-t border-slate-900 pt-4">
        Controlled Self-Owned Test Bench Environment &bull; No 3rd-Party VoIP Interception
      </footer>
    </div>
  );
}
