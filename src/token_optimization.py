"""
Token optimization strategies for Claude API multi-agent systems.

WHY THIS FILE EXISTS
====================
Multi-agent systems multiply costs:
  - Each agent call carries input + output token cost
  - Orchestrators pass context to every worker (fan-out)
  - A naive 3-worker system using the same model as a single agent
    costs 3-5× more before any actual savings are applied

This module documents and enforces 5 concrete strategies.
Expected overall cost reduction vs a naive "use Opus for everything" baseline: 85-90%.

PRICING REFERENCE (May 2026, first-party API)
=============================================
Model              Input $/1M   Output $/1M   Notes
claude-opus-4-7    $5.00        $25.00        Baseline for comparison
claude-sonnet-4-6  $3.00        $15.00        40% cheaper than Opus input
claude-haiku-4-5   $1.00        $5.00         80% cheaper than Opus input

Sources:
  https://platform.claude.com/docs/en/about-claude/models/overview
  https://www.finout.io/blog/anthropic-api-pricing
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass
from datetime import datetime as _datetime
from pathlib import Path as _Path

from anthropic import Anthropic

_USAGE_JSONL = _Path(__file__).parent.parent / "documentation" / "token_usage.jsonl"

# Pricing per 1M tokens (May 2026, first-party API)
_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-7":   {"input": 5.00, "output": 25.00, "cache_read": 0.50, "cache_write": 6.25},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-haiku-4-5":  {"input": 1.00, "output":  5.00, "cache_read": 0.10, "cache_write": 1.25},
}

def _get_prices(model: str) -> dict[str, float]:
    for prefix, prices in _PRICING.items():
        if model.startswith(prefix):
            return prices
    return _PRICING["claude-sonnet-4-6"]

# ---------------------------------------------------------------------------
# STRATEGY 1 — MODEL TIERING
# WHY: Model cost scales linearly with usage. Routing simple, focused tasks to
#      Haiku instead of Opus/Sonnet cuts per-call cost by 3-5×. The key insight
#      from production data (dev.to/whoffagents) is that ~60% of agent sub-calls
#      can be served by a cheaper model with no quality loss.
#
# RULE:
#   Orchestrator (plans, routes, synthesises)  → Sonnet 4.6 — needs reasoning
#   Workers (single focused task, one turn)    → Haiku 4.5  — speed + cost
#
# SAVINGS vs Opus 4.7 baseline:
#   Worker Haiku input:   $1/$5   vs $5/$25  → 5× cheaper
#   Orchestrator Sonnet:  $3/$15  vs $5/$25  → 1.67× cheaper
# ---------------------------------------------------------------------------
MODEL_ORCHESTRATOR = "claude-sonnet-4-6"        # reasoning, planning, synthesis
MODEL_WORKER = "claude-haiku-4-5-20251001"      # full ID — single-turn execution

# ---------------------------------------------------------------------------
# STRATEGY 2 — TIGHT MAX_TOKENS BUDGETS
# WHY: Output tokens cost 5× more than input tokens on every model.
#      A worker that "rambles" doubles your output bill silently.
#      Setting explicit ceilings forces concise output and prevents runaway costs.
#
# Budget rationale:
#   Worker (512):        ~1 focused paragraph — enough for a subtask answer
#   Orchestrator (1024): planning + synthesis, needs a bit more room
#
# Compared to the default max_tokens of 4096, these budgets are 8× and 4× tighter.
# For a 3-worker flow that runs 100×/day, the savings on output alone are significant.
# ---------------------------------------------------------------------------
MAX_TOKENS_WORKER = 512
MAX_TOKENS_ORCHESTRATOR = 1024

# ---------------------------------------------------------------------------
# STRATEGY 3 — PROMPT CACHING
# WHY: Cache reads cost 0.1× base input price (90% savings on cached tokens).
#      For a static system prompt reused across many calls, the break-even is
#      just 2 requests within the 5-minute TTL window.
#
# IMPORTANT CONSTRAINT — minimum cacheable prefix:
#   claude-haiku-4-5:   ≥ 4096 tokens (~3000 words) — very long system prompts only
#   claude-sonnet-4-6:  ≥ 2048 tokens (~1500 words)
#
# PRACTICAL IMPLICATION for this project:
#   Short worker instructions (<100 words) will NOT hit the minimum and silently
#   won't cache — verify with `usage.cache_creation_input_tokens` in the response.
#   For small prompts the overhead of cache_control is effectively zero (no error,
#   just no cache hit). We still include it so any prompt expansion later will
#   automatically start caching.
#
# When to use the 1h TTL (cost 2× to write vs 1.25× for 5min):
#   Use it when the same worker prompt is called LESS than once per 5 minutes
#   but more than once per hour — e.g. a nightly-batch worker.
# ---------------------------------------------------------------------------
CACHE_TTL_DEFAULT = "ephemeral"       # 5-minute TTL, write cost 1.25×

def cached_system(text: str, ttl: str = CACHE_TTL_DEFAULT) -> list[dict]:
    """
    Wrap a system prompt string in the block format required for cache_control.
    Returns the list of blocks expected by client.messages.create(system=...).

    Usage:
        system=cached_system("You are a research assistant. ...")
    """
    return [{"type": "text", "text": text, "cache_control": {"type": ttl}}]


# ---------------------------------------------------------------------------
# STRATEGY 4 — CONTEXT ISOLATION (single-turn workers)
# WHY: If you pass the full conversation history to each worker, context size
#      (and cost) grows quadratically with conversation length.
#      A 10-turn conversation with 3 workers → 30 full-history copies per turn.
#      Single-turn workers receive ONLY the specific slice they need.
#
# IMPLEMENTATION:
#   Workers never maintain self.messages — each call is stateless.
#   The orchestrator owns the full context; it extracts and passes a targeted
#   "task brief" to each worker. Workers respond with a single structured reply.
#
# SAVINGS: eliminates the O(turns × workers) context fan-out.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# STRATEGY 5 — effort PARAMETER (Sonnet 4.6 orchestrator only)
# WHY: The effort parameter controls thinking depth and overall token spend.
#      Lower effort = fewer consolidated tool calls, less preamble, terser output.
#      For orchestration tasks (planning, routing, synthesis), "medium" gives
#      a good quality/cost balance without paying for deep reasoning.
#
# CRITICAL: effort is NOT supported on Haiku 4.5 — it will return a 400 error.
#           Only apply it to the Sonnet 4.6 orchestrator.
#
# Effort levels (Sonnet 4.6):
#   "low"    — best for classification, summarization, simple routing
#   "medium" — balanced; good for orchestration and planning
#   "high"   — agentic / multi-step tasks (default)
# ---------------------------------------------------------------------------
EFFORT_ORCHESTRATOR = "medium"  # planning/routing don't need deep reasoning


# ---------------------------------------------------------------------------
# UTILITY — Token counting before expensive calls
# WHY: The count_tokens() endpoint is FREE. Use it before large orchestrator
#      calls to verify context size, catch accidental prompt bloat, and decide
#      whether to use the Batch API instead (see below).
# ---------------------------------------------------------------------------

def count_tokens(
    client: Anthropic,
    model: str,
    system: list[dict] | str | None,
    messages: list[dict],
) -> int:
    """Return the estimated input token count for a planned API call."""
    kwargs: dict = {"model": model, "messages": messages}
    if system is not None:
        kwargs["system"] = system
    result = client.messages.count_tokens(**kwargs)
    return result.input_tokens


# ---------------------------------------------------------------------------
# BONUS — Batch API (50% discount, non-latency-sensitive work)
# WHY: The Batch API processes requests asynchronously at half the standard price.
#      Combined with prompt caching, total savings can reach 90-95%.
#      Use it when: results are not needed in real-time (reports, bulk analysis).
#
# WHEN NOT to use:
#   - Interactive workflows where the user waits for a response
#   - Orchestration calls that gate subsequent worker dispatch
#
# INTEGRATION POINT:
#   Replace client.messages.create(...) with client.messages.batches.create(...)
#   and poll for results. See src/batch_demo.py for an example.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# SUMMARY — expected savings per call type
# ---------------------------------------------------------------------------
def log_usage(response, agent: str, call_type: str, run_id: str = "") -> None:
    """Append one token-usage record to documentation/token_usage.jsonl."""
    usage = response.usage
    model = response.model
    prices = _get_prices(model)

    inp = getattr(usage, "input_tokens", 0)
    out = getattr(usage, "output_tokens", 0)
    cr  = getattr(usage, "cache_read_input_tokens", 0)
    cw  = getattr(usage, "cache_creation_input_tokens", 0)

    cost = (
        inp * prices["input"] +
        out * prices["output"] +
        cr  * prices["cache_read"] +
        cw  * prices["cache_write"]
    ) / 1_000_000

    entry = {
        "ts":          _datetime.now().isoformat(timespec="seconds"),
        "run_id":      run_id,
        "agent":       agent,
        "call":        call_type,
        "model":       model,
        "input":       inp,
        "output":      out,
        "cache_read":  cr,
        "cache_write": cw,
        "cost_usd":    round(cost, 8),
    }

    _USAGE_JSONL.parent.mkdir(exist_ok=True)
    with _USAGE_JSONL.open("a", encoding="utf-8") as f:
        f.write(_json.dumps(entry) + "\n")


COST_SUMMARY = """
Optimization             | Mechanism                      | Est. Savings
-------------------------|--------------------------------|------------------
Model tiering            | Haiku for workers              | 80% vs Opus
                         | Sonnet for orchestrator        | 40% vs Opus
Tight max_tokens         | 512 (worker) / 1024 (orch.)   | 50-75% on output
Prompt caching           | cache reads at 0.1× price      | 60-90% on input*
Context isolation        | single-turn, no full history   | 50-80% on context
effort=medium (orch.)    | less preamble + planning       | 10-20% on output

Combined vs naive (Opus, full history, no caching):  ~85-90% reduction

* Only activates when system prompt >= 4096 tokens (Haiku) / 2048 (Sonnet).
  Verify with usage.cache_creation_input_tokens in the response.
"""
