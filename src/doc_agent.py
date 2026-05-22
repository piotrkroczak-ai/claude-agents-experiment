"""
DocumentationAgent — reads/writes the documentation/ and tests/ folders.

Capabilities:
  - audit()         : scan src/ and flag undocumented choices or open bugs
  - log_event()     : append a timestamped entry to documentation/logs.md
  - report_bug()    : append a new BUG-XXX entry to documentation/bugs.md
  - document_choice(): append a tech choice entry to documentation/tech_choix.md
  - record_test()   : append a test result to tests/tests.md
  - read_doc()      : read any file in documentation/ or tests/
  - update_state()  : rewrite the "What exists" table in current_state.md

The agent uses Claude (Haiku — single-turn reads, Sonnet — multi-step audit)
with file-reading/writing tools so it can inspect the actual codebase.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import date
from pathlib import Path

from anthropic import Anthropic
from src.token_optimization import (
    MODEL_ORCHESTRATOR,
    MODEL_WORKER,
    MAX_TOKENS_ORCHESTRATOR,
    MAX_TOKENS_WORKER,
    cached_system,
    log_usage,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
DOCS_DIR = ROOT / "documentation"
TESTS_DIR = ROOT / "tests"
SRC_DIR = ROOT / "src"


# ---------------------------------------------------------------------------
# Tool definitions (used by the audit agent's LLM loop)
# ---------------------------------------------------------------------------
_TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file from the project. Path is relative to project root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path, e.g. 'src/agents.py'"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files in a directory (non-recursive).",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Relative directory path, e.g. 'src'"}
            },
            "required": ["directory"],
        },
    },
    {
        "name": "write_doc_file",
        "description": "Write or overwrite a file in documentation/ or tests/.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename only, e.g. 'logs.md'"},
                "subfolder": {
                    "type": "string",
                    "enum": ["documentation", "tests"],
                    "description": "Target folder",
                },
                "content": {"type": "string", "description": "Full file content"},
            },
            "required": ["filename", "subfolder", "content"],
        },
    },
    {
        "name": "run_tests",
        "description": "Run the pytest test suite and return the output.",
        "input_schema": {
            "type": "object",
            "properties": {
                "args": {
                    "type": "string",
                    "description": "Extra pytest args, e.g. '-v -k test_agent_init'",
                }
            },
            "required": [],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------
def _execute_tool(name: str, tool_input: dict) -> str:
    if name == "read_file":
        path = ROOT / tool_input["path"]
        if not path.exists():
            return f"ERROR: file not found — {tool_input['path']}"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR reading file: {e}"

    if name == "list_files":
        directory = ROOT / tool_input["directory"]
        if not directory.exists():
            return f"ERROR: directory not found — {tool_input['directory']}"
        entries = sorted(p.name for p in directory.iterdir())
        return "\n".join(entries)

    if name == "write_doc_file":
        folder = DOCS_DIR if tool_input["subfolder"] == "documentation" else TESTS_DIR
        target = folder / tool_input["filename"]
        target.write_text(tool_input["content"], encoding="utf-8")
        return f"Written: {target.relative_to(ROOT)}"

    if name == "run_tests":
        args = tool_input.get("args", "")
        cmd = f"python -m pytest tests/ {args} -v --tb=short"
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
        output = result.stdout + result.stderr
        return output[:3000]  # cap to stay within token budget

    return f"ERROR: unknown tool '{name}'"


# ---------------------------------------------------------------------------
# DocumentationAgent
# ---------------------------------------------------------------------------
class DocumentationAgent:
    """
    Agent that maintains documentation/ and tests/ in sync with the codebase.

    Token strategy:
      - Simple file writes (log_event, report_bug, etc.) — pure Python, no API call.
      - audit() — uses Sonnet with tool loop to inspect src/ and generate findings.
      - update_state() — uses Haiku for a single-turn file-list read + rewrite.
    """

    def __init__(self):
        self.client = Anthropic()

    # ------------------------------------------------------------------
    # Low-level helpers — no API call
    # ------------------------------------------------------------------

    def read_doc(self, filename: str, subfolder: str = "documentation") -> str:
        """Read a file from documentation/ or tests/."""
        folder = DOCS_DIR if subfolder == "documentation" else TESTS_DIR
        path = folder / filename
        if not path.exists():
            return f"ERROR: {filename} not found in {subfolder}/"
        return path.read_text(encoding="utf-8")

    def _next_bug_id(self) -> str:
        """Return the next BUG-XXX ID by counting existing ones in bugs.md."""
        content = self.read_doc("bugs.md")
        if content.startswith("ERROR"):
            return "BUG-001"
        count = content.count("## BUG-")
        return f"BUG-{count + 1:03d}"

    # ------------------------------------------------------------------
    # Append helpers — no API call, pure file writes
    # ------------------------------------------------------------------

    def log_event(self, event_type: str, description: str) -> None:
        """
        Append a timestamped entry to documentation/logs.md.

        Args:
            event_type: One of INIT, FEAT, FIX, REFACTOR, TEST, DOCS, BUG, USAGE
            description: Short description of the event
        """
        today = date.today().isoformat()
        entry = f"\n- `[{event_type}]` {description}"
        path = DOCS_DIR / "logs.md"
        current = path.read_text(encoding="utf-8")

        # Insert under today's date section, or append a new one
        date_header = f"\n## {today}"
        if date_header in current:
            # Append after the last entry under today's section
            idx = current.index(date_header)
            next_section = current.find("\n## ", idx + 1)
            if next_section == -1:
                current = current + entry
            else:
                current = current[:next_section] + entry + current[next_section:]
        else:
            current = current + f"\n\n{date_header}\n{entry}"

        path.write_text(current, encoding="utf-8")

    def report_bug(
        self,
        title: str,
        symptom: str,
        root_cause: str,
        resolution: str,
        status: str = "Open",
        files: str = "",
        lesson: str = "",
    ) -> str:
        """
        Append a new BUG-XXX entry to documentation/bugs.md.
        Returns the bug ID assigned.
        """
        bug_id = self._next_bug_id()
        today = date.today().isoformat()
        entry = f"""
