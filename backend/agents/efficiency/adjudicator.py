"""
Adjudicator for workflow-efficiency event candidates.

The agent is intentionally conservative. Brief pauses, quick check-ins, or
low-confidence observations should fall to not_an_issue or
insufficient_evidence rather than being over-flagged.
"""

from __future__ import annotations

from datetime import datetime

from backend.agents.models.messages import EventCandidate

CONFIRMED_CONFIDENCE = 0.80
POSSIBLE_CONFIDENCE = 0.55

STRICTNESS_OFFSETS = {
    "high": -0.10,
    "medium": 0.0,
    "low": 0.10,
}

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

POSSIBLE_DURATION_SECONDS: dict[str, float] = {
    "phone_usage": 10.0,
    "extended_chatting": 25.0,
    "idle_at_station": 20.0,
    "slow_task_execution": 30.0,
    "extended_task_interruption": 20.0,
    "unnecessary_movement": 20.0,
    "off_task_behavior": 15.0,
    "unclassified": 25.0,
}

CONFIRMED_DURATION_SECONDS: dict[str, float] = {
    "phone_usage": 18.0,
    "extended_chatting": 40.0,
    "idle_at_station": 35.0,
    "slow_task_execution": 45.0,
    "extended_task_interruption": 35.0,
    "unnecessary_movement": 30.0,
    "off_task_behavior": 25.0,
    "unclassified": 40.0,
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


def adjudicate_efficiency(
    event: EventCandidate,
    concluded_type: str,
    strictness: str = "medium",
) -> str:
    """Classify a workflow event into issue/not-issue buckets."""
    if concluded_type == "unclassified":
        return "insufficient_evidence"

    confidences = [obs.confidence for obs in event.observations]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    observation_count = len(event.observations)
    duration_seconds = calculate_duration_seconds(event)

    offset = STRICTNESS_OFFSETS.get(strictness, 0.0)
    confirmed_confidence = CONFIRMED_CONFIDENCE + offset
    possible_confidence = POSSIBLE_CONFIDENCE + offset

    repetition_bonus = min(max(observation_count - 1, 0) * 5.0, 10.0)
    effective_duration = duration_seconds + repetition_bonus

    min_duration = MIN_DURATION_SECONDS.get(concluded_type, 15.0)
    possible_duration = POSSIBLE_DURATION_SECONDS.get(concluded_type, 20.0)
    confirmed_duration = CONFIRMED_DURATION_SECONDS.get(concluded_type, 35.0)

    if effective_duration < min_duration:
        return "not_an_issue"
    if avg_confidence < possible_confidence:
        return "insufficient_evidence"
    if (
        avg_confidence >= confirmed_confidence
        and effective_duration >= confirmed_duration
    ):
        return "confirmed_issue"
    if effective_duration >= possible_duration:
        return "possible_issue"
    return "not_an_issue"
