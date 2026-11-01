"use client";

import React, { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { EvaluationReport, EvaluationFileResult } from "@/types";
import {
  BarChart3,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RefreshCw,
  Clock,
  ShieldCheck,
  Zap,
  Sliders,
  FileAudio,
  FolderOpen,
  Info,
} from "lucide-react";

export default function EvaluationPage() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<EvaluationFileResult | null>(null);

  const fetchLatestReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getLatestEvaluation();
      setReport(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load evaluation report.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLatestReport();
  }, [fetchLatestReport]);

  const handleRunEvaluation = async () => {
    setRunning(true);
    setError(null);
    try {
      const data = await api.runEvaluation();
      setReport(data);
    } catch (err: any) {
      setError(err?.message || "Evaluation run failed.");
    } finally {
      setRunning(false);
    }
  };

  const getVerdictBadge = (verdict: string) => {
    if (verdict === "DEEPFAKE") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950/70 text-rose-300 border border-rose-800/60">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse" />
          AI DEEPFAKE
        </span>
      );
    }
    if (verdict === "REAL") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/70 text-emerald-300 border border-emerald-800/60">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          BONAFIDE REAL
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/70 text-amber-300 border border-amber-800/60">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        UNCERTAIN
      </span>
    );
  };

  const getOutcomeBadge = (outcome: string, isCorrect: boolean) => {
    if (isCorrect) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5" />
          CORRECT ({outcome})
        </span>
      );
    }
    if (outcome.startsWith("UNCERTAIN")) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <AlertTriangle className="w-3.5 h-3.5" />
          FLAGGED ({outcome})
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
        <XCircle className="w-3.5 h-3.5" />
        MISCLASSIFIED ({outcome})
      </span>
    );
  };

  return (
    <AppShell>
      <div className="space-y-6 pb-12 max-w-7xl mx-auto">
        {/* Header & Benchmark Controls */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-[#0d1424] border border-slate-800/80 rounded-xl p-6 shadow-xl">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                <BarChart3 className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  Model Evaluation Harness
                  <span className="text-xs px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-mono">
                    Phase 3 Test-Bench
                  </span>
                </h1>
                <p className="text-sm text-slate-400 mt-0.5">
                  Automated validation suite computing classification metrics, confusion matrices, and feature attribution across benchmark audio.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchLatestReport}
              disabled={loading || running}
              className="px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-700 hover:border-slate-600 text-slate-300 hover:text-white text-sm font-medium flex items-center gap-2 transition disabled:opacity-50"
              title="Refresh latest saved report"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-cyan-400" : ""}`} />
              Refresh
            </button>
            <button
              onClick={handleRunEvaluation}
              disabled={running}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-sm font-bold flex items-center gap-2 shadow-lg shadow-cyan-950/50 transition disabled:opacity-50"
            >
              {running ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Running Pipeline...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  Run Full Evaluation
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-rose-950/40 border border-rose-800/60 rounded-xl p-4 text-rose-300 text-sm flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 text-rose-400 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold">Evaluation Error</p>
              <p className="text-xs text-rose-400/90 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Threshold Banner */}
        {report && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-[#0b1220] border border-slate-800/80 rounded-lg p-3 flex items-center gap-3">
              <div className="p-2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <span className="text-slate-400">REAL Threshold:</span>{" "}
                <span className="font-mono font-bold text-emerald-400">
                  &lt; {(report.thresholds.real_threshold * 100).toFixed(0)}%
                </span>
                <p className="text-[11px] text-slate-500">Low fake prob accepted as Bonafide</p>
              </div>
            </div>

            <div className="bg-[#0b1220] border border-slate-800/80 rounded-lg p-3 flex items-center gap-3">
              <div className="p-2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Sliders className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <span className="text-slate-400">UNCERTAIN Band:</span>{" "}
                <span className="font-mono font-bold text-amber-400">
                  {(report.thresholds.real_threshold * 100).toFixed(0)}% –{" "}
                  {(report.thresholds.deepfake_threshold * 100).toFixed(0)}%
                </span>
                <p className="text-[11px] text-slate-500">Indeterminate zone flagged for MFA</p>
              </div>
            </div>

            <div className="bg-[#0b1220] border border-slate-800/80 rounded-lg p-3 flex items-center gap-3">
              <div className="p-2 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                <Zap className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <span className="text-slate-400">DEEPFAKE Threshold:</span>{" "}
                <span className="font-mono font-bold text-rose-400">
                  &ge; {(report.thresholds.deepfake_threshold * 100).toFixed(0)}%
                </span>
                <p className="text-[11px] text-slate-500">High fake prob triggers restriction</p>
              </div>
            </div>
          </div>
        )}

        {/* Metrics Grid */}
        {report && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-[#0d1424] border border-slate-800/80 rounded-xl p-4">
              <div className="text-xs font-medium text-slate-400">Strict Accuracy</div>
              <div className="text-2xl font-black text-cyan-400 mt-1 font-mono">
                {(report.summary.strict_accuracy * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-1">All samples (TP+TN/N)</div>
            </div>

            <div className="bg-[#0d1424] border border-slate-800/80 rounded-xl p-4">
              <div className="text-xs font-medium text-slate-400">Decisive Accuracy</div>
              <div className="text-2xl font-black text-emerald-400 mt-1 font-mono">
                {(report.summary.decisive_accuracy * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Excl. uncertain</div>
            </div>

            <div className="bg-[#0d1424] border border-slate-800/80 rounded-xl p-4">
              <div className="text-xs font-medium text-slate-400">Precision</div>
              <div className="text-2xl font-black text-blue-400 mt-1 font-mono">
                {(report.summary.precision * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-1">TP / (TP + FP)</div>
            </div>

            <div className="bg-[#0d1424] border border-slate-800/80 rounded-xl p-4">
              <div className="text-xs font-medium text-slate-400">Recall / Sens.</div>
              <div className="text-2xl font-black text-indigo-400 mt-1 font-mono">
                {(report.summary.recall * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-1">TP / (TP + FN)</div>
            </div>

            <div className="bg-[#0d1424] border border-slate-800/80 rounded-xl p-4">
              <div className="text-xs font-medium text-slate-400">F1 Score</div>
              <div className="text-2xl font-black text-purple-400 mt-1 font-mono">
                {report.summary.f1_score.toFixed(3)}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Harmonic mean</div>
            </div>

            <div className="bg-[#0d1424] border border-slate-800/80 rounded-xl p-4">
              <div className="text-xs font-medium text-slate-400">Avg Latency</div>
              <div className="text-2xl font-black text-amber-400 mt-1 font-mono">
                {report.summary.average_latency_ms.toFixed(0)}
                <span className="text-xs font-normal text-slate-400 ml-1">ms</span>
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Per audio sample</div>
            </div>
          </div>
        )}

        {/* Confusion Matrix & Dataset Summary */}
        {report && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Confusion Matrix Card */}
            <div className="bg-[#0d1424] border border-slate-800/80 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400" />
                  Confusion Matrix
                </h2>
                <span className="text-xs text-slate-400 font-mono">
                  Total: {report.summary.total_files} samples
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-emerald-400 font-semibold uppercase tracking-wider">
                    True Positives (TP)
                  </div>
                  <div className="text-3xl font-black font-mono text-emerald-300 mt-1">
                    {report.confusion_matrix.true_positives}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">Deepfake correctly caught</div>
                </div>

                <div className="bg-rose-950/20 border border-rose-800/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-rose-400 font-semibold uppercase tracking-wider">
                    False Positives (FP)
                  </div>
                  <div className="text-3xl font-black font-mono text-rose-300 mt-1">
                    {report.confusion_matrix.false_positives}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">Real flagged as Deepfake</div>
                </div>

                <div className="bg-rose-950/20 border border-rose-800/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-rose-400 font-semibold uppercase tracking-wider">
                    False Negatives (FN)
                  </div>
                  <div className="text-3xl font-black font-mono text-rose-300 mt-1">
                    {report.confusion_matrix.false_negatives}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">Deepfake missed as Real</div>
                </div>

                <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-emerald-400 font-semibold uppercase tracking-wider">
                    True Negatives (TN)
                  </div>
                  <div className="text-3xl font-black font-mono text-emerald-300 mt-1">
                    {report.confusion_matrix.true_negatives}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">Real verified as Real</div>
                </div>
              </div>

              {/* Uncertain Samples Bar */}
              <div className="bg-amber-950/20 border border-amber-800/30 rounded-lg p-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span className="text-amber-300 font-semibold">
                    Indeterminate / Uncertain:
                  </span>
                  <span className="text-slate-300">
                    {report.confusion_matrix.total_uncertain} files (
                    {report.confusion_matrix.uncertain_fake} Fake, {report.confusion_matrix.uncertain_real} Real)
                  </span>
                </div>
                <span className="text-amber-400 font-mono font-bold">
                  {(report.summary.uncertain_rate * 100).toFixed(1)}% rate
                </span>
              </div>
            </div>

            {/* Benchmark Run Metadata */}
            <div className="bg-[#0d1424] border border-slate-800/80 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-400" />
                  Dataset & Execution Profile
                </h2>
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {new Date(report.timestamp).toLocaleTimeString()}
                </span>
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between items-center py-2 border-b border-slate-800/60">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <FolderOpen className="w-4 h-4 text-slate-500" />
                    Dataset Directory
                  </span>
                  <span className="font-mono text-slate-200 truncate max-w-[280px]" title={report.dataset_directory}>
                    {report.dataset_directory}
                  </span>
                </div>

                <div className="flex justify-between items-center py-2 border-b border-slate-800/60">
                  <span className="text-slate-400">Class Distribution</span>
                  <span className="text-slate-200 font-medium">
                    <span className="text-rose-400 font-bold">{report.summary.total_fake}</span> Synthetic Deepfake,{" "}
                    <span className="text-emerald-400 font-bold">{report.summary.total_real}</span> Bonafide Real
                  </span>
                </div>

                <div className="flex justify-between items-center py-2 border-b border-slate-800/60">
                  <span className="text-slate-400">Specificity (TNR)</span>
                  <span className="font-mono font-bold text-slate-200">
                    {(report.summary.specificity * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="flex justify-between items-center py-2 border-b border-slate-800/60">
                  <span className="text-slate-400">Total Pipeline Execution Time</span>
                  <span className="font-mono text-cyan-400 font-bold">
                    {report.summary.total_processing_time_sec}s
                  </span>
                </div>

                <div className="bg-slate-900/60 rounded-lg p-3 text-[11px] text-slate-400 flex items-start gap-2 border border-slate-800/60">
                  <Info className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
                  <span>
                    The evaluation harness tests whole audio files through VAD, feature extraction (MFCC + Mel-spectrogram), window inference, score aggregation, calibrated dual-thresholding, and acoustic explainability.
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Per-File Results Table */}
        {report && (
          <div className="bg-[#0d1424] border border-slate-800/80 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
                  <FileAudio className="w-5 h-5 text-cyan-400" />
                  Per-File Test Results
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Detailed pipeline verdicts, confidence levels, latency, and acoustic feature rationales for each sample.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-[#0a0f1d] text-slate-400 uppercase tracking-wider font-mono border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Sample File</th>
                    <th className="py-3 px-3">Ground Truth</th>
                    <th className="py-3 px-3">Fake Prob</th>
                    <th className="py-3 px-3">Predicted Verdict</th>
                    <th className="py-3 px-3">Test Status</th>
                    <th className="py-3 px-3">Latency</th>
                    <th className="py-3 px-4">Acoustic Reason (Why)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 font-sans">
                  {report.per_file_results.map((file, idx) => (
                    <tr
                      key={idx}
                      onClick={() => setSelectedFile(file)}
                      className="hover:bg-slate-800/30 transition cursor-pointer"
                    >
                      <td className="py-3 px-4 font-mono font-medium text-slate-200">
                        <div className="flex items-center gap-2">
                          <span className="text-slate-500 font-mono text-[11px]">{idx + 1}.</span>
                          <span className="truncate max-w-[220px]" title={file.filename}>
                            {file.filename}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-500 block font-normal font-sans">
                          {file.duration_sec}s &bull; {file.windows_count} window(s)
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono">
                        {file.ground_truth === "DEEPFAKE" ? (
                          <span className="text-rose-400 font-semibold">DEEPFAKE</span>
                        ) : (
                          <span className="text-emerald-400 font-semibold">REAL</span>
                        )}
                      </td>
                      <td className="py-3 px-3 font-mono">
                        <div className="flex items-center gap-2">
                          <span className="w-12">{(file.fake_probability * 100).toFixed(1)}%</span>
                          <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-full ${
                                file.fake_probability >= report.thresholds.deepfake_threshold
                                  ? "bg-rose-500"
                                  : file.fake_probability < report.thresholds.real_threshold
                                  ? "bg-emerald-500"
                                  : "bg-amber-500"
                              }`}
                              style={{ width: `${Math.min(100, file.fake_probability * 100)}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        {getVerdictBadge(file.predicted_verdict)}
                      </td>
                      <td className="py-3 px-3">
                        {getOutcomeBadge(file.outcome, file.is_correct)}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-400">
                        {file.latency_ms}ms
                      </td>
                      <td className="py-3 px-4 text-slate-300 text-xs max-w-xs truncate" title={file.top_reason}>
                        {file.top_reason || "Acoustic baseline"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* File Detail Modal / Drawer */}
        {selectedFile && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-[#0e1628] border border-slate-700/80 rounded-xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <FileAudio className="w-5 h-5 text-cyan-400" />
                  {selectedFile.filename}
                </h3>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-slate-400 hover:text-white p-1 rounded"
                >
                  &times;
                </button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Ground Truth:</span>
                  <div className="font-bold text-slate-200 mt-0.5">{selectedFile.ground_truth}</div>
                </div>
                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Verdict:</span>
                  <div className="font-bold text-slate-200 mt-0.5">{selectedFile.predicted_verdict}</div>
                </div>
                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Fake Probability:</span>
                  <div className="font-mono font-bold text-cyan-400 mt-0.5">
                    {(selectedFile.fake_probability * 100).toFixed(2)}%
                  </div>
                </div>
                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Latency:</span>
                  <div className="font-mono font-bold text-slate-200 mt-0.5">
                    {selectedFile.latency_ms} ms
                  </div>
                </div>
              </div>

              <div className="bg-[#0a0f1d] border border-slate-800 rounded-lg p-4 space-y-2">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Acoustic Feature Attribution &amp; Reasons
                </h4>
                <p className="text-sm font-medium text-cyan-300">
                  {selectedFile.top_reason}
                </p>
                {selectedFile.explanation?.details && selectedFile.explanation.details.length > 0 && (
                  <ul className="list-disc list-inside text-xs text-slate-400 space-y-1 mt-2">
                    {selectedFile.explanation.details.map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setSelectedFile(null)}
                  className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
