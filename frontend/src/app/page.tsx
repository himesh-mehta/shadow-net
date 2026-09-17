import React from "react";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#070a10] text-slate-100 flex flex-col justify-between p-6 sm:p-10 font-sans border-t-2 border-cyan-500">
      {/* Top Bar / SOC Navigation Header */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xl font-bold tracking-wider uppercase font-mono text-cyan-400">
            SHADOW-NET
          </span>
          <span className="text-xs px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-slate-400">
            PROTO-BUILD v0.1
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-700/60 text-emerald-400">
            PHASE 0: SCAFFOLD OK
          </span>
          <span className="px-2.5 py-1 rounded bg-amber-950/60 border border-amber-700/60 text-amber-400">
            DEMO MODE READY
          </span>
        </div>
      </header>

      {/* Hero Section */}
      <div className="my-auto py-12 max-w-4xl mx-auto w-full text-center space-y-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-cyan-300">
          <span className="inline-block w-2 h-2 rounded-full bg-cyan-400" />
          Deepfake Voice Interception & Risk Response System
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white font-mono">
          SHADOW<span className="text-cyan-400">-</span>NET
        </h1>

        <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto leading-relaxed">
          High-performance acoustic feature extraction and synthetic voice detection pipeline for controlled security testing.
        </p>

        {/* Phase Status Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 text-left font-mono">
          <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Backend API</div>
            <div className="text-emerald-400 text-sm font-semibold flex items-center justify-between">
              FastAPI /health
              <span className="text-[10px] bg-emerald-900/50 text-emerald-300 px-1.5 py-0.5 rounded">Ready</span>
            </div>
            <p className="text-xs text-slate-400 mt-2">Port 8000 | Uvicorn ASGI runtime configured</p>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Frontend Client</div>
            <div className="text-cyan-400 text-sm font-semibold flex items-center justify-between">
              Next.js 14 App Router
              <span className="text-[10px] bg-cyan-900/50 text-cyan-300 px-1.5 py-0.5 rounded">Ready</span>
            </div>
            <p className="text-xs text-slate-400 mt-2">Port 3000 | Tailwind CSS + Recharts stack</p>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Pipeline State</div>
            <div className="text-amber-400 text-sm font-semibold flex items-center justify-between">
              Phase 0 Complete
              <span className="text-[10px] bg-amber-900/50 text-amber-300 px-1.5 py-0.5 rounded">Next: Phase 1</span>
            </div>
            <p className="text-xs text-slate-400 mt-2">Ready for MongoDB models & JWT authentication</p>
          </div>
        </div>

        {/* Notice Card */}
        <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80 text-left text-xs font-mono text-slate-400 space-y-1">
          <span className="text-amber-400 font-semibold uppercase">Operational Scope Notice:</span>
          <p>
            This prototype is designed exclusively for controlled, user-initiated test sessions (local microphone or WAV file ingestion). It does not intercept external VoIP, Zoom, or Teams sessions.
          </p>
        </div>
      </div>

      {/* Footer */}
      <footer className="pt-6 border-t border-slate-900 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs font-mono text-slate-500">
        <div>SHADOW-NET Prototype &bull; Multi-Phase Architecture</div>
        <div>SOC Baseline Environment</div>
      </footer>
    </main>
  );
}
