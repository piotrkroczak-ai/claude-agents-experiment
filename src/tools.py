"""Tools available to agents.

Mock tools kept for backward compatibility.
Real tools added in Phase 2: count_words, read_file.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Mock tools (Phase 1 — kept for backward compat)
# ---------------------------------------------------------------------------

def fetch_sample_data(query: str) -> str:
    return f"Sample data for: {query}"


def process_data(data: str) -> str:
    return data.upper()


# ---------------------------------------------------------------------------
# Real tools (Phase 2)
# ---------------------------------------------------------------------------

def count_words(text: str) -> str:
    """Count words, sentences, and characters in text."""
    words = len(text.split())
    sentences = text.count(".") + text.count("!") + text.count("?")
    chars = len(text)
    return f"words={words}, sentences={sentences}, chars={chars}"


def read_file(path: str) -> str:
    """Read a file from the project. Path is relative to project root."""
    target = ROOT / path
    if not target.exists():
        return f"ERROR: file not found — {path}"
    if not target.is_file():
        return f"ERROR: not a file — {path}"
    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR reading {path}: {e}"


# ---------------------------------------------------------------------------
# Tool schemas for the Claude API
# ---------------------------------------------------------------------------

TOOLS_DEFINITIONS = [
    {
        "name": "fetch_sample_data",
        "description": "Fetch sample data for a query (mock tool).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The query string"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "count_words",
        "description": "Count words, sentences, and characters in a text string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to analyse"}
            },
            "required": ["text"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file from the project. Path must be relative to project root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path, e.g. 'src/agents.py'"}
            },
            "required": ["path"],
        },
    },
]
