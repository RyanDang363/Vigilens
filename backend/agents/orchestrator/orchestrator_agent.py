"""
Orchestrator Agent — the coordinator of the multi-agent pipeline.

Flow:
1. Receives an OrchestratorRequest (via chat or REST) with observations
2. Fans out: sends health events to Health Agent, efficiency events to Efficiency Agent
3. Collects responses from both agents
4. Compiles a merged report and POSTs it to the backend API (for the dashboard)
5. Optionally sends BrowserActionRequests (email, sheets, training docs)
6. Responds to the original sender with a summary

Follows the fetch-hackathon-quickstarter orchestrator pattern.
"""

from __future__ import annotations

import httpx
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Agent, Context, Protocol, Model
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from backend.agents.models.config import (
    ORCHESTRATOR_SEED,
    HEALTH_AGENT_ADDRESS,
    EFFICIENCY_AGENT_ADDRESS,
    BROWSER_AGENT_ADDRESS,
)
from backend.agents.models.messages import (
    BrowserActionRequest,
    BrowserActionResponse,
    EventCandidate,
    HealthEvalRequest,
    HealthEvalResponse,
    EfficiencyEvalRequest,
    EfficiencyEvalResponse,
    Observation,
    OrchestratorRequest,
)
from backend.agents.orchestrator.state import PipelineState, state_service


BACKEND_API_URL = "http://localhost:8000"
SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

orchestrator = Agent(
    name="orchestrator",
    seed=ORCHESTRATOR_SEED,
    port=8004,
    mailbox=True,
    publish_agent_details=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _max_severity(*severities: str) -> str:
    best = "low"
    for s in severities:
        if SEVERITY_ORDER.get(s, 0) > SEVERITY_ORDER.get(best, 0):
            best = s
    return best


def _build_report_summary(state: PipelineState) -> str:
    total = len(state.health_findings) + len(state.efficiency_findings)
    lines = [
        f"Report for {state.employee_name} — clip {state.clip_id}",
        f"Jurisdiction: {state.jurisdiction}",
        f"Total findings: {total}",
        f"  Health (code-backed): {state.health_code_backed}",
        f"  Health (guidance): {state.health_guidance}",
        f"  Efficiency: {state.efficiency_count}",
        f"Highest severity: {state.highest_severity}",
    ]
    return "\n".join(lines)


async def _post_report_to_backend(state: PipelineState):
    """POST the compiled report to the dashboard backend API."""
    # Convert findings to the backend schema format
    findings_payload = []

    for f in state.health_findings:
        pr = f.get("policy_reference", {})
        findings_payload.append({
            "concluded_type": f.get("concluded_type", ""),
            "status": f.get("status", ""),
            "finding_class": f.get("finding_class", ""),
            "severity": f.get("severity", ""),
            "agent_source": "health",
            "policy_code": pr.get("code", ""),
            "policy_section": pr.get("section", ""),
            "policy_short_rule": pr.get("short_rule", ""),
            "policy_url": pr.get("official_url", ""),
            "evidence_confidence": f.get("evidence_confidence", 0.0),
            "reasoning": f.get("reasoning", ""),
            "training_recommendation": f.get("training_recommendation", ""),
            "corrective_action_observed": f.get("corrective_action_observed", False),
            "timestamp_start": f.get("timestamp_start", ""),
            "timestamp_end": f.get("timestamp_end", ""),
        })

    for f in state.efficiency_findings:
        ref = f.get("reference", {})
        findings_payload.append({
            "concluded_type": f.get("concluded_type", ""),
            "status": f.get("status", ""),
            "finding_class": f.get("finding_class", ""),
            "severity": f.get("severity", ""),
            "agent_source": "efficiency",
            "policy_code": ref.get("code", ""),
            "policy_section": ref.get("section", ""),
            "policy_short_rule": ref.get("short_rule", ""),
            "evidence_confidence": f.get("evidence_confidence", 0.0),
            "reasoning": f.get("reasoning", ""),
            "training_recommendation": f.get("coaching_recommendation", ""),
            "timestamp_start": f.get("timestamp_start", ""),
            "timestamp_end": f.get("timestamp_end", ""),
        })

    report_payload = {
        "employee_id": state.employee_id,
        "clip_id": state.clip_id,
        "session_id": state.chat_session_id,
        "jurisdiction": state.jurisdiction,
        "code_backed_count": state.health_code_backed,
        "guidance_count": state.health_guidance,
        "efficiency_count": state.efficiency_count,
        "highest_severity": state.highest_severity,
        "findings": findings_payload,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_API_URL}/api/reports",
            json=report_payload,
            timeout=10.0,
        )
        return resp.json() if resp.status_code == 200 else None