---

## {bug_id} — {title}

**Status:** {status}
**Discovered:** {today}
**File(s):** {files or "N/A"}

**Symptom:**
{symptom}

**Root cause:**
{root_cause}

**Resolution:**
{resolution}

**Lesson:**
{lesson or "N/A"}
"""
        path = DOCS_DIR / "bugs.md"
        current = path.read_text(encoding="utf-8")
        path.write_text(current + entry, encoding="utf-8")
        self.log_event("BUG", f"{bug_id} added: {title}")
        return bug_id

    def document_choice(
        self,
        number: int,
        title: str,
        decision: str,
        alternatives: str,
        why: str,
        trade_offs: str,
        reference: str = "",
    ) -> None:
        """Append a tech choice entry to documentation/tech_choix.md."""
        entry = f"""
---

## {number}. {title}

**Decision:** {decision}

**Alternatives:** {alternatives}

**Why:**
{why}

**Trade-offs:** {trade_offs}
"""
        if reference:
            entry += f"\n**Reference:** {reference}\n"

        path = DOCS_DIR / "tech_choix.md"
        current = path.read_text(encoding="utf-8")
        path.write_text(current + entry, encoding="utf-8")
        self.log_event("DOCS", f"Tech choice #{number} added: {title}")

    def record_test(
        self,
        test_file: str,
        test_name: str,
        test_type: str,
        result: str,
        notes: str = "",
    ) -> None:
        """
        Append a test result entry to tests/tests.md.

        Args:
            test_file: e.g. "test_token_optimization.py"
            test_name: e.g. "test_cached_system_format"
            test_type: "UNIT" or "LIVE"
            result: "PASS", "FAIL", or "SKIP"
            notes: Optional details, error messages, token cost
        """
        today = date.today().isoformat()
        icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "⊘"}.get(result, "?")
        entry = f"""
