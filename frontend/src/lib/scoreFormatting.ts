/**
 * Score Formatting Utilities for SHADOW-NET
 * Ensures consistent, non-invented display of AI score, Real score, and progress meters.
 */

/**
 * Formats a probability value [0.0, 1.0] as a percentage string (e.g. 0.069 -> "6.9%").
 * Nullish checks ensure that valid 0 or 0.0 remains "0.0%".
 * Missing, null, undefined, NaN, or non-numeric values return "Unavailable".
 */
export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined || typeof score !== "number" || isNaN(score)) {
    return "Unavailable";
  }
  return `${(score * 100).toFixed(1)}%`;
}

/**
 * Converts a score to a CSS percentage width string [0%, 100%].
 * Missing or invalid scores return "0%".
 */
export function scoreToWidth(score: number | null | undefined): string {
  if (score === null || score === undefined || typeof score !== "number" || isNaN(score)) {
    return "0%";
  }
  const clamped = Math.min(100, Math.max(0, score * 100));
  return `${clamped}%`;
}

/**
 * Returns accurate score type label based on operational mode and training status.
 */
export function getScoreSublabel(mode?: string, model_status?: string): string {
  if (mode === "demo") {
    return "Demo placeholder score";
  }
  return "Uncalibrated model score";
}
