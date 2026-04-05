"""Pydantic schemas for API request/response serialization."""

from pydantic import BaseModel
from datetime import datetime


# --- Findings ---

class FindingCreate(BaseModel):
    concluded_type: str
    status: str
    finding_class: str
    severity: str
    agent_source: str = "health"
    policy_code: str = ""
    policy_section: str = ""
    policy_short_rule: str = ""
    policy_url: str = ""
    evidence_confidence: float = 0.0
    reasoning: str = ""
    training_recommendation: str = ""
    corrective_action_observed: bool = False
    timestamp_start: str = ""
    timestamp_end: str = ""
    clip_url: str = ""


class FindingOut(FindingCreate):
    id: str
    report_id: str

    class Config:
        from_attributes = True


# --- Reports ---

class ReportCreate(BaseModel):
    employee_id: str
    clip_id: str = ""
    session_id: str = ""
    jurisdiction: str = "federal"
    code_backed_count: int = 0
    guidance_count: int = 0
    efficiency_count: int = 0
    highest_severity: str = "low"
    findings: list[FindingCreate] = []


class ReportOut(BaseModel):
    id: str
    employee_id: str
    clip_id: str
    session_id: str
    jurisdiction: str
    created_at: datetime | None
    code_backed_count: int
    guidance_count: int
    efficiency_count: int
    highest_severity: str
    findings: list[FindingOut] = []

    class Config:
        from_attributes = True


class ReportSummary(BaseModel):
    id: str
    clip_id: str
    created_at: datetime | None
    highest_severity: str
    code_backed_count: int
    guidance_count: int
    efficiency_count: int
    total_findings: int

    class Config:
        from_attributes = True


# --- Employees ---

class EmployeeCreate(BaseModel):
    id: str
    name: str
    role: str = ""
    station: str = ""
    start_date: str = ""


class EmployeeOut(BaseModel):
    id: str
    name: str
    role: str
    station: str
    start_date: str
    total_findings: int = 0
    total_reports: int = 0
    highest_severity: str = "low"

    class Config:
        from_attributes = True
