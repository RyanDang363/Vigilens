"""
Browser actions — each function uses Browser Use Cloud SDK to perform
a real browser task.

- send_report_email: uses agentmail (built-in email per session) to send
  the report to the employee/manager. No Gmail login needed.
- log_to_sheets: navigates to a Google Sheet and appends finding rows.
- get_training_docs: navigates to a training doc and extracts relevant sections.
"""

from __future__ import annotations

from backend.agents.models.messages import BrowserActionRequest


def _format_email_body(request: BrowserActionRequest) -> str:
    """Build a plain-text email body from the report summary and findings."""
    lines = [
        f"Workplace Safety & Performance Report",
        f"Employee: {request.employee_name}",
        "",
        request.report_summary,
        "",
        "--- Findings Detail ---",
    ]
    for f in request.findings_data:
        severity = f.get("severity", "").upper()
        concluded = f.get("concluded_type", "unknown").replace("_", " ").title()
        status = f.get("status", "").replace("_", " ")
        coaching = f.get("training_recommendation") or f.get("coaching_recommendation", "")
        policy = f.get("policy_code", "") or f.get("policy_section", "")
        lines.append(f"[{severity}] {concluded} ({status})")
        if policy:
            lines.append(f"  Policy: {policy}")
        if coaching:
            lines.append(f"  Coaching: {coaching}")
        lines.append("")

    lines.append("This report was generated automatically by SafeWatch.")
    return "\n".join(lines)


def _format_sheet_rows(request: BrowserActionRequest) -> str:
    """Build text describing rows to append to a Google Sheet."""
    rows = []
    for f in request.findings_data:
        concluded = f.get("concluded_type", "unknown").replace("_", " ").title()
        severity = f.get("severity", "")
        status = f.get("status", "").replace("_", " ")
        timestamp = f.get("timestamp_start", "")
        policy = f"{f.get('policy_code', '')} {f.get('policy_section', '')}".strip()
        coaching = f.get("training_recommendation") or f.get("coaching_recommendation", "")
        rows.append(
            f"- {request.employee_name} | {concluded} | {severity} | {status} | "
            f"{timestamp} | {policy} | {coaching}"
        )
    return "\n".join(rows)


async def send_report_email(client, session_id: str, request: BrowserActionRequest):
    """Send a report email using Browser Use agentmail.

    Agentmail is enabled by default — each session gets a unique email address.
    The agent uses its built-in email to compose and send to the recipient.
    No Gmail login required.
    """
    email_body = _format_email_body(request)
    to = request.employee_email or request.manager_email or ""
    cc = request.manager_email if request.employee_email and request.manager_email else ""

    task = f"""You have a built-in email address (agentmail). Use it to send an email.

Compose and send an email with the following details:
To: {to}
{"CC: " + cc if cc else ""}
Subject: Workplace Safety & Performance Report - {request.employee_name}

Body:
{email_body}

Send this email using your agentmail capabilities. Confirm when sent."""

    result = await client.run(
        task=task,
        model="gemini-3-flash",
        session_id=session_id,
        agentmail=True,
    )
    return result


async def log_to_sheets(client, session_id: str, request: BrowserActionRequest):
    """Append finding rows to a Google Sheet."""
    rows_text = _format_sheet_rows(request)

    task = f"""Go to this Google Sheet: {request.sheet_url}

If you are not logged in or see a Google sign-in page, stop and report
"NOT_LOGGED_IN" as your output. Do NOT attempt to log in.

If you can see the spreadsheet:
For each of the following items, append a new row at the bottom of the sheet.
The columns are: Employee Name, Finding Type, Severity, Status, Timestamp, Policy Citation, Coaching Recommendation

Items to add:
{rows_text}

Type each row into the next empty row in the sheet."""

    result = await client.run(
        task=task,
        model="gemini-3-flash",
        session_id=session_id,
    )
    return result


async def get_training_docs(client, session_id: str, request: BrowserActionRequest):
    """Navigate to a training doc and extract relevant sections."""
    finding_types = [
        f.get("concluded_type", "").replace("_", " ").title()
        for f in request.findings_data
    ]
    topics = ", ".join(dict.fromkeys(finding_types))  # deduplicate, preserve order

    task = f"""Go to this training document: {request.training_doc_url}

Find sections relevant to these topics: {topics}

Extract the key training points for each topic. Return the extracted text
as a structured summary with one section per topic."""

    result = await client.run(
        task=task,
        model="gemini-3-flash",
        session_id=session_id,
    )
    return result
