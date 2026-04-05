"""
Browser Agent — executes real-world browser actions (email, sheets, training docs)
using Browser Use Cloud SDK, wrapped in a Fetch.ai uAgents agent.

Receives BrowserActionRequest from the orchestrator, performs the action via
a managed cloud browser, and returns BrowserActionResponse with status +
optional session recording URL.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from backend.agents.models.config import (
    BROWSER_AGENT_SEED,
    BROWSER_USE_API_KEY,
    GOOGLE_PROFILE_ID,
)
from backend.agents.models.messages import (
    BrowserActionRequest,
    BrowserActionResponse,
)
from backend.agents.browser.actions import (
    send_report_email,
    log_to_sheets,
    get_training_docs,
)

# Lazy-import the SDK so the agent module can still be loaded if the SDK
# isn't installed yet (e.g. during tests of other agents).
_bu_client = None


def _get_client():
    global _bu_client
    if _bu_client is None:
        from browser_use_sdk.v3 import AsyncBrowserUse
        _bu_client = AsyncBrowserUse()
    return _bu_client


browser_agent = Agent(
    name="browser_agent",
    seed=BROWSER_AGENT_SEED,
    port=8003,
    mailbox=True,
    publish_agent_details=True,
)


@browser_agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info(f"Browser Agent started -> {browser_agent.address}")
    ctx.logger.info(f"Browser Use API key present: {bool(BROWSER_USE_API_KEY)}")
    ctx.logger.info(f"Google profile ID: {GOOGLE_PROFILE_ID or 'not set'}")


# ---------------------------------------------------------------------------
# Core handler: structured BrowserActionRequest from orchestrator
# ---------------------------------------------------------------------------

ACTION_HANDLERS = {
    "send_email": send_report_email,
    "log_sheet": log_to_sheets,
    "get_training_docs": get_training_docs,
}

# Track processed requests to ignore mailbox duplicates
_processed_sessions: set[str] = set()


@browser_agent.on_message(BrowserActionRequest)
async def handle_action(ctx: Context, sender: str, msg: BrowserActionRequest):
    # Deduplicate — ignore if we already handled this session + action
    dedup_key = f"{msg.chat_session_id}:{msg.action_type}"
    if dedup_key in _processed_sessions:
        ctx.logger.info(f"Skipping duplicate: {dedup_key}")
        return
    _processed_sessions.add(dedup_key)

    ctx.logger.info(
        f"Browser action: {msg.action_type} for {msg.employee_name}"
    )

    handler = ACTION_HANDLERS.get(msg.action_type)
    if not handler:
        await ctx.send(sender, BrowserActionResponse(
            chat_session_id=msg.chat_session_id,
            action_type=msg.action_type,
            success=False,
            message=f"Unknown action type: {msg.action_type}",
        ))
        return

    client = _get_client()
    recording_url = None

    try:
        # Email uses agentmail (no Google login needed).
        # Sheets and training docs need the Google profile for authentication.
        needs_google = msg.action_type in ("log_sheet", "get_training_docs")

        session_kwargs = {"enable_recording": True}
        if needs_google and GOOGLE_PROFILE_ID:
            session_kwargs["profile_id"] = GOOGLE_PROFILE_ID

        session = await client.sessions.create(**session_kwargs)
        ctx.logger.info(f"Browser session created: {session.id}")
        ctx.logger.info(f"Live view: {session.live_url}")

        # Execute the action
        result = await handler(client, session.id, msg)
        output = getattr(result, "output", str(result)) if result else ""

        # Check if Google login failed (only relevant for sheets/docs)
        if needs_google and "NOT_LOGGED_IN" in (output or ""):
            ctx.logger.warning(
                "Google session expired. Re-run profile setup:\n"
                "  python -m backend.agents.browser.setup_profile"
            )
            response = BrowserActionResponse(
                chat_session_id=msg.chat_session_id,
                action_type=msg.action_type,
                success=False,
                message="Google login expired. Re-run profile setup to re-authenticate.",
                recording_url=None,
            )
        else:
            # Try to get recording
            try:
                recordings = await client.sessions.wait_for_recording(session.id)
                if recordings:
                    recording_url = recordings[0]
                    ctx.logger.info(f"Recording URL: {recording_url}")
                else:
                    ctx.logger.info("No recording available")
            except Exception as rec_err:
                ctx.logger.warning(f"Could not get recording: {rec_err}")

            success = result is not None and getattr(result, "status", "") != "error"

            response = BrowserActionResponse(
                chat_session_id=msg.chat_session_id,
                action_type=msg.action_type,
                success=success,
                message=output[:500] if output else "Action completed",
                recording_url=recording_url,
            )

    except Exception as e:
        ctx.logger.exception(f"Browser action failed: {e}")
        response = BrowserActionResponse(
            chat_session_id=msg.chat_session_id,
            action_type=msg.action_type,
            success=False,
            message=f"Error: {str(e)[:300]}",
        )

    finally:
        # Always stop the session to save profile state
        try:
            await client.sessions.stop(session.id)
        except Exception:
            pass

    await ctx.send(sender, response)
    ctx.logger.info(
        f"Browser action complete: {msg.action_type} "
        f"success={response.success}"
    )


# ---------------------------------------------------------------------------
# Chat protocol: demo via Agentverse chat inspector
# ---------------------------------------------------------------------------

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

    # Demo: show what the agent can do
    response_text = (
        "Browser Agent — I execute web actions on behalf of the orchestrator.\n\n"
        "Supported actions:\n"
        "  send_email — compose and send a report email via Gmail\n"
        "  log_sheet — append finding rows to a Google Sheet\n"
        "  get_training_docs — extract relevant training sections from a doc\n\n"
        f"Browser Use API key: {'configured' if BROWSER_USE_API_KEY else 'NOT SET'}\n"
        f"Google profile: {GOOGLE_PROFILE_ID or 'NOT SET'}\n\n"
        "Send me a BrowserActionRequest from the orchestrator to trigger an action."
    )

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


browser_agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    browser_agent.run()
