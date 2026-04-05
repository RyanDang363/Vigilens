import os

from dotenv import find_dotenv, load_dotenv
from uagents_core.identity import Identity

load_dotenv(find_dotenv())

HEALTH_AGENT_SEED = os.getenv("HEALTH_AGENT_SEED", "health-agent-dev-seed")
EFFICIENCY_AGENT_SEED = os.getenv("EFFICIENCY_AGENT_SEED", "efficiency-agent-dev-seed")
BROWSER_AGENT_SEED = os.getenv("BROWSER_AGENT_SEED", "browser-agent-dev-seed")
ORCHESTRATOR_SEED = os.getenv("ORCHESTRATOR_SEED", "orchestrator-dev-seed")

HEALTH_AGENT_ADDRESS = Identity.from_seed(seed=HEALTH_AGENT_SEED, index=0).address
EFFICIENCY_AGENT_ADDRESS = Identity.from_seed(seed=EFFICIENCY_AGENT_SEED, index=0).address
BROWSER_AGENT_ADDRESS = Identity.from_seed(seed=BROWSER_AGENT_SEED, index=0).address

# Browser Use Cloud
BROWSER_USE_API_KEY = (os.getenv("BROWSER_USE_API_KEY") or "").strip()
GOOGLE_PROFILE_ID = (os.getenv("GOOGLE_PROFILE_ID") or "").strip()

# Optional LLM keys (v2 upgrade)
ASI_ONE_API_KEY = (os.getenv("ASI_ONE_API_KEY") or "").strip()
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
