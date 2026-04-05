from uagents import Model
from typing import Optional


class Observation(Model):
    """A single thing the vision pipeline observed. These are raw evidence,
    not conclusions. The Health Agent combines observations into findings."""

    observation_id: str
    observation_type: str  # evidence-level label (see AGENTS.md for full list)
    timestamp_start: str  # "HH:MM:SS"
    timestamp_end: str
    confidence: float  # 0.0-1.0 from vision pipeline
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
    strictness: str = "medium"  # "low" | "medium" | "high"
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
    status: str  # confirmed_violation | possible_violation | insufficient_evidence | cleared
    finding_class: str  # code_backed_food_safety | workplace_safety_rule | house_rule
    severity: str  # low | medium | high | critical
    corrective_action_observed: bool
    corrective_action_adequate: Optional[bool] = None
    policy_reference: PolicyReference
    evidence_confidence: float
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
    strictness: str = "medium"  # "low" | "medium" | "high"
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
    status: str  # confirmed_issue | possible_issue | insufficient_evidence | not_an_issue
    finding_class: str  # workflow_efficiency | focus_behavior | coaching_note
    severity: str  # low | medium | high
    duration_seconds: float
    repeated_behavior_observed: bool
    evidence_confidence: float
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
