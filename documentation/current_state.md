# Project Current State

> Maintained automatically by `DocumentationAgent` via `update_state()`.  
> Last updated: 2026-05-21  
> Update trigger: run `uv run python -c "from src.doc_agent import DocumentationAgent; DocumentationAgent().update_state()"`

---

## Status: 🟡 In Progress — Phase 2 underway (2.1 done, 2.2 + 2.3 next)

---

## What exists and works

### Source code (`src/`)

| File | Status | Description |
|---|---|---|
| `config.py` | ✅ Done | Re-exports model/token constants from `token_optimization.py` |
| `tools.py` | ✅ Done | `fetch_sample_data()`, `process_data()`, `TOOLS_DEFINITIONS` |
| `agents.py` | ✅ Done | `SimpleAgent` — single-agent with manual tool-use loop |
| `token_optimization.py` | ✅ Done | 5 strategies documented + implemented. Exports: models, budgets, `cached_system()`, `count_tokens()` |
| `teammate.py` | ✅ Done | `TeammateAgent` (Haiku worker) + `Orchestrator` (Sonnet planner). Optimizations applied |
| `doc_agent.py` | ✅ Done | `DocumentationAgent` — reads/writes docs, runs audit, appends entries |

### Examples (`examples/`)

| File | Status | Description |
|---|---|---|
| `demo.py` | ✅ Done | Runs `SimpleAgent` with a single query |
| `teammate_demo.py` | ✅ Done | Shows token estimates + multi-agent orchestration |

### Documentation (`documentation/`)

| File | Status | Description |
|---|---|---|
| `logs.md` | ✅ Done | Project activity log, append-only |
| `tech_choix.md` | ✅ Done | 10 justified technical choices |
| `bugs.md` | ✅ Done | 4 bugs documented (3 fixed, 1 won't fix) |
| `current_state.md` | ✅ Done | This file — project snapshot |
| `PLAN.md` | ✅ Done | Comprehensive dev plan for agents to follow |

### Tests (`tests/`)

| File | Status | Description |
|---|---|---|
| `test_agent.py` | ✅ Done | 2 tests: init (unit) + run (live) |
| `tests.md` | ✅ Done | Full test inventory with results and planned tests |
| `test_token_optimization.py` | 🔲 Planned | See `tests.md` → planned test list |
| `test_doc_agent.py` | 🔲 Planned | See `tests.md` → planned test list |

---

## What is NOT yet done (open items)

| Item | Priority | Tracked in |
|---|---|---|
| ~~Fix `pyproject.toml` hatchling packages config (BUG-003)~~ | ✅ Fixed | `bugs.md` |
| `test_token_optimization.py` — unit + live tests | High | `tests.md`, `PLAN.md` Phase 2 |
| `test_doc_agent.py` — unit tests | Medium | `tests.md`, `PLAN.md` Phase 2 |
| Structured outputs on Orchestrator (replace ROLE:/TASK: parsing) | Medium | `PLAN.md` Phase 3 |
| Parallel worker dispatch (currently sequential) | Medium | `PLAN.md` Phase 3 |
| Real tools for TeammateAgent (web search, file read) | High | `PLAN.md` Phase 2 |
| Batch API demo for non-interactive flows | Low | `PLAN.md` Phase 4 |
| GitHub push / CI setup | Low | `SETUP.md` |

---

## Known issues (open bugs)

| ID | Title | Impact |
|---|---|---|
| — | No open bugs | — |

---

## Environment

| Key | Value |
|---|---|
| Python | 3.13+ (UV managed) |
| anthropic SDK | ≥ 0.25.0 |
| Orchestrator model | `claude-sonnet-4-6` |
| Worker model | `claude-haiku-4-5-20251001` |
| API key | `ANTHROPIC_API_KEY` in `.env` |
