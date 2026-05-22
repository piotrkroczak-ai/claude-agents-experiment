# Project Statistics

> One section per completed phase. Updated at the end of each phase.
> Values marked `~` are estimates; all others are measured from git or test output.

---

## Phase 1 — Foundation

**Goal:** Working skeleton with agents, token optimizations, documentation infrastructure.

### Timeline

| Metric | Value |
|---|---|
| Start date | 2026-05-19 |
| Completion date | 2026-05-21 |
| Duration | ~3 h (estimated across two sessions) |
| Git commit | `86c6e56` (skeleton) — Phase 1 completion bundled into `5a6dfb0` |

### Codebase

| Metric | Value |
|---|---|
| Files created | ~15 source files + 5 documentation files |
| Lines of code added | ~1,800 (estimated from file sizes) |
| Lines of code modified | 0 (all new) |
| Lines deleted | 0 |
| Languages | Python, Markdown, TOML |

**Files created (Phase 1):**
`src/agents.py`, `src/tools.py`, `src/config.py`, `src/token_optimization.py`,
`src/teammate.py`, `src/doc_agent.py`, `examples/demo.py`, `examples/teammate_demo.py`,
`tests/test_agent.py`, `documentation/logs.md`, `documentation/tech_choix.md`,
`documentation/bugs.md`, `documentation/current_state.md`, `documentation/PLAN.md`,
`pyproject.toml`, `.gitignore`, `.env.example`, `README.md`, `SETUP.md`

### Quality

| Metric | Value |
|---|---|
| Bugs found | 4 |
| Bugs fixed in phase | 2 (BUG-001, BUG-002) |
| Bugs deferred | 1 (BUG-003 — hatchling build config) |
| Bugs won't fix | 1 (BUG-004 — prompt caching silently inactive on short prompts, by design) |
| Critical bugs | 1 (BUG-001 — `effort` param on Haiku 4.5 causes 400 error, caught and fixed immediately) |

### Tests

| Metric | Value |
|---|---|
| Tests created | 2 |
| Unit tests | 1 (`test_agent_init`) |
| Live tests | 1 (`test_agent_run`) |
| Unit pass rate | 1/1 — **100%** |
| Live pass rate | 0/1 — not run (no API credits at time of writing) |

### API Usage (project agents)

| Metric | Value |
|---|---|
| `log_usage()` active | No — not yet implemented |
| Agent API calls | N/A |
| Tokens consumed | N/A |
| Estimated cost | N/A |

### Documentation

| Metric | Value |
|---|---|
| Documentation files created | 5 |
| Technical choices documented | 10 (in `tech_choix.md`) |
| Bugs documented | 4 (in `bugs.md`) |
| Log entries | ~20 (in `logs.md`) |
| Plan phases written | 5 (in `PLAN.md`) |

### Dependencies

| Type | Packages added |
|---|---|
| Runtime | `anthropic>=0.25`, `python-dotenv>=1.0`, `pydantic>=2.5` |
| Dev | `pytest>=7.4`, `mypy>=1.5`, `ruff>=0.1`, `black>=23.9` |

### Key Achievements

- 4 agents designed and implemented: `SimpleAgent`, `TeammateAgent`, `Orchestrator`, `DocumentationAgent`
- 5 token optimisation strategies documented, implemented, and justified with pricing data
- Expected cost reduction vs naive Opus baseline: **~85–90%**
- Self-documenting infrastructure in place (agents maintain their own logs, bugs, state)
- Comprehensive 5-phase development plan written for agent-driven execution

---

## Phase 2 — Real Tools & Tests

**Goal:** Replace mock tools with real ones, complete the test suite, fix the build config, add token usage tracking.

### Timeline

| Metric | Value |
|---|---|
| Start date | 2026-05-21 |
| Completion date | 2026-05-22 |
| Duration | ~2 h (estimated) |
| Git commit | `5a6dfb0` |

### Codebase

| Metric | Value |
|---|---|
| Files changed | 23 |
| New files created | 15 |
| Existing files modified | 8 |
| Lines added | 2,965 |
| Lines deleted | 71 |
| Net lines added | 2,894 |

