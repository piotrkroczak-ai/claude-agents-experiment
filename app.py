"""
FastAPI web interface for Claude Agents Experiment.

Start:  uv run python app.py
Then:   open http://localhost:8000
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.registry import SpecialistRegistry, AgentPipeline
from src.teammate import Orchestrator

app = FastAPI(title="Claude Agents", docs_url=None, redoc_url=None)

# ---------------------------------------------------------------------------
# Shared registry — agents initialised once at startup
# ---------------------------------------------------------------------------
_registry = SpecialistRegistry()

_STATIC = Path(__file__).parent / "static"
_USAGE_JSONL = Path(__file__).parent / "documentation" / "token_usage.jsonl"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    task: str
    approach: str = "orchestrator"  # single | orchestrator | async | pipeline


class RunResponse(BaseModel):
    result: str
    approach: str
    elapsed: float


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    return (_STATIC / "index.html").read_text(encoding="utf-8")


@app.post("/run", response_model=RunResponse)
async def run(req: RunRequest):
    t0 = time.perf_counter()
    task = req.task.strip()

    if req.approach == "single":
        result = _registry.get("researcher").ask(task)

    elif req.approach == "orchestrator":
        orch = Orchestrator(teammates=_registry.subset(["researcher", "writer"]))
        result = orch.run(task)

    elif req.approach == "async":
        orch = Orchestrator(teammates=_registry.subset(["researcher", "writer"]))
        result = await orch.run_async(task)

    elif req.approach == "pipeline":
        pipeline = AgentPipeline(stages=_registry.subset(["researcher", "writer"]))
        result = pipeline.final(task)

    else:
        result = f"Unknown approach: {req.approach!r}"

    return RunResponse(result=result, approach=req.approach, elapsed=round(time.perf_counter() - t0, 2))


@app.get("/usage")
async def usage():
    if not _USAGE_JSONL.exists():
        return []
    lines = _USAGE_JSONL.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(l) for l in lines[-50:] if l.strip()]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
