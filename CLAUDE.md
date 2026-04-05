# DIAMONDHACKS 26 PROJECT

## IDEA

### Tech Stack: 
TwelveLabs = understand the video event
Semantic Video Search: Instantly find the exact moment or scene in any video using natural language.
Automated Video Summarization & Captions: Generate rich summaries, highlights, or social-ready captions for long-form or short-form content.
Custom Video Analytics: Extract insights, create Q&A bots, or build tools that understand context across hours of footage.
Fetch.ai = coordinate agent decisions
Browser Use = carry out web actions
Palantir analogy = the operational layer that stores incidents, links them to assets/locations, and records actions taken (https://www.palantir.com/docs/foundry/ontology/overview/), 
Possible other sponsor technologies:
Gemini API (if we need LLM input/output not covered by fetch.ai)
Solana, Vultr (if we need additional computing power)

### Pitch:
We want to monitor a workspace for safety, quality control, and operational issues in real-time. Our system monitors real-world events and processes pertinent information using AI-powered agents to perform specific tasks and trigger workflows in the browser (submitting forms, filling out Google Docs/Sheets, or anything that can be done with a web browser)
Track incidents/violations for training purposes (e.g. food safety) -> email to employee/employer with a report of violations and things to improve on, specific things done wrong, etc

### Features:
Must Have:
- multi-agent architecture
  - health violation agent (using authoritative health code source)
  - efficiency agent (distractions, on phone, etc)
  - final orchestral agent that uses all other agents to create report/overview of employee performance for the purpose of training -> suggest mitigation or training recommendations
- browser agent
  - sends emails
  - dashboard 
- video processing using twelvelabs
  - identifying key events and timestamps
  - specific employee/infraction performed
- Browser use to google sheets 
- Browser use to access training documents (customization)


Could Have:
AI-powered dashboard (Gemini API)
Infraction severity in report 
Solana, Vultr


Dashboard
For Manager
OAuth
Employee Profiles
Report
Name
Id
DOB
Start Date

Report
For Each Employee
Infraction
Desc
Timestamp
Clip
Mitigation Recommendation
Documentation (i.e. Sources)

Infractions:
Dropping the food
Dropping Utensil (wash or not wash)
Cutting Too Slowly (efficiency)
On Phone (Efficiency)
Chatting it up for too long
Wash hands for too little
Unsafe Knife Handling (pointer at others)
Unsafe Knife Placement (edge of table)
Cross Contamination
Record for Normal Behavior and Infractions 

### Agents

### HEALTH AGENT

### Purpose

The Health Agent reviews timestamped event candidates from the video pipeline and decides whether each event is a likely food safety or workplace safety violation. Its primary policy backbone is the FDA Food Code 2022, which is a model code for retail and food service safety. It should also use CDC food safety guidance, the USDA/FoodSafety.gov "Clean, Separate, Cook, Chill" framework, and the California Retail Food Code when the demo is framed as operating in California. :contentReference[oaicite:0]{index=0}

## Scope

The Health Agent is responsible for:

- classifying food safety violations
- classifying sanitation and hygiene violations
- classifying certain physical safety hazards in the prep area
- assigning severity
- citing the policy basis for each finding
- recommending corrective action or training follow-up

The Health Agent is **not** responsible for:

- detecting events directly from raw video
- scoring employee productivity or efficiency
- sending emails or updating browser workflows
- making final cross-agent decisions when multiple agents disagree

## Inputs
The Health Agent expects:
- `clip_id`
- `employee_id` or `worker_label`
- `location_id` or `station_id`
- `event_candidates[]` from the video/perception agent
- optional `employee_history[]`
- policy configuration:
  - `jurisdiction = federal | california | custom`
  - `strictness = low | medium | high`

### Event Types It Should Evaluate
The Health Agent should evaluate events such as:
- `cross_contamination`
- `insufficient_handwashing`
- `unsafe_knife_handling`
- `unsafe_knife_placement`
- `food_dropped`
- `utensil_dropped`
- `possible_reuse_after_contamination`
- `surface_not_sanitized`
- `hand_to_face_then_food_contact`
- `glove_misuse`

### Policy Hierarchy
Use this priority order when evaluating incidents:

1. **FDA Food Code 2022 / 2024 Supplement**
   - primary source of truth for retail food safety rules and definitions. :contentReference[oaicite:1]{index=1}
2. **California Retail Food Code**
   - use when the demo is set in California or when you want state-specific realism. CDPH states that the California Retail Food Code contains structural, equipment, and operational requirements for California retail food facilities. :contentReference[oaicite:2]{index=2}
3. **CDC food safety guidance**
   - use for risk explanation, training recommendations, and behavioral framing such as handwashing and contamination prevention. :contentReference[oaicite:3]{index=3}
4. **USDA / FoodSafety.gov principles**
   - use to map each issue to `Clean`, `Separate`, `Cook`, or `Chill` for simple human-readable explanations. :contentReference[oaicite:4]{index=4}
5. **Custom house rules**
   - optional internal rules for the demo, such as knife staging zones or required rewashing after a dropped utensil

### Core Decision Logic
For each event candidate, the Health Agent should:

1. read the event type, timestamp, confidence, and description
2. decide whether the event is:
   - `confirmed_violation`
   - `possible_violation`
   - `not_a_violation`
3. attach the policy basis
4. assign severity
5. generate a plain-language explanation
6. generate a recommended corrective action
7. return a structured finding

### Severity Rules
Use a simple severity system:

- `low`
  - minor hygiene or handling issue with limited immediate harm
  - example: handwashing appears shorter than expected but evidence is partial
- `medium`
  - meaningful safety lapse that should trigger coaching
  - example: knife placed at edge of prep table
- `high`
  - clear contamination or injury risk
  - example: probable cross contamination between raw and ready-to-eat food
- `critical`
  - repeated or severe issue that should trigger escalation
  - example: contaminated item appears reused after contact with floor or unclean surface

### Required Reasoning Behavior
For every event, the Health Agent should answer:
- What happened?
- Why is it risky?
- Which policy source supports the finding?
- How severe is it?
- What should the employee do differently next time?

### Training-Oriented Output
The Health Agent should frame recommendations as coaching, not punishment. The output should focus on:
- contamination prevention
- hygiene correction
- safer knife handling
- proper recovery after dropped or contaminated items
- surface and utensil sanitation
- repeat-prevention habits

### Special Handling Rules
- If visual evidence is weak, label the result `possible_violation`, not `confirmed_violation`.
- If the event could belong to either safety or efficiency, only score the health/safety aspect and leave efficiency scoring to the Efficiency Agent.
- If the same event appears multiple times in overlapping timestamps, merge them into one finding when appropriate.
- If a rule depends on facts the video cannot verify, explicitly mark those assumptions.

### Example Policy Mappings
- `cross_contamination`
  - principle: `Separate`
  - likely severity: `high`
  - training focus: separating raw and ready-to-eat items, sanitizing surfaces
- `insufficient_handwashing`
  - principle: `Clean`
  - likely severity: `medium` or `high`
  - training focus: proper handwashing before food contact and after contamination risks
- `unsafe_knife_placement`
  - principle: workplace safety / safe prep practice
  - likely severity: `medium`
  - training focus: store knife flat and away from table edge when not actively cutting
- `food_dropped` or `utensil_dropped`
  - principle: contamination prevention
  - likely severity: `medium` to `critical` depending on apparent reuse
  - training focus: discard or rewash before reuse

### Output Schema
The Health Agent should return JSON shaped like this:

```json
{
  "agent": "health_agent",
  "clip_id": "clip_001",
  "employee_id": "worker_2",
  "findings": [
    {
      "event_id": "evt_12",
      "event_type": "cross_contamination",
      "status": "confirmed_violation",
      "severity": "high",
      "policy_reference": {
        "code": "FDA Food Code 2022",
        "section": "3-302.11",
        "rule": "Food must be protected from cross contamination"
      }
      "principle": "Separate",
      "reasoning": "Raw-food contact appears followed by contact with ready-to-eat food or a shared prep surface without adequate separation or sanitation.",
      "training_recommendation": "Use separate tools or sanitize the surface and hands before handling ready-to-eat items.",
      "timestamp_start": "00:01:42",
      "timestamp_end": "00:01:55",
      "confidence": 0.86
    }
  ],
  "summary": {
    "violation_count": 1,
    "highest_severity": "high"
  }
}
```


### Project Risk Assessment
Multi-worker tracking may fail if video quality is low or workers overlap
Event detection may miss small actions (e.g., a dropped utensil)
Fetch.ai agent logic may become complex if you over-engineer interactions
Mitigation: Keep clips short, label actions clearly, and use simple rule-based agents. Focus on visual clarity and actionable recommendations.

## INSTRUCTIONS FOR CREATING AGENTS

Before writing any agent code, look inside `./innovation-lab-examples/` to find the most relevant example(s) for the task at hand.

Use this process:

1. Read the top-level `./innovation-lab-examples/README.md` to get an overview of what examples exist.
2. Identify the 1-3 subdirectories most relevant to the user's request based on name and purpose. Relevant signals:
   - Framework being used (uAgents, CrewAI, OpenAI SDK, Claude Agent SDK, etc.)
   - Task type (RAG, payments, A2A, browser, MCP, etc.)
   - Integration needed (Stripe, Composio, Agentverse, etc.)
3. Read the code in those subdirectories before writing anything — understand the patterns, imports, agent setup, and how protocols/handlers are structured.
4. Follow those patterns when writing new agent code unless the user explicitly asks for a different approach.

Do not guess at uAgents or Fetch.ai API patterns from memory — always ground the implementation in what the examples show.

### SEE DOCS BELOW:
https://uagents.fetch.ai/docs
https://innovationlab.fetch.ai/resources/docs/intro
https://uagents.fetch.ai/docs/examples/asi-1
https://github.com/fetchai/innovation-lab-examples/tree/main/fetch-hackathon-quickstarter
https://github.com/fetchai/innovation-lab-examples
https://innovationlab.fetch.ai/resources/docs/intro
https://asi1.ai/chat
https://agentverse.ai/