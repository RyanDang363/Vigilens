"""
Resolver for workflow-efficiency observations.

The video pipeline sends event candidates with evidence-level observation types.
This module maps them to an efficiency conclusion and a coaching-oriented
reference for downstream reporting.
"""

from __future__ import annotations


OBSERVATION_PATTERNS: list[tuple[frozenset[str], str]] = [
    (frozenset({"phone_usage"}), "phone_usage"),
    (frozenset({"extended_chatting"}), "extended_chatting"),
    (frozenset({"idle_at_station"}), "idle_at_station"),
    (frozenset({"slow_task_execution"}), "slow_task_execution"),
    (frozenset({"extended_task_interruption"}), "extended_task_interruption"),
    (frozenset({"unnecessary_movement"}), "unnecessary_movement"),
    (frozenset({"off_task_behavior"}), "off_task_behavior"),
]


POLICY_DB: dict[str, dict] = {
    "phone_usage": {
        "finding_class": "focus_behavior",
        "reference": {
            "source_tier": "workflow_standard",
            "code": "Internal Workflow Coaching Guide",
            "section": "phone_usage",
            "short_rule": (
                "Personal phone use should not interrupt active prep or service."
            ),
        },
        "reasoning_template": (
            "{observation_label} {obs_types} suggest attention shifted away from active work "
            "for a sustained period."
        ),
        "assumptions": [],
    },
    "extended_chatting": {
        "finding_class": "workflow_efficiency",
        "reference": {
            "source_tier": "workflow_standard",
            "code": "Internal Workflow Coaching Guide",
            "section": "extended_chatting",
            "short_rule": (
                "Brief coordination is normal, but extended social conversation "
                "should not pause prep flow."
            ),
        },
        "reasoning_template": (
            "{observation_label} {obs_types} suggest conversation paused task flow longer "
            "than a normal work check-in."
        ),
        "assumptions": ["conversation content could not be verified from video alone"],
    },
    "idle_at_station": {
        "finding_class": "workflow_efficiency",
        "reference": {
            "source_tier": "workflow_standard",
            "code": "Internal Workflow Coaching Guide",
            "section": "idle_at_station",
            "short_rule": (
                "Extended idle time at an active station is a coaching opportunity "
                "when work appears available."
            ),
        },
        "reasoning_template": (
            "{observation_label} {obs_types} suggest sustained idle time at the station "
            "while the task remained unfinished."
        ),
        "assumptions": ["no hidden dependency blocked the worker during the pause"],
    },
    "slow_task_execution": {
        "finding_class": "workflow_efficiency",
        "reference": {
            "source_tier": "workflow_standard",
            "code": "Internal Workflow Coaching Guide",
            "section": "slow_task_execution",
            "short_rule": (
                "Repeatedly slow task pace can indicate a coaching opportunity "
                "around technique or station setup."
            ),
        },
        "reasoning_template": (
            "{observation_label} {obs_types} suggest task pace was slower than expected "
            "for a meaningful span."
        ),
        "assumptions": ["worker was trained on the task being observed"],
    },
    "extended_task_interruption": {
        "finding_class": "workflow_efficiency",
        "reference": {
            "source_tier": "workflow_standard",
            "code": "Internal Workflow Coaching Guide",
            "section": "extended_task_interruption",
            "short_rule": (
                "Once prep has started, extended interruptions should be minimized "
                "unless operationally necessary."
            ),
        },
        "reasoning_template": (
            "{observation_label} {obs_types} suggest the task was paused long enough to "
            "materially interrupt workflow."
        ),
        "assumptions": ["the interruption was not required by a manager or customer need"],
    },
    "unnecessary_movement": {
        "finding_class": "workflow_efficiency",
        "reference": {
            "source_tier": "workflow_standard",
            "code": "Internal Workflow Coaching Guide",
            "section": "unnecessary_movement",
            "short_rule": (
                "Extra back-and-forth movement should be reduced when station layout "
                "or prep sequencing can be improved."
            ),
        },
        "reasoning_template": (
            "{observation_label} {obs_types} suggest avoidable movement added time without "
            "advancing the task."
        ),
        "assumptions": ["needed tools or ingredients were expected to be nearby"],
    },
    "off_task_behavior": {
        "finding_class": "focus_behavior",
        "reference": {
            "source_tier": "workflow_standard",
            "code": "Internal Workflow Coaching Guide",
            "section": "off_task_behavior",
            "short_rule": (
                "Off-task behavior should not pull attention away from active work "
                "for sustained periods."
            ),
        },
        "reasoning_template": (
            "{observation_label} {obs_types} suggest attention shifted to non-work activity "
            "during active prep time."
        ),
        "assumptions": [],
    },
}


UNKNOWN_POLICY: dict = {
    "finding_class": "coaching_note",
    "reference": {
        "source_tier": "house_rule",
        "code": "Internal Workflow Coaching Guide",
        "section": "unclassified",
        "short_rule": "Observation did not match a known efficiency pattern.",
    },
    "reasoning_template": (
        "{observation_label} {obs_types} did not match a known efficiency pattern."
    ),
    "assumptions": ["manual review recommended"],
}


def resolve_efficiency_policy(obs_types: list[str]) -> tuple[str, dict]:
    """Resolve an observation bundle to an efficiency finding and reference."""
    obs_set = set(obs_types)

    for pattern, concluded_type in OBSERVATION_PATTERNS:
        if pattern.issubset(obs_set):
            return concluded_type, POLICY_DB[concluded_type]

    return "unclassified", UNKNOWN_POLICY
