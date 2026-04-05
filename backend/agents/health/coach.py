"""
Coach Writer — deterministic coaching templates keyed by concluded_type.

v1: Pure template lookup. Fast, stable, no API dependency.
"""

from __future__ import annotations

COACHING_TEMPLATES: dict[str, str] = {
    "cross_contamination": (
        "Sanitize the food-contact surface and wash hands before switching "
        "from raw to ready-to-eat items."
    ),
    "insufficient_handwashing": (
        "Wash hands thoroughly for at least 20 seconds before handling food, "
        "after touching your face, and when switching tasks."
    ),
    "glove_misuse": (
        "Change gloves when switching tasks, after contamination, or when "
        "they become damaged. One pair per task."
    ),
    "bare_hand_rte_contact": (
        "Use utensils, deli tissue, or gloves when handling ready-to-eat food. "
        "Bare-hand contact should be avoided."
    ),
    "contaminated_utensil_reuse": (
        "A dropped or contaminated utensil must be washed and sanitized "
        "before reuse. Never reuse without cleaning."
    ),
    "contaminated_food_reuse": (
        "Food that has contacted the floor or a contaminated surface must be "
        "discarded. It should never be served to customers."
    ),
    "unsafe_knife_handling": (
        "Never point or direct a knife toward another person. Carry knives "
        "at your side with the blade pointed down."
    ),
    "unsafe_knife_placement": (
        "Place knives flat and away from the edge of the prep surface when "
        "not actively cutting."
    ),
}

RECOVERY_ADDENDUM = (
    " Good corrective action was observed — focus on preventing the initial "
    "lapse next time."
)


def get_coaching_text(
    concluded_type: str,
    corrective_action_observed: bool | None = None,
) -> str:
    """Look up coaching text by finding type.

    Args:
        concluded_type: The finding type concluded by the policy resolver.
        corrective_action_observed: Whether recovery was seen on video.

    Returns:
        A coaching recommendation string.
    """
    base = COACHING_TEMPLATES.get(
        concluded_type,
        "Review workplace procedures and ensure proper safety practices.",
    )

    if corrective_action_observed:
        base += RECOVERY_ADDENDUM

    return base
