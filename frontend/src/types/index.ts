export type UserRole = "Administrator" | "Security Analyst" | "User";

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export type SessionStatus = "active" | "stopped" | "restricted" | "completed";

export interface Session {
  session_id: string;
  user_id: string;
  status: SessionStatus;
  client_label: string;
  store_audio: boolean;
  started_at: string;
  stopped_at: string | null;
  notes?: string | null;
}

export type PredictionType = "REAL" | "DEEPFAKE" | "AI_SUSPECTED" | "UNCERTAIN";
export type ThreatLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ResponseAction = "ALERT" | "RESTRICT_SESSION" | "REQUIRE_MFA" | "NONE" | "LOG_ONLY" | "TERMINATE_CALL";
export type VerificationStatus = "PENDING" | "VERIFIED" | "FAILED" | "BYPASSED";

export interface WindowFeature {
  window_index: number;
  start_sec: number;
  end_sec: number;
  fake_probability: number;
  ai_probability?: number;
  real_probability?: number;
  prediction: PredictionType;
  verdict?: string;
  threat_level: ThreatLevel;
  speaker_id?: string;
  is_sustained_threat?: boolean;
  is_padded?: boolean;
  mel_shape?: number[];
  mfcc_shape?: number[];
  visual_matrix?: number[][];
}

export type WindowResult = WindowFeature;

export interface AudioAnalysis {
  status?: string;
  session_id?: string | null;
  mode: "demo" | "ml";
  model_name: string;
  model_version?: string;
  model_status?: "NOT_TRAINED" | "TRAINED";
  is_heuristic_placeholder?: boolean;
  display_verdict?: string;
  is_synthetic?: boolean;
  prediction: PredictionType;
  confidence: number;
  ai_probability?: number;
  real_probability?: number;
  threat_level: ThreatLevel;
  response_action?: ResponseAction;
  detection_latency_ms?: number;
  sample_rate?: number;
  original_duration_sec?: number;
  speech_duration_sec?: number;
  dropped_silence_sec?: number;
  vad_engine?: string;
  num_windows?: number;
  deepfake_window_count?: number;
  sustained_threat_detected?: boolean;
  windows: WindowFeature[];
  spectrogram_shape?: number[];
  explanation?: {
    top_reason?: string;
    verdict_summary?: string;
    details?: string[];
  };
}

export type DetectionAnalysis = AudioAnalysis;

export interface Incident {
  incident_id: string;
  session_id: string;
  timestamp: string;
  prediction: PredictionType;
  confidence: number;
  threat_level: ThreatLevel;
  detection_latency?: number;
  detection_latency_ms?: number;
  response_action: ResponseAction;
  verification_status: VerificationStatus;
  trigger_details?: Record<string, any>;
  timeline?: Array<{
    window_index: number;
    start_sec: number;
    end_sec: number;
    fake_probability: number;
    prediction: PredictionType;
    threat_level: ThreatLevel;
  }>;
  store_audio: boolean;
}

export interface IncidentDetail extends Incident {
  timeline: Array<{
    window_index: number;
    start_sec: number;
    end_sec: number;
    fake_probability: number;
    prediction: PredictionType;
    threat_level: ThreatLevel;
    visual_matrix?: number[][];
  }>;
}

export interface AnalyticsData {
  total_incidents: number;
  suspicious_sessions: number;
  real_vs_deepfake_counts: {
    REAL: number;
    DEEPFAKE: number;
    UNCERTAIN: number;
  };
  average_confidence: number;
  average_detection_latency_ms: number;
  threat_level_distribution: {
    LOW: number;
    MEDIUM: number;
    HIGH: number;
    CRITICAL: number;
  };
  pending_verifications: number;
  total_controlled_sessions: number;
}

export interface SystemSettings {
  detection_threshold: number;
  audio_window_length: number;
  vad_sensitivity: number;
  demo_mode: boolean;
  updated_at?: string;
  updated_by?: string;
}

export interface EvaluationFileResult {
  filename: string;
  duration_sec: number;
  windows_count: number;
  ground_truth: "REAL" | "DEEPFAKE";
  ground_truth_label: number;
  predicted_verdict: "REAL" | "DEEPFAKE" | "UNCERTAIN";
  fake_probability: number;
  confidence: number;
  outcome: "TP" | "TN" | "FP" | "FN" | "UNCERTAIN_REAL" | "UNCERTAIN_FAKE";
  is_correct: boolean;
  latency_ms: number;
  top_reason: string;
  explanation?: {
    top_reason?: string;
    details?: string[];
  };
}

export interface EvaluationReport {
  timestamp: string;
  dataset_directory: string;
  thresholds: {
    real_threshold: number;
    deepfake_threshold: number;
  };
  summary: {
    total_files: number;
    total_real: number;
    total_fake: number;
    strict_accuracy: number;
    decisive_accuracy: number;
    precision: number;
    recall: number;
    specificity: number;
    f1_score: number;
    uncertain_rate: number;
    average_latency_ms: number;
    total_processing_time_sec: number;
  };
  confusion_matrix: {
    true_positives: number;
    true_negatives: number;
    false_positives: number;
    false_negatives: number;
    uncertain_real: number;
    uncertain_fake: number;
    total_uncertain: number;
  };
  per_file_results: EvaluationFileResult[];
}
