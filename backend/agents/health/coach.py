"""
Coach Writer — deterministic coaching templates keyed by concluded_type + status.

v1: Pure template lookup. Fast, stable, no API dependency.
v2: Optionally pass template output to an LLM for context-specific polish.
"""

from __future__ import annotations

COACHING_TEMPLATES: dict[str, dict[str, str]] = {
    "cross_contamination": {
        "confirmed_violation": (
            "Sanitize the food-contact surface and wash hands before switching "
            "from raw to ready-to-eat items."
        ),
        "possible_violation": (
            "It appears the prep area may not have been sanitized between raw "
            "and ready-to-eat handling. Always sanitize when switching tasks."
        ),
        "insufficient_evidence": (
            "We couldn't clearly confirm what happened here. As a reminder, "
            "always sanitize surfaces between raw and ready-to-eat tasks."
        ),
    },
    "insufficient_handwashing": {
        "confirmed_violation": (
            "Wash hands thoroughly for at least 20 seconds before handling food, "
            "after touching your face, and when switching tasks."
        ),
        "possible_violation": (
            "Handwashing appeared shorter than expected. Take the full 20 seconds, "
            "especially before food contact."
        ),
        "insufficient_evidence": (
            "As a reminder, thorough handwashing is required before food contact "
            "and after any contamination risk."
        ),
    },
    "glove_misuse": {
        "confirmed_violation": (
            "Change gloves when switching tasks, after contamination, or when "
            "they become damaged. One pair per task."
        ),
        "possible_violation": (
            "Gloves may not have been changed between tasks. Always swap gloves "
            "when switching from one food type to another."
        ),
        "insufficient_evidence": (
            "As a reminder, single-use gloves should be discarded between tasks "
            "and after any contamination event."
        ),
    },
    "bare_hand_rte_contact": {
        "confirmed_violation": (
            "Use utensils, deli tissue, or gloves when handling ready-to-eat food. "
            "Bare-hand contact should be avoided."
        ),
        "possible_violation": (
            "It appears ready-to-eat food may have been contacted with bare hands. "
            "Use utensils or gloves as a standard practice."
        ),
        "insufficient_evidence": (
            "As a reminder, minimize bare-hand contact with ready-to-eat food "
            "and use appropriate utensils or gloves."
        ),
    },
    "contaminated_utensil_reuse": {
        "confirmed_violation": (
            "A dropped or contaminated utensil must be washed and sanitized "
            "before reuse. Never reuse without cleaning."
        ),
        "possible_violation": (
            "A utensil may have been reused after contamination without proper "
            "washing. Always wash and sanitize before reuse."
        ),
        "insufficient_evidence": (
            "As a reminder, any utensil that contacts the floor or a contaminated "
            "surface must be cleaned and sanitized before reuse."
        ),
    },
    "contaminated_food_reuse": {
        "confirmed_violation": (
            "Food that has contacted the floor or a contaminated surface must be "
            "discarded. It should never be served to customers."
        ),
        "possible_violation": (
            "Food may have been reused after contacting a contaminated surface. "
            "When in doubt, always discard."
        ),
        "insufficient_evidence": (
            "As a reminder, food that contacts the floor or any unclean surface "
            "should be discarded immediately."
        ),
    },
    "unsafe_knife_handling": {
        "confirmed_violation": (
            "Never point or direct a knife toward another person. Carry knives "
            "at your side with the blade pointed down."
        ),
        "possible_violation": (
            "A knife appeared to be directed toward another worker. Always keep "
            "blades pointed away from others."
        ),
        "insufficient_evidence": (
            "As a reminder, always carry knives with the blade pointed down and "
            "away from other workers."
        ),
    },
    "unsafe_knife_placement": {
        "confirmed_violation": (
            "Place knives flat and away from the edge of the prep surface when "
            "not actively cutting."
        ),
        "possible_violation": (
            "A knife appeared to be near the edge of the prep table. Keep knives "
            "centered and flat on the surface."
        ),
        "insufficient_evidence": (
            "As a reminder, store knives flat and well back from the table edge "
            "to prevent falls."
        ),
    },
}

RECOVERY_ADDENDUM = (
    " Good corrective action was observed — focus on preventing the initial "
    "lapse next time."
)


def get_coaching_text(
    concluded_type: str,
    status: str,
    corrective_action_observed: bool | None = None,
) -> str:
    """Look up coaching text by finding type and status.

    Args:
        concluded_type: The finding type concluded by the policy resolver.
        status: The adjudicated status.
        corrective_action_observed: Whether recovery was seen on video.

    Returns:
        A coaching recommendation string.
    """
    templates = COACHING_TEMPLATES.get(concluded_type, {})
    base = templates.get(
        status,
        f"Review workplace procedures and ensure proper safety practices.",
    )

    if corrective_action_observed:
        base += RECOVERY_ADDENDUM

    return base
