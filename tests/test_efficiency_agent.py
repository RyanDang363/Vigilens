"""
Test the efficiency agent's internal logic without needing a running uAgents network.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.agents.efficiency.adjudicator import (  # noqa: E402
    adjudicate_efficiency,
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
            confidence=observation.get("confidence", 0.85),
            description=observation.get("desc", f"Observed {observation['type']}"),
        ))

    return EventCandidate(
        event_id=event_id,
        observations=obs_list,
    )


def run_pipeline(event: EventCandidate, strictness: str = "medium") -> dict:
    obs_types = [obs.observation_type for obs in event.observations]
    concluded_type, policy = resolve_efficiency_policy(obs_types)
    status = adjudicate_efficiency(event, concluded_type, strictness)
    duration_seconds = calculate_duration_seconds(event)
    repeated_behavior_observed = len(event.observations) > 1
    severity = assign_efficiency_severity(
        concluded_type,
        status,
        duration_seconds,
        repeated_behavior_observed,
    )
    coaching = get_efficiency_coaching_text(concluded_type, status)

    return {
        "event_id": event.event_id,
        "concluded_type": concluded_type,
        "status": status,
        "finding_class": policy.get("finding_class"),
        "severity": severity,
        "duration_seconds": duration_seconds,
        "coaching": coaching,
    }


def test_brief_phone_usage_is_not_issue():
    event = build_event("eff_1", [
        {"type": "phone_usage", "start": "00:00:00", "end": "00:00:02", "confidence": 0.96},
    ])
    result = run_pipeline(event)
    assert result["status"] == "not_an_issue"
    print("  PASS: brief phone usage -> not_an_issue")


def test_sustained_phone_usage_is_confirmed():
    event = build_event("eff_2", [
        {"type": "phone_usage", "start": "00:00:00", "end": "00:00:20", "confidence": 0.90},
    ])
    result = run_pipeline(event)
    assert result["status"] == "confirmed_issue"
    assert result["severity"] == "medium"
    print("  PASS: sustained phone usage -> confirmed_issue")


def test_extended_chatting_is_possible():
    event = build_event("eff_3", [
        {"type": "extended_chatting", "start": "00:00:00", "end": "00:00:22", "confidence": 0.74},
        {"type": "extended_chatting", "start": "00:00:25", "end": "00:00:43", "confidence": 0.70},
    ])
    result = run_pipeline(event)
    assert result["status"] == "possible_issue"
    assert result["severity"] == "high"
    print("  PASS: repeated extended chatting -> possible_issue with higher severity")


def test_low_confidence_idle_is_insufficient_evidence():
    event = build_event("eff_4", [
        {"type": "idle_at_station", "start": "00:00:00", "end": "00:00:30", "confidence": 0.42},
    ])
    result = run_pipeline(event)
    assert result["status"] == "insufficient_evidence"
    print("  PASS: low confidence idle_at_station -> insufficient_evidence")


def test_slow_task_execution_needs_meaningful_duration():
    event = build_event("eff_5", [
        {"type": "slow_task_execution", "start": "00:00:00", "end": "00:00:12", "confidence": 0.91},
    ])
    result = run_pipeline(event)
    assert result["status"] == "not_an_issue"
    print("  PASS: short slow_task_execution signal -> not_an_issue")


def test_off_task_behavior_can_be_high_severity():
    event = build_event("eff_6", [
        {"type": "off_task_behavior", "start": "00:00:00", "end": "00:00:35", "confidence": 0.93},
        {"type": "off_task_behavior", "start": "00:00:40", "end": "00:01:10", "confidence": 0.90},
    ])
    result = run_pipeline(event)
    assert result["status"] == "confirmed_issue"
    assert result["severity"] == "high"
    print("  PASS: repeated off_task_behavior -> confirmed_issue, high severity")


def test_high_strictness_can_promote_possible_issue():
    event = build_event("eff_7", [
        {"type": "extended_task_interruption", "start": "00:00:00", "end": "00:00:36", "confidence": 0.72},
    ])
    result = run_pipeline(event, strictness="high")
    assert result["status"] == "confirmed_issue"
    print("  PASS: strictness=high promotes extended_task_interruption to confirmed_issue")


if __name__ == "__main__":
    tests = [
        test_brief_phone_usage_is_not_issue,
        test_sustained_phone_usage_is_confirmed,
        test_extended_chatting_is_possible,
        test_low_confidence_idle_is_insufficient_evidence,
        test_slow_task_execution_needs_meaningful_duration,
        test_off_task_behavior_can_be_high_severity,
        test_high_strictness_can_promote_possible_issue,
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
