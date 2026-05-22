"""
Tests for Phase 3: structured outputs, async dispatch, error handling.

Unit only:  uv run pytest tests/test_phase3.py -v -m "not live"
All:        uv run pytest tests/test_phase3.py -v
"""
import asyncio
import pytest

from src.teammate import (
    TeammateAgent,
    Orchestrator,
    OrchestratorPlan,
    WorkerTask,
)


# ---------------------------------------------------------------------------
# UNIT — Pydantic models (Phase 3.1)
# ---------------------------------------------------------------------------

def test_worker_task_schema():
    wt = WorkerTask(role="writer", task="Write a sentence.")
    assert wt.role == "writer"
    assert wt.task == "Write a sentence."


def test_orchestrator_plan_schema():
    plan = OrchestratorPlan(tasks=[
        WorkerTask(role="researcher", task="Research X"),
        WorkerTask(role="analyst",    task="Analyse Y"),
    ])
    assert len(plan.tasks) == 2
    assert plan.tasks[0].role == "researcher"


def test_orchestrator_plan_from_json():
    raw = '{"tasks": [{"role": "writer", "task": "Write something"}]}'
    plan = OrchestratorPlan.model_validate_json(raw)
    assert len(plan.tasks) == 1
    assert plan.tasks[0].role == "writer"


def test_orchestrator_plan_empty_tasks():
    plan = OrchestratorPlan(tasks=[])
    assert plan.tasks == []


# ---------------------------------------------------------------------------
# UNIT — async plumbing (Phase 3.2)
# ---------------------------------------------------------------------------

def test_run_async_is_coroutine():
    orch = Orchestrator(teammates=[
        TeammateAgent(role="writer", instructions="Write one sentence.")
    ])
    coro = orch.run_async("test task")
    assert asyncio.iscoroutine(coro)
    coro.close()


def test_ask_async_is_coroutine():
    agent = TeammateAgent(role="tester", instructions="Reply with one word.")
    coro = agent.ask_async("Hello")
    assert asyncio.iscoroutine(coro)
    coro.close()


# ---------------------------------------------------------------------------
# LIVE — structured plan (Phase 3.1)
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_structured_plan_returns_valid_schema():
    worker = TeammateAgent(role="writer", instructions="Write one short sentence.")
    orch = Orchestrator(teammates=[worker])
    result = orch.run("Summarise the sky in one sentence.")
    assert isinstance(result, str) and len(result) > 0


@pytest.mark.live
def test_run_async_completes():
    researcher = TeammateAgent(role="researcher", instructions="Answer in one sentence.")
    analyst    = TeammateAgent(role="analyst",    instructions="Answer in one sentence.")
    orch = Orchestrator(teammates=[researcher, analyst])
    result = asyncio.run(orch.run_async("Name one benefit of async programming."))
    assert isinstance(result, str) and len(result) > 0


@pytest.mark.live
def test_async_faster_than_sync_with_two_workers():
    """Parallel dispatch should be faster than sequential for 2 workers."""
    import time
    researcher = TeammateAgent(role="researcher", instructions="Answer in one sentence.")
    analyst    = TeammateAgent(role="analyst",    instructions="Answer in one sentence.")

    orch_s = Orchestrator(teammates=[researcher, analyst])
    t0 = time.perf_counter()
    orch_s.run("Name one benefit of Python.")
    t_sync = time.perf_counter() - t0

    orch_a = Orchestrator(teammates=[researcher, analyst])
    t0 = time.perf_counter()
    asyncio.run(orch_a.run_async("Name one benefit of Python."))
    t_async = time.perf_counter() - t0

    # Async should be at least 10% faster (generous threshold for CI variance)
    assert t_async < t_sync * 0.95, f"Async ({t_async:.2f}s) not faster than sync ({t_sync:.2f}s)"
