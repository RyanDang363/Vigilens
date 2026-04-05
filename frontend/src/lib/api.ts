import axios from "axios";

function apiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    if (hostname === "127.0.0.1" || hostname === "localhost") {
      return `${protocol}//${hostname}:8000`;
    }
  }
  return "http://localhost:8000";
}

const api = axios.create({
  baseURL: apiBaseUrl(),
  headers: {
    "X-Role": "manager",
  },
});

export interface Employee {
  id: string;
  name: string;
  role: string;
  station: string;
  start_date: string;
  total_findings: number;
  total_reports: number;
  highest_severity: string;
}

export interface Finding {
  id: string;
  report_id: string;
  agent_source: string;
  concluded_type: string;
  finding_class: string;
  severity: string;
  policy_code: string;
  policy_section: string;
  policy_short_rule: string;
  policy_url: string;
  reasoning: string;
  training_recommendation: string;
  corrective_action_observed: boolean;
  timestamp_start: string;
  timestamp_end: string;
  clip_url: string;
}

export interface ActionLog {
  id: string;
  action_type: string;
  status: string;
  success: boolean;
  full_output: string;
  recording_url: string;
  created_at: string;
}

export interface Report {
  id: string;
  employee_id: string;
  clip_id: string;
  session_id: string;
  jurisdiction: string;
  created_at: string;
  code_backed_count: number;
  guidance_count: number;
  efficiency_count: number;
  highest_severity: string;
  findings: Finding[];
  action_logs: ActionLog[];
}

export interface ReportSummary {
  id: string;
  clip_id: string;
  created_at: string;
  highest_severity: string;
  code_backed_count: number;
  guidance_count: number;
  efficiency_count: number;
  total_findings: number;
}

export interface TrainingChunk {
  id: string;
  chunk_index: number;
  heading: string;
  text: string;
  word_count: number;
  tags: string[];
  metadata: Record<string, unknown>;
}

export interface WorkspaceTrainingRule {
  rule_id: string;
  category: string;
  rule_text: string;
  expected_behavior: string;
  bad_examples: string;
  severity_hint: string;
  source_section: string;
  active_version: boolean;
}

export interface TrainingSourceSummary {
  id: string;
  source_type: "upload" | "google_doc";
  title: string;
  mime_type: string;
  tags: string[];
  workspace_id: string;
  version: number;
  status: "uploaded" | "parsed" | "approved" | "indexed";
  active_version: boolean;
  created_at: string;
  last_indexed_at: string | null;
  rule_count: number;
  chunk_count: number;
}

export interface TrainingSource extends TrainingSourceSummary {
  owner_manager_id: string;
  raw_text: string;
  updated_at: string | null;
  google_file_id: string;
  source_url: string;
  chunks: TrainingChunk[];
  rules: WorkspaceTrainingRule[];
}

export async function fetchEmployees(): Promise<Employee[]> {
  const { data } = await api.get("/api/employees");
  return data;
}

export async function fetchEmployee(id: string): Promise<Employee> {
  const { data } = await api.get(`/api/employees/${id}`);
  return data;
}

export interface EmployeeCreatePayload {
  id: string;
  name: string;
  role?: string;
  station?: string;
  start_date?: string;
}

export async function createEmployee(
  payload: EmployeeCreatePayload
): Promise<Employee> {
  const { data } = await api.post("/api/employees", {
    id: payload.id.trim(),
    name: payload.name.trim(),
    role: payload.role?.trim() ?? "",
    station: payload.station?.trim() ?? "",
    start_date: payload.start_date?.trim() ?? "",
  });
  return data;
}

export async function deleteEmployee(employeeId: string): Promise<void> {
  const id = employeeId.trim();
  if (!id) {
    throw new Error("Employee id is required to remove an employee.");
  }
  const enc = encodeURIComponent(id);
  // POST avoids "405 Method Not Allowed" when DELETE hits /api/employees with a dropped id,
  // and works on networks that block DELETE.
  await api.post(`/api/employees/${enc}/delete`);
}