async def _trigger_browser_actions(ctx: Context, state: PipelineState):
    """Send BrowserActionRequests for each requested action."""
    summary = _build_report_summary(state)
    all_findings = state.health_findings + state.efficiency_findings

    for action in state.actions:
        request = BrowserActionRequest(
            chat_session_id=state.chat_session_id,
            action_type=action,
            employee_name=state.employee_name,
            employee_email=state.employee_email,
            manager_email=state.manager_email,
            report_summary=summary,
            findings_data=all_findings,
            sheet_url=state.sheet_url,
            training_doc_url=state.training_doc_url,
        )
        await ctx.send(BROWSER_AGENT_ADDRESS, request)
        ctx.logger.info(f"Sent browser action: {action}")


async def _finalize_pipeline(ctx: Context, session_id: str):
    """Called when all agent responses are collected. Compiles report,
    posts to backend, triggers browser actions, responds to user."""
    # Atomic take — only the first caller gets the state, all others get None
    state = state_service.take(session_id)
    if not state or not state.is_complete:
        return

    ctx.logger.info(f"Pipeline complete for session {session_id}")

    # Post report to dashboard backend
    try:
        report = await _post_report_to_backend(state)
        if report:
            ctx.logger.info(f"Report posted to backend: {report.get('id', 'unknown')}")
        else:
            ctx.logger.warning("Failed to post report to backend")
    except Exception as e:
        ctx.logger.exception(f"Backend POST failed: {e}")

    # Trigger browser actions if any
    if state.actions:
        await _trigger_browser_actions(ctx, state)

    # Respond to original sender (skip if triggered via REST with no sender)
    if state.user_sender_address:
        summary = _build_report_summary(state)
        await ctx.send(
            state.user_sender_address,
            ChatMessage(
                timestamp=datetime.now(tz=timezone.utc),
                msg_id=uuid4(),
                content=[
                    TextContent(type="text", text=summary),
                    EndSessionContent(type="end-session"),
                ],
            ),
        )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@orchestrator.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info(f"Orchestrator started -> {orchestrator.address}")
    ctx.logger.info(f"Health Agent: {HEALTH_AGENT_ADDRESS}")
    ctx.logger.info(f"Efficiency Agent: {EFFICIENCY_AGENT_ADDRESS}")
    ctx.logger.info(f"Browser Agent: {BROWSER_AGENT_ADDRESS}")


# ---------------------------------------------------------------------------
# Handle OrchestratorRequest — kick off the pipeline
# ---------------------------------------------------------------------------

@orchestrator.on_message(OrchestratorRequest)
async def handle_request(ctx: Context, sender: str, msg: OrchestratorRequest):
    session_id = str(uuid4())
    ctx.logger.info(
        f"New pipeline: session={session_id} clip={msg.clip_id} "
        f"employee={msg.employee_id} health_events={len(msg.health_events)} "
        f"efficiency_events={len(msg.efficiency_events)}"
    )

    state = PipelineState(
        chat_session_id=session_id,
        clip_id=msg.clip_id,
        employee_id=msg.employee_id,
        employee_name=msg.employee_name,
        employee_email=msg.employee_email or "",
        manager_email=msg.manager_email or "",
        jurisdiction=msg.jurisdiction,
        sheet_url=msg.sheet_url or "",
        training_doc_url=msg.training_doc_url or "",
        actions=msg.actions,
        user_sender_address=sender,
        awaiting_health=len(msg.health_events) > 0,
        awaiting_efficiency=len(msg.efficiency_events) > 0,
    )
    state_service.set(session_id, state)

    # Fan out to Health Agent
    if msg.health_events:
        await ctx.send(HEALTH_AGENT_ADDRESS, HealthEvalRequest(
            chat_session_id=session_id,
            clip_id=msg.clip_id,
            employee_id=msg.employee_id,
            station_id=msg.station_id or "",
            jurisdiction=msg.jurisdiction,
            strictness=msg.strictness,
            event_candidates=msg.health_events,
            user_sender_address=orchestrator.address,
        ))
        ctx.logger.info("Sent health eval request")

    # Fan out to Efficiency Agent
    if msg.efficiency_events:
        await ctx.send(EFFICIENCY_AGENT_ADDRESS, EfficiencyEvalRequest(
            chat_session_id=session_id,
            clip_id=msg.clip_id,
            employee_id=msg.employee_id,
            station_id=msg.station_id or "",
            strictness=msg.strictness,
            event_candidates=msg.efficiency_events,
            user_sender_address=orchestrator.address,
        ))
        ctx.logger.info("Sent efficiency eval request")

    # If no events at all, finalize immediately
    if not msg.health_events and not msg.efficiency_events:
        await _finalize_pipeline(ctx, session_id)


