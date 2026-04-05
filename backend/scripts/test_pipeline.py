#!/usr/bin/env python3
"""
Test the full TwelveLabs -> Agent pipeline end-to-end.

Usage:
    # From the project root, with the backend venv activated:
    python -m backend.scripts.test_pipeline backend/videos/YOUR_VIDEO.mov emp_1

    # With optional flags:
    python -m backend.scripts.test_pipeline backend/videos/clip.mov emp_1 --jurisdiction california --strictness high

    # Skip TwelveLabs (use mock detections for testing agent wiring):
    python -m backend.scripts.test_pipeline --mock emp_1
"""

import argparse
import json
import logging
import sys

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ORCHESTRATOR_URL = "http://localhost:8004"

HEALTH_OBSERVATION_TYPES = {
    "food_dropped", "utensil_dropped", "hand_wash_short", "hand_wash_skipped",
    "knife_pointed_at_person", "knife_near_table_edge", "cross_contamination",
    "hand_to_face", "bare_hand_rte", "glove_not_changed",
}

EFFICIENCY_OBSERVATION_TYPES = {
    "phone_usage", "extended_chatting", "slow_task_execution",
    "idle_at_station", "off_task_behavior",
}

MOCK_DETECTIONS = [
    {"type": "cross_contamination", "timestamp_start": 12.0, "timestamp_end": 18.5,
     "description": "Worker handled raw chicken then touched lettuce without washing hands."},
    {"type": "knife_near_table_edge", "timestamp_start": 42.0, "timestamp_end": 48.0,
     "description": "Knife placed at the edge of the prep table."},
    {"type": "phone_usage", "timestamp_start": 60.0, "timestamp_end": 82.0,
     "description": "Worker texting on phone while prep station is active."},
]


def secs_to_hms(s: float) -> str:
    m, sec = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def build_events(detections: list[dict]) -> tuple[list[dict], list[dict]]:
    health_events = []
    efficiency_events = []

    for i, det in enumerate(detections):
        obs = {
            "observation_id": f"obs_{i}",
            "observation_type": det["type"],
            "timestamp_start": secs_to_hms(det["timestamp_start"]),
            "timestamp_end": secs_to_hms(det["timestamp_end"]),
            "description": det["description"],
        }
        event = {"event_id": f"evt_{i}", "observations": [obs]}

        if det["type"] in HEALTH_OBSERVATION_TYPES:
            health_events.append(event)
        elif det["type"] in EFFICIENCY_OBSERVATION_TYPES:
            efficiency_events.append(event)
        else:
            logger.warning("Unknown type: %s — routing to health", det["type"])
            health_events.append(event)

    return health_events, efficiency_events


def run_twelvelabs(video_path: str) -> list[dict]:
    from backend.services.twelvelabs_service import run_detection_pipeline
    result = run_detection_pipeline(video_path)
    return [
        {
            "type": d.type,
            "timestamp_start": d.timestamp_start,
            "timestamp_end": d.timestamp_end,
            "description": d.description,
        }
        for d in result.detections
    ]


def submit_to_orchestrator(payload: dict) -> dict | None:
    try:
        resp = httpx.post(
            f"{ORCHESTRATOR_URL}/api/analyze", json=payload, timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json()
        logger.error("Orchestrator returned %d: %s", resp.status_code, resp.text)
    except httpx.ConnectError:
        logger.error("Cannot reach orchestrator at %s — is it running?", ORCHESTRATOR_URL)
    return None


def main():
    parser = argparse.ArgumentParser(description="Test the full analysis pipeline")
    parser.add_argument("video_path", nargs="?", help="Path to video file")
    parser.add_argument("employee_id", help="Employee ID (e.g. emp_1)")
    parser.add_argument("--mock", action="store_true", help="Use mock detections instead of TwelveLabs")
    parser.add_argument("--jurisdiction", default="federal")
    parser.add_argument("--strictness", default="medium")
    args = parser.parse_args()

    if args.mock:
        logger.info("Using mock detections (skipping TwelveLabs)")
        detections = MOCK_DETECTIONS
    else:
        if not args.video_path:
            parser.error("video_path is required when not using --mock")
        logger.info("Running TwelveLabs detection on %s ...", args.video_path)
        detections = run_twelvelabs(args.video_path)

    print("\n=== Pegasus Detections ===")
    print(json.dumps(detections, indent=2))

    health_events, efficiency_events = build_events(detections)

    print(f"\n=== Event Routing ===")
    print(f"  Health events:     {len(health_events)}")
    print(f"  Efficiency events: {len(efficiency_events)}")

    print("\n=== Health Events (agent format) ===")
    print(json.dumps(health_events, indent=2))

    print("\n=== Efficiency Events (agent format) ===")
    print(json.dumps(efficiency_events, indent=2))

    payload = {
        "clip_id": "test_clip",
        "employee_id": args.employee_id,
        "employee_name": "Test Employee",
        "jurisdiction": args.jurisdiction,
        "strictness": args.strictness,
        "health_events": health_events,
        "efficiency_events": efficiency_events,
        "actions": [],
    }

    print("\n=== Submitting to Orchestrator ===")
    result = submit_to_orchestrator(payload)
    if result:
        print(json.dumps(result, indent=2))
        print("\nPipeline submitted. The orchestrator will fan out to agents")
        print("and POST the report to http://localhost:8000/api/reports when done.")
    else:
        print("Failed to submit to orchestrator.")
        sys.exit(1)


if __name__ == "__main__":
    main()
