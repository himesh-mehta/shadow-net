import {
  User,
  Session,
  Incident,
  IncidentDetail,
  AnalyticsData,
  SystemSettings,
  AudioAnalysis,
} from "@/types";

export const mockUsers: Record<string, User> = {
  admin: {
    id: "usr-admin-001",
    username: "alex.vance",
    email: "alex.vance@shadow-net.internal",
    role: "Administrator",
    is_active: true,
    created_at: "2026-03-01T08:00:00Z",
  },
  analyst: {
    id: "usr-analyst-002",
    username: "marcus.kane",
    email: "marcus.kane@shadow-net.internal",
    role: "Security Analyst",
    is_active: true,
    created_at: "2026-03-05T10:30:00Z",
  },
  user: {
    id: "usr-standard-003",
    username: "elena.rostova",
    email: "elena.rostova@shadow-net.internal",
    role: "User",
    is_active: true,
    created_at: "2026-03-10T14:15:00Z",
  },
};

export const mockCurrentUser: User = mockUsers.admin;

export const mockActiveSession: Session = {
  session_id: "sess-8f2b-491c-99d0",
  user_id: "usr-admin-001",
  status: "active",
  client_label: "SOC Controlled Test Audio Bench 01",
  store_audio: false,
  started_at: new Date(Date.now() - 145000).toISOString(), // ~2.5 mins ago
  stopped_at: null,
  notes: "Controlled microphone synthesis testing — VoiceClone RVC benchmark",
};

export const mockRestrictedSession: Session = {
  session_id: "sess-3e11-7a82-12aa",
  user_id: "usr-analyst-002",
  status: "restricted",
  client_label: "Test Bench Audio Ingest (Synthetic Stream)",
  store_audio: false,
  started_at: new Date(Date.now() - 360000).toISOString(),
  stopped_at: null,
  notes: "Restricted following deepfake signature interception at 17:42",
};

// Generate a synthetic 16x32 normalized frequency matrix
export const mockSpectrogramMatrix: number[][] = Array.from({ length: 16 }, (_, r) =>
  Array.from({ length: 32 }, (_, c) => {
    const val = 0.5 * Math.sin((r * 0.4) + (c * 0.2)) + 0.3 * Math.cos(c * 0.5) + 0.2;
    return Math.max(0.05, Math.min(0.98, parseFloat(val.toFixed(2))));
  })
);

export const mockLiveAnalysis: AudioAnalysis = {
  status: "success",
  session_id: "sess-8f2b-491c-99d0",
  mode: "demo",
  model_name: "ResNet-18 Acoustic Classifier",
  is_synthetic: true,
  prediction: "DEEPFAKE",
  confidence: 0.942,
  threat_level: "CRITICAL",
  response_action: "RESTRICT_SESSION",
  detection_latency_ms: 24.8,
  sample_rate: 16000,
  original_duration_sec: 4.5,
  speech_duration_sec: 3.2,
  dropped_silence_sec: 1.3,
  vad_engine: "EnergyVAD",
  num_windows: 3,
  deepfake_window_count: 2,
  windows: [
    {
      window_index: 0,
      start_sec: 0.0,
      end_sec: 2.0,
      fake_probability: 0.32,
      prediction: "REAL",
      threat_level: "LOW",
      is_padded: false,
      mel_shape: [128, 63],
      mfcc_shape: [20, 63],
      visual_matrix: mockSpectrogramMatrix,
    },
    {
      window_index: 1,
      start_sec: 1.0,
      end_sec: 3.0,
      fake_probability: 0.88,
      prediction: "DEEPFAKE",
      threat_level: "HIGH",
      is_padded: false,
      mel_shape: [128, 63],
      mfcc_shape: [20, 63],
      visual_matrix: mockSpectrogramMatrix,
    },
    {
      window_index: 2,
      start_sec: 2.0,
      end_sec: 3.2,
      fake_probability: 0.96,
      prediction: "DEEPFAKE",
      threat_level: "CRITICAL",
      is_padded: true,
      mel_shape: [128, 63],
      mfcc_shape: [20, 63],
      visual_matrix: mockSpectrogramMatrix,
    },
  ],
};

