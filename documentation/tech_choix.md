# Technical Choices — Justifications

Each choice is documented with: **Decision**, **Alternatives considered**, **Why we chose it**, **Trade-offs**.

---

## 1. Package Manager: UV

**Decision:** UV (Astral) instead of pip/poetry/conda.

**Alternatives:** pip + venv, Poetry, Conda.

**Why:**
- Resolution is 10-100× faster than pip (Rust-based resolver).
- `uv sync` is fully reproducible from `uv.lock` — no "works on my machine" drift.
- `uv run` executes in the managed venv without manual activation.
- Single binary, no daemon, no separate virtualenv step.

**Trade-offs:** Newer tool (less StackOverflow coverage). `pyproject.toml` must be clean; hatchling build requires explicit `packages` config (see `bugs.md` BUG-003).

---

## 2. Build Backend: Hatchling

**Decision:** Hatchling via `[build-system] requires = ["hatchling"]`.

**Alternatives:** setuptools, flit, poetry-core.

**Why:**
- Native PEP 517/518 compliance.
- Zero-config for standard `src/` layout when packages are declared.
- Works well with UV's editable installs.

**Trade-offs:** Requires `[tool.hatch.build.targets.wheel] packages = ["src"]` when the package name doesn't match the directory. This tripped us once (BUG-003).

---

## 3. LLM Provider: Anthropic Claude API (first-party)

**Decision:** Direct Anthropic SDK (`anthropic>=0.25.0`), not OpenAI or LangChain.

**Alternatives:** OpenAI GPT-4, LangChain abstraction layer, LlamaIndex.

**Why:**
- Native access to prompt caching (`cache_control`), which is Anthropic-specific and provides 90% cost savings on repeated prefixes.
- Native `effort` parameter on Sonnet 4.6 for fine-grained cost control.
- No abstraction overhead — direct control over `messages`, `tools`, `stop_reason`.
- Avoids LangChain lock-in and its version fragmentation issues.

**Trade-offs:** Tightly coupled to Anthropic. Switching to another provider requires rewriting tool-use and message-format logic.

---

## 4. Model Strategy: Tiered (Haiku workers / Sonnet orchestrator)

**Decision:** `claude-haiku-4-5-20251001` for workers, `claude-sonnet-4-6` for orchestrators.

**Alternatives:** Single model (Opus for everything), single model (Sonnet for everything).

**Why:**
- Cost: Haiku at $1/$5 per 1M tokens vs Opus at $5/$25 = 5× cheaper for worker tasks.
- Workers do single-turn focused tasks (research, analysis) that don't need deep reasoning.
- Orchestrator plans and synthesises — Sonnet's reasoning justifies the extra cost.
- Industry data shows ~60% of agent sub-calls can be served by a cheaper model with no quality loss.

**Trade-offs:** Two models to manage. `effort` param works on Sonnet but errors on Haiku (BUG-001). Model tiering logic must be kept in sync when models are updated.

**Reference:** `src/token_optimization.py` — STRATEGY 1.

---

## 5. Token Budget Strategy: Tight max_tokens per role

**Decision:** `MAX_TOKENS_WORKER = 512`, `MAX_TOKENS_ORCHESTRATOR = 1024`.

**Alternatives:** Default 4096, unlimited, per-task dynamic budgets.

**Why:**
- Output tokens cost 5× input tokens. Unbounded output = unpredictable bills.
- Workers produce one focused paragraph; 512 tokens is sufficient.
- Orchestrators plan and synthesise; 1024 tokens covers multi-step reasoning output.
- Forces concise answers from LLMs, which is also better UX.

**Trade-offs:** May truncate edge-case long outputs. Increase per-agent if tasks grow in scope.

**Reference:** `src/token_optimization.py` — STRATEGY 2.

---

## 6. Prompt Caching: cache_control on system prompts

**Decision:** `cache_control: {"type": "ephemeral"}` on all system blocks.

**Alternatives:** No caching, manual TTL management.

**Why:**
- Cache reads cost 0.1× base price (90% savings on cached tokens).
- Break-even is just 2 requests within the 5-minute TTL window.
- Adding `cache_control` to short prompts is a no-op if below the minimum — safe to add preemptively.

**Important constraint:**
- Haiku 4.5 minimum cacheable prefix: ≥ 4096 tokens.
- Sonnet 4.6 minimum: ≥ 2048 tokens.
- Short system prompts (<100 words) will NOT cache — verified via `usage.cache_creation_input_tokens`.

**Trade-offs:** Cache write costs 1.25× (5-min TTL) or 2× (1h TTL). Only beneficial at sufficient volume.

**Reference:** `src/token_optimization.py` — STRATEGY 3.

---

## 7. Context Isolation: Stateless single-turn workers

**Decision:** Workers have no `self.messages` history — each call is stateless.

**Alternatives:** Pass full orchestrator history to each worker, shared message bus.

**Why:**
- Passing full history to N workers at turn T = O(T × N) token cost growth.
- Workers only need a targeted brief from the orchestrator, not full context.
- Stateless workers are easier to test, debug, and parallelize.

**Trade-offs:** Workers cannot refer to prior exchanges. Multi-turn worker workflows require a different pattern.

**Reference:** `src/token_optimization.py` — STRATEGY 4.

---

## 8. effort Parameter: "medium" on orchestrator

**Decision:** `output_config={"effort": "medium"}` on Sonnet orchestrator calls only.

**Alternatives:** "high" (default), "low", omit entirely.

**Why:**
- `effort` controls thinking depth and token spend. "medium" gives balanced quality for planning/routing without paying for deep extended reasoning.
- Planning calls don't need the same depth as autonomous agentic loops.
- Reduces preamble and consolidates tool calls → 10-20% output savings.

**CRITICAL:** `effort` is NOT supported on Haiku 4.5 — returns 400 error. Applied exclusively to the Sonnet orchestrator.

**Reference:** `src/token_optimization.py` — STRATEGY 5. See also BUG-001.

---

## 9. Architecture: Orchestrator + TeammateAgent pattern

**Decision:** `Orchestrator` (plans/dispatches/synthesises) + N × `TeammateAgent` (single-turn workers).

**Alternatives:** Single monolithic agent, LangGraph-style graph, LangChain agents.

**Why:**
- Clean separation of concerns: coordination vs execution.
- Each role maps to the cheapest capable model.
- Orchestrator's 3-step flow (plan → dispatch → synthesise) is auditable and deterministic.
- No external framework dependency — easier to understand, test, and modify.

**Trade-offs:** Orchestrator must parse its own plan format (ROLE:/TASK: lines). Brittle if model output format drifts. For production, structured outputs (`output_config.format`) should be used instead.

---

## 10. Validation: Pydantic (available, not yet used)

**Decision:** Pydantic in dependencies, not yet instantiated.

**Why declared:** Planned for structured tool inputs, agent responses, and configuration validation as the project grows.

**When to introduce:** When `TeammateAgent` results need schema enforcement, or when config grows beyond simple constants.
