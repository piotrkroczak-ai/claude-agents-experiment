"""
Specialist agent registry and sequential pipeline (Phase 5.1 + 5.2).

SpecialistRegistry — pre-configured TeammateAgent instances addressable by role.
AgentPipeline      — chain agents where each stage receives the prior output as context.
"""
from __future__ import annotations

import uuid

from src.teammate import TeammateAgent
from src.token_optimization import MODEL_WORKER

# ---------------------------------------------------------------------------
# Pre-configured specialist definitions
# ---------------------------------------------------------------------------

SPECIALIST_CONFIGS: dict[str, dict] = {
    "researcher": {
        "instructions": (
            "You are a precise technical researcher. "
            "Find relevant facts and explain them concisely. "
            "Cite your reasoning. Answer in 2-3 sentences."
        ),
        "model": MODEL_WORKER,
    },
    "coder": {
        "instructions": (
            "You are a concise Python expert. "
            "Write clean, working code snippets with minimal explanation. "
            "Use type hints. No boilerplate."
        ),
        "model": MODEL_WORKER,
    },
    "reviewer": {
        "instructions": (
            "You are a sharp code and text reviewer. "
            "Identify the single most important issue or improvement. "
            "Be direct — one key point only."
        ),
        "model": MODEL_WORKER,
    },
    "writer": {
        "instructions": (
            "You are a technical writer. "
            "Transform raw information into clear, structured prose. "
            "Use plain language and be concise."
        ),
        "model": MODEL_WORKER,
    },
}


# ---------------------------------------------------------------------------
# SpecialistRegistry
# ---------------------------------------------------------------------------

class SpecialistRegistry:
    """
    Pre-configured specialist agents, addressable by role name.

    Usage:
        reg = SpecialistRegistry()                    # all 4 specialists
        reg = SpecialistRegistry(roles=["coder"])     # subset
        agent = reg.get("researcher")
        orch  = Orchestrator(teammates=reg.subset(["researcher", "writer"]))
    """

    def __init__(self, roles: list[str] | None = None):
        wanted = roles or list(SPECIALIST_CONFIGS.keys())
        self._agents: dict[str, TeammateAgent] = {
            role: TeammateAgent(role=role, **SPECIALIST_CONFIGS[role])
            for role in wanted
            if role in SPECIALIST_CONFIGS
        }

    def get(self, role: str) -> TeammateAgent:
        if role not in self._agents:
            raise KeyError(f"No specialist with role '{role}'. Available: {self.roles}")
        return self._agents[role]

    def all(self) -> list[TeammateAgent]:
        return list(self._agents.values())

    def subset(self, roles: list[str]) -> list[TeammateAgent]:
        return [self._agents[r] for r in roles if r in self._agents]

    @property
    def roles(self) -> list[str]:
        return list(self._agents.keys())


# ---------------------------------------------------------------------------
# AgentPipeline
# ---------------------------------------------------------------------------

class AgentPipeline:
    """
    Sequential pipeline: output of stage N feeds into stage N+1.

    Each stage receives:
        "Original task: <task>\\n\\nWork so far from [<role>]:\\n<output>\\n\\nContinue..."

    Use when agents should refine each other's work (research → write → review).
    Use Orchestrator.run_async() instead when stages are independent.
    """

    def __init__(self, stages: list[TeammateAgent]):
        self.stages = stages

    def run(self, task: str) -> dict[str, str]:
        """Execute pipeline sequentially. Returns {role: output} for all stages."""
        run_id = uuid.uuid4().hex[:8]
        results: dict[str, str] = {}
        context = task

        for agent in self.stages:
            output = agent.ask(context, run_id=run_id)
            results[agent.role] = output
            context = (
                f"Original task: {task}\n\n"
                f"Work so far from [{agent.role}]:\n{output}\n\n"
                "Continue, refine, or build on the above."
            )

        return results

    def final(self, task: str) -> str:
        """Run pipeline and return only the last stage's output."""
        results = self.run(task)
        return results[self.stages[-1].role] if self.stages else ""
