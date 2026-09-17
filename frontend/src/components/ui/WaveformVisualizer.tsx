"use client";

import React, { useRef, useEffect } from "react";

interface WaveformVisualizerProps {
  isActive?: boolean;
  audioData?: number[];
  height?: number;
  color?: string;
}

export function WaveformVisualizer({
  isActive = false,
  audioData,
  height = 96,
  color = "#06b6d4", // Cyan
}: WaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let phase = 0;

    const render = () => {
      const width = canvas.width;
      const h = canvas.height;

      ctx.clearRect(0, 0, width, h);

      // Draw grid line
      ctx.strokeStyle = "#1e293b";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, h / 2);
      ctx.lineTo(width, h / 2);
      ctx.stroke();

      if (!isActive) {
        // Flat baseline
        ctx.strokeStyle = "#334155";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(0, h / 2);
        ctx.lineTo(width, h / 2);
        ctx.stroke();
        return;
      }

      // Draw animated simulated or real waveform
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();

      const points = 128;
      const sliceWidth = width / points;

      for (let i = 0; i < points; i++) {
        let sample = 0;
        if (audioData && audioData.length > 0) {
          const idx = Math.floor((i / points) * audioData.length);
          sample = audioData[idx];
        } else {
          // Synthetic audio wave animation
          const t = i / 10 + phase;
          sample =
            0.4 * Math.sin(t) +
            0.2 * Math.sin(t * 2.3) +
            0.15 * Math.sin(t * 4.1);
        }

        const y = h / 2 + sample * (h * 0.4);
        if (i === 0) {
          ctx.moveTo(0, y);
        } else {
          ctx.lineTo(i * sliceWidth, y);
        }
      }

      ctx.stroke();
      phase += 0.08;
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [isActive, audioData, height, color]);

  return (
    <div className="w-full bg-[#050811] border border-slate-800 rounded-lg p-3 relative overflow-hidden">
      <div className="flex justify-between items-center text-[10px] font-mono text-slate-500 mb-1">
        <span>AUDIO OSCILLOSCOPE (16kHz MONO)</span>
        <span className={isActive ? "text-cyan-400 animate-pulse" : "text-slate-600"}>
          {isActive ? "LIVE SIGNAL DETECTED" : "INPUT IDLE"}
        </span>
      </div>
      <canvas
        ref={canvasRef}
        width={600}
        height={height}
        className="w-full rounded bg-[#03060c]"
      />
    </div>
  );
}
