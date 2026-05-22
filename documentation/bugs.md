# Bug Tracker

Format per entry:
```
## BUG-XXX — <title>
**Status:** Open | Fixed | Won't fix
**Discovered:** YYYY-MM-DD
**File(s):** path/to/file.py
**Symptom:** What went wrong / what error appeared
**Root cause:** Why it happened
**Resolution:** What was changed to fix it
**Lesson:** What to watch for in future
```

---

## BUG-001 — `effort` parameter causes 400 on Haiku 4.5

**Status:** Fixed  
**Discovered:** 2026-05-21  
**File(s):** `src/teammate.py` (original version)

**Symptom:**
```
anthropic.BadRequestError: 400 — invalid_request_error
```
When `output_config={"effort": "medium"}` was included in `TeammateAgent` calls using `claude-haiku-4-5-20251001`.

**Root cause:**
The `effort` parameter (`output_config.effort`) is supported only on Sonnet 4.6 and Opus models. It is explicitly NOT supported on Haiku 4.5 — the API returns a hard 400 error if sent.

From the Anthropic skill docs:
> "Works on Opus 4.5, Opus 4.6, Opus 4.7, and Sonnet 4.6. Will error on Sonnet 4.5 / Haiku 4.5."

**Resolution:**
Removed `output_config` entirely from `TeammateAgent.__init__` and `TeammateAgent.ask()`. The `effort` parameter is now only applied in `Orchestrator._create()` which exclusively uses `claude-sonnet-4-6`.

Added explicit documentation in `src/token_optimization.py` STRATEGY 5:
```
# CRITICAL: effort is NOT supported on Haiku 4.5 — it will return a 400 error.
#           Only apply it to the Sonnet 4.6 orchestrator.
```

**Lesson:** Always check model capability matrix before applying `effort`, `thinking`, or beta parameters. Verify with the Anthropic SDK docs or `client.models.retrieve(model_id)`.

---

## BUG-002 — `examples/demo.py` imports from wrong module path

**Status:** Fixed  
**Discovered:** 2026-05-21  
**File(s):** `examples/demo.py`

**Symptom:**
```
ModuleNotFoundError: No module named 'src.agent'
```

**Root cause:**
`demo.py` imports `from src.agent import SimpleAgent`, but the actual module is `src/agents.py` (plural).

**Resolution:**
The demo was updated to reference the correct import. Note: this is a known issue in early scaffolding — file was `agents.py` but imported as `agent`.

**Lesson:** Keep module names consistent with class names from the start. `agents.py` is fine for a multi-agent file, but a one-class file named `agents.py` invites import confusion. Consider aligning or documenting the divergence.

---

## BUG-003 — Hatchling build fails: "Unable to determine which files to ship"

**Status:** Fixed  
**Discovered:** 2026-05-21  
**Fixed:** 2026-05-21  
**File(s):** `pyproject.toml`

**Symptom:**
```
ValueError: Unable to determine which files to ship inside the wheel using the following heuristics
The most likely cause of this is that there is no directory that matches the name of your project (claude_agents_experiment).
```
Occurs when running `uv run python ...` which triggers an editable install via hatchling.

**Root cause:**
The project name in `pyproject.toml` is `claude-agents-experiment` (kebab-case). Hatchling expects a package directory named `claude_agents_experiment` (snake_case). The code lives in `src/` without a matching package name declared.

**Resolution:**
Added to `pyproject.toml`:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src"]
```
Also consolidated the duplicate `dependencies` block left by `uv add` (it prepends a new block rather than merging). Verified with `uv run python -c "import src.agents"` and `import src.doc_agent` — both pass.

**Lesson:** When using hatchling with a `src/` layout and a project name that doesn't match the directory, always declare `packages` explicitly in `pyproject.toml`.

---

## BUG-004 — Prompt caching silently inactive for short system prompts

**Status:** Won't fix (by design — documented)  
**Discovered:** 2026-05-21  
**File(s):** `src/teammate.py`, `src/token_optimization.py`

**Symptom:**
`cache_control: {"type": "ephemeral"}` is applied to system prompts, but `usage.cache_creation_input_tokens` returns 0 on every call. No error is raised.

**Root cause:**
The Anthropic API has a minimum cacheable prefix length:
- `claude-haiku-4-5`: ≥ 4096 tokens (~3000 words)
- `claude-sonnet-4-6`: ≥ 2048 tokens (~1500 words)

Current worker system prompts are ~30-50 words, far below the minimum. The API silently skips caching.

**Resolution:**
No fix applied — caching on short prompts is a non-issue (no error, no cost penalty). The `cache_control` marker is kept preemptively so that if system prompts grow (e.g., by adding examples or domain context), caching will activate automatically without code changes.

Documented explicitly in `src/token_optimization.py` STRATEGY 3 and `documentation/tech_choix.md` item 6.

**How to verify:** Check `response.usage.cache_creation_input_tokens` and `response.usage.cache_read_input_tokens` after each call. Non-zero values confirm caching is active.

**Lesson:** Always verify caching is working with `usage` fields, not by assumption. Add a debug log or assertion in test environments when caching is load-bearing for cost projections.
