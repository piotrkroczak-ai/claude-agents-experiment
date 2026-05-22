"""
Tests for Phase 5: specialist registry and agent pipeline.

Unit only:  uv run pytest tests/test_phase5.py -v -m "not live"
All:        uv run pytest tests/test_phase5.py -v
"""
import pytest

from src.registry import SpecialistRegistry, AgentPipeline, SPECIALIST_CONFIGS


# ---------------------------------------------------------------------------
# UNIT — SpecialistRegistry
# ---------------------------------------------------------------------------

def test_registry_default_roles():
    reg = SpecialistRegistry()
    assert set(reg.roles) == set(SPECIALIST_CONFIGS.keys())


def test_registry_get_known_role():
    reg = SpecialistRegistry()
    agent = reg.get("researcher")
    assert agent.role == "researcher"


def test_registry_get_unknown_raises():
    reg = SpecialistRegistry()
    with pytest.raises(KeyError, match="chef"):
        reg.get("chef")


def test_registry_subset():
    reg = SpecialistRegistry()
    agents = reg.subset(["researcher", "writer"])
    assert len(agents) == 2
    assert {a.role for a in agents} == {"researcher", "writer"}


def test_registry_partial_init():
    reg = SpecialistRegistry(roles=["coder", "reviewer"])
    assert set(reg.roles) == {"coder", "reviewer"}
    with pytest.raises(KeyError):
        reg.get("researcher")


def test_registry_all_returns_agents():
    reg = SpecialistRegistry()
    agents = reg.all()
    assert len(agents) == len(SPECIALIST_CONFIGS)


def test_pipeline_stages_stored():
    reg = SpecialistRegistry()
    pipeline = AgentPipeline(stages=reg.subset(["researcher", "writer"]))
    assert len(pipeline.stages) == 2
    assert pipeline.stages[0].role == "researcher"
    assert pipeline.stages[1].role == "writer"


def test_pipeline_empty_stages():
    pipeline = AgentPipeline(stages=[])
    result = pipeline.final("anything")
    assert result == ""


# ---------------------------------------------------------------------------
# LIVE
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_registry_researcher_responds():
    reg = SpecialistRegistry()
    result = reg.get("researcher").ask("What is a Python decorator?")
    assert isinstance(result, str) and len(result) > 0


@pytest.mark.live
def test_pipeline_produces_all_stage_outputs():
    reg = SpecialistRegistry()
    pipeline = AgentPipeline(stages=reg.subset(["researcher", "writer"]))
    results = pipeline.run("What is a Python decorator?")
    assert "researcher" in results
    assert "writer" in results
    assert all(len(v) > 0 for v in results.values())


@pytest.mark.live
def test_orchestrator_with_registry():
    from src.teammate import Orchestrator
    reg = SpecialistRegistry()
    orch = Orchestrator(teammates=reg.subset(["researcher", "writer"]))
    result = orch.run("What is a Python decorator?")
    assert isinstance(result, str) and len(result) > 0
