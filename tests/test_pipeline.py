"""
Test the full orchestrator pipeline via REST.

Prerequisites: all agents running (health on 8001, efficiency on 8002,
browser on 8003, orchestrator on 8004, backend on 8000).

Usage:
    python -m tests.test_pipeline              # email only (default)
    python -m tests.test_pipeline all           # all 4 actions
    python -m tests.test_pipeline sheet         # sheet only
    python -m tests.test_pipeline research      # web research only
    python -m tests.test_pipeline email,sheet   # comma-separated combo
"""

import asyncio
import json
import sys

import httpx
from dotenv import load_dotenv
load_dotenv()


ORCHESTRATOR_URL = "http://localhost:8004"

# --- Test event data ---


PAYLOAD = {
    "clip_id": "test_clip_001",
    "employee_id": "emp_1",
    "employee_name": "Maria Garcia",
    "employee_email": "evanbnguyen@gmail.com",
    "manager_email": "",
    "jurisdiction": "california",
    "strictness": "medium",
    "health_events": [
        {
            "event_id": "test_h1",
            "observations": [
                {
                    "observation_id": "o1",
                    "observation_type": "cross_contamination",
                    "timestamp_start": "00:01:42",
                    "timestamp_end": "00:01:52",
                    "description": "Worker handled raw chicken then touched lettuce prep area without washing hands",
                },
            ],
            "corrective_action_observed": False,
        },
        {
            "event_id": "test_h2",
            "observations": [
                {
                    "observation_id": "o2",
                    "observation_type": "knife_near_table_edge",
                    "timestamp_start": "00:04:10",
                    "timestamp_end": "00:04:15",
                    "description": "Knife placed at edge of prep table",
                },
            ],
            "corrective_action_observed": False,
        },
        {
            "event_id": "test_h3",
            "observations": [
                {
                    "observation_id": "o3",
                    "observation_type": "brief_hand_rinse",
                    "timestamp_start": "00:06:30",
                    "timestamp_end": "00:06:38",
                    "description": "Worker rinsed hands for about 8 seconds without soap before returning to prep",
                },
            ],
            "corrective_action_observed": False,
        },
    ],
    "efficiency_events": [
        {
            "event_id": "test_e1",
            "observations": [
                {
                    "observation_id": "o4",
                    "observation_type": "phone_usage",
                    "timestamp_start": "00:02:00",
                    "timestamp_end": "00:02:25",
                    "description": "Worker texting on phone during prep",
                },
            ],
        },
        {
            "event_id": "test_e2",
            "observations": [
                {
                    "observation_id": "o5",
                    "observation_type": "extended_chatting",
                    "timestamp_start": "00:08:00",
                    "timestamp_end": "00:08:45",
                    "description": "Worker chatting with coworker for 45 seconds while food sits on prep surface",
                },
            ],
        },
    ],
    "actions": [],
}


def get_actions() -> list[str]:
    arg = sys.argv[1] if len(sys.argv) > 1 else "email"
    if arg == "all":
        return ["send_email", "log_sheet", "get_training_docs", "research_violations"]
    if arg == "email":
        return ["send_email"]
    if arg == "sheet":
        return ["log_sheet"]
    if arg == "training":
        return ["get_training_docs"]
    if arg == "research":
        return ["research_violations"]
    return [a.strip() for a in arg.split(",")]


async def main():
    actions = get_actions()
    PAYLOAD["actions"] = actions

    print(f"Sending pipeline request to orchestrator at {ORCHESTRATOR_URL}")
    print(f"Actions: {actions}")
    print(f"Health events: {len(PAYLOAD['health_events'])}")
    print(f"Efficiency events: {len(PAYLOAD['efficiency_events'])}")
    print()

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{ORCHESTRATOR_URL}/api/analyze",
            json=PAYLOAD,
        )

    print(f"Status: {resp.status_code}")
    print()

    if resp.status_code == 200:
        data = resp.json()
        print("Pipeline Results:")
        print(f"  Session ID:          {data.get('session_id')}")
        print(f"  Status:              {data.get('status')}")
        print(f"  Health findings:     {data.get('health_findings')}")
        print(f"  Efficiency findings: {data.get('efficiency_findings')}")
        print(f"  Highest severity:    {data.get('highest_severity')}")
        print(f"  Report ID:           {data.get('report_id')}")
    else:
        print(f"Error: {resp.text}")


if __name__ == "__main__":
    asyncio.run(main())