**New files (Phase 2):**
`src/token_optimization.py`, `src/teammate.py`, `src/doc_agent.py`,
`examples/teammate_demo.py`, `examples/usage_report.py`,
`tests/test_doc_agent.py`, `tests/test_token_optimization.py`, `tests/tests.md`,
`conftest.py`, `uv.lock`,
`documentation/PLAN.md`, `documentation/bugs.md`, `documentation/current_state.md`,
`documentation/logs.md`, `documentation/tech_choix.md`

**Modified files:**
`.env.example`, `.gitignore`, `README.md`, `pyproject.toml`,
`src/agents.py`, `src/config.py`, `src/tools.py`, `tests/test_agent.py`

### Quality

| Metric | Value |
|---|---|
| Bugs found | 2 |
| Bugs fixed in phase | 3 (BUG-002 re-fix in test_agent.py, BUG-003, Windows `tmp_path` permission error) |
| Bugs deferred | 0 |
| Regressions introduced | 0 |

**Bugs fixed:**
- BUG-003: hatchling `packages = ["src"]` added to `pyproject.toml`
- BUG-002 (re-manifested): `test_agent.py` still importing `src.agent` instead of `src.agents`
- Windows `tmp_path` permission error: fixed by redirecting pytest basetemp to `.pytest_tmp/`

### Tests

| Metric | Value |
|---|---|
| Tests created this phase | 14 |
| Total tests in project | 16 |
| Unit tests | 11 |
| Live tests | 5 |
| Unit pass rate | **11/11 — 100%** |
| Live pass rate | 0/5 — not run (API credits required) |
| Test files | 3 (`test_agent.py`, `test_token_optimization.py`, `test_doc_agent.py`) |

### API Usage (project agents)

| Metric | Value |
|---|---|
| `log_usage()` active | Yes — wired into all 4 agents as of this phase |
| Agent API calls | 0 (no live runs made yet) |
| Tokens consumed | 0 |
| Estimated cost | $0.00 |

> Once live tests are run, costs will appear automatically in `documentation/token_usage.jsonl`
> and `documentation/token_report.html` (generated by `uv run python examples/usage_report.py`).

### Documentation

| Metric | Value |
|---|---|
| README rewritten | Yes — English, full architecture reference |
| New documentation files | 5 (`PLAN.md`, `logs.md`, `bugs.md`, `tech_choix.md`, `current_state.md`) |
| Stats file created | This file |
| `.gitignore` entries added | 3 (`.claude/`, `token_report.html`, `.pytest_tmp/`) |

### Infrastructure

| Metric | Value |
|---|---|
| Token tracking | `log_usage()` in `src/token_optimization.py` |
| Usage storage | `documentation/token_usage.jsonl` (append-only, one JSON line per API call) |
| Dashboard | `documentation/token_report.html` (interactive Chart.js, generated on demand) |
| Dashboard charts | 3 (cost by agent, token mix by model, cumulative cost per run) |
| Pricing models covered | 3 (Opus 4.7, Sonnet 4.6, Haiku 4.5) |

### Dependencies

| Type | Change |
|---|---|
| Runtime | `anthropic` pinned to `>=0.103.1` (upgraded from `>=0.25`) |
| Runtime | `python-dotenv`, `pydantic` restored after `uv add` wiped them |
| No new packages | Dashboard uses Chart.js via CDN — zero new Python dependencies |

### Key Achievements

- `uv run python examples/...` now works correctly end-to-end (BUG-003 resolved)
- 11 unit tests passing with zero API calls required
- Every API call in every agent now automatically logged with cost calculation
- Interactive HTML dashboard ready to populate once live tests are run
- README rewritten in English with full architecture and cost reference table

---

## Phases 3–5 — Planned

| Phase | Status | Key goal |
|---|---|---|
| Phase 3 — Robustness | 🔲 Next | Structured outputs (replace ROLE:/TASK: parsing), async parallel workers |
| Phase 4 — Production Patterns | 🔲 Planned | Batch API demo, file-based memory, token usage logging (partially done) |
| Phase 5 — Multi-Agent Coordination | 🔲 Future | Specialist registry, agent-to-agent protocol, evaluation framework |

*Stats rows for these phases will be added upon completion.*
