# AGENTS

## Health Agent — Implementation Plan

### Overview

The Health Agent receives timestamped event candidates from the video/perception pipeline and adjudicates whether each event is a food safety, hygiene, or workplace safety violation. It outputs structured findings with policy citations, severity, and training-oriented recommendations.

It does **not** detect events from video, score efficiency, send emails, or make cross-agent decisions.

### Architecture

```
┌──────────────────────────────────────────────────┐
│                  Health Agent                     │
│                                                   │
│  ┌─────────────┐   ┌──────────────┐              │
│  │  Message     │──▶│  Policy      │              │
│  │  Handler     │   │  Resolver    │              │
│  └─────────────┘   └──────┬───────┘              │
│                           │                       │
│                    ┌──────▼───────┐               │
│                    │ Adjudicator  │               │
│                    └──────┬───────┘               │
│                           │                       │
│                    ┌──────▼───────┐               │
│                    │  Severity    │               │
│                    │  Engine      │               │
│                    └──────┬───────┘               │
│                           │                       │
│                    ┌──────▼───────┐               │
│                    │ Coach Writer │               │
│                    │ (templates)  │               │
│                    └──────┬───────┘               │
│                           │                       │
│                    ┌──────▼───────┐               │
│                    │  Response    │──▶ Orchestrator│
│                    │  Builder     │               │
│                    └─────────────┘               │
└──────────────────────────────────────────────────┘
```

### File Structure

```
agents/
├── models/
│   ├── __init__.py
│   ├── config.py              # Seed phrases, agent addresses, env loading
│   └── messages.py            # Pydantic message models (shared across agents)
├── health/
│   ├── __init__.py
│   ├── health_agent.py        # Agent definition, message handlers
│   ├── policy_resolver.py     # Maps observations → policy source + rule
│   ├── adjudicator.py         # Decides status (confirmed/possible/insufficient/cleared)
│   ├── severity.py            # Simple rules table for severity
│   └── coach.py               # Deterministic templates (v1), optional LLM upgrade (v2)
└── ...
```

Follows the modular pattern from `innovation-lab-examples/fetch-hackathon-quickstarter/` — agent definition is thin, logic lives in services/modules.

### Message Models (agents/models/messages.py)

Based on the `SharedAgentState` pattern from the quickstarter, but domain-specific.

**Key design choice:** Inputs are **evidence-based observations**, not pre-adjudicated labels. The vision pipeline sends what it *saw* (e.g. `raw_food_contact`, `no_sanitation_between_tasks`), and the Health Agent decides the legal-ish conclusion (e.g. `cross_contamination`). This prevents the agent from rubber-stamping labels that already sound like violations.

```python
from uagents import Model
from typing import Optional

class Observation(Model):
    """A single thing the vision pipeline observed. These are raw evidence,
    not conclusions. The Health Agent combines observations into findings."""
    observation_id: str
    observation_type: str    # evidence-level labels (see table below)
    timestamp_start: str     # "HH:MM:SS"
    timestamp_end: str
    confidence: float        # 0.0–1.0 from vision pipeline
    description: str         # natural language from TwelveLabs

class EventCandidate(Model):
    """A group of related observations that may constitute a finding."""
    event_id: str
    observations: list[Observation]
    corrective_action_observed: Optional[bool] = None  # did recovery happen?
    corrective_action_description: Optional[str] = None

class HealthEvalRequest(Model):
    chat_session_id: str
    clip_id: str
    employee_id: str
    station_id: Optional[str] = None
    jurisdiction: str = "federal"       # "federal" | "california" | "custom"
    strictness: str = "medium"          # "low" | "medium" | "high"
    event_candidates: list[EventCandidate]
    user_sender_address: str            # for routing response back

class PolicyReference(Model):
    source_tier: str         # "fda" | "calcode" | "osha" | "house_rule"
    code: str                # e.g. "FDA Food Code 2022"
    section: str             # e.g. "3-302.11"
    short_rule: str          # human-readable summary

class HealthFinding(Model):
    event_id: str
    concluded_type: str      # the Health Agent's conclusion (e.g. "cross_contamination")
    status: str              # confirmed_violation | possible_violation | insufficient_evidence | cleared
    finding_class: str       # code_backed_food_safety | workplace_safety_rule | house_rule
    severity: str            # low | medium | high | critical
    corrective_action_observed: bool
    corrective_action_adequate: Optional[bool] = None
    policy_reference: PolicyReference
    evidence_confidence: float
    assumptions: list[str]
    reasoning: str
    training_recommendation: str
    timestamp_start: str
    timestamp_end: str

class HealthEvalResponse(Model):
    chat_session_id: str
    clip_id: str
    employee_id: str
    jurisdiction: str
    findings: list[HealthFinding]
    summary: dict            # {code_backed_count, guidance_count, highest_severity}
```

