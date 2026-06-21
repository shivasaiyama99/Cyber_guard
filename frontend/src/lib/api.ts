export type BackendStatus = "running" | "idle" | "complete";
export interface StatusResponse {
  status: BackendStatus;
  session_active: boolean;
}

const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL ?? (typeof window !== "undefined" && window.location.hostname !== "localhost" ? "/api" : "http://localhost:8000");

function getAuthToken() {
  return localStorage.getItem("cyberguard_token");
}

export function isTokenValid(): boolean {
  const token = localStorage.getItem("cyberguard_token");
  if (!token) return false;
  try {
    // decode JWT payload (middle part between dots)
    const payload = JSON.parse(atob(token.split(".")[1]));
    // check expiry
    const now = Math.floor(Date.now() / 1000);
    return payload.exp > now;
  } catch {
    return false;
  }
}


function getHeaders(initHeaders?: HeadersInit) {
  const token = getAuthToken();
  const headers = new Headers(initHeaders);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

async function handleResponse(res: Response) {
  const urlObj = new URL(res.url);
  const endpoint = urlObj.pathname;
  console.log(`API ${endpoint} status: ${res.status}`);
  if (res.status === 401) {
    console.error('401 Unauthorized on:', endpoint);
  }

  if (!res.ok) {
    if (res.status === 401 && !res.url.includes("/auth/login") && !res.url.includes("/auth/signin")) {
      localStorage.removeItem("cyberguard_token");
      localStorage.removeItem("cyberguard_user");
      window.location.href = "/signin";
    }
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res;
}

export async function runSimulation(): Promise<{ accepted: boolean }> {
  const res = await fetch(`${BASE_URL}/run-simulation`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
  }).then(handleResponse);
  return res.json();
}

export async function fetchLogs(): Promise<string> {
  const res = await fetch(`${BASE_URL}/logs`, { 
    method: "GET",
    headers: getHeaders()
  }).then(handleResponse);
  return res.text();
}

export async function fetchLogsCount(): Promise<{ count: number }> {
  const res = await fetch(`${BASE_URL}/logs/count`, {
    method: "GET",
    headers: getHeaders(),
  }).then(handleResponse);
  return res.json();
}

export async function fetchReport(): Promise<string> {
  const res = await fetch(`${BASE_URL}/report`, { 
    method: "GET",
    headers: getHeaders()
  }).then(handleResponse);
  return res.text();
}

export async function fetchReportRaw(): Promise<string> {
  console.log('=== fetchReportRaw called ===');
  try {
    const res = await fetch(`${BASE_URL}/report/raw`, { 
      method: "GET",
      headers: getHeaders()
    });
    console.log('=== fetchReportRaw status:', res.status);
    if (res.status === 401) {
      localStorage.removeItem("cyberguard_token");
      localStorage.removeItem("cyberguard_user");
      window.location.href = "/signin";
      return '';
    }
    if (!res.ok) {
      console.error('=== fetchReportRaw failed:', res.status);
      return '';
    }
    const text = await res.text();
    console.log('=== fetchReportRaw length:', text.length);
    console.log('=== fetchReportRaw first 100 chars:', text.substring(0, 100));
    return text;
  } catch (err) {
    console.error('=== fetchReportRaw error:', err);
    return '';
  }
}

export async function fetchStatus(): Promise<StatusResponse> {
  const res = await fetch(`${BASE_URL}/status`, { 
    method: "GET",
    headers: getHeaders()
  }).then(handleResponse);
  return res.json();
}

export async function uploadLogs(file: File): Promise<{ accepted: boolean }> {
  const form = new FormData();
  form.append("file", file, file.name);
  const res = await fetch(`${BASE_URL}/upload-logs`, {
    method: "POST",
    headers: getHeaders(),
    body: form,
  }).then(handleResponse);
  return res.json();
}

export interface StructuredReport {
  incident_id?: string | null;
  timestamps?: { created?: string | null; updated?: string | null };
  attack_type?: string | null;
  risk_score?: string | null;
  severity?: string | null;
  source_ip?: string | null;
  targeted_service?: string | null;
  evidence?: string | null;
  recommended_actions: string[];
  agent_notes: { agent: string; note: string }[];
  timeline: { time: string; event: string }[];
}

export async function fetchStructuredReport(): Promise<StructuredReport> {
  console.log('=== fetchStructuredReport called ===')
  const response = await fetch(`${BASE_URL}/report/structured`, { 
    method: "GET",
    headers: getHeaders()
  }).then(handleResponse);
  
  console.log('=== response status:', response.status ?? 200)
  const data = await response.json();
  console.log('=== raw response data:', JSON.stringify(data))
  return data;
}

// --- New API functions (Task 5) ---

export interface LlmStatus {
  backend: string;
  model: string;
  ollama_available: boolean;
}

export async function getLlmStatus(): Promise<LlmStatus> {
  const res = await fetch(`${BASE_URL}/llm-status`, { 
    method: "GET",
    headers: getHeaders()
  }).then(handleResponse);
  return res.json();
}

export interface AnomalyReport {
  anomalous_count: number;
  anomalous_ips: string[];
}

export async function getAnomalyReport(): Promise<AnomalyReport> {
  const res = await fetch(`${BASE_URL}/anomaly-report`, { 
    method: "GET",
    headers: getHeaders()
  }).then(handleResponse);
  return res.json();
}

export async function postAutoRespond(dryRun: boolean): Promise<{ actions: unknown[] }> {
  const res = await fetch(`${BASE_URL}/auto-respond`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ dry_run: dryRun }),
  }).then(handleResponse);
  return res.json();
}

