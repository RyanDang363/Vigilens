import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
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

export interface FindingWithEmployee extends Finding {
  employee_name: string;
  employee_id: string;
  employee_role: string;
}

export async function fetchAllFindings(): Promise<FindingWithEmployee[]> {
  const { data } = await api.get("/api/findings");
  return data;
}