**Observation types (input vocabulary from vision pipeline):**

| Observation Type | What it means |
| --- | --- |
| `raw_food_contact` | Worker touched raw animal food |
| `rte_food_contact` | Worker touched ready-to-eat food |
| `no_sanitation_between_tasks` | No visible surface/hand sanitation between actions |
| `surface_sanitation_observed` | Worker sanitized surface (positive evidence) |
| `hand_wash_short` | Handwashing appeared shorter than expected |
| `hand_wash_skipped` | No handwashing observed after trigger event |
| `hand_to_face` | Worker touched face/hair/body |
| `bare_hand_rte` | Bare-hand contact with ready-to-eat food |
| `glove_not_changed` | Glove kept on across task switch or after contamination |
| `glove_changed` | Glove changed (positive evidence) |
| `utensil_dropped` | Utensil fell to floor/contaminated surface |
| `food_dropped` | Food item fell to floor/contaminated surface |
| `item_reused_without_wash` | Dropped/contaminated item appeared reused |
| `item_discarded` | Dropped item was discarded (positive evidence) |
| `knife_pointed_at_person` | Knife blade directed toward another worker |
| `knife_near_table_edge` | Knife placed at/near edge of prep surface |

The Health Agent reads these observations, groups them, and **concludes** the finding type (e.g. `raw_food_contact` + `rte_food_contact` + `no_sanitation_between_tasks` → `cross_contamination`).

### Agent Definition (agents/health/health_agent.py)

Follows the pattern from `fetch-hackathon-quickstarter/agents/alice/`:

```python
from uagents import Agent, Context
from dotenv import load_dotenv
import os

from agents.models.config import HEALTH_AGENT_SEED
from agents.models.messages import HealthEvalRequest, HealthEvalResponse, HealthFinding, PolicyReference
from agents.health.policy_resolver import resolve_policy
from agents.health.adjudicator import adjudicate
from agents.health.severity import assign_severity
from agents.health.coach import get_coaching_text

load_dotenv()

health_agent = Agent(
    name="health_agent",
    seed=HEALTH_AGENT_SEED,
    port=8001,
    mailbox=True,
)

@health_agent.on_message(HealthEvalRequest)
async def handle_eval(ctx: Context, sender: str, msg: HealthEvalRequest):
    ctx.logger.info(f"Health eval for clip={msg.clip_id} employee={msg.employee_id}")

    findings: list[HealthFinding] = []
    for event in msg.event_candidates:
        # 1. Read observations and conclude what type of finding this is
        obs_types = [o.observation_type for o in event.observations]
        concluded_type, policy = resolve_policy(obs_types, msg.jurisdiction)

        # 2. Decide status (does NOT auto-clear on recovery)
        status = adjudicate(event, policy, msg.strictness)

        # 3. Assign severity (recovery can reduce severity, not erase finding)
        sev = assign_severity(concluded_type, status, event.corrective_action_observed)

        # 4. Get coaching text from templates
        recommendation = get_coaching_text(concluded_type, status, policy)

        avg_confidence = sum(o.confidence for o in event.observations) / len(event.observations)

        findings.append(HealthFinding(
            event_id=event.event_id,
            concluded_type=concluded_type,
            status=status,
            finding_class=policy["finding_class"],
            severity=sev,
            corrective_action_observed=event.corrective_action_observed or False,
            corrective_action_adequate=None,  # set by adjudicator if recovery seen
            policy_reference=PolicyReference(**policy["reference"]),
            evidence_confidence=avg_confidence,
            assumptions=policy.get("assumptions", []),
            reasoning=policy["reasoning_template"].format(obs_types=obs_types),
            training_recommendation=recommendation,
            timestamp_start=event.observations[0].timestamp_start,
            timestamp_end=event.observations[-1].timestamp_end,
        ))

    code_backed = sum(1 for f in findings if f["finding_class"] == "code_backed_food_safety")
    guidance = sum(1 for f in findings if f["finding_class"] != "code_backed_food_safety")
    highest = max((f["severity"] for f in findings), key=lambda s: ["low","medium","high","critical"].index(s), default="low")

    response = HealthEvalResponse(
        chat_session_id=msg.chat_session_id,
        clip_id=msg.clip_id,
        employee_id=msg.employee_id,
        jurisdiction=msg.jurisdiction,
        findings=findings,
        summary={
            "code_backed_count": code_backed,
            "guidance_count": guidance,
            "highest_severity": highest,
        },
    )

    await ctx.send(sender, response)
    ctx.logger.info(f"Health eval complete: {len(findings)} findings, highest={highest}")

if __name__ == "__main__":
    health_agent.run()
```

