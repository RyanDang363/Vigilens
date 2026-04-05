"""
Browser actions for the Vigilens browser agent.

- send_report_email: Browser Use agentmail to send report emails.
- log_to_sheets: Google Sheets API via the backend (no browser).
- get_training_docs: queries the local /api/training endpoint (no browser).
- research_violations: Browser Use to search online for supporting
  documentation and best practices related to findings.
"""

from __future__ import annotations

import httpx

from backend.agents.models.messages import BrowserActionRequest


def _format_email_body(request: BrowserActionRequest) -> str:
    """Build a markdown email body from the report summary and findings."""
    lines = [
        f"# Workplace Safety & Performance Report\n",
        f"**Employee:** {request.employee_name}\n",
        request.report_summary + "\n",
        "---\n",
        "## Findings\n",
    ]
    for i, f in enumerate(request.findings_data, 1):
        severity = f.get("severity", "").upper()
        concluded = f.get("concluded_type", "unknown").replace("_", " ").title()
        coaching = f.get("training_recommendation") or f.get("coaching_recommendation", "")
        policy_code = f.get("policy_code", "")
        policy_section = f.get("policy_section", "")
        reasoning = f.get("reasoning", "")
        ts = f.get("timestamp_start", "")

        lines.append(f"### {i}. {concluded} [{severity}]")
        if ts:
            lines.append(f"**Timestamp:** {ts}\n")
        if reasoning:
            lines.append(f"{reasoning}\n")
        if policy_code:
            lines.append(f"**Policy:** {policy_code} {policy_section}\n")
        if coaching:
            lines.append(f"**Coaching:** {coaching}\n")
        lines.append("")

    lines.append("---\n")
    lines.append("*This report was generated automatically by Vigilens.*")
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

    # Store the actual email content (not the Browser Use summary)
    subject = f"Workplace Safety & Performance Report - {request.employee_name}"
    full_record = (
        f"**To:** {to}\n\n"
        + (f"**CC:** {cc}\n\n" if cc else "")
        + f"**Subject:** {subject}\n\n"
        f"---\n\n"
        f"{email_body}"
    )

    class _Result:
        output = full_record
    return _Result()


