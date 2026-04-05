"""Deterministic coaching templates for workflow-efficiency findings."""

from __future__ import annotations

COACHING_TEMPLATES: dict[str, dict[str, str]] = {
    "phone_usage": {
        "confirmed_issue": (
            "Keep personal phone use off the station during active prep so task flow "
            "stays uninterrupted."
        ),
        "possible_issue": (
            "Phone use may have interrupted active work. A good habit is to finish "
            "the step in progress before checking a device."
        ),
        "insufficient_evidence": (
            "We could not clearly confirm whether device use interrupted work. As a "
            "reminder, keep attention on the station during active prep."
        ),
        "not_an_issue": (
            "No coaching needed here. The pause looks brief enough to fall within "
            "normal workflow variation."
        ),
    },
    "extended_chatting": {
        "confirmed_issue": (
            "Keep station conversation task-focused during active prep and save longer "
            "social chats for natural breaks."
        ),
        "possible_issue": (
            "Conversation may have run long enough to slow the line. Brief check-ins "
            "are fine, but return to the task quickly."
        ),
        "insufficient_evidence": (
            "The video does not make it clear whether this was task-related. As a "
            "reminder, keep active-prep conversations short and purposeful."
        ),
        "not_an_issue": (
            "No coaching needed here. This looks consistent with a normal brief "
            "coordination exchange."
        ),
    },
    "idle_at_station": {
        "confirmed_issue": (
            "If work is available, re-engage the next prep step promptly so the station "
            "does not stall."
        ),
        "possible_issue": (
            "There may have been extra idle time at the station. Resetting the next "
            "step earlier can help keep flow moving."
        ),
        "insufficient_evidence": (
            "We could not confirm whether something external blocked progress. As a "
            "reminder, use natural pauses to stage the next step when possible."
        ),
        "not_an_issue": (
            "No coaching needed here. The pause appears short enough to be routine."
        ),
    },
    "slow_task_execution": {
        "confirmed_issue": (
            "Task pace looked consistently slower than expected. Coaching around "
            "technique or station setup could help improve throughput."
        ),
        "possible_issue": (
            "Task pace may have been slower than expected. A quick technique review or "
            "better mise en place may help."
        ),
        "insufficient_evidence": (
            "We could not clearly compare pace against the task context. As a reminder, "
            "prep speed should stay steady without sacrificing quality."
        ),
        "not_an_issue": (
            "No coaching needed here. The pace appears within normal variation."
        ),
    },
    "extended_task_interruption": {
        "confirmed_issue": (
            "Try to complete or hand off active prep before stepping away so the task "
            "does not sit interrupted."
        ),
        "possible_issue": (
            "The task may have been paused longer than needed. Re-entering the workflow "
            "sooner can help reduce delays."
        ),
        "insufficient_evidence": (
            "It is unclear whether the interruption was operationally necessary. As a "
            "reminder, minimize extended breaks in active prep flow."
        ),
        "not_an_issue": (
            "No coaching needed here. The interruption appears brief or routine."
        ),
    },
    "unnecessary_movement": {
        "confirmed_issue": (
            "Extra movement added time without helping the task. Staging tools and "
            "ingredients up front can tighten the workflow."
        ),
        "possible_issue": (
            "There may have been avoidable back-and-forth movement. A small station "
            "setup adjustment could make the task smoother."
        ),
        "insufficient_evidence": (
            "We could not tell whether the movement was necessary. As a reminder, "
            "keeping needed items close helps reduce wasted motion."
        ),
        "not_an_issue": (
            "No coaching needed here. The movement does not appear substantial enough "
            "to affect workflow."
        ),
    },
    "off_task_behavior": {
        "confirmed_issue": (
            "Attention appeared to shift away from work long enough to affect flow. "
            "Refocusing on the active task sooner would help throughput."
        ),
        "possible_issue": (
            "There may have been off-task behavior during active prep. Returning to "
            "the station sooner can help keep the workflow on pace."
        ),
        "insufficient_evidence": (
            "We could not clearly determine whether this behavior was work-related. "
            "As a reminder, active prep time should stay focused on the task."
        ),
        "not_an_issue": (
            "No coaching needed here. The behavior appears too brief or ambiguous to "
            "treat as a workflow issue."
        ),
    },
    "unclassified": {
        "insufficient_evidence": (
            "This event needs manual review before any coaching recommendation is made."
        ),
        "not_an_issue": "No coaching needed here.",
    },
}


def get_efficiency_coaching_text(concluded_type: str, status: str) -> str:
    templates = COACHING_TEMPLATES.get(concluded_type, {})
    return templates.get(
        status,
        "Review workflow expectations and reinforce the next-step habit during prep.",
    )