export const mockIncidents: Incident[] = [
  {
    incident_id: "inc-9412-a7f",
    session_id: "sess-3e11-7a82-12aa",
    timestamp: "2026-09-17T17:35:12Z",
    prediction: "DEEPFAKE",
    confidence: 0.965,
    threat_level: "CRITICAL",
    detection_latency: 22.4,
    response_action: "RESTRICT_SESSION",
    verification_status: "PENDING",
    trigger_details: { anomaly: "Spectral centroid discontinuity", threshold_exceeded: 0.75 },
    store_audio: false,
  },
  {
    incident_id: "inc-8810-bc2",
    session_id: "sess-8f2b-491c-99d0",
    timestamp: "2026-09-17T16:14:05Z",
    prediction: "DEEPFAKE",
    confidence: 0.812,
    threat_level: "HIGH",
    detection_latency: 26.1,
    response_action: "RESTRICT_SESSION",
    verification_status: "VERIFIED",
    trigger_details: { anomaly: "Mel phase inversion artifact" },
    store_audio: false,
  },
  {
    incident_id: "inc-7402-dd9",
    session_id: "sess-1922-33cc-44ee",
    timestamp: "2026-09-17T14:48:22Z",
    prediction: "UNCERTAIN",
    confidence: 0.584,
    threat_level: "MEDIUM",
    detection_latency: 19.8,
    response_action: "ALERT",
    verification_status: "BYPASSED",
    trigger_details: { anomaly: "Borderline acoustic score (0.58)" },
    store_audio: false,
  },
  {
    incident_id: "inc-6109-fe4",
    session_id: "sess-0012-77aa-99bb",
    timestamp: "2026-09-17T11:20:41Z",
    prediction: "REAL",
    confidence: 0.932,
    threat_level: "LOW",
    detection_latency: 18.2,
    response_action: "NONE",
    verification_status: "VERIFIED",
    trigger_details: { anomaly: "Normal speech harmonics" },
    store_audio: false,
  },
];

export const mockIncidentDetail: IncidentDetail = {
  ...mockIncidents[0],
  timeline: [
    { window_index: 0, start_sec: 0.0, end_sec: 2.0, fake_probability: 0.24, prediction: "REAL", threat_level: "LOW" },
    { window_index: 1, start_sec: 1.0, end_sec: 3.0, fake_probability: 0.45, prediction: "UNCERTAIN", threat_level: "MEDIUM" },
    { window_index: 2, start_sec: 2.0, end_sec: 4.0, fake_probability: 0.91, prediction: "DEEPFAKE", threat_level: "HIGH" },
    { window_index: 3, start_sec: 3.0, end_sec: 4.5, fake_probability: 0.97, prediction: "DEEPFAKE", threat_level: "CRITICAL" },
  ],
};

export const mockAnalytics: AnalyticsData = {
  total_incidents: 24,
  suspicious_sessions: 9,
  real_vs_deepfake_counts: {
    REAL: 14,
    DEEPFAKE: 8,
    UNCERTAIN: 2,
  },
  average_confidence: 0.884,
  average_detection_latency_ms: 23.4,
  threat_level_distribution: {
    LOW: 14,
    MEDIUM: 2,
    HIGH: 5,
    CRITICAL: 3,
  },
  pending_verifications: 2,
  total_controlled_sessions: 31,
};

export const mockSettings: SystemSettings = {
  detection_threshold: 0.75,
  audio_window_length: 2.0,
  vad_sensitivity: 2,
  demo_mode: true,
  updated_at: "2026-09-17T12:00:00Z",
  updated_by: "alex.vance",
};
