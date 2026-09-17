"use client";

import React, { useRef, useEffect } from "react";

interface SpectrogramMatrixProps {
  matrix?: number[][];
  height?: number;
  label?: string;
}

export function SpectrogramMatrix({
  matrix,
  height = 140,
  label = "LOG MEL-SPECTROGRAM (128 MELS)",
}: SpectrogramMatrixProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rows = matrix && matrix.length > 0 ? matrix.length : 16;
    const cols = matrix && matrix[0] ? matrix[0].length : 32;

    const w = canvas.width;
    const h = canvas.height;
    const cellW = w / cols;
    const cellH = h / rows;

    ctx.clearRect(0, 0, w, h);

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        // High frequencies at top, low frequencies at bottom (invert r)
        const rowIdx = rows - 1 - r;
        const val = matrix && matrix[rowIdx] ? matrix[rowIdx][c] : 0.05;

        // Color mapping: 0.0 -> dark blue, 0.4 -> cyan, 0.7 -> amber, 1.0 -> hot red/white
        let rVal = 0;
        let gVal = 0;
        let bVal = 0;

        if (val < 0.3) {
          rVal = 10;
          gVal = Math.floor(val * 3 * 150);
          bVal = Math.floor(val * 3 * 255);
        } else if (val < 0.7) {
          const t = (val - 0.3) / 0.4;
          rVal = Math.floor(t * 240);
          gVal = Math.floor(150 + t * 50);
          bVal = Math.floor(255 * (1 - t));
        } else {
          const t = (val - 0.7) / 0.3;
          rVal = 240 + Math.floor(t * 15);
          gVal = Math.floor(180 * (1 - t));
          bVal = 30;
        }

        ctx.fillStyle = `rgb(${rVal}, ${gVal}, ${bVal})`;
        ctx.fillRect(c * cellW, r * cellH, cellW + 0.5, cellH + 0.5);
      }
    }
  }, [matrix, height]);

  return (
    <div className="w-full bg-[#050811] border border-slate-800 rounded-lg p-3 relative overflow-hidden">
      <div className="flex justify-between items-center text-[10px] font-mono text-slate-400 mb-1">
        <span>{label}</span>
        <span className="text-cyan-400">8kHz ─── 0Hz</span>
      </div>
      <canvas
        ref={canvasRef}
        width={480}
        height={height}
        className="w-full rounded bg-[#03060c] border border-slate-900"
      />
      <div className="flex justify-between text-[9px] font-mono text-slate-500 mt-1">
        <span>0.0s</span>
        <span>TIME WINDOW (ROLLING)</span>
        <span>2.0s</span>
      </div>
    </div>
  );
}
