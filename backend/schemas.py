"""Pydantic schemas for API request/response serialization."""

from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, PlainSerializer


def _serialize_utc_datetime(value: datetime | None) -> str | None:
    """Emit UTC ISO-8601 with Z so clients (e.g. JavaScript Date) parse as UTC, not local wall time."""
    if value is None:
        return None
    if value.tzinfo is None:
        u = value.replace(tzinfo=timezone.utc)
    else:
        u = value.astimezone(timezone.utc)
    return u.isoformat().replace("+00:00", "Z")


# Naive DB datetimes are stored as UTC (SQLite CURRENT_TIMESTAMP). JSON must include Z.
UtcDateTime = Annotated[
    datetime | None,
    PlainSerializer(_serialize_utc_datetime, when_used="json"),
]


# --- Findings ---

class FindingCreate(BaseModel):
    concluded_type: str
    finding_class: str
    severity: str
    agent_source: str = "health"
    policy_code: str = ""
    policy_section: str = ""
    policy_short_rule: str = ""
    policy_url: str = ""
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


class ActionLogOut(BaseModel):
    id: str
    action_type: str
    status: str = "in_progress"
    success: bool
    full_output: str = ""
    recording_url: str | None = ""
    created_at: UtcDateTime = None

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    id: str
    employee_id: str
    clip_id: str
    session_id: str
    jurisdiction: str
    created_at: UtcDateTime
    code_backed_count: int
    guidance_count: int
    efficiency_count: int
    highest_severity: str
    findings: list[FindingOut] = []
    action_logs: list[ActionLogOut] = []

    class Config:
        from_attributes = True


class ReportSummary(BaseModel):
    id: str
    clip_id: str
    created_at: UtcDateTime
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
    email: str = ""
    role: str = ""
    station: str = ""
    start_date: str = ""


class EmployeeOut(BaseModel):
    id: str
    name: str
    email: str = ""
    role: str
    station: str
    start_date: str
    total_findings: int = 0
    total_reports: int = 0
    highest_severity: str = "low"

    class Config:
        from_attributes = True


# --- Training ---


class TrainingSourceBase(BaseModel):
    id: str
    source_type: str
    title: str
    mime_type: str
    owner_manager_id: str
    workspace_id: str
    raw_text: str
    tags: list[str] = []
    version: int
    status: str
    active_version: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime
    last_indexed_at: UtcDateTime = None
    google_file_id: str = ""
    source_url: str = ""


class TrainingSourceOut(TrainingSourceBase):
    chunks: list[dict] = []
    rules: list[dict] = []


class TrainingSourceSummary(BaseModel):
    id: str
    source_type: str
    title: str
    mime_type: str
    tags: list[str] = []
    workspace_id: str
    version: int
    status: str
    active_version: bool
    created_at: UtcDateTime
    last_indexed_at: UtcDateTime = None


class TrainingUploadResponse(BaseModel):
    source: TrainingSourceOut
    message: str
