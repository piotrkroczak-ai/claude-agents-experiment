"""
Tests for src/doc_agent.py

UNIT tests use tmp_path + monkeypatch to redirect DOCS_DIR — no real files modified.
LIVE test calls the real Anthropic API.

Run unit only:  uv run pytest tests/test_doc_agent.py -v -m "not live"
Run all:        uv run pytest tests/test_doc_agent.py -v
"""
import pytest
from src.doc_agent import DocumentationAgent


# ---------------------------------------------------------------------------
# UNIT tests — no API call, no real file mutation
# ---------------------------------------------------------------------------

def test_read_doc_existing():
    agent = DocumentationAgent()
    content = agent.read_doc("logs.md")
    assert not content.startswith("ERROR")
    assert len(content) > 0


def test_read_doc_missing():
    agent = DocumentationAgent()
    result = agent.read_doc("this_file_does_not_exist.md")
    assert result.startswith("ERROR")


def test_append_log_entry(tmp_path, monkeypatch):
    (tmp_path / "logs.md").write_text(
        "# Project Logs\n\n## 2026-05-22\n", encoding="utf-8"
    )
    monkeypatch.setattr("src.doc_agent.DOCS_DIR", tmp_path)

    agent = DocumentationAgent()
    agent.log_event("TEST", "unit test log entry")

    content = (tmp_path / "logs.md").read_text(encoding="utf-8")
    assert "[TEST]" in content
    assert "unit test log entry" in content


def test_report_bug_format(tmp_path, monkeypatch):
    (tmp_path / "bugs.md").write_text("# Bug Tracker\n", encoding="utf-8")
    (tmp_path / "logs.md").write_text(
        "# Project Logs\n\n## 2026-05-22\n", encoding="utf-8"
    )
    monkeypatch.setattr("src.doc_agent.DOCS_DIR", tmp_path)

    agent = DocumentationAgent()
    bug_id = agent.report_bug(
        title="Test bug",
        symptom="Something broke",
        root_cause="Bad input",
        resolution="Fixed validation",
    )

    assert bug_id == "BUG-001"
    content = (tmp_path / "bugs.md").read_text(encoding="utf-8")
    assert "## BUG-001" in content
    assert "Test bug" in content
    assert "Fixed validation" in content


# ---------------------------------------------------------------------------
# LIVE test — calls the real Anthropic API
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_audit_runs():
    agent = DocumentationAgent()
    result = agent.audit(focus="state")
    assert isinstance(result, str) and len(result) > 0
