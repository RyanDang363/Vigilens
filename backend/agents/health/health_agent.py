"""
Health Agent — receives observation-based event candidates from the orchestrator,
adjudicates food safety and workplace safety findings, and returns structured
results with policy citations and coaching recommendations.

Also includes a chat protocol handler so the agent can respond in the
Agentverse chat inspector with a demo using mock data.

Follows the uAgents pattern from fetch-hackathon-quickstarter.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Agent, Context, Model, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from backend.agents.models.config import HEALTH_AGENT_SEED
from backend.agents.models.messages import (
    EventCandidate,
    HealthEvalRequest,
    HealthEvalResponse,
    HealthFinding,
    Observation,
    PolicyReference,
)
from backend.agents.health.policy_resolver import resolve_policy
from backend.agents.health.adjudicator import adjudicate
from backend.agents.health.severity import assign_severity, SEVERITY_LEVELS
from backend.agents.health.coach import get_coaching_text


health_agent = Agent(
    name="health_agent",
    seed=HEALTH_AGENT_SEED,
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)


# ---------------------------------------------------------------------------
# Core handler: structured HealthEvalRequest from orchestrator
# ---------------------------------------------------------------------------

def evaluate_events(event_candidates, jurisdiction, strictness):
    """Run the health pipeline on a list of EventCandidates. Returns findings list."""
    findings: list[HealthFinding] = []

    for event in event_candidates:
        obs_types = [obs.observation_type for obs in event.observations]
        concluded_type, policy = resolve_policy(obs_types, jurisdiction)

        if concluded_type is None:
            continue

        status = adjudicate(event, policy, strictness)
        severity = assign_severity(
            concluded_type, status, event.corrective_action_observed
        )
        recommendation = get_coaching_text(
            concluded_type, status, event.corrective_action_observed
        )

        avg_confidence = (
            sum(obs.confidence for obs in event.observations) / len(event.observations)
            if event.observations
            else 0.0
        )
        reasoning = policy.get("reasoning_template", "").format(obs_types=obs_types)
        ref = policy.get("reference", {})

        findings.append(HealthFinding(
            event_id=event.event_id,
            concluded_type=concluded_type,
            status=status,
            finding_class=policy.get("finding_class", "house_rule"),
            severity=severity,
            corrective_action_observed=event.corrective_action_observed or False,
            corrective_action_adequate=None,
            policy_reference=PolicyReference(
                source_tier=ref.get("source_tier", "house_rule"),
                code=ref.get("code", ""),
                section=ref.get("section", ""),
                short_rule=ref.get("short_rule", ""),
            ),
            evidence_confidence=round(avg_confidence, 3),
            assumptions=policy.get("assumptions", []),
            reasoning=reasoning,
            training_recommendation=recommendation,
            timestamp_start=event.observations[0].timestamp_start,
            timestamp_end=event.observations[-1].timestamp_end,
        ))

    return findings


@health_agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info(f"Health Agent started -> {health_agent.address}")


@health_agent.on_message(HealthEvalRequest)
async def handle_eval(ctx: Context, sender: str, msg: HealthEvalRequest):
    ctx.logger.info(
        f"Health eval for clip={msg.clip_id} employee={msg.employee_id} "
        f"jurisdiction={msg.jurisdiction} events={len(msg.event_candidates)}"
    )

    findings = evaluate_events(
        msg.event_candidates, msg.jurisdiction, msg.strictness
    )

    code_backed = sum(1 for f in findings if f.finding_class == "code_backed_food_safety")
    guidance = sum(1 for f in findings if f.finding_class != "code_backed_food_safety")
    highest = max(
        (f.severity for f in findings),
        key=lambda s: SEVERITY_LEVELS.index(s),
        default="low",
    )

    response = HealthEvalResponse(
        chat_session_id=msg.chat_session_id,
        clip_id=msg.clip_id,
        employee_id=msg.employee_id,
        jurisdiction=msg.jurisdiction,
        findings=findings,
        code_backed_count=code_backed,
        guidance_count=guidance,
        highest_severity=highest,
    )

    await ctx.send(sender, response)
    ctx.logger.info(
        f"Health eval complete: {len(findings)} findings, "
        f"code_backed={code_backed}, guidance={guidance}, highest={highest}"
    )


# ---------------------------------------------------------------------------
# Chat protocol: lets the agent respond in Agentverse chat inspector
# Runs a demo evaluation with mock data so you can see the pipeline in action.
# ---------------------------------------------------------------------------

DEMO_EVENTS = [
    EventCandidate(
        event_id="demo_evt_1",
        observations=[
            Observation(
                observation_id="obs_1a",
                observation_type="raw_food_contact",
                timestamp_start="00:01:42",
                timestamp_end="00:01:45",
                confidence=0.90,
                description="Worker handled raw chicken",
            ),
            Observation(
                observation_id="obs_1b",
                observation_type="rte_food_contact",
                timestamp_start="00:01:48",
                timestamp_end="00:01:52",
                confidence=0.85,
                description="Worker touched lettuce prep area",
            ),
            Observation(
                observation_id="obs_1c",
                observation_type="no_sanitation_between_tasks",
                timestamp_start="00:01:45",
                timestamp_end="00:01:48",
                confidence=0.88,
                description="No visible hand wash or surface sanitation between tasks",
            ),
        ],
        corrective_action_observed=False,
    ),
    EventCandidate(
        event_id="demo_evt_2",
        observations=[
            Observation(
                observation_id="obs_2a",
                observation_type="knife_near_table_edge",
                timestamp_start="00:03:10",
                timestamp_end="00:03:15",
                confidence=0.82,
                description="Knife placed at edge of prep table",
            ),
        ],
        corrective_action_observed=False,
    ),
]

chat_proto = Protocol(spec=chat_protocol_spec)


@chat_proto.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=msg.msg_id,
        ),
    )

    # Extract text
    user_text = " ".join(
        item.text for item in msg.content if isinstance(item, TextContent)
    ).strip()

    ctx.logger.info(f"Chat message from {sender}: {user_text[:100]}")

    # Run demo evaluation
    findings = evaluate_events(DEMO_EVENTS, jurisdiction="california", strictness="medium")

    # Format findings as readable text
    lines = [f"Health Agent Demo — {len(findings)} finding(s):\n"]
    for f in findings:
        lines.append(
            f"[{f.severity.upper()}] {f.concluded_type}\n"
            f"  Status: {f.status}\n"
            f"  Class: {f.finding_class}\n"
            f"  Policy: {f.policy_reference.code} {f.policy_reference.section}\n"
            f"  Rule: {f.policy_reference.short_rule}\n"
            f"  Confidence: {f.evidence_confidence}\n"
            f"  Coaching: {f.training_recommendation}\n"
            f"  Time: {f.timestamp_start} - {f.timestamp_end}\n"
        )

    response_text = "\n".join(lines)

    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text=response_text),
                EndSessionContent(type="end-session"),
            ],
        ),
    )


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"ACK from {sender}")


health_agent.include(chat_proto, publish_manifest=True)


# ---------------------------------------------------------------------------
# REST endpoint for direct HTTP evaluation (bypasses uagents message passing)
# ---------------------------------------------------------------------------

@health_agent.on_rest_post("/evaluate", HealthEvalRequest, HealthEvalResponse)
async def handle_rest_eval(ctx: Context, req: HealthEvalRequest) -> HealthEvalResponse:
    ctx.logger.info(
        f"REST health eval for clip={req.clip_id} employee={req.employee_id} "
        f"jurisdiction={req.jurisdiction} events={len(req.event_candidates)}"
    )

    findings = evaluate_events(req.event_candidates, req.jurisdiction, req.strictness)
    code_backed = sum(1 for f in findings if f.finding_class == "code_backed_food_safety")
    guidance = sum(1 for f in findings if f.finding_class != "code_backed_food_safety")
    highest = max(
        (f.severity for f in findings),
        key=lambda s: SEVERITY_LEVELS.index(s),
        default="low",
    )

    ctx.logger.info(
        f"REST health eval complete: {len(findings)} findings, "
        f"code_backed={code_backed}, guidance={guidance}, highest={highest}"
    )

    return HealthEvalResponse(
        chat_session_id=req.chat_session_id,
        clip_id=req.clip_id,
        employee_id=req.employee_id,
        jurisdiction=req.jurisdiction,
        findings=findings,
        code_backed_count=code_backed,
        guidance_count=guidance,
        highest_severity=highest,
    )


if __name__ == "__main__":
    health_agent.run()
