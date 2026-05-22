"""File-based session memory — persist agent context across Python process runs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_MEMORY_FILE = Path(__file__).parent.parent / "memory" / "sessions.json"


def save_session(key: str, data: dict[str, Any]) -> None:
    """Write (or overwrite) a named session to disk."""
    _MEMORY_FILE.parent.mkdir(exist_ok=True)
    all_sessions = _load_all()
    all_sessions[key] = data
    _MEMORY_FILE.write_text(json.dumps(all_sessions, indent=2), encoding="utf-8")


def load_session(key: str) -> dict[str, Any] | None:
    """Return the session dict for *key*, or None if it doesn't exist."""
    return _load_all().get(key)


def delete_session(key: str) -> bool:
    """Remove a session. Returns True if it existed, False otherwise."""
    all_sessions = _load_all()
    if key not in all_sessions:
        return False
    del all_sessions[key]
    _MEMORY_FILE.write_text(json.dumps(all_sessions, indent=2), encoding="utf-8")
    return True


def _load_all() -> dict[str, Any]:
    if not _MEMORY_FILE.exists():
        return {}
    try:
        return json.loads(_MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