export function getStreamUrl(): string {
  return `${BASE_URL}/stream`;
}

export function getAgentFeedUrl(): string {
  return `${BASE_URL}/agent-feed`;
}

export function getAlertsLiveUrl(): string {
  return `${BASE_URL}/alerts/live`;
}

export async function fetchAgentMessages(): Promise<{ messages: Array<{ id: number; agent: string; message: string; type: string; timestamp: string }> }> {
  const res = await fetch(`${BASE_URL}/agent-messages`, {
    method: "GET",
    headers: getHeaders(),
  }).then(handleResponse);
  return res.json();
}

// --- Phase 2 API functions ---

export async function getThresholds(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE_URL}/thresholds`, { method: "GET" }).then(handleResponse);
  return res.json();
}

export async function updateThresholds(config: Record<string, unknown>): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE_URL}/thresholds`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  }).then(handleResponse);
  return res.json();
}

export async function getAlerts(limit: number = 500): Promise<unknown[]> {
  const res = await fetch(`${BASE_URL}/alerts?limit=${limit}`, { method: "GET" }).then(handleResponse);
  return res.json();
}

export async function getSmtpStatus(): Promise<{ enabled: boolean; configured: boolean; last_sent: string | null }> {
  const res = await fetch(`${BASE_URL}/smtp-status`, { 
    method: "GET",
    headers: getHeaders()
  }).then(handleResponse);
  return res.json();
}

export async function postTestEmail(): Promise<{ success: boolean; error: string }> {
  const res = await fetch(`${BASE_URL}/test-email`, { 
    method: "POST",
    headers: getHeaders()
  }).then(handleResponse);
  return res.json();
}

export async function getScanHistory(limit: number = 10): Promise<unknown[]> {
  const res = await fetch(`${BASE_URL}/port-scan-history?limit=${limit}`, { method: "GET" }).then(handleResponse);
  return res.json();
}

export async function postScanPorts(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE_URL}/scan-ports`, { method: "POST" }).then(handleResponse);
  return res.json();
}

export async function updateAllowedPorts(ports: number[]): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE_URL}/allowed-ports`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ports }),
  }).then(handleResponse);
  return res.json();
}

// --- Auth APIs (MongoDB-backed) ---

export async function signup(data: any): Promise<any> {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  }).then(handleResponse);
  return res.json();
}

export async function signin(data: any): Promise<any> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  }).then(handleResponse);
  return res.json();
}

export async function googleLogin(idToken: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: idToken }),
  }).then(handleResponse);
  return res.json();
}

export async function authLogout(): Promise<any> {
  const res = await fetch(`${BASE_URL}/auth/logout`, {
    method: "POST",
    headers: getHeaders(),
  }).then(handleResponse);
  return res.json();
}

export async function getMe(): Promise<any> {
  const res = await fetch(`${BASE_URL}/auth/me`, {
    method: "GET",
    headers: getHeaders(),
  }).then(handleResponse);
  return res.json();
}

// --- Incidents API (MongoDB) ---

export interface Incident {
  id: string;
  incident_id: string;
  attack_type?: string | null;
  risk_score?: number | null;
  severity?: string | null;
  source_ip?: string | null;
  timestamp: string;
  status: string;
  agent_notes: string[];
}

export async function getIncidents(): Promise<Incident[]> {
  const res = await fetch(`${BASE_URL}/incidents`, {
    method: "GET",
    headers: getHeaders(),
  }).then(handleResponse);
  return res.json();
}

export async function getIncidentById(incidentId: string): Promise<Incident> {
  const res = await fetch(`${BASE_URL}/incidents/${incidentId}`, {
    method: "GET",
    headers: getHeaders(),
  }).then(handleResponse);
  return res.json();
}

export async function deleteIncident(incidentId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/incidents/${incidentId}`, {
    method: "DELETE",
    headers: getHeaders(),
  }).then(handleResponse);
  return res.json();
}

export async function resetSession(): Promise<any> {
  const res = await fetch(`${BASE_URL}/reset-session`, {
    method: "POST",
    headers: getHeaders(),
  }).then(handleResponse);
  return res.json();
}

// --- Blocked IPs API ---

export interface BlockedIP {
  ip: string;
  blocked_at: string;
  trigger: string;
  dry_run: boolean;
}

export async function getBlockedIPs(): Promise<{blocked_ips: BlockedIP[]}> {
  const res = await fetch(`${BASE_URL}/blocked-ips`, {
    headers: getHeaders()
  }).then(handleResponse);
  return res.json();
}

export async function unblockIP(ip: string): Promise<{status: string; message?: string}> {
  const res = await fetch(`${BASE_URL}/unblock-ip`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ ip })
  }).then(handleResponse);
  return res.json();
}

export async function blockIP(ip: string): Promise<{status: string; message?: string}> {
  const res = await fetch(`${BASE_URL}/block-ip`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ ip })
  }).then(handleResponse);
  return res.json();
}

