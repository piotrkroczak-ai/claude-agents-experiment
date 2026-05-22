"""
Batch API demo (Phase 4.1) — 50% cost savings for non-interactive workloads.

Submits 5 research questions as a single batch, polls for completion,
then prints results with a sync-vs-batch cost comparison.

Usage:
    uv run python examples/batch_demo.py

Note: the Batch API may take up to 24 hours in production.
      In practice small batches often complete within seconds.
"""
import time

from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic
from src.token_optimization import MODEL_WORKER, MAX_TOKENS_WORKER

QUESTIONS = [
    "What is a Python generator and when should you use one?",
    "Explain the difference between a process and a thread.",
    "What is the purpose of a context manager in Python?",
    "What is memoization and how does it reduce computation?",
    "Why is immutability valuable in functional programming?",
]

# Haiku 4.5 pricing ($/1M tokens); batch is 50% off standard rates
_INPUT_PRICE  = 1.00
_OUTPUT_PRICE = 5.00


def main() -> None:
    client = Anthropic(max_retries=2)

    print(f"Submitting batch of {len(QUESTIONS)} questions to {MODEL_WORKER}...\n")

    batch = client.messages.batches.create(
        requests=[
            {
                "custom_id": f"q{i}",
                "params": {
                    "model": MODEL_WORKER,
                    "max_tokens": MAX_TOKENS_WORKER,
                    "messages": [{"role": "user", "content": q}],
                },
            }
            for i, q in enumerate(QUESTIONS)
        ]
    )

    print(f"Batch ID:  {batch.id}")
    print(f"Status:    {batch.processing_status}")
    print("Polling...\n")

    while batch.processing_status == "in_progress":
        time.sleep(5)
        batch = client.messages.batches.retrieve(batch.id)
        print(f"  {batch.processing_status}")

    print(f"\nFinal status: {batch.processing_status}")
    print("=" * 60)

    total_input = 0
    total_output = 0

    for item in client.messages.batches.results(batch.id):
        idx = int(item.custom_id[1:])
        print(f"\n[{item.custom_id}] {QUESTIONS[idx]}")
        if item.result.type == "succeeded":
            msg = item.result.message
            total_input  += msg.usage.input_tokens
            total_output += msg.usage.output_tokens
            answer = msg.content[0].text
            print(f"→ {answer[:300]}{'...' if len(answer) > 300 else ''}")
        else:
            print(f"→ ERROR: {item.result.error}")

    print("\n" + "=" * 60)
    sync_cost  = (total_input * _INPUT_PRICE + total_output * _OUTPUT_PRICE) / 1_000_000
    batch_cost = sync_cost * 0.50
    print(f"Tokens:        {total_input} input  |  {total_output} output")
    print(f"Sync cost:     ${sync_cost:.6f}")
    print(f"Batch cost:    ${batch_cost:.6f}  (50% discount)")
    print(f"Saved:         ${sync_cost - batch_cost:.6f}")


if __name__ == "__main__":
    main()
