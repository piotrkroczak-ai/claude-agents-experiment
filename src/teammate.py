"""Teammate agents — optimized for token cost.

Phase 3 additions:
  - Structured outputs: OrchestratorPlan replaces fragile ROLE:/TASK: string parsing
  - Async parallel dispatch: ask_async() + run_async() via AsyncAnthropic
  - Error handling: max_retries=2 on all clients, explicit except on API errors
"""
from __future__ import annotations

import asyncio
import uuid

from src.memory import load_session, save_session

from anthropic import (
    Anthropic,
    AsyncAnthropic,
    RateLimitError,
    APIStatusError,
    APIConnectionError,
)
from pydantic import BaseModel

from src.token_optimization import (
    MODEL_ORCHESTRATOR,
    MODEL_WORKER,
    MAX_TOKENS_ORCHESTRATOR,
    MAX_TOKENS_WORKER,
    EFFORT_ORCHESTRATOR,
    cached_system,
    count_tokens,
    log_usage,
)


# ---------------------------------------------------------------------------
# Structured output schema (Phase 3.1)
# ---------------------------------------------------------------------------

class WorkerTask(BaseModel):
    role: str
    task: str

class OrchestratorPlan(BaseModel):
    tasks: list[WorkerTask]


# API requires additionalProperties: false on every object node in the schema
_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "task": {"type": "string"},
                },
                "required": ["role", "task"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["tasks"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# TeammateAgent
# ---------------------------------------------------------------------------

class TeammateAgent:
    """
    Single-turn worker agent.

    Strategies applied:
      1. Haiku model — 80% cheaper than Opus
      2. max_tokens capped at 512
      3. cache_control on system prompt
      4. Stateless — receives only its task brief
      NOTE: effort param omitted — Haiku 4.5 returns 400 on effort
    """

    def __init__(
        self,
        role: str,
        instructions: str,
        model: str = MODEL_WORKER,
        max_tokens: int = MAX_TOKENS_WORKER,
    ):
        # max_retries=2: SDK auto-retries 429 and 5xx (Phase 3.3)
        self.client = Anthropic(max_retries=2)
        self.role = role
        self.model = model
        self.max_tokens = max_tokens
        self._system = cached_system(instructions)
        self._async_client: AsyncAnthropic | None = None

    def ask(self, task: str, run_id: str = "") -> str:
        """Single-turn, stateless call."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self._system,
                messages=[{"role": "user", "content": task}],
            )
        except RateLimitError:
            raise
        except (APIStatusError, APIConnectionError) as e:
            raise RuntimeError(f"TeammateAgent[{self.role}] API error: {e}") from e
        log_usage(response, agent=f"TeammateAgent[{self.role}]", call_type="ask", run_id=run_id)
        return response.content[0].text

    async def ask_async(self, task: str, run_id: str = "") -> str:
        """Async single-turn call for parallel dispatch (Phase 3.2)."""
        if self._async_client is None:
            self._async_client = AsyncAnthropic(max_retries=2)
        try:
            response = await self._async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self._system,
                messages=[{"role": "user", "content": task}],
            )
        except RateLimitError:
            raise
        except (APIStatusError, APIConnectionError) as e:
            raise RuntimeError(f"TeammateAgent[{self.role}] async API error: {e}") from e
        log_usage(response, agent=f"TeammateAgent[{self.role}]", call_type="ask_async", run_id=run_id)
        return response.content[0].text


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Plans subtasks, dispatches workers, synthesises results.

    Strategies applied:
      1. Sonnet model for reasoning
      2. max_tokens capped at 1024
      3. cache_control on system prompt
      4. Workers receive a targeted brief, not full history
      5. effort=medium on synthesis call
      6. Structured JSON output for plan (Phase 3.1) — no fragile string parsing
      7. Async parallel worker dispatch via run_async() (Phase 3.2)
    """

    def __init__(self, teammates: list[TeammateAgent], memory_key: str | None = None):
        self.client = Anthropic(max_retries=2)
        self.teammates = {t.role: t for t in teammates}
        self._system = cached_system(
            "You are an orchestrator. Delegate subtasks to specialized teammates "
            "and synthesise their outputs into a final concise answer. "
            "Be direct — your token budget is limited."
        )
        self._memory_key = memory_key
        self._prior_context: dict = load_session(memory_key) if memory_key else {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _plan(self, task: str, run_id: str) -> OrchestratorPlan:
        """Return a structured plan. Uses JSON schema output — no string parsing."""
        try:
            response = self.client.messages.create(
                model=MODEL_ORCHESTRATOR,
                max_tokens=MAX_TOKENS_ORCHESTRATOR,
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": _PLAN_SCHEMA,
                    }
                },
                thinking={"type": "disabled"},
                system=self._system,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Task: {task}\n\n"
                        f"Available teammates: {list(self.teammates.keys())}\n\n"
                        "Assign each relevant teammate a focused subtask."
                    ),
                }],
            )
        except RateLimitError:
            raise
        except (APIStatusError, APIConnectionError) as e:
            raise RuntimeError(f"Orchestrator plan error: {e}") from e
        log_usage(response, agent="Orchestrator", call_type="plan", run_id=run_id)
        return OrchestratorPlan.model_validate_json(response.content[0].text)

    def _synthesise(self, task: str, results: dict[str, str], run_id: str) -> str:
        """Combine worker outputs into a final answer."""
        worker_outputs = "\n\n".join(f"[{role}]\n{out}" for role, out in results.items())
        try:
            response = self.client.messages.create(
                model=MODEL_ORCHESTRATOR,
                max_tokens=MAX_TOKENS_ORCHESTRATOR,
                output_config={"effort": EFFORT_ORCHESTRATOR},
                thinking={"type": "disabled"},
                system=self._system,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Original task: {task}\n\n"
                        f"Teammate outputs:\n{worker_outputs}\n\n"
                        "Write a concise final answer."
                    ),
                }],
            )
        except RateLimitError:
            raise
        except (APIStatusError, APIConnectionError) as e:
            raise RuntimeError(f"Orchestrator synthesise error: {e}") from e
        log_usage(response, agent="Orchestrator", call_type="synthesise", run_id=run_id)
        return response.content[0].text

    # ------------------------------------------------------------------
    # Public API — synchronous
    # ------------------------------------------------------------------

    def run(self, task: str) -> str:
        """Coordinate teammates synchronously (sequential worker dispatch)."""
        run_id = uuid.uuid4().hex[:8]

        plan = self._plan(task, run_id)

        results: dict[str, str] = {}
        for wt in plan.tasks:
            if wt.role in self.teammates:
                results[wt.role] = self.teammates[wt.role].ask(wt.task, run_id=run_id)

        if not results:
            return str(plan.model_dump())

        answer = self._synthesise(task, results, run_id)
        if self._memory_key:
            save_session(self._memory_key, {"last_task": task, "result": answer})
        return answer

    # ------------------------------------------------------------------
    # Public API — asynchronous (Phase 3.2)
    # ------------------------------------------------------------------

    async def run_async(self, task: str) -> str:
        """Coordinate teammates with parallel worker dispatch via asyncio.gather()."""
        run_id = uuid.uuid4().hex[:8]

        # Plan is synchronous — needed before we can dispatch workers
        plan = self._plan(task, run_id)

        async def dispatch(wt: WorkerTask) -> tuple[str, str]:
            if wt.role not in self.teammates:
                return wt.role, f"No teammate with role '{wt.role}'"
            result = await self.teammates[wt.role].ask_async(wt.task, run_id=run_id)
            return wt.role, result

        pairs = await asyncio.gather(*[dispatch(wt) for wt in plan.tasks])
        results = dict(pairs)

        if not results:
            return str(plan.model_dump())

        answer = self._synthesise(task, results, run_id)
        if self._memory_key:
            save_session(self._memory_key, {"last_task": task, "result": answer})
        return answer

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def estimate_cost(self, task: str) -> dict:
        """Pre-call token estimate using the free count_tokens endpoint."""
        plan_msg = [{"role": "user", "content": f"Task: {task}\nAvailable teammates: {list(self.teammates.keys())}"}]
        plan_tokens = count_tokens(self.client, MODEL_ORCHESTRATOR, self._system, plan_msg)
        return {
            "orchestrator_plan_input_tokens": plan_tokens,
            "model_orchestrator": MODEL_ORCHESTRATOR,
            "model_worker": MODEL_WORKER,
            "max_tokens_orchestrator": MAX_TOKENS_ORCHESTRATOR,
            "max_tokens_worker": MAX_TOKENS_WORKER,
        }
