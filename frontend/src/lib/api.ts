import type { AudioAnalysis, AnalyticsData, EvaluationReport, Incident, IncidentDetail, Session, SystemSettings, User } from "@/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || API_URL.replace(/^http/, "ws");
const TOKEN_KEY = "shadow-net-token";
export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
export function getToken(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY);
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (getToken()) headers.set("Authorization", `Bearer ${getToken()}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`, response.status);
  return body as T;
}
const query = (params: Record<string, string | number | undefined> = {}) => {
  const values = Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]);
  return new URLSearchParams(values).toString();
};
export const api = {
  getToken,
  setToken(token: string | null) { if (token) localStorage.setItem(TOKEN_KEY, token); else localStorage.removeItem(TOKEN_KEY); },
  login: (username: string, password: string) => request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  getMe: () => request<User>("/auth/me"),
  getHealth: () => request<{ status: string; database: { engine: string }; detector: { mode: string; loaded: boolean; model_name: string | null; model_status: string; error?: string | null } }>("/health"),
  startSession: (payload: { client_label?: string; store_audio?: boolean }) => request<Session>("/session/start", { method: "POST", body: JSON.stringify(payload) }),
  stopSession: (session_id: string) => request<Session>(`/session/stop?${query({ session_id })}`, { method: "POST" }),
  getSessionStatus: () => request<Session>("/session/status"),
  getAnalytics: () => request<AnalyticsData>("/analytics"),
  listIncidents: (params: { limit?: number; threat_level?: string; prediction?: string } = {}) => request<Incident[]>(`/incidents?${query(params)}`),
  getIncident: (id: string) => request<IncidentDetail>(`/incidents/${encodeURIComponent(id)}`),
  exportIncidentEvidence: (id: string) => request<Record<string, unknown>>(`/incidents/${encodeURIComponent(id)}/export`),
  getSettings: () => request<SystemSettings>("/settings"),
  updateSettings: (payload: SystemSettings) => request<SystemSettings>("/settings", { method: "PUT", body: JSON.stringify(payload) }),
  getLatestEvaluation: () => request<EvaluationReport>("/evaluation/latest"),
  runEvaluation: () => request<EvaluationReport>("/evaluation/run", { method: "POST", body: "{}" }),
  requestOtp: (payload: { session_id: string }) => request<Record<string, string>>("/verify/request-otp", { method: "POST", body: JSON.stringify(payload) }),
  verifyOtp: (payload: { session_id: string; code: string }) => request<{ message?: string }>("/verify", { method: "POST", body: JSON.stringify({ session_id: payload.session_id, otp_code: payload.code }) }),
  analyzeAudioChunk: (payload: { session_id: string; audio_base64: string }) => {
    const form = new FormData();
    form.set("session_id", payload.session_id); form.set("audio_base64", payload.audio_base64);
    return request<AudioAnalysis>("/audio/analyze", { method: "POST", body: form });
  },
};
