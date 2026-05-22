# Test Inventory & Results

## Setup

**Framework:** pytest  
**Runner:** `uv run pytest tests/ -v`  
**Environment:** Requires `ANTHROPIC_API_KEY` in `.env` for live tests.  
**Test types:**
- `[LIVE]` — calls the real Anthropic API (costs tokens, needs key)
- `[UNIT]` — no API call, pure logic

---

## Test File: `tests/test_agent.py`

### test_agent_init `[UNIT]`

**Purpose:** Verify `SimpleAgent` initialises without error and the Anthropic client is set up.

**What it checks:**
- `agent.client is not None`

**Does it call the API?** No — `Anthropic()` constructor does not make a network call. It only reads `ANTHROPIC_API_KEY` from the environment.

**Result (2026-05-21):** PASS ✓ (requires key to be present in env; fails with `ValueError` if missing — expected behaviour per `src/config.py`).

---

### test_agent_run `[LIVE]`

**Purpose:** Verify `SimpleAgent.run()` returns a non-empty string response.

**What it checks:**
- Return type is `str`
- Response length > 0

**Does it call the API?** YES — sends `"Test simple"` to `claude-sonnet-4-6` with tool definitions. Approximate cost: ~500 input tokens × $3/1M = ~$0.0015 per run.

**Result (2026-05-21):** NOT RUN — API key not set in CI environment. Expected to PASS when key is available.

**Known issue:** If `src/config.py` imports from `src/token_optimization.py` which imports `anthropic`, the test will fail at import time if `anthropic` is not installed. Use `uv run pytest` (not bare `python -m pytest`) to ensure the venv is active.

---

## Test File: `tests/test_token_optimization.py`

**Status:** Created 2026-05-22. 6 UNIT tests passing, 3 LIVE tests pending API key.

### test_model_constants_valid [UNIT]
**Result (2026-05-22):** PASS ✓
**Notes:** `MODEL_ORCHESTRATOR` and `MODEL_WORKER` are non-empty strings.

### test_max_token_budgets_sane [UNIT]
**Result (2026-05-22):** PASS ✓
**Notes:** `MAX_TOKENS_WORKER <= MAX_TOKENS_ORCHESTRATOR`, both within expected ranges.

### test_effort_orchestrator_value [UNIT]
**Result (2026-05-22):** PASS ✓
**Notes:** `EFFORT_ORCHESTRATOR` is one of the valid enum values.

### test_cached_system_format [UNIT]
**Result (2026-05-22):** PASS ✓
**Notes:** Block has `type`, `text`, and `cache_control: {type: ephemeral}`.

### test_cached_system_custom_ttl [UNIT]
**Result (2026-05-22):** PASS ✓
**Notes:** TTL passed through correctly.

### test_cached_system_returns_new_list_each_call [UNIT]
**Result (2026-05-22):** PASS ✓
**Notes:** Each call returns a distinct list object (no shared mutable state).

### test_count_tokens_returns_positive_int [LIVE]
**Result (2026-05-22):** NOT RUN — API key not set.
**Notes:** Expects a positive `int` from `count_tokens()`.

### test_effort_not_on_haiku [LIVE]
**Result (2026-05-22):** NOT RUN — API key not set.
**Notes:** Verifies `TeammateAgent.ask()` does not raise 400 (no `effort` on Haiku 4.5).

### test_orchestrator_plan_parses [LIVE]
**Result (2026-05-22):** NOT RUN — API key not set.
**Notes:** `Orchestrator.run()` must return a non-empty string.

---

## Test File: `tests/test_doc_agent.py` (planned)

**Status:** Not yet created.

**Planned tests:**

| Test name | Type | What it checks |
|---|---|---|
| `test_read_doc_existing` | UNIT | `DocumentationAgent.read_doc("logs.md")` returns file content |
| `test_read_doc_missing` | UNIT | `DocumentationAgent.read_doc("nonexistent.md")` returns error string |
| `test_append_log_entry` | UNIT | `log_event()` appends a correctly formatted line to `logs.md` |
| `test_report_bug_format` | UNIT | `report_bug()` creates a valid BUG-XXX section in `bugs.md` |
| `test_audit_runs` | LIVE | `DocumentationAgent.audit()` completes without exception |

---

## Manual Test Results

### Teammate demo — 2026-05-21

**Command:** `uv run python examples/teammate_demo.py`  
**Status:** NOT RUN (API key required)  
**Expected:** Prints COST_SUMMARY, token estimate dict, then final synthesised answer.  
**Known pre-condition:** `documentation/` folder must exist (created 2026-05-21).

---

## How to Add a New Test Result

Append to the relevant section above, or create a new section:

```markdown
### test_name [LIVE|UNIT]
**Result (YYYY-MM-DD):** PASS ✓ / FAIL ✗ / SKIP
**Notes:** Any relevant observation, error message, or token cost.
```

The `DocumentationAgent` can also update this file automatically via `record_test()`.
