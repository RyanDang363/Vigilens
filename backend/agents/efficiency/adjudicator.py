"""
Adjudicator for workflow-efficiency event candidates.

The agent is intentionally conservative. Brief pauses and quick check-ins
should not be flagged. Duration thresholds gate whether an observation
warrants a finding.
"""

from __future__ import annotations

from datetime import datetime

from backend.agents.models.messages import EventCandidate

MIN_DURATION_SECONDS: dict[str, float] = {
    "phone_usage": 6.0,
    "extended_chatting": 15.0,
    "idle_at_station": 12.0,
    "slow_task_execution": 20.0,
    "extended_task_interruption": 15.0,
    "unnecessary_movement": 15.0,
    "off_task_behavior": 8.0,
    "unclassified": 20.0,
}


def _parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%H:%M:%S")


def calculate_duration_seconds(event: EventCandidate) -> float:
    """Estimate total event duration from the event span and observation spans."""
    if not event.observations:
        return 0.0

    starts = [_parse_timestamp(obs.timestamp_start) for obs in event.observations]
    ends = [_parse_timestamp(obs.timestamp_end) for obs in event.observations]
    event_span = max((max(ends) - min(starts)).total_seconds(), 0.0)
    observed_total = sum(
        max((end - start).total_seconds(), 0.0)
        for start, end in zip(starts, ends)
    )
    return max(event_span, observed_total)


def should_flag(
    event: EventCandidate,
    concluded_type: str,
) -> bool:
    """Decide whether an efficiency event warrants a finding based on duration.

    Returns True if the event duration exceeds the minimum threshold for its type.
    """
    if concluded_type == "unclassified":
        return False

    duration_seconds = calculate_duration_seconds(event)
    repetition_bonus = min(max(len(event.observations) - 1, 0) * 5.0, 10.0)
    effective_duration = duration_seconds + repetition_bonus

    min_duration = MIN_DURATION_SECONDS.get(concluded_type, 15.0)
    return effective_duration >= min_duration
