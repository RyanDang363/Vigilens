"""
Severity Engine — flat rules table with one modifier for recovery.

Default severity per finding type. Recovery drops it one level.
"""

from __future__ import annotations

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]

DEFAULT_SEVERITY: dict[str, str] = {
    "cross_contamination": "high",
    "insufficient_handwashing": "medium",
    "glove_misuse": "medium",
    "bare_hand_rte_contact": "medium",
    "contaminated_utensil_reuse": "high",
    "contaminated_food_reuse": "critical",
    "unsafe_knife_handling": "medium",
    "unsafe_knife_placement": "low",
    "unclassified": "low",
}


def _drop_one_level(severity: str) -> str:
    idx = SEVERITY_LEVELS.index(severity)
    return SEVERITY_LEVELS[max(0, idx - 1)]


def assign_severity(
    concluded_type: str,
    corrective_action_observed: bool | None,
) -> str:
    """Assign severity based on finding type and recovery.

    Rules:
        1. Start with the default for the finding type.
        2. If corrective action was observed, drop one level.
    """
    severity = DEFAULT_SEVERITY.get(concluded_type, "low")

    if corrective_action_observed:
        severity = _drop_one_level(severity)

    return severity
