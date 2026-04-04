"""
Adjudicator — decides the status of a finding based on evidence confidence.

Statuses:
    confirmed_violation  — high confidence, clearly matches a policy rule
    possible_violation   — medium confidence, or evidence is partial
    insufficient_evidence — low confidence, or critical context missing
    cleared              — observation pattern does not match any violation

Recovery does NOT auto-clear a finding. It is tracked separately and affects
severity and coaching tone, but the finding still exists in the report.
"""

from __future__ import annotations

from agents.models.messages import EventCandidate

# Base confidence thresholds
CONFIRMED_THRESHOLD = 0.80
POSSIBLE_THRESHOLD = 0.50

# Strictness offsets
STRICTNESS_OFFSETS = {
    "high": -0.10,   # more aggressive flagging
    "medium": 0.0,
    "low": 0.10,     # more lenient
}


def adjudicate(
    event: EventCandidate,
    policy: dict,
    strictness: str = "medium",
) -> str:
    """Determine the status of a finding based on observation confidence.

    Args:
        event: The EventCandidate containing observations.
        policy: The resolved policy dict (empty dict means cleared by resolver).
        strictness: "low" | "medium" | "high" — shifts confidence thresholds.

    Returns:
        One of: "confirmed_violation", "possible_violation",
                "insufficient_evidence", "cleared"
    """
    # If the resolver already cleared this (e.g. drop + discard), respect that
    if not policy:
        return "cleared"

    # Average confidence across all observations in the event
    confidences = [obs.confidence for obs in event.observations]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Apply strictness offset
    offset = STRICTNESS_OFFSETS.get(strictness, 0.0)
    confirmed_thresh = CONFIRMED_THRESHOLD + offset
    possible_thresh = POSSIBLE_THRESHOLD + offset

    if avg_confidence >= confirmed_thresh:
        return "confirmed_violation"
    elif avg_confidence >= possible_thresh:
        return "possible_violation"
    else:
        return "insufficient_evidence"
