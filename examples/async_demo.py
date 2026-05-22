"""
Async parallel worker dispatch demo (Phase 3.2).

Runs the same task with run() (sequential) and run_async() (parallel),
prints both results and compares elapsed time.

Usage:
    uv run python examples/async_demo.py
"""
import asyncio
import time

from dotenv import load_dotenv
load_dotenv()

from src.teammate import TeammateAgent, Orchestrator


TASK = "What are two key benefits of using async programming in Python?"

def make_orchestrator() -> Orchestrator:
    researcher = TeammateAgent(
        role="researcher",
        instructions="You are a concise technical researcher. Answer in 1-2 sentences.",
    )
    analyst = TeammateAgent(
        role="analyst",
        instructions="You are a concise technical analyst. Answer in 1-2 sentences.",
    )
    return Orchestrator(teammates=[researcher, analyst])


def run_sync(orch: Orchestrator) -> tuple[str, float]:
    t0 = time.perf_counter()
    result = orch.run(TASK)
    return result, time.perf_counter() - t0


async def run_async(orch: Orchestrator) -> tuple[str, float]:
    t0 = time.perf_counter()
    result = await orch.run_async(TASK)
    return result, time.perf_counter() - t0


def main() -> None:
    print(f"Task: {TASK}\n")
    print("=" * 60)

    orch_sync = make_orchestrator()
    result_sync, t_sync = run_sync(orch_sync)
    print(f"[SEQUENTIAL]  {t_sync:.2f}s")
    print(result_sync)
    print()

    orch_async = make_orchestrator()
    result_async, t_async = asyncio.run(run_async(orch_async))
    print(f"[PARALLEL]    {t_async:.2f}s")
    print(result_async)
    print()

    speedup = t_sync / t_async if t_async > 0 else 1
    saved = t_sync - t_async
    print("=" * 60)
    print(f"Speedup: {speedup:.2f}x  |  Time saved: {saved:.2f}s")
    print("(Both calls go through the same plan + synthesis steps;")
    print(" speedup comes from dispatching workers in parallel.)")


if __name__ == "__main__":
    main()