export async function fetchEmployeeReports(
  employeeId: string
): Promise<ReportSummary[]> {
  const { data } = await api.get(`/api/employees/${employeeId}/reports`);
  return data;
}

export async function fetchReport(reportId: string): Promise<Report> {
  const { data } = await api.get(`/api/reports/${reportId}`);
  return data;
}

export async function fetchTrainingSources(): Promise<TrainingSourceSummary[]> {
  const { data } = await api.get("/api/training");
  return data;
}

export async function fetchTrashedTrainingSources(): Promise<TrainingSourceSummary[]> {
  const { data } = await api.get("/api/training/trash");
  return data;
}

export async function fetchTrainingSource(id: string): Promise<TrainingSource> {
  const { data } = await api.get(`/api/training/${id}`);
  return data;
}

export async function uploadTrainingFile(file: File): Promise<TrainingSource> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/api/training/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return data.source;
}

export async function trashTrainingSource(id: string): Promise<void> {
  await api.post(`/api/training/${id}/trash`);
}

export async function restoreTrainingSource(id: string): Promise<void> {
  await api.post(`/api/training/${id}/restore`);
}

export function getTrainingSourceFileUrl(id: string): string {
  return `${api.defaults.baseURL}/api/training/${id}/file`;
}

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => item?.msg || JSON.stringify(item))
        .join(", ");
    }
    return error.message || "Request failed.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong.";
}
export interface FindingWithEmployee extends Finding {
  employee_name: string;
  employee_id: string;
  employee_role: string;
}

export async function fetchAllFindings(): Promise<FindingWithEmployee[]> {
  const { data } = await api.get("/api/findings");
  return data;
}

/** Response from POST /api/analyze (TwelveLabs + orchestrator pipeline). */
export interface AnalyzeVideoResponse {
  status: string;
  asset_id: string;
  total_detections: number;
  health_events: number;
  efficiency_events: number;
  detections: Array<{
    type: string;
    timestamp_start: number;
    timestamp_end: number;
    description: string;
  }>;
  orchestrator: {
    session_id?: string;
    status?: string;
    health_event_count?: number;
    efficiency_event_count?: number;
    health_findings?: number;
    efficiency_findings?: number;
    highest_severity?: string;
    report_id?: string;
  } | null;
}

/**
 * Upload a station video for an employee. Runs TwelveLabs, then the health +
 * efficiency agents via the orchestrator, and persists a report to the dashboard.
 * Can take several minutes; uses an extended timeout.
 */
export async function analyzeEmployeeVideo(
  employeeId: string,
  file: File
): Promise<AnalyzeVideoResponse> {
  const formData = new FormData();
  formData.append("video", file);
  formData.append("employee_id", employeeId);

  const { data } = await api.post<AnalyzeVideoResponse>(
    "/api/analyze",
    formData,
    {
      timeout: 600_000,
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
    }
  );
  return data;
}

// --- Google OAuth + Sheets ---

export interface GoogleStatus {
  connected: boolean;
  email?: string;
  sheet_id?: string;
  sheet_url?: string;
}

export async function fetchGoogleStatus(): Promise<GoogleStatus> {
  const { data } = await api.get("/api/google/status");
  return data;
}

export async function getGoogleLoginUrl(): Promise<string> {
  const { data } = await api.get("/api/google/login");
  return data.auth_url;
}

export async function createGoogleSheet(): Promise<{
  sheet_id: string;
  sheet_url: string;
}> {
  const { data } = await api.post("/api/google/create-sheet");
  return data;
}

export async function logFindingsToSheet(
  reportId: string
): Promise<{ rows_appended: number; sheet_url: string }> {
  const { data } = await api.post(
    `/api/google/log-findings?report_id=${reportId}`
  );
  return data;
}
