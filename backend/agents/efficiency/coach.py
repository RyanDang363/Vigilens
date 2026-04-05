"""Deterministic coaching templates for workflow-efficiency findings."""

from __future__ import annotations

COACHING_TEMPLATES: dict[str, str] = {
    "phone_usage": (
        "Keep personal phone use off the station during active prep so task flow "
        "stays uninterrupted."
    ),
    "extended_chatting": (
        "Keep station conversation task-focused during active prep and save longer "
        "social chats for natural breaks."
    ),
    "idle_at_station": (
        "If work is available, re-engage the next prep step promptly so the station "
        "does not stall."
    ),
    "slow_task_execution": (
        "Task pace looked consistently slower than expected. Coaching around "
        "technique or station setup could help improve throughput."
    ),
    "extended_task_interruption": (
        "Try to complete or hand off active prep before stepping away so the task "
        "does not sit interrupted."
    ),
    "unnecessary_movement": (
        "Extra movement added time without helping the task. Staging tools and "
        "ingredients up front can tighten the workflow."
    ),
    "off_task_behavior": (
        "Attention appeared to shift away from work long enough to affect flow. "
        "Refocusing on the active task sooner would help throughput."
    ),
    "unclassified": (
        "This event needs manual review before any coaching recommendation is made."
    ),
}


def get_efficiency_coaching_text(concluded_type: str) -> str:
    return COACHING_TEMPLATES.get(
        concluded_type,
        "Review workflow expectations and reinforce the next-step habit during prep.",
    )
