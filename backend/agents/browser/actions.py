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
        async with httpx.AsyncClient(timeout=60.0) as http:
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
    async with httpx.AsyncClient(timeout=60.0) as http:
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

    Uses ASI-1 to semantically match training documents to finding topics
    and extract the most relevant excerpts.
    No browser needed — these are local files uploaded by the manager.
    """
    import asyncio
    import os
    from openai import OpenAI

    finding_types = [
        f.get("concluded_type", "").replace("_", " ")
        for f in request.findings_data
    ]
    topics = list(dict.fromkeys(finding_types))  # deduplicate, preserve order

    async with httpx.AsyncClient(timeout=60.0) as http:
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

        # Collect all document texts
        docs = []
        for src in sources:
            detail_resp = await http.get(
                f"http://localhost:8000/api/training/{src['id']}",
                headers={"X-Role": "manager"},
            )
            if detail_resp.status_code != 200:
                continue
            detail = detail_resp.json()
            raw_text = detail.get("raw_text", "")
            if raw_text:
                docs.append({
                    "title": detail.get("title", src["id"]),
                    "text": raw_text,
                })

        if not docs:
            return "No training documents with content found."

        # Build a combined context of all docs (truncate each to avoid token limits)
        doc_context = ""
        for i, doc in enumerate(docs):
            truncated = doc["text"][:3000]
            doc_context += f"\n\n--- Document {i+1}: {doc['title']} ---\n{truncated}"

        prompt = (
            f"You are analyzing workplace training documents for a food safety monitoring system.\n\n"
            f"The following violations/topics were detected:\n"
            f"{chr(10).join(f'- {t}' for t in topics)}\n\n"
            f"Here are the available training documents:\n{doc_context}\n\n"
            f"For each topic, find the most relevant excerpts from the documents above. "
            f"Return your response in this format:\n"
            f"--- [Document Title] (relevant to: [topic]) ---\n"
            f"[relevant excerpt from the document]\n\n"
            f"If no documents are relevant to a topic, say so. Be concise — return only "
            f"the most directly relevant paragraphs or sentences, not the entire document."
        )

        client = OpenAI(
            api_key=os.getenv("ASI_ONE_API_KEY", ""),
            base_url="https://api.asi1.ai/v1",
        )
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="asi1",
            temperature=0.2,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": "You extract relevant excerpts from training documents based on detected workplace violations."},
                {"role": "user", "content": prompt},
            ],
        )

        result_text = response.choices[0].message.content or ""

    if not result_text.strip():
        return (
            f"No relevant training content found for topics: {', '.join(topics)}. "
            "Consider uploading training materials on the Training page."
        )

    return f"Found relevant training content for: {', '.join(topics)}\n\n{result_text}"


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

    # Pick the top 2 most severe findings to research (avoid timeout)
    sorted_findings = sorted(
        finding_details,
        key=lambda d: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(
            d.split("severity: ")[1].split(",")[0] if "severity: " in d else "low", 0
        ),
        reverse=True,
    )
    focused = "\n".join(sorted_findings[:2])

    task = f"""An employee named {request.employee_name} had these workplace safety findings:

{focused}

Do TWO things using your browser:

1. Go to https://www.youtube.com and search for a training video for each
   finding (e.g. search "cross contamination food safety training").
   For each finding, get the title and URL of the top relevant video.

2. Go to https://www.fda.gov/food/fda-food-code/food-code-2022 and find
   the specific section cited in the finding. Quote the regulation text.

Return a structured markdown summary with:
- Finding name and severity
- The YouTube training video title and URL
- The official regulation text and source URL"""

    result = await client.run(
        task=task,
        model="gemini-3-flash",
        session_id=session_id,
    )
    return result
