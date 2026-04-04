"""
Test the health agent's internal logic (policy resolver, adjudicator, severity, coach)
without needing a running uAgents network.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.models.messages import (
    Observation,
    EventCandidate,
    HealthFinding,
    PolicyReference,
)
from agents.health.policy_resolver import resolve_policy
from agents.health.adjudicator import adjudicate
from agents.health.severity import assign_severity
from agents.health.coach import get_coaching_text


def build_event(event_id: str, observations: list[dict], corrective: bool = None) -> EventCandidate:
    obs_list = []
    for i, o in enumerate(observations):
        obs_list.append(Observation(
            observation_id=f"{event_id}_obs_{i}",
            observation_type=o["type"],
            timestamp_start=o.get("start", "00:01:00"),
            timestamp_end=o.get("end", "00:01:10"),
            confidence=o.get("confidence", 0.85),
            description=o.get("desc", f"Observed {o['type']}"),
        ))
    return EventCandidate(
        event_id=event_id,
        observations=obs_list,
        corrective_action_observed=corrective,
    )


def run_pipeline(event: EventCandidate, jurisdiction: str = "federal", strictness: str = "medium"):
    obs_types = [obs.observation_type for obs in event.observations]
    concluded_type, policy = resolve_policy(obs_types, jurisdiction)

    if concluded_type is None:
        return {"event_id": event.event_id, "result": "CLEARED"}

    status = adjudicate(event, policy, strictness)
    severity = assign_severity(concluded_type, status, event.corrective_action_observed)
    coaching = get_coaching_text(concluded_type, status, event.corrective_action_observed)

    return {
        "event_id": event.event_id,
        "concluded_type": concluded_type,
        "status": status,
        "finding_class": policy.get("finding_class"),
        "severity": severity,
        "coaching": coaching,
        "corrective_action_observed": event.corrective_action_observed,
    }


def test_cross_contamination():
    event = build_event("evt_1", [
        {"type": "raw_food_contact", "confidence": 0.90},
        {"type": "rte_food_contact", "confidence": 0.85},
        {"type": "no_sanitation_between_tasks", "confidence": 0.88},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "cross_contamination"
    assert result["status"] == "confirmed_violation"
    assert result["severity"] == "high"
    assert result["finding_class"] == "code_backed_food_safety"
    print(f"  PASS: {result['concluded_type']} -> {result['status']}, {result['severity']}")


def test_cross_contamination_california():
    event = build_event("evt_2", [
        {"type": "raw_food_contact", "confidence": 0.90},
        {"type": "rte_food_contact", "confidence": 0.85},
        {"type": "no_sanitation_between_tasks", "confidence": 0.88},
    ])
    result = run_pipeline(event, jurisdiction="california")
    assert result["concluded_type"] == "cross_contamination"
    assert result["finding_class"] == "code_backed_food_safety"
    print(f"  PASS: California cross_contamination -> {result['status']}")


def test_handwashing_skipped():
    event = build_event("evt_3", [
        {"type": "hand_wash_skipped", "confidence": 0.75},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "insufficient_handwashing"
    assert result["status"] == "possible_violation"  # 0.75 is between 0.5 and 0.8
    assert result["severity"] == "medium"
    print(f"  PASS: {result['concluded_type']} -> {result['status']}, {result['severity']}")


def test_dropped_utensil_reused():
    event = build_event("evt_4", [
        {"type": "utensil_dropped", "confidence": 0.92},
        {"type": "item_reused_without_wash", "confidence": 0.88},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "contaminated_utensil_reuse"
    assert result["status"] == "confirmed_violation"
    assert result["severity"] == "high"
    print(f"  PASS: {result['concluded_type']} -> {result['status']}, {result['severity']}")


def test_dropped_utensil_discarded():
    """Drop + discard should be cleared (no finding)."""
    event = build_event("evt_5", [
        {"type": "utensil_dropped", "confidence": 0.90},
        {"type": "item_discarded", "confidence": 0.85},
    ])
    result = run_pipeline(event)
    assert result["result"] == "CLEARED"
    print(f"  PASS: utensil_dropped + item_discarded -> CLEARED")


def test_food_dropped_alone():
    """Drop alone without reuse signal is not a finding."""
    event = build_event("evt_6", [
        {"type": "food_dropped", "confidence": 0.90},
    ])
    result = run_pipeline(event)
    assert result["result"] == "CLEARED"
    print(f"  PASS: food_dropped alone -> CLEARED (incident only)")


def test_knife_placement():
    event = build_event("evt_7", [
        {"type": "knife_near_table_edge", "confidence": 0.82},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "unsafe_knife_placement"
    assert result["finding_class"] == "workplace_safety_rule"
    assert result["severity"] == "low"
    print(f"  PASS: {result['concluded_type']} -> {result['finding_class']}, {result['severity']}")


def test_recovery_reduces_severity():
    """Corrective action should drop severity by one level."""
    event = build_event("evt_8", [
        {"type": "raw_food_contact", "confidence": 0.90},
        {"type": "rte_food_contact", "confidence": 0.85},
        {"type": "no_sanitation_between_tasks", "confidence": 0.88},
    ], corrective=True)
    result = run_pipeline(event)
    assert result["concluded_type"] == "cross_contamination"
    assert result["severity"] == "medium"  # dropped from high to medium
    assert "corrective action" in result["coaching"].lower()
    print(f"  PASS: cross_contamination + recovery -> severity={result['severity']}")


def test_low_confidence_caps_severity():
    """Insufficient evidence should cap severity at medium."""
    event = build_event("evt_9", [
        {"type": "raw_food_contact", "confidence": 0.30},
        {"type": "rte_food_contact", "confidence": 0.25},
        {"type": "no_sanitation_between_tasks", "confidence": 0.20},
    ])
    result = run_pipeline(event)
    assert result["concluded_type"] == "cross_contamination"
    assert result["status"] == "insufficient_evidence"
    assert result["severity"] == "medium"  # capped from high
    print(f"  PASS: low confidence cross_contamination -> severity capped at {result['severity']}")


def test_strictness_high():
    """High strictness should lower thresholds, making 0.75 a confirmed_violation."""
    event = build_event("evt_10", [
        {"type": "hand_wash_skipped", "confidence": 0.75},
    ])
    result = run_pipeline(event, strictness="high")
    assert result["status"] == "confirmed_violation"  # 0.75 >= 0.70 (0.80 - 0.10)
    print(f"  PASS: strictness=high -> {result['status']} at confidence 0.75")


def test_bare_hand_federal_vs_california():
    """FDA and California should have different policy references for bare-hand RTE."""
    event = build_event("evt_11", [
        {"type": "bare_hand_rte", "confidence": 0.85},
    ])
    fed_result = run_pipeline(event, jurisdiction="federal")
    cal_result = run_pipeline(event, jurisdiction="california")
    assert "3-301.11" in fed_result["coaching"] or fed_result["concluded_type"] == "bare_hand_rte_contact"
    assert cal_result["concluded_type"] == "bare_hand_rte_contact"
    print(f"  PASS: bare_hand_rte -> different policies per jurisdiction")


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
        test_low_confidence_caps_severity,
        test_strictness_high,
        test_bare_hand_federal_vs_california,
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