### Policy Resolver (agents/health/policy_resolver.py)

The resolver does two things: (1) **concludes a finding type** from a set of observations, and (2) **looks up the policy source** for that finding type.

Key design decisions:

- **Separate code-backed findings from guidance/house-rule findings**
- **Inputs are observation bundles, not pre-labeled violations** — the resolver pattern-matches observation types to conclude the finding
- Use **CalCode or FDA** as the primary rule source depending on jurisdiction; **CDC** only for training-language reinforcement; **OSHA** only for workplace safety items. USDA "Clean/Separate/Cook/Chill" labels are optional flavor, not a v1 dependency.

```text
Finding classes:
  code_backed_food_safety  → FDA Food Code / CalCode citation
  workplace_safety_rule    → OSHA guidance / general prep safety
  house_rule               → Internal kitchen policy
```

**Observation → Conclusion mapping (how the resolver pattern-matches):**

| Observation combo | Concluded finding | Finding Class |
| --- | --- | --- |
| `raw_food_contact` + `rte_food_contact` + `no_sanitation_between_tasks` | `cross_contamination` | `code_backed_food_safety` |
| `hand_wash_short` or `hand_wash_skipped` | `insufficient_handwashing` | `code_backed_food_safety` |
| `hand_to_face` + `rte_food_contact` + `hand_wash_skipped` | `insufficient_handwashing` | `code_backed_food_safety` |
| `glove_not_changed` (after contamination trigger) | `glove_misuse` | `code_backed_food_safety` |
| `bare_hand_rte` | `bare_hand_rte_contact` | `code_backed_food_safety` |
| `utensil_dropped` + `item_reused_without_wash` | `contaminated_utensil_reuse` | `code_backed_food_safety` |
| `food_dropped` + `item_reused_without_wash` | `contaminated_food_reuse` | `code_backed_food_safety` |
| `knife_pointed_at_person` | `unsafe_knife_handling` | `workplace_safety_rule` |
| `knife_near_table_edge` | `unsafe_knife_placement` | `workplace_safety_rule` |

**Note:** `utensil_dropped` or `food_dropped` alone (without `item_reused_without_wash`) is an **incident candidate**, not a finding. If `item_discarded` is present, no finding is generated.

**Concluded finding → policy reference (5 core code-backed + 2 workplace):**