### {test_name} [{test_type}]
**Result ({today}):** {result} {icon}
**Notes:** {notes or "—"}
"""
        path = TESTS_DIR / "tests.md"
        # Find the section for the test file and append there
        content = path.read_text(encoding="utf-8")
        section_header = f"## Test File: `tests/{test_file}`"
        if section_header in content:
            # Append at end of that section (before next ##)
            idx = content.index(section_header)
            next_section = content.find("\n## ", idx + len(section_header))
            if next_section == -1:
                content = content + entry
            else:
                content = content[:next_section] + entry + content[next_section:]
        else:
            # Create a new section at the end
            content = content + f"\n\n{section_header}\n{entry}"
        path.write_text(content, encoding="utf-8")
        self.log_event("TEST", f"{test_file}::{test_name} → {result}")

    # ------------------------------------------------------------------
    # update_state — single-turn Haiku call to refresh current_state.md
    # ------------------------------------------------------------------

    def update_state(self) -> str:
        """
        Ask Haiku to read the project files and rewrite current_state.md.
        Single-turn, no history — Haiku model to keep cost low.
        """
        # Gather current file listings
        src_files = "\n".join(sorted(p.name for p in SRC_DIR.iterdir() if p.is_file()))
        doc_files = "\n".join(sorted(p.name for p in DOCS_DIR.iterdir() if p.is_file()))
        test_files = "\n".join(sorted(p.name for p in TESTS_DIR.iterdir() if p.is_file()))
        existing_state = self.read_doc("current_state.md")

        prompt = (
            f"Today: {date.today().isoformat()}\n\n"
            f"src/ files:\n{src_files}\n\n"
            f"documentation/ files:\n{doc_files}\n\n"
            f"tests/ files:\n{test_files}\n\n"
            f"Existing current_state.md:\n{existing_state[:2000]}\n\n"
            "Update the 'What exists and works' and 'What is NOT yet done' tables "
            "in current_state.md to reflect the file listings above. "
            "Return only the complete updated markdown file content."
        )

        run_id = uuid.uuid4().hex[:8]
        response = self.client.messages.create(
            model=MODEL_WORKER,
            max_tokens=MAX_TOKENS_WORKER * 3,  # state file needs a bit more room
            system=cached_system(
                "You maintain a project state file. Update tables accurately based on "
                "the file listings provided. Return only the full markdown content."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        log_usage(response, agent="DocumentationAgent", call_type="update_state", run_id=run_id)
        new_content = response.content[0].text
        (DOCS_DIR / "current_state.md").write_text(new_content, encoding="utf-8")
        self.log_event("DOCS", "current_state.md updated via update_state()")
        return new_content

    # ------------------------------------------------------------------
    # audit — multi-step Sonnet tool loop
    # ------------------------------------------------------------------

    def audit(self, focus: str = "all") -> str:
        """
        Ask Sonnet to inspect the codebase and produce an audit report.

        The agent reads src/ files, documentation files, and test files,
        then reports:
          - Tech choices not yet documented in tech_choix.md
          - Open bugs that may need resolution
          - Tests missing for existing modules
          - Inconsistencies between current_state.md and actual files

        Args:
            focus: "all" | "bugs" | "tests" | "tech" | "state"

        Returns the audit report as a string.
        """
        focus_instruction = {
            "all": "Check all documentation: bugs, tech choices, test coverage, and current_state.",
            "bugs": "Focus on open bugs in bugs.md — check if they are still reproducible.",
            "tests": "Focus on test coverage — which src/ modules lack tests?",
            "tech": "Focus on tech_choix.md — are all architectural decisions documented?",
            "state": "Focus on current_state.md — is it accurate vs actual files?",
        }.get(focus, "Check all documentation.")

        system = cached_system(
            "You are a documentation auditor for a Python project. "
            "You have tools to read files and run tests. "
            "Produce a concise audit report: what is missing, what is wrong, "
            "what should be updated. Be specific — name files and line numbers where relevant. "
            "When done, output your findings as a markdown report and stop."
        )

        run_id = uuid.uuid4().hex[:8]
        messages: list[dict] = [{
            "role": "user",
            "content": (
                f"{focus_instruction}\n\n"
                "Start by listing files in src/, documentation/, and tests/. "
                "Then read the relevant files. Then produce your report."
            ),
        }]

        # Agentic tool loop — Sonnet with multi-step reasoning
        while True:
            response = self.client.messages.create(
                model=MODEL_ORCHESTRATOR,
                max_tokens=MAX_TOKENS_ORCHESTRATOR,
                output_config={"effort": "medium"},
                thinking={"type": "disabled"},
                system=system,
                tools=_TOOLS,
                messages=messages,
            )
            log_usage(response, agent="DocumentationAgent", call_type=f"audit.{focus}", run_id=run_id)

            if response.stop_reason == "end_turn":
                final = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                self.log_event("DOCS", f"audit({focus}) completed")
                return final

            if response.stop_reason != "tool_use":
                break

            # Execute tool calls and append results
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        return "Audit loop exited unexpectedly."
