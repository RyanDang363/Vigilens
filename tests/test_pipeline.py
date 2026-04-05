"""
Send a test OrchestratorRequest to the running orchestrator agent.
This simulates what the video pipeline would do after analyzing a clip.

Prerequisites: all agents running (health, efficiency, orchestrator, backend API).

Usage:
    python -m tests.test_pipeline
"""

from uagents import Agent, Context
from backend.agents.models.config import ORCHESTRATOR_SEED
from uagents_core.identity import Identity
from backend.agents.models.messages import (
    OrchestratorRequest,
    EventCandidate,
    Observation,
)
from uagents_core.contrib.protocols.chat import ChatMessage, TextContent

ORCHESTRATOR_ADDRESS = Identity.from_seed(seed=ORCHESTRATOR_SEED, index=0).address

# Local endpoint for the orchestrator (port 8004)
ORCHESTRATOR_ENDPOINT = "http://127.0.0.1:8004"

test_agent = Agent(
    name="test_trigger",
    seed="test-trigger-throwaway-seed-12345",
    port=8099,
    endpoint=["http://127.0.0.1:8099/submit"],
)


@test_agent.on_event("startup")
async def send_test(ctx: Context):
    ctx.logger.info(f"Sending test request to orchestrator at {ORCHESTRATOR_ENDPOINT}")

    request = OrchestratorRequest(
        clip_id="test_clip_001",
        employee_id="emp_1",
        employee_name="Maria Garcia",
        employee_email="evanbnguyen@gmail.com",
        manager_email="",
        jurisdiction="california",
        health_events=[
            EventCandidate(
                event_id="test_h1",
                observations=[
                    Observation(
                        observation_id="o1",
                        observation_type="cross_contamination",
                        timestamp_start="00:01:42",
                        timestamp_end="00:01:52",
                        description="Worker handled raw chicken then touched lettuce prep area without washing hands",
                    ),
                ],
                corrective_action_observed=False,
            ),
            EventCandidate(
                event_id="test_h2",
                observations=[
                    Observation(
                        observation_id="o2",
                        observation_type="knife_near_table_edge",
                        timestamp_start="00:04:10",
                        timestamp_end="00:04:15",
                        description="Knife placed at edge of prep table",
                    ),
                ],
                corrective_action_observed=False,
            ),
        ],
        efficiency_events=[
            EventCandidate(
                event_id="test_e1",
                observations=[
                    Observation(
                        observation_id="o3",
                        observation_type="phone_usage",
                        timestamp_start="00:02:00",
                        timestamp_end="00:02:25",
                        description="Worker texting on phone during prep",
                    ),
                ],
            ),
        ],
        actions=["send_email"],
    )

    await ctx.send(ORCHESTRATOR_ADDRESS, request)
    ctx.logger.info("Request sent! Watch the orchestrator logs for the pipeline.")


@test_agent.on_message(ChatMessage)
async def handle_response(ctx: Context, sender: str, msg: ChatMessage):
    text = " ".join(item.text for item in msg.content if isinstance(item, TextContent))
    ctx.logger.info(f"\n{'='*60}\nORCHESTRATOR RESPONSE:\n{'='*60}\n{text}\n{'='*60}")


if __name__ == "__main__":
    test_agent.run()