async def log_to_sheets(request: BrowserActionRequest):
    """Append finding rows via the Google Sheets API (no browser needed).

    Calls the backend endpoint which uses stored OAuth tokens to append
    rows directly through the Sheets API.
    """
    # If we have a report_id, use the backend endpoint directly
    if request.report_id:
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                "http://localhost:8000/api/google/log-findings",
                params={"report_id": request.report_id},
                headers={"X-Role": "manager"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return f"Logged {data['rows_appended']} findings to sheet: {data.get('sheet_url', '')}"
            else:
                return f"Sheet API error: {resp.text}"

    # Fallback: post findings data directly to a new endpoint
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            "http://localhost:8000/api/google/log-findings-direct",
            json={
                "employee_name": request.employee_name,
                "findings": request.findings_data,
            },
            headers={"X-Role": "manager"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return f"Logged {data['rows_appended']} findings to sheet: {data.get('sheet_url', '')}"
        else:
            return f"Sheet API error: {resp.text}"


async def get_training_docs(request: BrowserActionRequest):
    """Query the local training library for docs relevant to the findings.

    Fetches all training sources from the backend, then searches their
    raw_text for mentions of the finding topics. Returns matched excerpts.
    No browser needed — these are local files uploaded by the manager.
    """
    finding_types = [
        f.get("concluded_type", "").replace("_", " ")
        for f in request.findings_data
    ]
    topics = list(dict.fromkeys(finding_types))  # deduplicate, preserve order
    keywords = set()
    for t in topics:
        keywords.update(t.lower().split())
    # Remove generic words
    keywords -= {"of", "the", "a", "an", "and", "or", "to", "in", "on", "for"}

    async with httpx.AsyncClient() as http:
        # Get all training sources
        resp = await http.get(
            "http://localhost:8000/api/training",
            headers={"X-Role": "manager"},
        )
        if resp.status_code != 200:
            return f"Failed to fetch training sources: {resp.text}"

        sources = resp.json()
        if not sources:
            return "No training documents uploaded. Upload docs on the Training page."

        matches = []
        for src in sources:
            # Fetch the full source to get raw_text
            detail_resp = await http.get(
                f"http://localhost:8000/api/training/{src['id']}",
                headers={"X-Role": "manager"},
            )
            if detail_resp.status_code != 200:
                continue

            detail = detail_resp.json()
            raw_text = detail.get("raw_text", "")
            if not raw_text:
                continue

            # Search for keyword matches in the text
            text_lower = raw_text.lower()
            matched_keywords = [kw for kw in keywords if kw in text_lower]
            if not matched_keywords:
                continue

            # Extract relevant paragraphs (ones containing keywords)
            paragraphs = raw_text.split("\n\n")
            relevant = []
            for para in paragraphs:
                para_lower = para.lower()
                if any(kw in para_lower for kw in matched_keywords):
                    relevant.append(para.strip())

            if relevant:
                matches.append({
                    "source": detail.get("title", src["id"]),
                    "matched_topics": matched_keywords,
                    "excerpts": relevant[:5],  # cap at 5 excerpts per source
                })

    if not matches:
        return (
            f"No relevant training content found for topics: {', '.join(topics)}. "
            "Consider uploading training materials on the Training page."
        )

    # Format the output
    lines = [f"Found relevant training content for: {', '.join(topics)}\n"]
    for m in matches:
        lines.append(f"--- {m['source']} (matched: {', '.join(m['matched_topics'])}) ---")
        for excerpt in m["excerpts"]:
            lines.append(excerpt)
        lines.append("")

    return "\n".join(lines)


async def research_violations(client, session_id: str, request: BrowserActionRequest):
    """Search online for supporting documentation specific to
    the employee's actual infractions.

    Uses Browser Use to search the web, visit authoritative sources
    (FDA, OSHA, CDC, etc.), and compile info tailored to each finding.
    """
    # Build a detailed description of each finding for the browser agent
    finding_details = []
    for f in request.findings_data:
        concluded = f.get("concluded_type", "unknown").replace("_", " ").title()
        severity = f.get("severity", "unknown")
        reasoning = f.get("reasoning", "")
        code = f.get("policy_code", "")
        section = f.get("policy_section", "")
        rule = f.get("policy_short_rule", "")
        coaching = f.get("training_recommendation") or f.get("coaching_recommendation", "")
        ts = f.get("timestamp_start", "")

        detail = f"- {concluded} (severity: {severity}, at {ts})"
        if reasoning:
            detail += f"\n  What happened: {reasoning}"
        if code and section:
            detail += f"\n  Cited policy: {code} {section}"
        if rule:
            detail += f"\n  Rule: {rule}"
        if coaching:
            detail += f"\n  Current coaching note: {coaching}"
        finding_details.append(detail)

    findings_text = "\n".join(finding_details)

    task = f"""An employee named {request.employee_name} received the following
workplace safety findings during a shift review:

{findings_text}

You have a real web browser. Use it to do the following — don't just read
search result snippets, actually click through and navigate the sites:

TASK 1 — Find the official regulation text:
- Go to https://www.fda.gov/food/fda-food-code/food-code-2022 and navigate
  to find the specific sections cited in the findings above (e.g. 3-302.11,
  2-301.14). Click into the relevant chapter, scroll to the section, and
  quote the actual regulation text.
- If an OSHA standard is cited, go to https://www.osha.gov/laws-regs/regulations/standardnumber
  and navigate to the specific standard.

TASK 2 — Find training videos:
- Go to https://www.youtube.com and search for training videos related to
  each violation. For example search "food safety cross contamination training"
  or "proper handwashing technique food service". For each violation, find
  1-2 relevant training videos and note their title and URL.

TASK 3 — Check real inspection enforcement:
- Go to Google and search for real health inspection cases related to these
  violations (e.g. "restaurant fined cross contamination health inspection").
  Find 1-2 real examples of consequences (fines, closures) to show why
  these violations matter.

Return a structured summary for each finding with:
- The exact regulation text you found on the official site
- The URL of the page you found it on
- Training video titles and YouTube URLs
- A real-world example of consequences for this type of violation"""

    result = await client.run(
        task=task,
        model="gemini-3-flash",
        session_id=session_id,
    )
    return result
