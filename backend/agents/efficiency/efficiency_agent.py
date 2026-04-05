"""
Efficiency Agent for Fetch.ai/uAgents.

Evaluates workflow-efficiency event candidates and returns structured,
coaching-oriented findings without over-flagging brief pauses.
"""

from __future__ import annotations

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

from backend.agents.efficiency.adjudicator import (
    should_flag,
    calculate_duration_seconds,
)
from backend.agents.efficiency.coach import get_efficiency_coaching_text
from backend.agents.efficiency.resolver import resolve_efficiency_policy
from backend.agents.efficiency.severity import (
    SEVERITY_LEVELS,
    assign_efficiency_severity,
)
from backend.agents.models.config import EFFICIENCY_AGENT_SEED
from backend.agents.models.messages import (
    EfficiencyEvalRequest,
    EfficiencyEvalResponse,
    EfficiencyFinding,
    EfficiencyReference,
    EventCandidate,
    Observation,
)


efficiency_agent = Agent(
    name="efficiency_agent",
    seed=EFFICIENCY_AGENT_SEED,
    port=8002,
    mailbox=True,
    publish_agent_details=True,
)


def evaluate_events(event_candidates):
    findings: list[EfficiencyFinding] = []

    for event in event_candidates:
        obs_types = [obs.observation_type for obs in event.observations]
        concluded_type, policy = resolve_efficiency_policy(obs_types)

        if not should_flag(event, concluded_type):
            continue

        duration_seconds = round(calculate_duration_seconds(event), 2)
        repeated_behavior_observed = len(event.observations) > 1
        severity = assign_efficiency_severity(
            concluded_type,
            duration_seconds,
            repeated_behavior_observed,
        )
        coaching = get_efficiency_coaching_text(concluded_type)
        reference = policy.get("reference", {})
        reasoning = policy.get("reasoning_template", "").format(obs_types=obs_types)

        findings.append(EfficiencyFinding(
            event_id=event.event_id,
            concluded_type=concluded_type,
            finding_class=policy.get("finding_class", "coaching_note"),
            severity=severity,
            duration_seconds=duration_seconds,
            repeated_behavior_observed=repeated_behavior_observed,
            reference=EfficiencyReference(
                source_tier=reference.get("source_tier", "house_rule"),
                code=reference.get("code", "Internal Workflow Coaching Guide"),
                section=reference.get("section", "unclassified"),
                short_rule=reference.get(
                    "short_rule",
                    "Observation did not match a known workflow coaching rule.",
                ),
            ),
            assumptions=policy.get("assumptions", []),
            reasoning=reasoning,
            coaching_recommendation=coaching,
            timestamp_start=event.observations[0].timestamp_start,
            timestamp_end=event.observations[-1].timestamp_end,
        ))

    return findings


@efficiency_agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info(f"Efficiency Agent started -> {efficiency_agent.address}")


@efficiency_agent.on_message(EfficiencyEvalRequest)
async def handle_eval(ctx: Context, sender: str, msg: EfficiencyEvalRequest):
    ctx.logger.info(
        f"Efficiency eval for clip={msg.clip_id} employee={msg.employee_id} "
        f"events={len(msg.event_candidates)}"
    )

    findings = evaluate_events(msg.event_candidates)
    confirmed_issue_count = len(findings)
    coaching_opportunity_count = len(findings)
    highest_severity = max(
        (finding.severity for finding in findings),
        key=lambda value: SEVERITY_LEVELS.index(value),
        default="low",
    )

    response = EfficiencyEvalResponse(
        chat_session_id=msg.chat_session_id,
        clip_id=msg.clip_id,
        employee_id=msg.employee_id,
        findings=findings,
        confirmed_issue_count=confirmed_issue_count,
        coaching_opportunity_count=coaching_opportunity_count,
        highest_severity=highest_severity,
    )

    await ctx.send(sender, response)
    ctx.logger.info(
        f"Efficiency eval complete: {len(findings)} findings, "
        f"confirmed={confirmed_issue_count}, highest={highest_severity}"
    )


DEMO_EVENTS = [
    EventCandidate(
        event_id="demo_eff_1",
        observations=[
            Observation(
                observation_id="eff_obs_1",
                observation_type="phone_usage",
                timestamp_start="00:00:10",
                timestamp_end="00:00:32",
                description="Worker appears to text on phone while prep is paused.",
            )
        ],
    ),
    EventCandidate(
        event_id="demo_eff_2",
        observations=[
            Observation(
                observation_id="eff_obs_2a",
                observation_type="extended_chatting",
                timestamp_start="00:01:00",
                timestamp_end="00:01:18",
                description="Two workers talk while station work is paused.",
            ),
            Observation(
                observation_id="eff_obs_2b",
                observation_type="extended_chatting",
                timestamp_start="00:01:24",
                timestamp_end="00:01:40",
                description="Conversation continues before prep resumes.",
            ),
        ],
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

    findings = evaluate_events(DEMO_EVENTS)
    lines = [f"Efficiency Agent Demo - {len(findings)} finding(s):\n"]

    for finding in findings:
        lines.append(
            f"[{finding.severity.upper()}] {finding.concluded_type}\n"
            f"  Class: {finding.finding_class}\n"
            f"  Duration: {finding.duration_seconds}s\n"
            f"  Guidance: {finding.coaching_recommendation}\n"
            f"  Time: {finding.timestamp_start} - {finding.timestamp_end}\n"
        )

    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text="\n".join(lines)),
                EndSessionContent(type="end-session"),
            ],
        ),
    )


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"ACK from {sender}")


efficiency_agent.include(chat_proto, publish_manifest=True)


# ---------------------------------------------------------------------------
# REST endpoint for direct HTTP evaluation (bypasses uagents message passing)
# ---------------------------------------------------------------------------

@efficiency_agent.on_rest_post("/evaluate", EfficiencyEvalRequest, EfficiencyEvalResponse)
async def handle_rest_eval(ctx: Context, req: EfficiencyEvalRequest) -> EfficiencyEvalResponse:
    ctx.logger.info(
        f"REST efficiency eval for clip={req.clip_id} employee={req.employee_id} "
        f"events={len(req.event_candidates)}"
    )

    findings = evaluate_events(req.event_candidates)
    confirmed_issue_count = len(findings)
    coaching_opportunity_count = len(findings)
    highest_severity = max(
        (f.severity for f in findings),
        key=lambda value: SEVERITY_LEVELS.index(value),
        default="low",
    )

    ctx.logger.info(
        f"REST efficiency eval complete: {len(findings)} findings, highest={highest_severity}"
    )

    return EfficiencyEvalResponse(
        chat_session_id=req.chat_session_id,
        clip_id=req.clip_id,
        employee_id=req.employee_id,
        findings=findings,
        confirmed_issue_count=confirmed_issue_count,
        coaching_opportunity_count=coaching_opportunity_count,
        highest_severity=highest_severity,
    )


if __name__ == "__main__":
    efficiency_agent.run()
