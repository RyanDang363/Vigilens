"""
In-memory state service for tracking orchestrator pipeline progress.

Each pipeline run is keyed by chat_session_id. The orchestrator creates
the state, sends requests to health/efficiency agents, and collects
responses as they arrive. Once all expected responses are in, it
compiles the final report.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PipelineState:
    chat_session_id: str
    clip_id: str
    employee_id: str
    employee_name: str
    employee_email: str
    manager_email: str
    jurisdiction: str
    sheet_url: str
    training_doc_url: str
    actions: list[str]
    user_sender_address: str

    # What we're waiting for
    awaiting_health: bool = False
    awaiting_efficiency: bool = False

    # Collected responses (raw dicts from agent findings)
    health_findings: list[dict] = field(default_factory=list)
    efficiency_findings: list[dict] = field(default_factory=list)

    # Summary stats
    health_code_backed: int = 0
    health_guidance: int = 0
    efficiency_count: int = 0
    highest_severity: str = "low"

    @property
    def is_complete(self) -> bool:
        return not self.awaiting_health and not self.awaiting_efficiency


class PipelineStateService:
    def __init__(self):
        self._store: dict[str, PipelineState] = {}

    def set(self, session_id: str, state: PipelineState):
        self._store[session_id] = state

    def get(self, session_id: str) -> PipelineState | None:
        return self._store.get(session_id)

    def remove(self, session_id: str):
        self._store.pop(session_id, None)


state_service = PipelineStateService()
