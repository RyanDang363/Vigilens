"""
Orchestrator Agent -- the coordinator of the multi-agent pipeline.

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

import asyncio
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
from uagents_core.contrib.protocols.payment import (
    CommitPayment,
    CompletePayment,
    Funds,
    RejectPayment,
    RequestPayment,
)

from backend.agents.models.config import (
    ORCHESTRATOR_SEED,
    HEALTH_AGENT_ADDRESS,
    EFFICIENCY_AGENT_ADDRESS,
    BROWSER_AGENT_ADDRESS,
    STRIPE_AMOUNT_CENTS,
    STRIPE_SECRET_KEY,
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
from backend.agents.orchestrator.stripe_payments import (
    create_checkout_session,
    verify_checkout_paid,
)
from backend.agents.orchestrator.payment_proto import build_payment_proto


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
    sev = state.highest_severity.upper()
    return (
        f"**Jurisdiction:** {state.jurisdiction.title()}  \n"
        f"**Total findings:** {total}  \n"
        f"- Health (code-backed): {state.health_code_backed}  \n"
        f"- Health (guidance): {state.health_guidance}  \n"
        f"- Efficiency: {state.efficiency_count}  \n"
        f"**Highest severity:** {sev}"
    )


async def _post_report_to_backend(state: PipelineState):
    """POST the compiled report to the dashboard backend API."""
    # Convert findings to the backend schema format
    findings_payload = []

    for f in state.health_findings:
        pr = f.get("policy_reference", {})
        findings_payload.append({
            "concluded_type": f.get("concluded_type", ""),
            "finding_class": f.get("finding_class", ""),
            "severity": f.get("severity", ""),
            "agent_source": "health",
            "policy_code": pr.get("code", ""),
            "policy_section": pr.get("section", ""),
            "policy_short_rule": pr.get("short_rule", ""),
            "policy_url": pr.get("official_url", ""),
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
            "finding_class": f.get("finding_class", ""),
            "severity": f.get("severity", ""),
            "agent_source": "efficiency",
            "policy_code": ref.get("code", ""),
            "policy_section": ref.get("section", ""),
            "policy_short_rule": ref.get("short_rule", ""),
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
    # Atomic take --??? only the first caller gets the state, all others get None
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
        report_text = _format_rich_report(state)
        await ctx.send(state.user_sender_address, _make_end_chat(report_text))


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
# Handle OrchestratorRequest -- kick off the pipeline
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
# Chat protocol -- interactive demo via ASI One / Agentverse
# Supports intent detection, parameter extraction, multiple scenarios,
# and Stripe payment gating.
# ---------------------------------------------------------------------------

# Demo scenarios — each represents a different employee clip
DEMO_SCENARIOS = {
    "maria": {
        "employee_id": "emp_1",
        "employee_name": "Maria Garcia",
        "description": "Line cook at Prep Station A — cross contamination and phone use during prep",
        "health_events": [
            EventCandidate(
                event_id="demo_h1",
                observations=[
                    Observation(observation_id="o1", observation_type="cross_contamination",
                                timestamp_start="00:01:42", timestamp_end="00:01:52",
                                description="Worker handled raw chicken then touched lettuce prep area without washing hands"),
                ],
                corrective_action_observed=False,
            ),
            EventCandidate(
                event_id="demo_h2",
                observations=[
                    Observation(observation_id="o2", observation_type="brief_hand_rinse",
                                timestamp_start="00:06:30", timestamp_end="00:06:38",
                                description="Worker rinsed hands for about 8 seconds without soap"),
                ],
                corrective_action_observed=False,
            ),
        ],
        "efficiency_events": [
            EventCandidate(
                event_id="demo_e1",
                observations=[
                    Observation(observation_id="o4", observation_type="phone_usage",
                                timestamp_start="00:03:00", timestamp_end="00:03:22",
                                description="Worker texting during prep"),
                ],
            ),
        ],
    },
    "james": {
        "employee_id": "emp_2",
        "employee_name": "James Chen",
        "description": "Sous chef at Grill Station — unsafe knife placement and extended chatting",
        "health_events": [
            EventCandidate(
                event_id="demo_h3",
                observations=[
                    Observation(observation_id="o5", observation_type="knife_near_table_edge",
                                timestamp_start="00:04:10", timestamp_end="00:04:15",
                                description="Knife placed at edge of prep table, handle hanging over"),
                ],
                corrective_action_observed=False,
            ),
        ],
        "efficiency_events": [
            EventCandidate(
                event_id="demo_e2",
                observations=[
                    Observation(observation_id="o6", observation_type="extended_chatting",
                                timestamp_start="00:08:00", timestamp_end="00:08:45",
                                description="Worker chatting with coworker for 45 seconds during service"),
                ],
            ),
        ],
    },
    "sarah": {
        "employee_id": "emp_3",
        "employee_name": "Sarah Johnson",
        "description": "Prep cook at Station B — glove misuse and dropped utensil reuse",
        "health_events": [
            EventCandidate(
                event_id="demo_h4",
                observations=[
                    Observation(observation_id="o7", observation_type="glove_not_changed",
                                timestamp_start="00:02:20", timestamp_end="00:02:30",
                                description="Worker continued with same gloves after handling raw meat then touched ready-to-eat items"),
                ],
                corrective_action_observed=False,
            ),
            EventCandidate(
                event_id="demo_h5",
                observations=[
                    Observation(observation_id="o8", observation_type="utensil_dropped",
                                timestamp_start="00:05:00", timestamp_end="00:05:08",
                                description="Worker dropped tongs on floor and picked them up to continue using"),
                    Observation(observation_id="o9", observation_type="utensil_reused_after_floor",
                                timestamp_start="00:05:08", timestamp_end="00:05:15",
                                description="Dropped tongs placed back on prep surface without washing"),
                ],
                corrective_action_observed=False,
            ),
        ],
        "efficiency_events": [],
    },
}

# --- LLM-powered intent detection (ASI-1) with keyword fallback ---

from backend.agents.orchestrator.llm import parse_chat_message


# --- Rich response formatting ---

_SEVERITY_ICON = {"low": "[LOW]", "medium": "[MED]", "high": "[HIGH]", "critical": "[CRIT]"}


def _format_rich_report(state: PipelineState) -> str:
    """Format a rich, readable report for the chat response."""
    total = len(state.health_findings) + len(state.efficiency_findings)
    sev = state.highest_severity.upper()

    lines = [
        f"SafeWatch Analysis Report",
        f"========================",
        f"Employee: {state.employee_name}",
        f"Jurisdiction: {state.jurisdiction.upper()}",
        f"Highest Severity: {sev}",
        f"",
        f"Summary: {total} finding(s) detected",
        f"  Health/Safety: {len(state.health_findings)} ({state.health_code_backed} code-backed, {state.health_guidance} guidance)",
        f"  Efficiency: {len(state.efficiency_findings)}",
        "",
    ]

    if state.health_findings:
        lines.append("--- Health & Safety Findings ---")
        for f in state.health_findings:
            sev_icon = _SEVERITY_ICON.get(f.get("severity", "low"), "[?]")
            concluded = f.get("concluded_type", "unknown").replace("_", " ").title()
            ts = f.get("timestamp_start", "")
            reasoning = f.get("reasoning", "")
            policy = f.get("policy_reference", {})
            code = policy.get("code", "")
            section = policy.get("section", "")
            recommendation = f.get("training_recommendation", "")

            lines.append(f"")
            lines.append(f"{sev_icon} {concluded} ({ts})")
            if reasoning:
                lines.append(f"  {reasoning}")
            if code and section:
                lines.append(f"  Policy: {code} {section}")
            if recommendation:
                lines.append(f"  Coaching: {recommendation}")

    if state.efficiency_findings:
        lines.append("")
        lines.append("--- Efficiency Findings ---")
        for f in state.efficiency_findings:
            sev_icon = _SEVERITY_ICON.get(f.get("severity", "low"), "[?]")
            concluded = f.get("concluded_type", "unknown").replace("_", " ").title()
            ts = f.get("timestamp_start", "")
            coaching = f.get("coaching_recommendation", "")
            duration = f.get("duration_seconds", 0)

            lines.append(f"")
            lines.append(f"{sev_icon} {concluded} ({ts}, {duration:.0f}s)")
            if coaching:
                lines.append(f"  Coaching: {coaching}")

    lines.append("")
    lines.append("Report saved to SafeWatch dashboard.")
    lines.append("Actions triggered: email notification, Google Sheets log, training doc lookup, web research.")

    return "\n".join(lines)


# --- Chat protocol ---

chat_proto = Protocol(spec=chat_protocol_spec)


def _make_chat(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text)],
    )


def _make_end_chat(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text=text),
            EndSessionContent(type="end-session"),
        ],
    )


def _load_pay_state(ctx: Context, sender: str) -> dict:
    return ctx.storage.get(f"pay:{sender}") or {}


def _save_pay_state(ctx: Context, sender: str, state: dict):
    ctx.storage.set(f"pay:{sender}", state)


def _clear_pay_state(ctx: Context, sender: str):
    ctx.storage.set(f"pay:{sender}", {})


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

    # Use ASI-1 LLM to understand the user's message
    parsed = await parse_chat_message(user_text)
    intent = parsed.get("intent", "analyze")
    llm_response = parsed.get("response", "")
    params = parsed.get("params", {})

    ctx.logger.info(f"LLM parsed: intent={intent} params={params}")

    # --- Greeting / Help / Chat ---
    if intent in ("greeting", "chat", "status"):
        await ctx.send(sender, _make_chat(llm_response))
        return

    # --- Analysis request ---
    scenario_key = params.get("employee", "maria")
    jurisdiction = params.get("jurisdiction", "california")
    strictness = params.get("strictness", "medium")

    if scenario_key not in DEMO_SCENARIOS:
        scenario_key = "maria"

    scenario = DEMO_SCENARIOS[scenario_key]

    # --- Stripe payment gate (if configured) ---
    pay_state = _load_pay_state(ctx, sender)
    awaiting_payment = bool(pay_state.get("awaiting_payment"))
    pending_stripe = pay_state.get("pending_stripe")

    if STRIPE_SECRET_KEY:
        if awaiting_payment and pending_stripe:
            req = RequestPayment(
                accepted_funds=[
                    Funds(currency="USD", amount=f"{STRIPE_AMOUNT_CENTS / 100:.2f}", payment_method="stripe")
                ],
                recipient=str(ctx.agent.address),
                deadline_seconds=300,
                reference=str(ctx.session),
                description=f"Pay ${STRIPE_AMOUNT_CENTS / 100:.2f} for SafeWatch analysis — {scenario['employee_name']}",
                metadata={"stripe": pending_stripe, "service": "safewatch_report"},
            )
            await ctx.send(sender, req)
            await ctx.send(sender, _make_chat(llm_response or "Payment is still pending. Complete the checkout above."))
            return

        description = f"SafeWatch safety analysis for {scenario['employee_name']}"
        checkout = await asyncio.to_thread(
            create_checkout_session,
            user_address=sender,
            chat_session_id=str(ctx.session),
            description=description,
        )

        _save_pay_state(ctx, sender, {
            "awaiting_payment": True,
            "pending_stripe": checkout,
            "scenario_key": scenario_key,
            "jurisdiction": jurisdiction,
            "strictness": strictness,
        })

        req = RequestPayment(
            accepted_funds=[
                Funds(currency="USD", amount=f"{STRIPE_AMOUNT_CENTS / 100:.2f}", payment_method="stripe")
            ],
            recipient=str(ctx.agent.address),
            deadline_seconds=300,
            reference=str(ctx.session),
            description=f"Pay ${STRIPE_AMOUNT_CENTS / 100:.2f} for SafeWatch analysis — {scenario['employee_name']}",
            metadata={"stripe": checkout, "service": "safewatch_report"},
        )
        await ctx.send(sender, req)
        await ctx.send(sender, _make_chat(
            llm_response or f"Preparing analysis for {scenario['employee_name']}. Complete the payment above."
        ))
        return

    # --- No Stripe: run pipeline directly ---
    await ctx.send(sender, _make_chat(
        llm_response or f"Running SafeWatch analysis for {scenario['employee_name']}..."
    ))

    await _run_analysis(ctx, sender, scenario_key, jurisdiction, strictness)


async def _run_analysis(
    ctx: Context, sender: str,
    scenario_key: str, jurisdiction: str, strictness: str,
):
    """Run the multi-agent pipeline for a given demo scenario."""
    scenario = DEMO_SCENARIOS[scenario_key]

    request = OrchestratorRequest(
        clip_id=f"demo_{scenario_key}_001",
        employee_id=scenario["employee_id"],
        employee_name=scenario["employee_name"],
        jurisdiction=jurisdiction,
        strictness=strictness,
        health_events=scenario["health_events"],
        efficiency_events=scenario["efficiency_events"],
        actions=["send_email", "log_sheet", "get_training_docs", "research_violations"],
    )

    await handle_request(ctx, sender, request)


# ---------------------------------------------------------------------------
# Stripe payment handlers
# ---------------------------------------------------------------------------

async def _on_payment_commit(ctx: Context, sender: str, msg: CommitPayment):
    ctx.logger.info(f"Payment commit from {sender}: tx={msg.transaction_id}")

    if msg.funds.payment_method != "stripe" or not msg.transaction_id:
        await ctx.send(sender, RejectPayment(
            reason="Unsupported payment method (expected Stripe)."
        ))
        return

    paid = await asyncio.to_thread(verify_checkout_paid, msg.transaction_id)
    if not paid:
        await ctx.send(sender, RejectPayment(
            reason="Stripe payment not completed yet. Please finish checkout."
        ))
        return

    await ctx.send(sender, CompletePayment(transaction_id=msg.transaction_id))

    # Recover saved parameters
    pay_state = _load_pay_state(ctx, sender)
    scenario_key = pay_state.get("scenario_key", "maria")
    jurisdiction = pay_state.get("jurisdiction", "california")
    strictness = pay_state.get("strictness", "medium")
    _clear_pay_state(ctx, sender)

    scenario = DEMO_SCENARIOS.get(scenario_key, DEMO_SCENARIOS["maria"])

    ctx.logger.info(f"Payment verified for {sender} — running {scenario_key} pipeline")
    await ctx.send(sender, _make_chat(
        f"Payment confirmed! Running full SafeWatch analysis for {scenario['employee_name']}...\n"
        "Dispatching to Health Agent + Efficiency Agent + Browser Agent..."
    ))

    await _run_analysis(ctx, sender, scenario_key, jurisdiction, strictness)


async def _on_payment_reject(ctx: Context, sender: str, msg: RejectPayment):
    ctx.logger.info(f"Payment rejected by {sender}: {msg.reason}")
    _clear_pay_state(ctx, sender)
    await ctx.send(sender, _make_chat(
        f"Payment cancelled. {msg.reason or ''}\n\nSend me a message anytime to try again.".strip()
    ))


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"ACK from {sender}")


orchestrator.include(chat_proto, publish_manifest=True)
orchestrator.include(
    build_payment_proto(_on_payment_commit, _on_payment_reject),
    publish_manifest=True,
)


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
BROWSER_AGENT_URL = "http://localhost:8003"


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

    # Trigger browser actions via HTTP concurrently
    if state.actions and report_id:
        summary = _build_report_summary(state)
        all_findings = state.health_findings + state.efficiency_findings

        # Create placeholder "in progress" action logs immediately
        async with httpx.AsyncClient(timeout=10.0) as init_client:
            for action in state.actions:
                try:
                    await init_client.post(
                        f"{BACKEND_API_URL}/api/action-logs",
                        json={
                            "report_id": report_id,
                            "action_type": action,
                            "success": False,
                            "full_output": "",
                            "recording_url": "",
                            "status": "in_progress",
                        },
                        headers={"X-Role": "manager"},
                    )
                except Exception:
                    pass

        async def _run_browser_action(action: str):
            action_payload = BrowserActionRequest(
                chat_session_id=state.chat_session_id,
                action_type=action,
                employee_name=state.employee_name,
                employee_email=state.employee_email,
                manager_email=state.manager_email,
                report_summary=summary,
                report_id=report_id,
                findings_data=all_findings,
                sheet_url=state.sheet_url,
                training_doc_url=state.training_doc_url,
            )
            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    resp = await client.post(
                        f"{BROWSER_AGENT_URL}/execute",
                        json=action_payload.model_dump(),
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    ctx.logger.info(
                        f"Browser action {action}: success={data.get('success')} "
                        f"msg={data.get('message', '')[:100]}"
                    )
                    # Save result to database
                    if report_id:
                        try:
                            async with httpx.AsyncClient(timeout=10.0) as db_client:
                                await db_client.post(
                                    f"{BACKEND_API_URL}/api/action-logs",
                                    json={
                                        "report_id": report_id,
                                        "action_type": action,
                                        "success": data.get("success", False),
                                        "full_output": data.get("message", ""),
                                        "recording_url": data.get("recording_url", ""),
                                    },
                                    headers={"X-Role": "manager"},
                                )
                        except Exception as db_err:
                            ctx.logger.warning(f"Failed to save action log: {db_err}")
                else:
                    ctx.logger.warning(f"Browser agent returned {resp.status_code} for {action}")
            except Exception as e:
                ctx.logger.warning(f"Browser action {action} failed: {e}")

        # Fire browser actions in the background — don't block the REST response
        for a in state.actions:
            asyncio.ensure_future(_run_browser_action(a))

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
