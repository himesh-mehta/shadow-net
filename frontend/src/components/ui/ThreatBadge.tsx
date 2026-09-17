import React from "react";
import { ThreatLevel, PredictionType, VerificationStatus } from "@/types";

interface ThreatBadgeProps {
  type: ThreatLevel | PredictionType | VerificationStatus | "demo" | "ml" | string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function ThreatBadge({ type, size = "md", className = "" }: ThreatBadgeProps) {
  let style = "bg-slate-800 text-slate-300 border-slate-700";
  let label = type;

  switch (type) {
    case "CRITICAL":
    case "DEEPFAKE":
    case "FAILED":
      style = "bg-red-950/70 text-red-400 border-red-800/80";
      break;
    case "HIGH":
    case "UNCERTAIN":
    case "demo":
      style = "bg-amber-950/70 text-amber-400 border-amber-800/80";
      break;
    case "MEDIUM":
    case "PENDING":
      style = "bg-yellow-950/60 text-yellow-300 border-yellow-800/70";
      break;
    case "LOW":
    case "REAL":
    case "VERIFIED":
    case "ml":
      style = "bg-emerald-950/70 text-emerald-400 border-emerald-800/80";
      break;
    case "BYPASSED":
      style = "bg-slate-900 text-slate-400 border-slate-700";
      break;
  }

  const sizeClasses = {
    sm: "text-[10px] px-1.5 py-0.5",
    md: "text-xs px-2.5 py-1",
    lg: "text-sm px-3.5 py-1.5 font-bold tracking-wide",
  }[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded font-mono border uppercase ${sizeClasses} ${style} ${className}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          type === "CRITICAL" || type === "DEEPFAKE"
            ? "bg-red-500 animate-pulse"
            : type === "HIGH" || type === "UNCERTAIN" || type === "demo"
            ? "bg-amber-500"
            : "bg-emerald-500"
        }`}
      />
      {label}
    </span>
  );
}
