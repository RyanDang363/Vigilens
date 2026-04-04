# CLAUDE.md

## IDEA

Tech Stack: 
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
Pitch:
We want to monitor a workspace for safety, quality control, and operational issues in real-time. Our system monitors real-world events and processes pertinent information using AI-powered agents to perform specific tasks and trigger workflows in the browser (submitting forms, filling out Google Docs/Sheets, or anything that can be done with a web browser)
Track incidents/violations for training purposes (e.g. food safety) -> email to employee/employer with a report of violations and things to improve on, specific things done wrong, etc
Features:
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
SSN
League Rank
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

Agents
health agent
efficiency agent
evidence agent
orchestrator

Project Risk Assessment
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