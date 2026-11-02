"""Deterministic routing: only implemented learning events can invoke an agent."""

from typing import Protocol


class LearningAgent(Protocol):
    agent_id: str
    prompt_version: str

    def analyze(self, evidence: dict) -> dict: ...


class AgentDispatcher:
    # Resume/retry share the original assessment task and its cache.
    ROUTES = {
        "assessment.completed": "assessment_review",
        "assessment.report_requested": "assessment_review",
    }

    def __init__(self, agents: list[LearningAgent]):
        self.agents = {agent.agent_id: agent for agent in agents}
        if len(self.agents) != len(agents):
            raise ValueError("Duplicate agent registration")

    def run(self, event: str, evidence: dict) -> dict:
        agent_id = self.ROUTES.get(event)
        if agent_id not in self.agents:
            raise ValueError("No implemented agent for this event")
        return self.agents[agent_id].analyze(evidence)
