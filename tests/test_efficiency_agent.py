"""
Test the efficiency agent's internal logic without needing a running uAgents network.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.agents.efficiency.adjudicator import (  # noqa: E402
    should_flag,
    calculate_duration_seconds,
)
from backend.agents.efficiency.coach import get_efficiency_coaching_text  # noqa: E402
from backend.agents.efficiency.resolver import resolve_efficiency_policy  # noqa: E402
from backend.agents.efficiency.severity import assign_efficiency_severity  # noqa: E402
from backend.agents.models.messages import EventCandidate, Observation  # noqa: E402


def build_event(event_id: str, observations: list[dict]) -> EventCandidate:
    obs_list = []
    for i, observation in enumerate(observations):
        obs_list.append(Observation(
            observation_id=f"{event_id}_obs_{i}",
            observation_type=observation["type"],
            timestamp_start=observation.get("start", "00:01:00"),
            timestamp_end=observation.get("end", "00:01:10"),
            description=observation.get("desc", f"Observed {observation['type']}"),
        ))

    return EventCandidate(
        event_id=event_id,
        observations=obs_list,
    )


def run_pipeline(event: EventCandidate) -> dict:
    obs_types = [obs.observation_type for obs in event.observations]
    concluded_type, policy = resolve_efficiency_policy(obs_types)

    if not should_flag(event, concluded_type):
        return {
            "event_id": event.event_id,
            "concluded_type": concluded_type,
            "flagged": False,
        }

    duration_seconds = calculate_duration_seconds(event)
    repeated_behavior_observed = len(event.observations) > 1
    severity = assign_efficiency_severity(
        concluded_type,
        duration_seconds,
        repeated_behavior_observed,
    )
    coaching = get_efficiency_coaching_text(concluded_type)

    return {
        "event_id": event.event_id,
        "concluded_type": concluded_type,
        "flagged": True,
        "finding_class": policy.get("finding_class"),
        "severity": severity,
        "duration_seconds": duration_seconds,
        "coaching": coaching,
    }


def test_brief_phone_usage_not_flagged():
    event = build_event("eff_1", [
        {"type": "phone_usage", "start": "00:00:00", "end": "00:00:02"},
    ])
    result = run_pipeline(event)
    assert not result["flagged"]
    print("  PASS: brief phone usage -> not flagged")


def test_sustained_phone_usage_flagged():
    event = build_event("eff_2", [
        {"type": "phone_usage", "start": "00:00:00", "end": "00:00:20"},
    ])
    result = run_pipeline(event)
    assert result["flagged"]
    assert result["severity"] == "medium"
    print("  PASS: sustained phone usage -> flagged, medium severity")


def test_extended_chatting_repeated():
    event = build_event("eff_3", [
        {"type": "extended_chatting", "start": "00:00:00", "end": "00:00:22"},
        {"type": "extended_chatting", "start": "00:00:25", "end": "00:00:43"},
    ])
    result = run_pipeline(event)
    assert result["flagged"]
    assert result["severity"] == "high"
    print("  PASS: repeated extended chatting -> flagged, high severity (raised by repetition)")


def test_short_idle_not_flagged():
    event = build_event("eff_4", [
        {"type": "idle_at_station", "start": "00:00:00", "end": "00:00:05"},
    ])
    result = run_pipeline(event)
    assert not result["flagged"]
    print("  PASS: short idle_at_station -> not flagged")


def test_slow_task_short_not_flagged():
    event = build_event("eff_5", [
        {"type": "slow_task_execution", "start": "00:00:00", "end": "00:00:12"},
    ])
    result = run_pipeline(event)
    assert not result["flagged"]
    print("  PASS: short slow_task_execution -> not flagged")


def test_off_task_behavior_long_and_repeated():
    event = build_event("eff_6", [
        {"type": "off_task_behavior", "start": "00:00:00", "end": "00:00:35"},
        {"type": "off_task_behavior", "start": "00:00:40", "end": "00:01:10"},
    ])
    result = run_pipeline(event)
    assert result["flagged"]
    assert result["severity"] == "high"
    print("  PASS: repeated off_task_behavior -> flagged, high severity")


def test_sustained_idle_flagged():
    event = build_event("eff_7", [
        {"type": "idle_at_station", "start": "00:00:00", "end": "00:00:30"},
    ])
    result = run_pipeline(event)
    assert result["flagged"]
    assert result["severity"] == "low"
    print("  PASS: sustained idle_at_station -> flagged, low severity")


if __name__ == "__main__":
    tests = [
        test_brief_phone_usage_not_flagged,
        test_sustained_phone_usage_flagged,
        test_extended_chatting_repeated,
        test_short_idle_not_flagged,
        test_slow_task_short_not_flagged,
        test_off_task_behavior_long_and_repeated,
        test_sustained_idle_flagged,
    ]

    print(f"\nRunning {len(tests)} efficiency agent tests...\n")
    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as exc:
            print(f"  FAIL: {test.__name__} - {exc}")
            failed += 1
        except Exception as exc:
            print(f"  ERROR: {test.__name__} - {type(exc).__name__}: {exc}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed out of {len(tests)}")
