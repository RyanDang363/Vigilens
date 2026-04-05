"""Helpers for observation wording in agent reasoning strings."""

from __future__ import annotations


def format_reasoning_from_template(template: str, obs_types: list[str]) -> str:
    """
    Choose singular/plural "Observation(s)" from unique types, not raw row count.
    Deduplicate types for display when there is only one distinct observation type.
    """
    cleaned = [t for t in obs_types if t]
    unique = list(dict.fromkeys(cleaned))
    if len(unique) == 1:
        label = "Observation"
        types_for_str = [unique[0]]
    else:
        label = "Observations"
        types_for_str = cleaned
    return template.format(observation_label=label, obs_types=types_for_str)
