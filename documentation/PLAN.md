# Development Plan

> This file is the authoritative roadmap for all agents and contributors.  
> Agents implementing a phase MUST: update `current_state.md`, append to `logs.md`, and mark items `[DONE]` here.  
> Created: 2026-05-21 | Updated: 2026-05-21

---

## Guiding Principles

1. **No premature abstraction.** Build what is needed for the current phase. Three similar lines is better than a wrong abstraction.
2. **Document as you go.** Every significant decision → `tech_choix.md`. Every bug → `bugs.md`. Every change → `logs.md`.
3. **Token discipline.** All new Claude API calls must follow `src/token_optimization.py` strategies. No bare `client.messages.create()` without model/budget justification.
4. **Tests before merge.** New modules get at least one unit test and one live test (marked `[LIVE]` in `tests.md`).
5. **State stays current.** After each phase, run `DocumentationAgent().update_state()` to refresh `current_state.md`.

---

## Phase 1 — Foundation ✅ COMPLETE

**Goal:** Working skeleton with one agent, one tool, basic tests, and documented optimizations.

| Task | Status | File(s) |
|---|---|---|
| Project structure (UV, hatchling, src/ layout) | [DONE] | `pyproject.toml` |
| `SimpleAgent` with tool-use loop | [DONE] | `src/agents.py` |
| Mock tools (`fetch_sample_data`, `process_data`) | [DONE] | `src/tools.py` |
| Config with model/token constants | [DONE] | `src/config.py` |
| Token optimization module (5 strategies) | [DONE] | `src/token_optimization.py` |
| `TeammateAgent` + `Orchestrator` pattern | [DONE] | `src/teammate.py` |
| Demos (simple + teammate) | [DONE] | `examples/` |
| Initial tests | [DONE] | `tests/test_agent.py` |
| Documentation folder | [DONE] | `documentation/` |
| Fix BUG-001 (effort on Haiku) | [DONE] | `src/teammate.py` |
| Fix BUG-002 (wrong import path in demo) | [DONE] | `examples/demo.py` |

---

## Phase 2 — Real Tools & Tests 🔲 NEXT

**Goal:** Replace mock tools with real ones, add a complete test suite, fix the build config.

### 2.1 Fix build config (BUG-003) ✅ DONE

