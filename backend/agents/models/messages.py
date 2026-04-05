from uagents import Model
from typing import Optional


class Observation(Model):
    """A single thing the vision pipeline observed. These are raw evidence,
    not conclusions. The Health Agent combines observations into findings."""

    observation_id: str
    observation_type: str  # evidence-level label (see AGENTS.md for full list)
    timestamp_start: str  # "HH:MM:SS"
    timestamp_end: str
    description: str  # natural language from TwelveLabs


class EventCandidate(Model):
    """A group of related observations that may constitute a finding."""

    event_id: str
    observations: list[Observation]
    corrective_action_observed: Optional[bool] = None
    corrective_action_description: Optional[str] = None


class HealthEvalRequest(Model):
    """Sent by the orchestrator to the Health Agent."""

    chat_session_id: str
    clip_id: str
    employee_id: str
    station_id: Optional[str] = None
    jurisdiction: str = "federal"  # "federal" | "california" | "custom"
    event_candidates: list[EventCandidate]
    user_sender_address: str  # for routing response back


class PolicyReference(Model):
    source_tier: str  # "fda" | "calcode" | "osha" | "house_rule"
    code: str  # e.g. "FDA Food Code 2022"
    section: str  # e.g. "3-302.11"
    short_rule: str  # human-readable summary


class HealthFinding(Model):
    event_id: str
    concluded_type: str  # the Health Agent's conclusion (e.g. "cross_contamination")
    finding_class: str  # code_backed_food_safety | workplace_safety_rule | house_rule
    severity: str  # low | medium | high | critical
    corrective_action_observed: bool
    corrective_action_adequate: Optional[bool] = None
    policy_reference: PolicyReference
    assumptions: list[str]
    reasoning: str
    training_recommendation: str
    timestamp_start: str
    timestamp_end: str


class HealthEvalResponse(Model):
    """Sent by the Health Agent back to the orchestrator."""

    chat_session_id: str
    clip_id: str
    employee_id: str
    jurisdiction: str
    findings: list[HealthFinding]
    code_backed_count: int
    guidance_count: int
    highest_severity: str


class EfficiencyEvalRequest(Model):
    """Sent by the orchestrator to the Efficiency Agent."""

    chat_session_id: str
    clip_id: str
    employee_id: str
    station_id: Optional[str] = None
    event_candidates: list[EventCandidate]
    user_sender_address: str  # for routing response back


class EfficiencyReference(Model):
    source_tier: str  # "workflow_standard" | "house_rule"
    code: str  # e.g. "Internal Workflow Coaching Guide"
    section: str  # e.g. "phone_usage"
    short_rule: str  # human-readable summary


class EfficiencyFinding(Model):
    event_id: str
    concluded_type: str  # e.g. "phone_usage"
    finding_class: str  # workflow_efficiency | focus_behavior | coaching_note
    severity: str  # low | medium | high
    duration_seconds: float
    repeated_behavior_observed: bool
    reference: EfficiencyReference
    assumptions: list[str]
    reasoning: str
    coaching_recommendation: str
    timestamp_start: str
    timestamp_end: str


class EfficiencyEvalResponse(Model):
    """Sent by the Efficiency Agent back to the orchestrator."""

    chat_session_id: str
    clip_id: str
    employee_id: str
    findings: list[EfficiencyFinding]
    confirmed_issue_count: int
    coaching_opportunity_count: int
    highest_severity: str


# ---------------------------------------------------------------------------
# Browser Agent models
# ---------------------------------------------------------------------------

class BrowserActionRequest(Model):
    """Sent by the orchestrator to the Browser Agent."""

    chat_session_id: str
    action_type: str  # "send_email" | "log_sheet" | "get_training_docs" | "research_violations"
    employee_name: str
    employee_email: Optional[str] = None
    manager_email: Optional[str] = None
    report_summary: str  # formatted text summary of findings
    findings_data: list[dict]  # raw finding dicts for sheet logging
    report_id: Optional[str] = None  # for Sheets API logging
    sheet_url: Optional[str] = None  # Google Sheets URL
    training_doc_url: Optional[str] = None


class BrowserActionResponse(Model):
    """Sent back to the orchestrator by the Browser Agent."""

    chat_session_id: str
    action_type: str
    success: bool
    message: str  # human-readable result or error
    recording_url: Optional[str] = None  # MP4 of the browser session


# ---------------------------------------------------------------------------
# Orchestrator models
# ---------------------------------------------------------------------------

class OrchestratorRequest(Model):
    """Trigger the orchestrator to evaluate a clip for an employee.
    Typically sent via REST or chat, contains the raw observations from
    the video pipeline."""

    clip_id: str
    employee_id: str
    employee_name: str
    employee_email: Optional[str] = None
    manager_email: Optional[str] = None
    station_id: Optional[str] = None
    jurisdiction: str = "federal"
    health_events: list[EventCandidate] = []
    efficiency_events: list[EventCandidate] = []
    sheet_url: Optional[str] = None
    training_doc_url: Optional[str] = None
    actions: list[str] = []  # e.g. ["send_email", "log_sheet"]
