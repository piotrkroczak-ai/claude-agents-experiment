"""
Tests for Phase 4: memory module, batch request format, memory+orchestrator integration.

Unit only:  uv run pytest tests/test_phase4.py -v -m "not live"
All:        uv run pytest tests/test_phase4.py -v
"""
import pytest

import src.memory as _mem
from src.memory import save_session, load_session, delete_session


# ---------------------------------------------------------------------------
# UNIT — memory module (Phase 4.2)
# ---------------------------------------------------------------------------

def test_memory_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(_mem, "_MEMORY_FILE", tmp_path / "sessions.json")
    save_session("k", {"value": 42})
    assert load_session("k") == {"value": 42}


def test_memory_missing_key(tmp_path, monkeypatch):
    monkeypatch.setattr(_mem, "_MEMORY_FILE", tmp_path / "sessions.json")
    assert load_session("ghost") is None


def test_memory_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(_mem, "_MEMORY_FILE", tmp_path / "sessions.json")
    save_session("k", {"v": 1})
    save_session("k", {"v": 2})
    assert load_session("k") == {"v": 2}


def test_memory_multiple_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(_mem, "_MEMORY_FILE", tmp_path / "sessions.json")
    save_session("a", {"x": 1})
    save_session("b", {"x": 2})
    assert load_session("a") == {"x": 1}
    assert load_session("b") == {"x": 2}


def test_memory_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(_mem, "_MEMORY_FILE", tmp_path / "sessions.json")
    save_session("k", {"v": 1})
    assert delete_session("k") is True
    assert load_session("k") is None


def test_memory_delete_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(_mem, "_MEMORY_FILE", tmp_path / "sessions.json")
    assert delete_session("ghost") is False


# ---------------------------------------------------------------------------
# UNIT — batch request structure (Phase 4.1)
# ---------------------------------------------------------------------------

def test_batch_request_format():
    """Validate request dict structure without calling the API."""
    from src.token_optimization import MODEL_WORKER, MAX_TOKENS_WORKER
    requests = [
        {
            "custom_id": f"q{i}",
            "params": {
                "model": MODEL_WORKER,
                "max_tokens": MAX_TOKENS_WORKER,
                "messages": [{"role": "user", "content": f"Question {i}"}],
            },
        }
        for i in range(5)
    ]
    assert len(requests) == 5
    assert all("custom_id" in r and "params" in r for r in requests)
    assert all(r["params"]["model"] == MODEL_WORKER for r in requests)
    assert requests[2]["custom_id"] == "q2"


def test_orchestrator_memory_key_stored():
    """Orchestrator exposes memory_key without calling the API."""
    from src.teammate import TeammateAgent, Orchestrator
    orch = Orchestrator(
        teammates=[TeammateAgent(role="w", instructions="reply")],
        memory_key="my_session",
    )
    assert orch._memory_key == "my_session"


# ---------------------------------------------------------------------------
# LIVE — memory persists across Orchestrator runs (Phase 4.2)
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_memory_saved_after_orchestrator_run(tmp_path, monkeypatch):
    monkeypatch.setattr(_mem, "_MEMORY_FILE", tmp_path / "sessions.json")

    from src.teammate import TeammateAgent, Orchestrator
    worker = TeammateAgent(role="writer", instructions="Answer in one sentence.")
    orch = Orchestrator(teammates=[worker], memory_key="live_session")
    result = orch.run("Name one benefit of Python.")

    session = load_session("live_session")
    assert session is not None
    assert session["last_task"] == "Name one benefit of Python."
    assert isinstance(session["result"], str) and len(session["result"]) > 0


# ---------------------------------------------------------------------------
# LIVE — batch API (Phase 4.1)
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_batch_creates_successfully():
    """Batch API accepts the request and returns a batch ID.

    Completion is not asserted here — the Batch API can take up to 24 hours.
    Use examples/batch_demo.py to run and observe a full end-to-end batch.
    """
    from anthropic import Anthropic
    from src.token_optimization import MODEL_WORKER

    client = Anthropic(max_retries=2)
    batch = client.messages.batches.create(
        requests=[{
            "custom_id": "test_q0",
            "params": {
                "model": MODEL_WORKER,
                "max_tokens": 64,
                "messages": [{"role": "user", "content": "Reply with one word: hello"}],
            },
        }]
    )
    assert batch.id is not None
    assert batch.id.startswith("msgbatch_")
    assert batch.processing_status in ("in_progress", "ended")
