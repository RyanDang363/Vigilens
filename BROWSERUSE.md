USE THIS DOCUMENTATION FOR CONTEXT:
https://docs.browser-use.com/cloud/llms.txt

# Browser Agent — Design Document

## Purpose

The Browser Agent is the **action layer** of the system. After the Health Agent and Efficiency Agent produce findings and the orchestrator compiles a report, the Browser Agent carries out real-world actions: sending emails, filling Google Sheets, and accessing training documents. It uses [Browser Use Cloud](https://docs.browser-use.com) to drive a real browser with natural language instructions.

It does **not** analyze video, decide violations, or produce findings — it receives structured reports and acts on them.

## What It Does

### Must-Have Actions

1. **Send report emails** — compose and send an email (via Gmail or any webmail) to the employee and/or manager with a summary of findings, coaching recommendations, and relevant policy citations
2. **Log findings to Google Sheets** — open a Google Sheet and append rows for each finding: employee name, finding type, severity, timestamp, coaching text, policy citation
3. **Access training documents** — navigate to a training doc URL (Google Docs, company wiki, etc.) and extract relevant sections based on the finding types in the report

### Could-Have Actions

4. **Generate report PDF** — use the browser to navigate to the dashboard report page and trigger a print-to-PDF
5. **Post to Slack** — send a summary message to a Slack channel

## Architecture

```text
┌──────────────────────────────────────────────────┐
│                Orchestrator Agent                  │
│  (compiles Health + Efficiency findings)          │
│                      │                             │
│                      ▼                             │
│              Browser Agent                         │
│         (receives report data)                     │
│                      │                             │
│          ┌───────────┼───────────┐                │
│          ▼           ▼           ▼                │
│      Send Email   Log Sheet   Get Training Docs   │
│   (Browser Use)  (Browser Use)  (Browser Use)     │
└──────────────────────────────────────────────────┘
```

The Browser Agent is a uAgents agent that:
1. Receives a `BrowserActionRequest` from the orchestrator
2. Determines which action(s) to perform
3. Calls Browser Use Cloud SDK to execute each action in a real browser
4. Returns a `BrowserActionResponse` with success/failure status

## Integration with Browser Use Cloud

### SDK Setup

```python
from browser_use_sdk.v3 import AsyncBrowserUse

client = AsyncBrowserUse()  # Uses BROWSER_USE_API_KEY env var
```

### Why Cloud (not local)

- No local Chromium/Playwright install needed
- Stealth browsing with residential proxies (avoids bot detection on Gmail, Google Sheets)
- Session recording for demo playback
- Persistent browser profiles (stay logged into Google across runs)

### Key SDK Methods We'll Use

| Method | Purpose |
| --- | --- |
| `client.run(task, ...)` | Execute a natural-language browser task |
| `client.sessions.create(profile_id=...)` | Start session with saved Google login |
| `client.sessions.stop(session_id)` | End session and save profile state |
| `client.profiles.create(name)` | Create a persistent login profile |

### Model Choice

Use `gemini-3-flash` for browser actions — cheapest ($0.60/M input) and fast enough for form-filling and email composition. No need for Opus-level reasoning here.

```python
result = await client.run(
    task="...",
    model="gemini-3-flash",
    session_id=session.id,
)
```

## Message Models

```python
from uagents import Model
from typing import Optional

class BrowserActionRequest(Model):
    """Sent by the orchestrator to the Browser Agent."""
    chat_session_id: str
    action_type: str        # "send_email" | "log_sheet" | "get_training_docs"
    employee_name: str
    employee_email: Optional[str] = None
    manager_email: Optional[str] = None
    report_summary: str     # formatted text summary of findings
    findings_data: list[dict]  # raw finding dicts for sheet logging
    sheet_url: Optional[str] = None  # Google Sheets URL
    training_doc_url: Optional[str] = None

class BrowserActionResponse(Model):
    """Sent back to the orchestrator."""
    chat_session_id: str
    action_type: str
    success: bool
    message: str            # human-readable result or error
    recording_url: Optional[str] = None  # MP4 of the browser session
```

## Action Implementations

### 1. Send Report Email

```python
async def send_report_email(client, session_id, request):
    email_body = format_email_body(request.report_summary, request.findings_data)

    result = await client.run(
        task=f"""
        Go to Gmail. Compose a new email.
        To: {request.employee_email}
        CC: {request.manager_email}
        Subject: Workplace Safety & Performance Report - {request.employee_name}
        Body:
        {email_body}

        Send the email.
        """,
        model="gemini-3-flash",
        session_id=session_id,
    )
    return result
```

### 2. Log Findings to Google Sheets

```python
async def log_to_sheets(client, session_id, request):
    rows_text = format_sheet_rows(request.findings_data)

    result = await client.run(
        task=f"""
        Go to this Google Sheet: {request.sheet_url}
        For each of the following rows, append a new row at the bottom of the sheet:
        {rows_text}

        Each row has columns: Employee Name, Finding Type, Severity, Status,
        Timestamp, Policy Citation, Coaching Recommendation
        """,
        model="gemini-3-flash",
        session_id=session_id,
    )
    return result
```

### 3. Access Training Documents

```python
async def get_training_docs(client, session_id, request):
    finding_types = [f["concluded_type"] for f in request.findings_data]

    result = await client.run(
        task=f"""
        Go to this training document: {request.training_doc_url}
        Find sections relevant to these topics: {', '.join(finding_types)}
        Extract the key training points for each topic.
        Return the extracted text.
        """,
        model="gemini-3-flash",
        session_id=session_id,
        output_schema=TrainingExtracts,  # structured output
    )
    return result
```

## Authentication Strategy

Use **persistent browser profiles** so we only log into Google once:

```python
# One-time setup: create profile and log in manually
profile = await client.profiles.create(name="workspace-google-account")
session = await client.sessions.create(profile_id=profile.id)
print(f"Log in at: {session.live_url}")
input("Complete Google login + 2FA, then press Enter...")
await client.sessions.stop(session.id)  # saves cookies

# All future runs: reuse the profile, no login needed
session = await client.sessions.create(profile_id=profile.id)
result = await client.run(task="...", session_id=session.id)
```

For the hackathon demo, do this setup once before presenting. The profile persists across runs.

## uAgents Integration

The Browser Agent follows the same pattern as Health/Efficiency agents:

```python
from uagents import Agent, Context
from browser_use_sdk.v3 import AsyncBrowserUse

browser_agent = Agent(
    name="browser_agent",
    seed=BROWSER_AGENT_SEED,
    port=8003,
    mailbox=True,
    publish_agent_details=True,
)

bu_client = AsyncBrowserUse()

@browser_agent.on_message(BrowserActionRequest)
async def handle_action(ctx: Context, sender: str, msg: BrowserActionRequest):
    ctx.logger.info(f"Browser action: {msg.action_type} for {msg.employee_name}")

    session = await bu_client.sessions.create(
        profile_id=GOOGLE_PROFILE_ID,
        enable_recording=True,
    )

    try:
        if msg.action_type == "send_email":
            result = await send_report_email(bu_client, session.id, msg)
        elif msg.action_type == "log_sheet":
            result = await log_to_sheets(bu_client, session.id, msg)
        elif msg.action_type == "get_training_docs":
            result = await get_training_docs(bu_client, session.id, msg)
        else:
            result = None

        recording = await bu_client.sessions.wait_for_recording(session.id)

        response = BrowserActionResponse(
            chat_session_id=msg.chat_session_id,
            action_type=msg.action_type,
            success=result is not None and result.status != "error",
            message=result.output if result else "Unknown action type",
            recording_url=recording[0] if recording else None,
        )
    except Exception as e:
        response = BrowserActionResponse(
            chat_session_id=msg.chat_session_id,
            action_type=msg.action_type,
            success=False,
            message=str(e),
        )
    finally:
        await bu_client.sessions.stop(session.id)

    await ctx.send(sender, response)
```

## Dashboard Integration

The dashboard triggers browser actions via the backend API:

```text
Dashboard "Send Report" button
    → POST /api/reports/{id}/email
    → Backend sends BrowserActionRequest to Browser Agent
    → Browser Agent opens Gmail via Browser Use, sends email
    → Returns success + recording URL
    → Dashboard shows confirmation + optional recording playback
```

The same pattern works for "Log to Sheets" and "Get Training Docs" buttons.

## Environment Variables

```text
BROWSER_USE_API_KEY=bu_your_key_here
BROWSER_AGENT_SEED=<unique seed phrase>
GOOGLE_PROFILE_ID=<profile ID from one-time setup>
```

## Dependencies

```text
browser-use-sdk
uagents>=0.22.8
uagents-core>=0.3.8
python-dotenv
```

## Implementation Order

1. **Install SDK** — `pip install browser-use-sdk`
2. **Create Google profile** — one-time login setup via live URL
3. **Message models** — add `BrowserActionRequest` / `BrowserActionResponse` to messages.py
4. **Email action** — implement `send_report_email()` and test standalone
5. **Sheets action** — implement `log_to_sheets()` and test standalone
6. **Browser agent** — wire into uAgents with message handlers
7. **Dashboard endpoint** — `POST /api/reports/{id}/email` triggers the browser agent
8. **Demo** — record a session showing email send + sheet logging

## Demo Strategy

For the hackathon demo:

1. Pre-authenticate the Google profile (do this before presenting)
2. Show a report in the dashboard
3. Click "Send Report" — the browser agent opens Gmail, composes the email with findings, and sends it
4. Show the Google Sheet updating with logged findings
5. Play back the session recording to show what the browser did

The recording URL from Browser Use is an MP4 that can be embedded in the dashboard or shown as proof of action.

## Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Google login expires mid-demo | Re-authenticate profile 30 min before demo |
| Gmail bot detection | Browser Use has stealth + residential proxies enabled by default |
| Slow browser execution | Use `gemini-3-flash` (fastest model), keep tasks focused |
| Browser Use API is down | Have a pre-recorded session as backup |
| Email formatting is off | Pre-test the email body format; keep it simple plain text |
