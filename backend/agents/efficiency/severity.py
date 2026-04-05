"""Severity rules for workflow-efficiency findings."""

from __future__ import annotations

SEVERITY_LEVELS = ["low", "medium", "high"]

DEFAULT_SEVERITY: dict[str, str] = {
    "phone_usage": "medium",
    "extended_chatting": "medium",
    "idle_at_station": "low",
    "slow_task_execution": "low",
    "extended_task_interruption": "medium",
    "unnecessary_movement": "low",
    "off_task_behavior": "medium",
    "unclassified": "low",
}


def _raise_one_level(severity: str) -> str:
    idx = SEVERITY_LEVELS.index(severity)
    return SEVERITY_LEVELS[min(len(SEVERITY_LEVELS) - 1, idx + 1)]


def assign_efficiency_severity(
    concluded_type: str,
    duration_seconds: float,
    repeated_behavior_observed: bool,
) -> str:
    """Assign severity using duration and repetition."""
    severity = DEFAULT_SEVERITY.get(concluded_type, "low")

    if repeated_behavior_observed:
        severity = _raise_one_level(severity)

    if duration_seconds >= 60:
        severity = _raise_one_level(severity)

    return severity