| Concluded Finding | Primary Source (federal) | Section | Primary Source (california) | Section |
| --- | --- | --- | --- | --- |
| `cross_contamination` | FDA Food Code 2022 | 3-302.11 | CalCode | 113986 |
| `insufficient_handwashing` | FDA Food Code 2022 | 2-301.12, 2-301.14 | CalCode | 113953.3 |
| `glove_misuse` | FDA Food Code 2022 | 3-304.15 | FDA Food Code 2022 | 3-304.15 |
| `bare_hand_rte_contact` | FDA Food Code 2022 | 3-301.11 | CalCode (DIFFERENT RULE) | see below |
| `contaminated_utensil_reuse` | FDA Food Code 2022 | 3-304.11 | CalCode | 113984 |

**Jurisdiction-aware logic:**

- `bare_hand_rte_contact` has **different rules** in FDA vs California. FDA generally prohibits bare-hand contact with RTE food; California allows it in approved prep areas if hands are cleaned per CalCode. The resolver must branch on `jurisdiction`.
- For all other findings, FDA and CalCode are substantively aligned — different section numbers, same rule.

### Adjudicator (agents/health/adjudicator.py)

Four statuses (not three — adding `insufficient_evidence`):

| Status | When to use |
| --- | --- |
| `confirmed_violation` | High-confidence event, clearly matches a policy rule |
| `possible_violation` | Medium confidence, or event matches but evidence is partial |
| `insufficient_evidence` | Low confidence, or critical context is missing (worker occluded, camera angle) |
| `cleared` | Observations were present but the resolver found no matching violation pattern (e.g. `utensil_dropped` + `item_discarded`) |

**Key change: recovery does NOT auto-clear a finding.** A worker can commit a real lapse and then recover correctly afterward. That should reduce severity and change coaching tone, but should **not erase the finding**. Recovery is tracked separately via `corrective_action_observed` and `corrective_action_adequate` on the `HealthFinding`.

**Decision rules:**

```text
confidence >= 0.8  → confirmed_violation
confidence >= 0.5  → possible_violation
confidence < 0.5   → insufficient_evidence

cleared is ONLY set when the observation pattern does not match any violation
(e.g. drop + discard, or positive-only observations like surface_sanitation_observed)
```

**How recovery affects findings (without erasing them):**

- `corrective_action_observed = true` + adequate → severity drops one level, coaching says "good recovery, here's how to prevent it next time"
- `corrective_action_observed = true` + inadequate → severity unchanged, coaching notes the attempt was insufficient
- `corrective_action_observed = false` → severity unchanged

Strictness adjusts confidence thresholds:

- `high`: lower thresholds by 0.1 (more aggressive flagging)
- `low`: raise thresholds by 0.1 (more lenient)
- `medium`: use defaults above

### Severity Engine (agents/health/severity.py)

Simple rules table. No complex engine for v1 — just a default per finding type with one modifier (recovery drops it one level).

**Default severity by finding type:**

| Concluded Finding | Default Severity | Rationale |
| --- | --- | --- |
| `cross_contamination` | `high` | Direct contamination risk to consumer |
| `insufficient_handwashing` | `medium` | Meaningful hygiene lapse |
| `glove_misuse` | `medium` | Contamination pathway |
| `bare_hand_rte_contact` | `medium` | Depends on jurisdiction; medium is safe default |
| `contaminated_utensil_reuse` | `high` | Direct reuse of contaminated item |
| `contaminated_food_reuse` | `critical` | Contaminated food served |
| `unsafe_knife_handling` | `medium` | Injury risk |
| `unsafe_knife_placement` | `low` | Minor prep safety issue |

**Modifiers:**

