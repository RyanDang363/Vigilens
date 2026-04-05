"""
Quick test for the browser agent actions.

Usage:
    python -m tests.test_browser_agent [action]

Actions:
    email   — test send_report_email (uses Browser Use agentmail)
    sheet   — test log_to_sheets (uses Sheets API via backend)
    all     — test both
"""

import asyncio
import sys
from dotenv import load_dotenv
load_dotenv()

# Test data
SAMPLE_FINDINGS = [
    {
        "concluded_type": "cross_contamination",
        "severity": "high",
        "status": "confirmed_violation",
        "timestamp_start": "00:01:42",
        "policy_code": "FDA Food Code 2022",
        "policy_section": "3-302.11",
        "training_recommendation": "Use separate tools for raw and ready-to-eat items.",
    },
    {
        "concluded_type": "insufficient_handwashing",
        "severity": "medium",
        "status": "possible_violation",
        "timestamp_start": "00:03:15",
        "policy_code": "FDA Food Code 2022",
        "policy_section": "2-301.14",
        "training_recommendation": "Wash hands for at least 20 seconds after handling raw food.",
    },
]


async def test_sheet_logging():
    """Test the Sheets API path (no browser needed)."""
    from backend.agents.browser.actions import log_to_sheets
    from backend.agents.models.messages import BrowserActionRequest

    request = BrowserActionRequest(
        chat_session_id="test-session-001",
        action_type="log_sheet",
        employee_name="Jane Doe",
        report_summary="Test report with 2 findings.",
        findings_data=SAMPLE_FINDINGS,
    )

    print("Testing log_to_sheets via Sheets API...")
    result = await log_to_sheets(request)
    print(f"Result: {result}")
    return result


async def test_email():
    """Test the email action (requires Browser Use API key)."""
    from backend.agents.browser.actions import send_report_email
    from backend.agents.models.messages import BrowserActionRequest

    request = BrowserActionRequest(
        chat_session_id="test-session-002",
        action_type="send_email",
        employee_name="Jane Doe",
        employee_email="test@example.com",
        report_summary="Test report: 2 findings detected during shift.",
        findings_data=SAMPLE_FINDINGS,
    )

    print("Testing send_report_email via Browser Use agentmail...")
    print("(This will open a cloud browser session)")

    try:
        from browser_use_sdk.v3 import AsyncBrowserUse
        client = AsyncBrowserUse()
        session = await client.sessions.create(enable_recording=True)
        print(f"Session ID: {session.id}")
        print(f"Live view: {session.live_url}")

        result = await send_report_email(client, session.id, request)
        output = getattr(result, "output", str(result)) if result else ""
        print(f"Result: {output[:300].encode('ascii', errors='replace').decode()}")

        await client.sessions.stop(session.id)
    except ImportError:
        print("browser_use_sdk not installed — skipping email test")
    except Exception as e:
        print(f"Email test error: {e}")


async def test_training_docs():
    """Test the get_training_docs action (queries local backend API)."""
    from backend.agents.browser.actions import get_training_docs
    from backend.agents.models.messages import BrowserActionRequest

    request = BrowserActionRequest(
        chat_session_id="test-session-003",
        action_type="get_training_docs",
        employee_name="Jane Doe",
        report_summary="Test report with 2 findings.",
        findings_data=SAMPLE_FINDINGS,
    )

    print("Testing get_training_docs via local backend API...")
    result = await get_training_docs(request)
    print(f"Result: {str(result)[:500].encode('ascii', errors='replace').decode()}")


async def test_research_violations():
    """Test the research_violations action (uses Browser Use)."""
    from backend.agents.browser.actions import research_violations
    from backend.agents.models.messages import BrowserActionRequest

    request = BrowserActionRequest(
        chat_session_id="test-session-004",
        action_type="research_violations",
        employee_name="Jane Doe",
        report_summary="Test report with 2 findings.",
        findings_data=SAMPLE_FINDINGS,
    )

    print("Testing research_violations via Browser Use...")
    print("(This will open a cloud browser session)")

    try:
        from browser_use_sdk.v3 import AsyncBrowserUse
        client = AsyncBrowserUse()
        session = await client.sessions.create(enable_recording=True)
        print(f"Session ID: {session.id}")
        print(f"Live view: {session.live_url}")

        result = await research_violations(client, session.id, request)
        output = getattr(result, "output", str(result)) if result else ""
        print(f"Result: {output[:500].encode('ascii', errors='replace').decode()}")

        await client.sessions.stop(session.id)
    except ImportError:
        print("browser_use_sdk not installed — skipping research test")
    except Exception as e:
        print(f"Research test error: {e}")


async def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "all"

    if action in ("sheet", "all"):
        await test_sheet_logging()
        print()

    if action in ("email", "all"):
        await test_email()

    if action in ("training", "all"):
        print()
        await test_training_docs()

    if action in ("research", "all"):
        print()
        await test_research_violations()


if __name__ == "__main__":
    asyncio.run(main())
