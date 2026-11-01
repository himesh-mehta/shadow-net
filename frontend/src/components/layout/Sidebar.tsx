"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/authContext";
import {
  ShieldAlert,
  Activity,
  Mic,
  Sliders,
  Radio,
  FileCheck2,
  Lock,
  BarChart3,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const { isAdmin, userRole } = useAuth();

  const navItems = [
    {
      name: "SOC Dashboard",
      href: "/dashboard",
      icon: Activity,
      adminOnly: false,
    },
    {
      name: "Controlled Session",
      href: "/session",
      icon: Mic,
      adminOnly: false,
    },
    {
      name: "Live Telemetry",
      href: "/live",
      icon: Radio,
      adminOnly: false,
    },
    {
      name: "Incident Response",
      href: "/incidents",
      icon: ShieldAlert,
      adminOnly: false,
    },
    {
      name: "Prototype MFA",
      href: "/verify",
      icon: FileCheck2,
      adminOnly: false,
    },
    {
      name: "Model Evaluation",
      href: "/evaluation",
      icon: BarChart3,
      adminOnly: false,
    },
    {
      name: "System Settings",
      href: "/settings",
      icon: Sliders,
      adminOnly: true, // Gated strictly to Administrator
    },
  ];

  return (
    <aside className="w-64 bg-[#080c16] border-r border-slate-800 flex flex-col justify-between shrink-0 select-none">
      <div>
        {/* Brand */}
        <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800/80">
          <div className="w-3 h-3 rounded-full bg-cyan-400 animate-ping" />
          <div>
            <div className="font-mono font-bold tracking-wider text-cyan-400 text-sm">
              SHADOW<span className="text-white">-NET</span>
            </div>
            <div className="text-[10px] font-mono text-slate-500">
              VOICE INTERCEPTION SOC
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1.5 font-mono text-xs">
          <div className="text-[10px] uppercase text-slate-500 px-3 py-1 tracking-wider font-semibold">
            Operations
          </div>
          {navItems.map((item) => {
            // Hide settings if non-admin
            if (item.adminOnly && !isAdmin) return null;

            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg transition ${
                  isActive
                    ? "bg-cyan-950/50 text-cyan-300 border border-cyan-800/60 font-medium"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border border-transparent"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? "text-cyan-400" : "text-slate-500"}`} />
                  <span>{item.name}</span>
                </div>
                {item.adminOnly && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-800/60">
                    ADMIN
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Scope Disclaimer Box */}
      <div className="p-4 border-t border-slate-900 text-[10px] font-mono text-slate-500 space-y-2">
        <div className="flex items-center gap-1.5 text-amber-500 font-semibold">
          <Lock className="w-3 h-3" />
          <span>CONTROLLED BENCH</span>
        </div>
        <p className="leading-relaxed text-slate-400">
          Operates strictly on self-owned test call sessions. No external VoIP or carrier interception.
        </p>
      </div>
    </aside>
  );
}
