"""
Small-scale teammate demo with token optimizations.

Run:  uv run python examples/teammate_demo.py

Token profile (see src/token_optimization.py for full justification):
  - Orchestrator: claude-sonnet-4-6, max 1024 tokens out, effort=medium
  - Workers:      claude-haiku-4-5, max 512 tokens out, no effort param
  - Cache:        cache_control on all system prompts (activates if >= 2048/4096 tokens)
  - Isolation:    each worker receives only its task brief, not full history
"""
from src.token_optimization import COST_SUMMARY
from src.teammate import Orchestrator, TeammateAgent


def main():
    print("=== Token Optimization Summary ===")
    print(COST_SUMMARY)

    researcher = TeammateAgent(
        role="researcher",
        instructions=(
            "You are a research assistant. Given a topic, provide 3-5 concise "
            "factual bullet points. Max 120 words total."
        ),
    )
    analyst = TeammateAgent(
        role="analyst",
        instructions=(
            "You are a data analyst. Given facts, identify the 2 most important "
            "insights. Max 120 words total."
        ),
    )

    orchestrator = Orchestrator(teammates=[researcher, analyst])

    task = "What are the main benefits and risks of using AI agents in software development?"

    # Free token count estimate before the real call
    estimate = orchestrator.estimate_cost(task)
    print("=== Pre-call token estimate (free API call) ===")
    for k, v in estimate.items():
        print(f"  {k}: {v}")
    print()

    print(f"Task: {task}\n")
    result = orchestrator.run(task)
    print("=== Final answer ===")
    print(result)


if __name__ == "__main__":
    main()
