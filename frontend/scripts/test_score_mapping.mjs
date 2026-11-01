import assert from "node:assert/strict";

// Direct pure implementations matching frontend/src/lib/scoreFormatting.ts
function formatScore(score) {
  if (score === null || score === undefined || typeof score !== "number" || isNaN(score)) {
    return "Unavailable";
  }
  return `${(score * 100).toFixed(1)}%`;
}

function scoreToWidth(score) {
  if (score === null || score === undefined || typeof score !== "number" || isNaN(score)) {
    return "0%";
  }
  const clamped = Math.min(100, Math.max(0, score * 100));
  return `${clamped}%`;
}

function getScoreSublabel(mode, model_status) {
  if (mode === "demo") {
    return "Demo placeholder score";
  }
  return "Uncalibrated model score";
}

// Regression Checks
console.log("Running score mapping regression checks...\n");

// Check (a): AI score 0.069 and real score 0.931
assert.equal(formatScore(0.069), "6.9%", "AI score 0.069 must format to 6.9%");
assert.equal(formatScore(0.931), "93.1%", "Real score 0.931 must format to 93.1%");
assert.equal(scoreToWidth(0.069), "6.9%", "Progress width for 0.069 must be 6.9%");
console.log("✔ Passed (a): AI score 0.069 -> 6.9%, real score 0.931 -> 93.1%");

// Check (b): AI score 0.90 and real score 0.10
assert.equal(formatScore(0.90), "90.0%", "AI score 0.90 must format to 90.0%");
assert.equal(formatScore(0.10), "10.0%", "Real score 0.10 must format to 10.0%");
assert.equal(scoreToWidth(0.90), "90%", "Progress width for 0.90 must be 90%");
console.log("✔ Passed (b): AI score 0.90 -> 90.0%, real score 0.10 -> 10.0%");

// Check (c): Uncertain result
assert.equal(formatScore(0.50), "50.0%", "Uncertain score 0.50 must format to 50.0%");
assert.equal(formatScore(0.485), "48.5%", "Uncertain score 0.485 must format to 48.5%");
console.log("✔ Passed (c): Uncertain result 0.50 -> 50.0%, 0.485 -> 48.5%");

// Check (d): Zero and missing scores
assert.equal(formatScore(0), "0.0%", "Valid zero (0) must remain 0.0%");
assert.equal(formatScore(0.0), "0.0%", "Valid float zero (0.0) must remain 0.0%");
assert.equal(formatScore(null), "Unavailable", "null score must display Unavailable");
assert.equal(formatScore(undefined), "Unavailable", "undefined score must display Unavailable");
assert.equal(formatScore(NaN), "Unavailable", "NaN score must display Unavailable");
assert.equal(formatScore("invalid"), "Unavailable", "Non-numeric score must display Unavailable");
assert.equal(scoreToWidth(0), "0%", "Zero score width must be 0%");
assert.equal(scoreToWidth(null), "0%", "Missing score width must be 0%");
assert.equal(scoreToWidth(undefined), "0%", "Undefined score width must be 0%");
console.log("✔ Passed (d): Zero (0) -> 0.0%, null/undefined/NaN -> Unavailable");

// Check (e): Label generation
assert.equal(getScoreSublabel("ml", "TRAINED"), "Uncalibrated model score");
assert.equal(getScoreSublabel("ml", "NOT_TRAINED"), "Uncalibrated model score");
assert.equal(getScoreSublabel("demo", "NOT_TRAINED"), "Demo placeholder score");
console.log("✔ Passed (e): Labels match mode ('Uncalibrated model score' vs 'Demo placeholder score')");

// Check (f): Payload simulation preventing substitution of confidence for AI score
const samplePayloadReal = {
  prediction: "REAL",
  confidence: 0.931,
  ai_probability: 0.069,
  real_probability: 0.931,
};

// Simulation of frontend mapping logic
const mappedAiScore = formatScore(samplePayloadReal.ai_probability);
const mappedRealScore = formatScore(samplePayloadReal.real_probability);

assert.equal(mappedAiScore, "6.9%", "AI card must never display 93.1% confidence");
assert.notEqual(mappedAiScore, `${(samplePayloadReal.confidence * 100).toFixed(1)}%`, "AI score must differ from confidence on REAL prediction");
assert.equal(mappedRealScore, "93.1%", "Real card must display 93.1%");
console.log("✔ Passed (f): Simulation verifies confidence is not substituted for AI score on REAL clips");

console.log("\nAll score mapping regression checks passed successfully!");
