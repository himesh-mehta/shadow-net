"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/authContext";
import { UserRole } from "@/types";
import { ThreatBadge } from "@/components/ui/ThreatBadge";
import { ChevronDown, Radio, Activity } from "lucide-react";
import { api } from "@/lib/api";

export function Header() {
  const { currentUser, userRole, switchRole } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [telemetryOnline, setTelemetryOnline] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(true);

  const roles: UserRole[] = ["Administrator", "Security Analyst", "User"];

  useEffect(() => {
    let isMounted = true;
    const checkStatus = async () => {
      try {
        const health = await api.getHealth();
        if (!isMounted) return;
        setTelemetryOnline(health?.status === "ok");
        
        try {
          const settings = await api.getSettings();
          if (isMounted) setIsDemoMode(Boolean(settings.demo_mode));
        } catch {
          // If settings unauthorized for non-admin, default remains
        }
      } catch {
        if (isMounted) setTelemetryOnline(false);
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="h-16 bg-[#080c16]/90 backdrop-blur border-b border-slate-800/80 px-6 flex items-center justify-between font-mono shrink-0">
      {/* Left: Operational Indicators */}
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          {telemetryOnline ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-slate-400">TELEMETRY:</span>
              <span className="text-emerald-400 font-bold">ONLINE</span>
            </>
          ) : (
            <>
              <span className="relative flex h-2 w-2">
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
              </span>
              <span className="text-slate-400">TELEMETRY:</span>
              <span className="text-red-400 font-bold">OFFLINE (CONNECTING...)</span>
            </>
          )}
        </div>

        <div className="hidden sm:block h-4 w-px bg-slate-800" />

        {/* Phase 3, 6 & 8 Requirement: Visible Persistent DEMO MODE / ML LIVE badge */}
        <ThreatBadge type={isDemoMode ? "demo" : "ml"} size="sm" className="inline-flex" />
      </div>

      {/* Right: Operator Profile & Role Switcher for Testing */}
      <div className="relative">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex items-center gap-3 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:border-slate-600 text-xs transition"
        >
          <div className="w-6 h-6 rounded-full bg-cyan-950 border border-cyan-800 flex items-center justify-center text-cyan-400 text-[10px] font-bold">
            {(currentUser?.username || "OP").substring(0, 2).toUpperCase()}
          </div>
          <div className="text-left">
            <div className="text-slate-200 text-xs font-semibold leading-tight">
              {currentUser?.username || "Operator"}
            </div>
            <div className="text-[10px] text-cyan-400 uppercase">
              {userRole}
            </div>
          </div>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-1" />
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 mt-2 w-56 bg-slate-950 border border-slate-800 rounded-lg shadow-2xl p-2 z-50 text-xs font-mono">
            <div className="text-[10px] uppercase text-slate-400 px-2 py-1 font-semibold border-b border-slate-800/80 mb-1">
              Switch Test Role
            </div>
            {roles.map((r) => (
              <button
                key={r}
                onClick={() => {
                  switchRole(r);
                  setDropdownOpen(false);
                }}
                className={`w-full text-left px-2.5 py-1.5 rounded flex items-center justify-between transition ${
                  r === userRole
                    ? "bg-cyan-950 text-cyan-300 font-bold"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                }`}
              >
                <span>{r}</span>
                {r === userRole && <span className="text-[10px] text-cyan-400">ACTIVE</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
