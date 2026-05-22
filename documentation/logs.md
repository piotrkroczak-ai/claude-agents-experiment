# Project Logs

Format: `[YYYY-MM-DD] [TYPE] Description`
Types: `INIT` · `FEAT` · `FIX` · `REFACTOR` · `TEST` · `DOCS` · `BUG`

---

## 2026-05-21

- `[INIT]` Project bootstrapped with UV, hatchling, src/ layout. Dependencies: anthropic, python-dotenv, pydantic. Dev deps: pytest, mypy, ruff, black.
- `[INIT]` Added `.env.example`, `.gitignore`, `SETUP.md`, `README.md`.
- `[FEAT]` `src/agents.py` — `SimpleAgent` with manual tool-use loop. Supports `fetch_sample_data` tool. Maintains `self.messages` history across turns.
- `[FEAT]` `src/tools.py` — `fetch_sample_data()`, `process_data()`, `TOOLS_DEFINITIONS` schema list.
- `[FEAT]` `src/config.py` — centralised model/token constants, loads `ANTHROPIC_API_KEY` from `.env`.
- `[FEAT]` `examples/demo.py` — minimal runner for `SimpleAgent`.
- `[TEST]` `tests/test_agent.py` — `test_agent_init`, `test_agent_run` (live API, requires key).
- `[FEAT]` `src/token_optimization.py` — 5 documented token-saving strategies with pricing reference. Exports: `MODEL_ORCHESTRATOR`, `MODEL_WORKER`, `MAX_TOKENS_*`, `EFFORT_ORCHESTRATOR`, `cached_system()`, `count_tokens()`, `COST_SUMMARY`.
- `[FEAT]` `src/teammate.py` — `TeammateAgent` (single-turn Haiku worker) + `Orchestrator` (Sonnet planner/synthesiser). Token optimizations applied end-to-end.
- `[FEAT]` `examples/teammate_demo.py` — shows pre-call token estimate + multi-agent run with optimization summary.
- `[REFACTOR]` `src/config.py` re-exports constants from `token_optimization.py` for backward compat.
- `[FIX]` Removed `effort` param from `TeammateAgent` (Haiku 4.5 returns 400 on `effort`). Applied only to Sonnet orchestrator. Documented in `token_optimization.py` and `bugs.md`.
- `[DOCS]` Created `documentation/` folder: `logs.md`, `tech_choix.md`, `bugs.md`.
- `[DOCS]` Created `tests/tests.md` with test inventory and results.
- `[FEAT]` `src/doc_agent.py` — `DocumentationAgent` with file read/write tools, audit loop, and helpers: `log_event()`, `report_bug()`, `document_choice()`, `record_test()`.
- `[DOCS]` Created `documentation/current_state.md` and `documentation/PLAN.md` (5-phase dev plan for agent coordination).
- `[FIX]` BUG-003 resolved — added `[tool.hatch.build.targets.wheel] packages = ["src"]` to `pyproject.toml`. Verified `uv run python -c "import src.agents"` passes. Also fixed duplicate `dependencies` block left by `uv add`.