# ---------------------------------------------------------------------------
# Collect responses from Health Agent
# ---------------------------------------------------------------------------

@orchestrator.on_message(HealthEvalResponse)
async def handle_health_response(ctx: Context, sender: str, msg: HealthEvalResponse):
    ctx.logger.info(
        f"Health response: session={msg.chat_session_id} "
        f"findings={len(msg.findings)} highest={msg.highest_severity}"
    )

    state = state_service.get(msg.chat_session_id)
    if not state:
        ctx.logger.warning(f"No pipeline state for session {msg.chat_session_id}")
        return

    # Store health findings as dicts
    state.health_findings = [f.model_dump() for f in msg.findings]
    state.health_code_backed = msg.code_backed_count
    state.health_guidance = msg.guidance_count
    state.highest_severity = _max_severity(state.highest_severity, msg.highest_severity)
    state.awaiting_health = False

    if state.is_complete:
        await _finalize_pipeline(ctx, msg.chat_session_id)


# ---------------------------------------------------------------------------
# Collect responses from Efficiency Agent
# ---------------------------------------------------------------------------

@orchestrator.on_message(EfficiencyEvalResponse)
async def handle_efficiency_response(ctx: Context, sender: str, msg: EfficiencyEvalResponse):
    ctx.logger.info(
        f"Efficiency response: session={msg.chat_session_id} "
        f"findings={len(msg.findings)} highest={msg.highest_severity}"
    )

    state = state_service.get(msg.chat_session_id)
    if not state:
        ctx.logger.warning(f"No pipeline state for session {msg.chat_session_id}")
        return

    state.efficiency_findings = [f.model_dump() for f in msg.findings]
    state.efficiency_count = msg.confirmed_issue_count
    state.highest_severity = _max_severity(state.highest_severity, msg.highest_severity)
    state.awaiting_efficiency = False

    if state.is_complete:
        await _finalize_pipeline(ctx, msg.chat_session_id)


# ---------------------------------------------------------------------------
# Collect responses from Browser Agent (log but no further action needed)
# ---------------------------------------------------------------------------

@orchestrator.on_message(BrowserActionResponse)
async def handle_browser_response(ctx: Context, sender: str, msg: BrowserActionResponse):
    ctx.logger.info(
        f"Browser response: action={msg.action_type} success={msg.success} "
        f"message={msg.message[:100]}"
    )
    if msg.recording_url:
        ctx.logger.info(f"Recording: {msg.recording_url}")


# ---------------------------------------------------------------------------
# Chat protocol — allows triggering the pipeline from Agentverse chat
# with a demo using mock observations
# ---------------------------------------------------------------------------

DEMO_HEALTH_EVENTS = [
    EventCandidate(
        event_id="demo_h1",
        observations=[
            Observation(observation_id="o1", observation_type="raw_food_contact",
                        timestamp_start="00:01:42", timestamp_end="00:01:45",
                        confidence=0.90, description="Worker handled raw chicken"),
            Observation(observation_id="o2", observation_type="rte_food_contact",
                        timestamp_start="00:01:48", timestamp_end="00:01:52",
                        confidence=0.85, description="Worker touched lettuce prep area"),
            Observation(observation_id="o3", observation_type="no_sanitation_between_tasks",
                        timestamp_start="00:01:45", timestamp_end="00:01:48",
                        confidence=0.88, description="No visible sanitation between tasks"),
        ],
        corrective_action_observed=False,
    ),
]

