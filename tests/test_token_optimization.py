"""
Tests for src/token_optimization.py

UNIT tests run with no API key and cost nothing.
LIVE tests call the real Anthropic API — mark them with pytest.ini or run:
    uv run pytest tests/test_token_optimization.py -v -m "not live"   # unit only
    uv run pytest tests/test_token_optimization.py -v                  # all
"""
import pytest
from anthropic import Anthropic

from src.token_optimization import (
    MODEL_ORCHESTRATOR,
    MODEL_WORKER,
    MAX_TOKENS_WORKER,
    MAX_TOKENS_ORCHESTRATOR,
    EFFORT_ORCHESTRATOR,
    cached_system,
    count_tokens,
)


# ---------------------------------------------------------------------------
# UNIT tests — no API call
# ---------------------------------------------------------------------------

def test_model_constants_valid():
    assert isinstance(MODEL_ORCHESTRATOR, str) and MODEL_ORCHESTRATOR
    assert isinstance(MODEL_WORKER, str) and MODEL_WORKER


def test_max_token_budgets_sane():
    assert 0 < MAX_TOKENS_WORKER <= 1024
    assert 0 < MAX_TOKENS_ORCHESTRATOR <= 2048
    assert MAX_TOKENS_WORKER <= MAX_TOKENS_ORCHESTRATOR


def test_effort_orchestrator_value():
    assert EFFORT_ORCHESTRATOR in {"low", "medium", "high", "max"}


def test_cached_system_format():
    result = cached_system("You are a test assistant.")
    assert isinstance(result, list) and len(result) == 1
    block = result[0]
    assert block["type"] == "text"
    assert block["text"] == "You are a test assistant."
    assert block["cache_control"] == {"type": "ephemeral"}


def test_cached_system_custom_ttl():
    result = cached_system("hello", ttl="ephemeral")
    assert result[0]["cache_control"]["type"] == "ephemeral"


def test_cached_system_returns_new_list_each_call():
    a = cached_system("prompt")
    b = cached_system("prompt")
    assert a is not b


# ---------------------------------------------------------------------------
# LIVE tests — require ANTHROPIC_API_KEY in environment / .env
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_count_tokens_returns_positive_int():
    client = Anthropic()
    n = count_tokens(
        client,
        model=MODEL_WORKER,
        system=cached_system("You are a concise assistant."),
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert isinstance(n, int) and n > 0


@pytest.mark.live
def test_effort_not_on_haiku():
    """Haiku 4.5 must NOT receive the effort param — verify no 400 is raised."""
    from src.teammate import TeammateAgent
    agent = TeammateAgent(role="tester", instructions="Reply with one word.")
    result = agent.ask("Say: ok")
    assert isinstance(result, str) and len(result) > 0


@pytest.mark.live
def test_orchestrator_plan_parses():
    """Orchestrator.run() must return a non-empty string."""
    from src.teammate import Orchestrator, TeammateAgent
    worker = TeammateAgent(role="writer", instructions="Write one short sentence.")
    orch = Orchestrator(teammates=[worker])
    result = orch.run("Write a one-sentence summary of the sky.")
    assert isinstance(result, str) and len(result) > 0
