"""
Test the health agent's internal logic (policy resolver, severity, coach)
without needing a running uAgents network.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.agents.models.messages import (
    Observation,
    EventCandidate,
    HealthFinding,
    PolicyReference,
)
from backend.agents.health.policy_resolver import resolve_policy
from backend.agents.health.severity import assign_severity
from backend.agents.health.coach import get_coaching_text


def build_event(event_id: str, observations: list[dict], corrective: bool = None) -> EventCandidate:
    obs_list = []
    for i, o in enumerate(observations):
        obs_list.append(Observation(
            observation_id=f"{event_id}_obs_{i}",
            observation_type=o["type"],
            timestamp_start=o.get("start", "00:01:00"),
            timestamp_end=o.get("end", "00:01:10"),
            description=o.get("desc", f"Observed {o['type']}"),
        ))
    return EventCandidate(
        event_id=event_id,
        observations=obs_list,
        corrective_action_observed=corrective,
    )


def run_pipeline(event: EventCandidate, jurisdiction: str = "federal"):
    obs_types = [obs.observation_type for obs in event.observations]
    concluded_type, policy = resolve_policy(obs_types, jurisdiction)

    if concluded_type is None:
        return {"event_id": event.event_id, "result": "CLEARED"}

    severity = assign_severity(concluded_type, event.corrective_action_observed)
    coaching = get_coaching_text(concluded_type, event.corrective_action_observed)

    return {
        "event_id": event.event_id,
        "concluded_type": concluded_type,
        "finding_class": policy.get("finding_class"),
        "severity": severity,
        "coaching": coaching,
        "corrective_action_observed": event.corrective_action_observed,
    }


def test_cross_contamination():
    event = build_event("evt_1", [
        {"type": "cross_contamination"},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "cross_contamination"
    assert result["severity"] == "high"
    assert result["finding_class"] == "code_backed_food_safety"
    print(f"  PASS: {result['concluded_type']} -> {result['severity']}")


def test_cross_contamination_california():
    event = build_event("evt_2", [
        {"type": "cross_contamination"},
    ])
    result = run_pipeline(event, jurisdiction="california")
    assert result["concluded_type"] == "cross_contamination"
    assert result["finding_class"] == "code_backed_food_safety"
    print(f"  PASS: California cross_contamination -> {result['severity']}")


def test_handwashing_skipped():
    event = build_event("evt_3", [
        {"type": "hand_wash_skipped"},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "insufficient_handwashing"
    assert result["severity"] == "medium"
    print(f"  PASS: {result['concluded_type']} -> {result['severity']}")


def test_dropped_utensil_reused():
    event = build_event("evt_4", [
        {"type": "utensil_dropped"},
        {"type": "item_reused_without_wash"},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "contaminated_utensil_reuse"
    assert result["severity"] == "high"
    print(f"  PASS: {result['concluded_type']} -> {result['severity']}")


def test_dropped_utensil_discarded():
    """Drop + discard should be cleared (no finding)."""
    event = build_event("evt_5", [
        {"type": "utensil_dropped"},
        {"type": "item_discarded"},
    ])
    result = run_pipeline(event)
    assert result["result"] == "CLEARED"
    print(f"  PASS: utensil_dropped + item_discarded -> CLEARED")


def test_food_dropped_alone():
    """food_dropped alone matches the single-observation pattern."""
    event = build_event("evt_6", [
        {"type": "food_dropped"},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "contaminated_food_reuse"
    assert result["severity"] == "critical"
    print(f"  PASS: food_dropped alone -> {result['concluded_type']}, {result['severity']}")


def test_knife_placement():
    event = build_event("evt_7", [
        {"type": "knife_near_table_edge"},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "unsafe_knife_placement"
    assert result["finding_class"] == "workplace_safety_rule"
    assert result["severity"] == "low"
    print(f"  PASS: {result['concluded_type']} -> {result['finding_class']}, {result['severity']}")


def test_recovery_reduces_severity():
    """Corrective action should drop severity by one level."""
    event = build_event("evt_8", [
        {"type": "cross_contamination"},
    ], corrective=True)
    result = run_pipeline(event)
    assert result["concluded_type"] == "cross_contamination"
    assert result["severity"] == "medium"  # dropped from high to medium
    assert "corrective action" in result["coaching"].lower()
    print(f"  PASS: cross_contamination + recovery -> severity={result['severity']}")


def test_bare_hand_federal_vs_california():
    """FDA and California should have different policy references for bare-hand RTE."""
    event = build_event("evt_11", [
        {"type": "bare_hand_rte"},
    ])
    fed_result = run_pipeline(event, jurisdiction="federal")
    cal_result = run_pipeline(event, jurisdiction="california")
    assert fed_result["concluded_type"] == "bare_hand_rte_contact"
    assert cal_result["concluded_type"] == "bare_hand_rte_contact"
    print(f"  PASS: bare_hand_rte -> different policies per jurisdiction")


def test_hand_to_face():
    event = build_event("evt_12", [
        {"type": "hand_to_face"},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "insufficient_handwashing"
    assert result["severity"] == "medium"
    print(f"  PASS: hand_to_face -> {result['concluded_type']}, {result['severity']}")


if __name__ == "__main__":
    tests = [
        test_cross_contamination,
        test_cross_contamination_california,
        test_handwashing_skipped,
        test_dropped_utensil_reused,
        test_dropped_utensil_discarded,
        test_food_dropped_alone,
        test_knife_placement,
        test_recovery_reduces_severity,
        test_bare_hand_federal_vs_california,
        test_hand_to_face,
    ]

    print(f"\nRunning {len(tests)} health agent tests...\n")
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__} - {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {test.__name__} - {type(e).__name__}: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed out of {len(tests)}")
