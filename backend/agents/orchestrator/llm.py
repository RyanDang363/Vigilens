"""
LLM integration for the orchestrator chat protocol.
Uses ASI-1 (OpenAI-compatible) for natural language understanding.
"""

from __future__ import annotations

import asyncio
import json

from openai import OpenAI

from backend.agents.models.config import ASI_ONE_API_KEY

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=ASI_ONE_API_KEY,
            base_url="https://api.asi1.ai/v1",
        )
    return _client


SYSTEM_PROMPT = """\
You are SafeWatch, an AI-powered workplace safety monitoring assistant.

You coordinate a multi-agent system that analyzes workplace footage for:
- Health code violations (FDA Food Code, California Retail Food Code)
- Workplace safety hazards (OSHA)
- Efficiency issues (phone use, distractions)

Your agents:
- Health Agent: evaluates food safety and hygiene violations with policy citations
- Efficiency Agent: detects productivity and focus issues
- Browser Agent: sends email reports, logs to Google Sheets, researches FDA/OSHA regulations, finds training videos

Available demo scenarios (employees with pre-recorded footage):
1. "Maria" (Maria Garcia) — Line cook, cross contamination + phone use (high severity)
2. "James" (James Chen) — Sous chef, unsafe knife placement + chatting (medium severity)
3. "Sarah" (Sarah Johnson) — Prep cook, glove misuse + dropped utensil reuse (critical severity)

When the user wants to run an analysis, extract these parameters from their message:
- employee: which employee/scenario (maria, james, or sarah). Default: maria
- jurisdiction: "california" or "federal". Default: california
- strictness: "low", "medium", or "high". Default: medium

Respond in JSON with this structure:
{
  "intent": "greeting" | "analyze" | "status" | "chat",
  "response": "your natural language response to the user",
  "params": {
    "employee": "maria" | "james" | "sarah",
    "jurisdiction": "california" | "federal",
    "strictness": "low" | "medium" | "high"
  }
}

Intent rules:
- "greeting": user says hi, asks what you do, asks for help, asks about payment
- "analyze": user wants to run an analysis on an employee
- "status": user asks about system status, which agents are running
- "chat": general conversation that doesn't fit the above

Always include a friendly, professional "response" field. Keep it concise (2-4 sentences).
The "params" field is only needed for "analyze" intent.
"""


async def parse_chat_message(user_text: str) -> dict:
    """Use ASI-1 to parse user intent and extract parameters."""
    client = _get_client()

    try:
        r = await asyncio.to_thread(
            client.chat.completions.create,
            model="asi1",
            temperature=0.2,
            max_tokens=300,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
        )

        raw = (r.choices[0].message.content or "").strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        if raw.startswith("json"):
            raw = raw[4:]

        parsed = json.loads(raw.strip())
        return parsed

    except (json.JSONDecodeError, Exception) as e:
        # Fallback if LLM doesn't return valid JSON
        return {
            "intent": "analyze",
            "response": f"I'll run a safety analysis for you.",
            "params": {
                "employee": "maria",
                "jurisdiction": "california",
                "strictness": "medium",
            },
        }
