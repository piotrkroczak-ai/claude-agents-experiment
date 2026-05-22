"""Teammate agents — optimized for token cost.

Each strategy is documented in src/token_optimization.py.
"""
import uuid

from anthropic import Anthropic
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


class TeammateAgent:
    """
    Single-turn worker agent.

    Applies:
      - Strategy 1: Haiku model (80% cheaper than Opus)
      - Strategy 2: max_tokens capped at 512
      - Strategy 3: system prompt wrapped with cache_control
      - Strategy 4: stateless — no history, receives only its slice of context
      - NOTE: effort param omitted — Haiku 4.5 does NOT support it (returns 400)
    """

    def __init__(
        self,
        role: str,
        instructions: str,
        model: str = MODEL_WORKER,
        max_tokens: int = MAX_TOKENS_WORKER,
    ):
        self.client = Anthropic()
        self.role = role
        self.model = model
        self.max_tokens = max_tokens
        # Strategy 3: cache_control on system prompt.
        # Will cache if prompt >= 4096 tokens (Haiku) or >= 2048 (Sonnet).
        # For short prompts the marker is a no-op — no error, no penalty.
        self._system = cached_system(instructions)

    def ask(self, task: str, run_id: str = "") -> str:
        """Single-turn, stateless call. No history kept."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self._system,
            messages=[{"role": "user", "content": task}],
        )
        log_usage(response, agent=f"TeammateAgent[{self.role}]", call_type="ask", run_id=run_id)
        return response.content[0].text


class Orchestrator:
    """
    Plans subtasks, dispatches workers, synthesises results.

    Applies:
      - Strategy 1: Sonnet model for reasoning
      - Strategy 2: max_tokens capped at 1024
      - Strategy 3: system prompt with cache_control
      - Strategy 4: passes only a targeted brief to each worker (not full history)
      - Strategy 5: effort="medium" — good balance for planning/routing
      - thinking disabled — planning tasks don't need extended reasoning
    """

    def __init__(self, teammates: list[TeammateAgent]):
        self.client = Anthropic()
        self.teammates = {t.role: t for t in teammates}
        self._system = cached_system(
            "You are an orchestrator. Delegate subtasks to specialized teammates "
            "and synthesise their outputs into a final concise answer. "
            "Be direct — your token budget is limited."
        )

    def _create(self, messages: list[dict], run_id: str = "", call_type: str = "orchestrate") -> str:
        response = self.client.messages.create(
            model=MODEL_ORCHESTRATOR,
            max_tokens=MAX_TOKENS_ORCHESTRATOR,
            # Strategy 5: effort reduces preamble and consolidates calls (Sonnet only)
            output_config={"effort": EFFORT_ORCHESTRATOR},
            # Disable thinking: planning tasks don't need extended reasoning
            thinking={"type": "disabled"},
            system=self._system,
            messages=messages,
        )
        log_usage(response, agent="Orchestrator", call_type=call_type, run_id=run_id)
        return response.content[0].text

    def run(self, task: str) -> str:
        """Coordinate teammates to complete a task."""
        run_id = uuid.uuid4().hex[:8]

        # Step 1: plan — which roles to call and with what brief
        plan_text = self._create([{
            "role": "user",
            "content": (
                f"Task: {task}\n\n"
                f"Available teammates: {list(self.teammates.keys())}\n\n"
                "For each teammate that should contribute:\n"
                "ROLE: <role> | TASK: <brief for that teammate>\n"
                "Output only these lines, nothing else."
            ),
        }], run_id=run_id, call_type="plan")

        # Step 2: dispatch — each worker receives only its targeted brief
        results: dict[str, str] = {}
        for line in plan_text.splitlines():
            if line.startswith("ROLE:") and "| TASK:" in line:
                parts = line.split("| TASK:")
                role = parts[0].replace("ROLE:", "").strip()
                brief = parts[1].strip()
                if role in self.teammates:
                    # Strategy 4: worker receives the brief, not the full conversation
                    results[role] = self.teammates[role].ask(brief, run_id=run_id)

        if not results:
            return plan_text

        # Step 3: synthesise — orchestrator combines worker outputs
        worker_outputs = "\n\n".join(
            f"[{role}]\n{output}" for role, output in results.items()
        )
        return self._create([{
            "role": "user",
            "content": (
                f"Original task: {task}\n\n"
                f"Teammate outputs:\n{worker_outputs}\n\n"
                "Write a concise final answer."
            ),
        }], run_id=run_id, call_type="synthesise")

    def estimate_cost(self, task: str) -> dict:
        """
        Estimate token usage for the orchestration flow (uses the free count_tokens API).
        Returns a dict with estimated input tokens per call.
        """
        plan_msg = [{"role": "user", "content": f"Task: {task}\nAvailable teammates: {list(self.teammates.keys())}"}]
        plan_tokens = count_tokens(self.client, MODEL_ORCHESTRATOR, self._system, plan_msg)
        return {
            "orchestrator_plan_input_tokens": plan_tokens,
            "model_orchestrator": MODEL_ORCHESTRATOR,
            "model_worker": MODEL_WORKER,
            "max_tokens_orchestrator": MAX_TOKENS_ORCHESTRATOR,
            "max_tokens_worker": MAX_TOKENS_WORKER,
        }