- If `corrective_action_observed = true` and adequate → drop one level (e.g. `high` → `medium`)
- If `status = insufficient_evidence` → cap at `medium` (don't flag high/critical on weak evidence)
- `critical` is reserved for direct consumer harm or contaminated food reuse. Don't over-use it.

Severity scale meaning:

| Severity | Meaning |
| --- | --- |
| `low` | Minor issue, coaching recommended |
| `medium` | Meaningful lapse, coaching required |
| `high` | Clear contamination or injury risk, flag for review |
| `critical` | Escalate to manager immediately |

### Coach Writer (agents/health/coach.py)

**v1: Deterministic templates.** Keyed by `concluded_type + status`. Stable, fast, no API dependency. Good enough for the hackathon demo.

**v2 (optional): LLM upgrade.** Wrap the template output as a base and send it to ASI-1 for polish. Only if time allows.

```python
# v1: template-based coaching
COACHING_TEMPLATES = {
    "cross_contamination": {
        "confirmed_violation": "Sanitize the food-contact surface and wash hands before switching from raw to ready-to-eat items.",
        "possible_violation": "It appears the prep area may not have been sanitized between raw and ready-to-eat handling. Always sanitize when switching tasks.",
        "insufficient_evidence": "We couldn't clearly confirm what happened here. As a reminder, always sanitize surfaces between raw and ready-to-eat tasks.",
    },
    "insufficient_handwashing": {
        "confirmed_violation": "Wash hands thoroughly for at least 20 seconds before handling food, after touching your face, and when switching tasks.",
        "possible_violation": "Handwashing appeared shorter than expected. Take the full 20 seconds, especially before food contact.",
        "insufficient_evidence": "As a reminder, thorough handwashing is required before food contact and after any contamination risk.",
    },
    "glove_misuse": {
        "confirmed_violation": "Change gloves when switching tasks, after contamination, or when they become damaged. One pair per task.",
        "possible_violation": "Gloves may not have been changed between tasks. Always swap gloves when switching from one food type to another.",
        "insufficient_evidence": "As a reminder, single-use gloves should be discarded between tasks and after any contamination event.",
    },
    # ... similar entries for bare_hand_rte_contact, contaminated_utensil_reuse, etc.
}

# Recovery addendum — appended when corrective_action_observed = true
RECOVERY_ADDENDUM = {
    True: " Good corrective action was observed — focus on preventing the initial lapse next time.",
    False: "",
}

def get_coaching_text(concluded_type: str, status: str, policy: dict) -> str:
    templates = COACHING_TEMPLATES.get(concluded_type, {})
    base = templates.get(status, f"Review {policy['short_rule']} and ensure proper procedure.")
    return base
```

**Tone rules (same as before, now enforced by template selection):**

- `confirmed_violation` → direct: "Do X next time."
- `possible_violation` → hedged: "It appears... As a habit, do X."
- `insufficient_evidence` → neutral: "As a reminder, do X."
- Recovery addendum is appended separately, never overwrites the finding.

### Output Schema

```json
{
  "agent": "health_agent",
  "clip_id": "clip_001",
  "employee_id": "worker_2",
  "jurisdiction": "california",
  "findings": [
    {
      "event_id": "evt_12",
      "concluded_type": "cross_contamination",
      "status": "confirmed_violation",
      "finding_class": "code_backed_food_safety",
      "severity": "high",
      "corrective_action_observed": false,
      "corrective_action_adequate": null,
      "policy_reference": {
        "source_tier": "calcode",
        "code": "California Retail Food Code",
        "section": "113986",
        "short_rule": "Protect food from cross-contamination by separation and sanitation"
      },
      "evidence_confidence": 0.88,
      "assumptions": ["surface was used for ready-to-eat food"],
      "reasoning": "Observations [raw_food_contact, rte_food_contact, no_sanitation_between_tasks] indicate raw-to-RTE cross-contamination without visible sanitation.",
      "training_recommendation": "Sanitize the food-contact surface and wash hands before switching from raw to ready-to-eat items.",
      "timestamp_start": "00:01:42",
      "timestamp_end": "00:01:55"
    }
  ],
  "summary": {
    "code_backed_count": 1,
    "guidance_count": 0,
    "highest_severity": "high"
  }
}
```

### Dependencies

```
uagents>=0.22.8
uagents-core>=0.3.8
python-dotenv
pydantic>=2.0
httpx>=0.27.0
```

### Environment Variables

```text
HEALTH_AGENT_SEED=<unique seed phrase>
ASI_ONE_API_KEY=<optional, only needed for v2 LLM coaching upgrade>
```

### Implementation Order

1. **`agents/models/messages.py`** — define all typed models (`Observation`, `EventCandidate`, `HealthEvalRequest`, `HealthFinding`, `PolicyReference`, `HealthEvalResponse`)
2. **`agents/models/config.py`** — seed phrases, addresses, env loading
3. **`agents/health/policy_resolver.py`** — observation-pattern → concluded-finding map + policy lookup for 5 MVP events
4. **`agents/health/adjudicator.py`** — confidence threshold logic (recovery does NOT auto-clear)
5. **`agents/health/severity.py`** — flat rules table with recovery modifier
6. **`agents/health/coach.py`** — deterministic coaching templates
7. **`agents/health/health_agent.py`** — wire it all together
8. **Test with mock `HealthEvalRequest`** — send a test message with raw observations and verify the agent concludes the right finding type, status, severity, and coaching text

### Design Decisions

- **Evidence-based inputs, not pre-adjudicated labels.** The vision pipeline sends observations (`raw_food_contact`, `no_sanitation_between_tasks`), and the Health Agent concludes the finding type (`cross_contamination`). This prevents the agent from rubber-stamping labels that already sound like violations and makes the adjudication more defensible.
- **Recovery does NOT auto-clear findings.** A real lapse happened even if the worker recovered. `corrective_action_observed` is a separate field that reduces severity and changes coaching tone, but the finding still exists in the report. `cleared` is only for when the observation pattern genuinely doesn't match a violation.
- **All models are fully typed** — `list[HealthFinding]`, not `list[dict]`. Prevents silent shape bugs.
- **Code-backed vs guidance findings** are separated so the orchestrator and report can distinguish hard citations from best-practice recommendations.
- **`insufficient_evidence`** status added — video-based detection cannot always confirm or deny, and this is safer than guessing.
- **Knife events downgraded** from health code violations to OSHA workplace safety — these are real hazards but not FDA Food Code citations.
- **Jurisdiction-aware resolver** — FDA and California disagree on bare-hand RTE contact. The agent branches, not assumes.
- **Drops and spills are incident candidates, not automatic violations** — only escalate if `item_reused_without_wash` is also observed.
- **Coaching is template-based for v1** — deterministic, no API dependency, stable for demos. LLM polish is a v2 upgrade.
- **Severity is a flat rules table** — default per finding type, one modifier for recovery. No complex engine until there's a reason for one.
- **Simplified source stack** — CalCode or FDA as primary (by jurisdiction), CDC for training reinforcement only, OSHA for workplace safety bucket. USDA labels are optional flavor.
- **Remove DOB/SSN from dashboard** — unnecessary for demo, creates privacy risk.

### LLM Integration — Making Rule-Based Logic Smarter (v2)

The v1 health agent is fully deterministic: pattern-match observations, threshold confidence, look up severity, return template coaching. This is fast, stable, and good enough for a demo. But several components can be upgraded with LLM reasoning for ambiguous cases.

**Where LLM calls could improve the pipeline:**

| Component | v1 (rule-based) | v2 (LLM-augmented) | Why it helps |
| --- | --- | --- | --- |
| **Policy Resolver** | Hardcoded observation-combo → finding-type map | LLM reads observation descriptions and concludes finding type | Handles novel observation combos the map doesn't cover; interprets natural-language descriptions from TwelveLabs |
| **Adjudicator** | Confidence threshold (0.8/0.5) | LLM weighs multiple signals: confidence, description text, corrective action context | Can reason about edge cases like "worker moved toward sink but camera cut away" instead of just checking a number |
| **Severity** | Flat default-per-type table | LLM considers context: was it near customers? repeated behavior? what food type? | Context-sensitive severity that a static table can't capture |
| **Coach Writer** | Template lookup by type + status | LLM generates specific coaching using observation descriptions | "You handled the raw chicken then touched the lettuce board" instead of generic "sanitize between tasks" |

**How to integrate (any of these LLMs work):**

```python
# Option A: ASI-1 via OpenAI SDK (proven in agent.py)
from openai import OpenAI
client = OpenAI(base_url='https://api.asi1.ai/v1', api_key=os.getenv('ASI_ONE_API_KEY'))
r = client.chat.completions.create(model="asi1", messages=[...])

# Option B: Gemini (proven in gemini-quickstart/)
from google import genai
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
r = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)

# Option C: ASI-1 via raw httpx (proven in community_agent/)
resp = httpx.post("https://api.asi1.ai/v1/chat/completions", json=payload, headers=headers)
```

**Recommended integration pattern — LLM as fallback, not replacement:**

```python
def resolve_policy(obs_types: list[str], jurisdiction: str, descriptions: list[str] = None):
    # 1. Try rule-based map first (fast, deterministic)
    concluded_type = OBSERVATION_MAP.get(frozenset(obs_types))

    if concluded_type:
        return concluded_type, POLICY_DB[concluded_type][jurisdiction]

    # 2. If no match, ask LLM to reason about it (slower, flexible)
    if descriptions:
        concluded_type = llm_classify_observations(obs_types, descriptions, jurisdiction)
        return concluded_type, POLICY_DB.get(concluded_type, UNKNOWN_POLICY)

    # 3. If no LLM available, return unclassified
    return "unclassified", UNKNOWN_POLICY
```

This way rules handle the common cases instantly, and the LLM only fires for edge cases the map doesn't cover. No latency hit on the happy path.

**Environment variables for v2:**

```text
ASI_ONE_API_KEY=<for ASI-1 integration>
GEMINI_API_KEY=<for Gemini integration>
```

**When to upgrade:** After v1 works end-to-end and you've seen real observation data from TwelveLabs. The LLM layer is most valuable when you know what the actual edge cases look like.


## Efficiency Agent

The Efficiency Agent reviews timestamped event candidates from the video pipeline and determines whether an employee's behavior reflects a meaningful workflow inefficiency, distraction, or avoidable slowdown during work.

### Core responsibility

The Efficiency Agent should answer:

- Is this behavior actually inefficient, or just a normal short pause?
- How long did it interrupt work?
- Did it happen once or repeatedly?
- Did it materially affect the workflow?
- What coaching suggestion would help improve performance?

### What it should do

The Efficiency Agent should:

- identify behaviors that reduce productivity or interrupt task flow
- distinguish brief normal pauses from actual inefficiency
- assign a severity level based on duration, frequency, and context
- explain why the behavior matters operationally
- recommend coaching-oriented improvements

### What it should evaluate

The Efficiency Agent may evaluate:

- `phone_usage`
- `extended_chatting`
- `idle_at_station`
- `slow_task_execution`
- `extended_task_interruption`
- `unnecessary_movement`
- `off_task_behavior`

For this project, the most relevant examples are:

- on phone
- chatting too long
- cutting too slowly
- unnecessary pauses in prep flow

### What it should not do

The Efficiency Agent should not:

- decide food safety violations
- decide sanitation or hygiene violations
- perform browser actions
- write the final cross-agent report
- punish normal human behavior or micro-pauses

The agent must be conservative and avoid over-flagging brief or ambiguous behavior.

### Decision guidance

Examples:

- Employee looks at phone for 2 seconds while waiting
  - `not_an_issue`
- Employee actively texts for 20 seconds during prep
  - `confirmed_issue`
- Two employees briefly exchange task-relevant words
  - `not_an_issue`
- Employee chats socially for 40 seconds while prep is paused
  - `possible_issue` or `confirmed_issue` depending on context
- Cutting speed is consistently much slower than expected across the clip
  - `possible_issue` or `confirmed_issue`

### Tone

The Efficiency Agent should frame findings as coaching for workflow improvement, not surveillance for punishment.

Avoid language like:

- "employee was lazy"

Prefer language like:

- "task flow was interrupted for a sustained period, suggesting a coaching opportunity around focus during prep"