**Agent instructions:**
1. Open `pyproject.toml`.
2. Add under `[build-system]`:
   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["src"]
   ```
3. Run `uv run python -c "import src.agents"` to verify editable install works.
4. Append `[FIX] BUG-003 resolved — hatchling packages config added` to `logs.md`.
5. Update BUG-003 status to `Fixed` in `bugs.md`.

**Completed 2026-05-21.** Also fixed duplicate `dependencies` block left by `uv add`. Verified: `src.agents` and `src.doc_agent` both import cleanly via `uv run`.

### 2.2 Real tools for TeammateAgent

**Goal:** Replace `fetch_sample_data` (returns a static string) with tools that do real work.

**Candidate tools:**
- `web_search(query)` — wraps Claude's `web_search_20260209` server-side tool
- `read_file(path)` — reads a local file from the project
- `count_words(text)` — simple analytical tool (unit-testable)

**Agent instructions:**
1. Add real tools to `src/tools.py`. Keep existing mocks for backward compat.
2. Update `TOOLS_DEFINITIONS` with the new schemas.
3. Add tool-use logic to `SimpleAgent._execute_tool()`.
4. Add tool to `TeammateAgent` — choose tools at init time.
5. Write at least one unit test per new tool in `tests/test_tools.py`.
6. Document each new tool choice in `tech_choix.md`.

### 2.3 Complete test suite

**Agent instructions:**
1. Create `tests/test_token_optimization.py` with these tests (from `tests.md`):
   - `test_cached_system_format` [UNIT] — check block structure
   - `test_model_constants_valid` [UNIT] — check non-empty strings
   - `test_count_tokens_returns_int` [LIVE] — positive int result
   - `test_effort_not_on_haiku` [LIVE] — no 400 error
   - `test_orchestrator_plan_parses` [LIVE] — non-empty result
2. Create `tests/test_doc_agent.py` with tests from `tests.md`.
3. Record all results in `tests/tests.md` with date and outcome.
4. Run full suite: `uv run pytest tests/ -v`.

---

## Phase 3 — Robustness & Structured Outputs 🔲 PLANNED

**Goal:** Harden the multi-agent flow. Replace fragile string parsing with structured outputs.

### 3.1 Structured outputs for orchestrator plan

**Problem:** `Orchestrator._create()` outputs plain text with `ROLE: x | TASK: y` lines. If the model deviates, parsing silently returns no workers.

**Solution:** Use `output_config.format` with a JSON schema to enforce structure.

**Agent instructions:**
1. Define a Pydantic model `OrchestratorPlan`:
   ```python
   class WorkerTask(BaseModel):
       role: str
       task: str

   class OrchestratorPlan(BaseModel):
       tasks: list[WorkerTask]
   ```
2. Replace the plan prompt + string parser in `Orchestrator.run()` with `client.messages.parse(output_format=OrchestratorPlan)`.
3. Update tests to use the new schema.
4. Document the change in `tech_choix.md` and `logs.md`.

### 3.2 Parallel worker dispatch

**Problem:** Workers are currently called sequentially (`for line in plan_text.splitlines()`). For N workers, latency = sum(worker latencies).

**Solution:** Use `asyncio` + `AsyncAnthropic` to dispatch workers concurrently.

**Agent instructions:**
1. Add `async def ask_async(self, task: str) -> str` to `TeammateAgent` using `AsyncAnthropic`.
2. Add `async def run_async(self, task: str) -> str` to `Orchestrator` using `asyncio.gather()`.
3. Add `examples/async_demo.py` showing the async flow.
4. Measure and document latency improvement in `tests.md`.
5. Keep synchronous `run()` for backward compat.

### 3.3 Error handling and retries

**Agent instructions:**
1. Wrap all `client.messages.create()` calls with `try/except anthropic.RateLimitError, anthropic.APIStatusError`.
2. Log errors to `documentation/logs.md` via `DocumentationAgent.log_event()`.
3. Add `BUG-005` template in `bugs.md` for any new error encountered.
4. Use SDK's built-in retry (`max_retries=2` on client init) for 429/5xx.

---

## Phase 4 — Production Patterns 🔲 PLANNED

**Goal:** Add patterns suitable for production: batch processing, memory, observability.

### 4.1 Batch API demo

**Goal:** Show 50% cost savings for non-interactive workloads.

**Agent instructions:**
1. Create `examples/batch_demo.py` — submits 5 research questions as a batch.
2. Use `client.messages.batches.create()` with `claude-haiku-4-5-20251001`.
3. Poll for completion, collect results.
4. Log total tokens and estimated cost vs synchronous equivalent.
5. Document choice in `tech_choix.md`.

### 4.2 Simple memory across sessions

**Goal:** Allow agents to remember context across separate Python process runs.

**Implementation:** File-based JSON memory in `memory/sessions.json`.

**Agent instructions:**
1. Create `src/memory.py` — `save_session(key, data)`, `load_session(key)`.
2. Integrate into `Orchestrator` — optionally load prior context at init.
3. Add `test_memory_round_trip` [UNIT] to test suite.
4. Document trade-offs in `tech_choix.md` (vs Anthropic Managed Agents memory stores).

### 4.3 Observability: token usage logging

**Goal:** Log actual token usage per call to track real vs estimated costs.

**Agent instructions:**
1. Add `log_usage(response, call_type: str)` helper in `src/token_optimization.py`.
2. Call it after every `client.messages.create()` in `Orchestrator` and `TeammateAgent`.
3. Write usage entries to `documentation/logs.md` in format:
   `[USAGE] call_type | input=N | output=N | cache_read=N | model=X`
4. Add `test_log_usage_format` [UNIT] to test suite.

---

## Phase 5 — Multi-Agent Coordination 🔲 FUTURE

**Goal:** Extend to true multi-agent collaboration with specialist agents.

### 5.1 Specialist agent registry

Define a registry of specialist agents (researcher, coder, reviewer, writer) with:
- Pre-defined system prompts
- Assigned tools
- Model assignment
- Input/output schemas

### 5.2 Agent-to-agent communication

Implement a message-passing protocol between agents:
- Orchestrator dispatches with structured briefs
- Workers can request clarification (back to orchestrator)
- Results are validated against expected schema before synthesis

### 5.3 Evaluation framework

- Define quality metrics per task type
- Run benchmark tasks against single-agent vs multi-agent
- Document results in `tests/tests.md`

---

## For Agents: How to use this plan

1. **Read this file first.** Identify the next incomplete task in the earliest open phase.
2. **Check `current_state.md`** to confirm the task is still open (not done by another agent).
3. **Implement the task.** Follow agent instructions exactly.
4. **Update documentation:**
   - `logs.md` → append what you did
   - `current_state.md` → mark the task done
   - `bugs.md` → document any new bugs found
   - `tests.md` → record test results
   - `PLAN.md` → mark the task `[DONE]`
5. **Do not skip steps.** Documentation is not optional — it is how agents coordinate.
