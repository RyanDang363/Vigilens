import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
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
  status: string;
  finding_class: string;
  severity: string;
  policy_code: string;
  policy_section: string;
  policy_short_rule: string;
  policy_url: string;
  evidence_confidence: number;
  reasoning: string;
  training_recommendation: string;
  corrective_action_observed: boolean;
  timestamp_start: string;
  timestamp_end: string;
  clip_url: string;
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
