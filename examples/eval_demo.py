"""
Evaluation framework demo (Phase 5.3).

Runs the same task through three approaches and compares results:
  1. Single specialist agent (direct call, cheapest)
  2. Orchestrator with two workers (parallel, structured)
  3. Pipeline — researcher → writer (sequential refinement)

Usage:
    uv run python examples/eval_demo.py
"""
import time

from dotenv import load_dotenv
load_dotenv()

from src.registry import SpecialistRegistry, AgentPipeline
from src.teammate import Orchestrator

TASK = "Explain what Python's GIL is and why it matters for multi-threaded code."


def _fmt(result: str, elapsed: float, label: str) -> None:
    print(f"\n[{label}]  {elapsed:.2f}s  |  {len(result)} chars")
    print("-" * 60)
    print(result)


def main() -> None:
    registry = SpecialistRegistry()
    print(f"Task: {TASK}\n{'=' * 60}")

    # 1. Single agent
    t0 = time.perf_counter()
    r1 = registry.get("researcher").ask(TASK)
    t1 = time.perf_counter() - t0
    _fmt(r1, t1, "Single agent — researcher")

    # 2. Orchestrator (parallel workers)
    orch = Orchestrator(teammates=registry.subset(["researcher", "writer"]))
    t0 = time.perf_counter()
    r2 = orch.run(TASK)
    t2 = time.perf_counter() - t0
    _fmt(r2, t2, "Orchestrator — researcher + writer (parallel plan + synthesise)")

    # 3. Pipeline (sequential refinement)
    pipeline = AgentPipeline(stages=registry.subset(["researcher", "writer"]))
    t0 = time.perf_counter()
    r3 = pipeline.final(TASK)
    t3 = time.perf_counter() - t0
    _fmt(r3, t3, "Pipeline — researcher → writer (sequential refinement)")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"{'Approach':<40} {'Time':>6}  {'Chars':>6}")
    print(f"{'-' * 40} {'-' * 6}  {'-' * 6}")
    print(f"{'Single agent':40} {t1:>6.2f}s  {len(r1):>6}")
    print(f"{'Orchestrator (plan + parallel + synth)':40} {t2:>6.2f}s  {len(r2):>6}")
    print(f"{'Pipeline (research → write)':40} {t3:>6.2f}s  {len(r3):>6}")
    print()
    print("Trade-offs:")
    print("  Single agent  — cheapest, fastest, least structured")
    print("  Orchestrator  — parallel workers, structured synthesis, higher cost")
    print("  Pipeline      — sequential refinement, each stage improves the last")


if __name__ == "__main__":
    main()