DEMO_EFFICIENCY_EVENTS = [
    EventCandidate(
        event_id="demo_e1",
        observations=[
            Observation(observation_id="o4", observation_type="phone_usage",
                        timestamp_start="00:03:00", timestamp_end="00:03:22",
                        confidence=0.91, description="Worker texting during prep"),
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

    user_text = " ".join(
        item.text for item in msg.content if isinstance(item, TextContent)
    ).strip()

    ctx.logger.info(f"Chat from {sender}: {user_text[:100]}")

    # Trigger a demo pipeline run
    demo_request = OrchestratorRequest(
        clip_id="demo_clip_001",
        employee_id="emp_1",
        employee_name="Maria Garcia",
        jurisdiction="california",
        strictness="medium",
        health_events=DEMO_HEALTH_EVENTS,
        efficiency_events=DEMO_EFFICIENCY_EVENTS,
        actions=[],  # no browser actions in demo chat
    )

    # Simulate the orchestrator receiving this request
    await handle_request(ctx, sender, demo_request)


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"ACK from {sender}")


orchestrator.include(chat_proto, publish_manifest=True)


# ---------------------------------------------------------------------------
# REST endpoints for triggering from the frontend / external tools
# ---------------------------------------------------------------------------

class HealthResponse(Model):
    status: str


class SubmitResponse(Model):
    session_id: str
    status: str
    health_event_count: int
    efficiency_event_count: int
    health_findings: int = 0
    efficiency_findings: int = 0
    highest_severity: str = "low"
    report_id: str = ""


HEALTH_AGENT_URL = "http://localhost:8001"
EFFICIENCY_AGENT_URL = "http://localhost:8002"


@orchestrator.on_rest_get("/health", HealthResponse)
async def health_check(ctx: Context) -> HealthResponse:
    return HealthResponse(status="ok")


@orchestrator.on_rest_post("/api/analyze", OrchestratorRequest, SubmitResponse)
async def handle_submit(ctx: Context, req: OrchestratorRequest) -> SubmitResponse:
    """REST entry point: calls agents via HTTP, compiles report, posts to backend."""
    session_id = str(uuid4())
    ctx.logger.info(
        f"REST submit: session={session_id} clip={req.clip_id} "
        f"employee={req.employee_id} health={len(req.health_events)} "
        f"efficiency={len(req.efficiency_events)}"
    )

    state = PipelineState(
        chat_session_id=session_id,
        clip_id=req.clip_id,
        employee_id=req.employee_id,
        employee_name=req.employee_name,
        employee_email=req.employee_email or "",
        manager_email=req.manager_email or "",
        jurisdiction=req.jurisdiction,
        sheet_url=req.sheet_url or "",
        training_doc_url=req.training_doc_url or "",
        actions=req.actions,
        user_sender_address="",
        awaiting_health=False,
        awaiting_efficiency=False,
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        if req.health_events:
            health_payload = HealthEvalRequest(
                chat_session_id=session_id,
                clip_id=req.clip_id,
                employee_id=req.employee_id,
                station_id=req.station_id or "",
                jurisdiction=req.jurisdiction,
                strictness=req.strictness,
                event_candidates=req.health_events,
                user_sender_address=orchestrator.address,
            )
            try:
                resp = await client.post(
                    f"{HEALTH_AGENT_URL}/evaluate",
                    json=health_payload.model_dump(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    state.health_findings = [f for f in data.get("findings", [])]
                    state.health_code_backed = data.get("code_backed_count", 0)
                    state.health_guidance = data.get("guidance_count", 0)
                    state.highest_severity = _max_severity(
                        state.highest_severity, data.get("highest_severity", "low")
                    )
                    ctx.logger.info(
                        f"Health agent returned {len(state.health_findings)} findings"
                    )
                else:
                    ctx.logger.warning(f"Health agent returned {resp.status_code}")
            except Exception as e:
                ctx.logger.warning(f"Health agent call failed: {e}")

        if req.efficiency_events:
            eff_payload = EfficiencyEvalRequest(
                chat_session_id=session_id,
                clip_id=req.clip_id,
                employee_id=req.employee_id,
                station_id=req.station_id or "",
                strictness=req.strictness,
                event_candidates=req.efficiency_events,
                user_sender_address=orchestrator.address,
            )
            try:
                resp = await client.post(
                    f"{EFFICIENCY_AGENT_URL}/evaluate",
                    json=eff_payload.model_dump(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    state.efficiency_findings = [f for f in data.get("findings", [])]
                    state.efficiency_count = data.get("confirmed_issue_count", 0)
                    state.highest_severity = _max_severity(
                        state.highest_severity, data.get("highest_severity", "low")
                    )
                    ctx.logger.info(
                        f"Efficiency agent returned {len(state.efficiency_findings)} findings"
                    )
                else:
                    ctx.logger.warning(f"Efficiency agent returned {resp.status_code}")
            except Exception as e:
                ctx.logger.warning(f"Efficiency agent call failed: {e}")

    state_service.set(session_id, state)

    report_id = ""
    try:
        report = await _post_report_to_backend(state)
        if report:
            report_id = report.get("id", "")
            ctx.logger.info(f"Report posted to backend: {report_id}")
        else:
            ctx.logger.warning("Failed to post report to backend")
    except Exception as e:
        ctx.logger.exception(f"Backend POST failed: {e}")

    if state.actions:
        await _trigger_browser_actions(ctx, state)

    state_service.remove(session_id)

    return SubmitResponse(
        session_id=session_id,
        status="complete",
        health_event_count=len(req.health_events),
        efficiency_event_count=len(req.efficiency_events),
        health_findings=len(state.health_findings),
        efficiency_findings=len(state.efficiency_findings),
        highest_severity=state.highest_severity,
        report_id=report_id,
    )


if __name__ == "__main__":
    orchestrator.run()
