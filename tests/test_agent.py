"""Tests for src/agents.py"""
import pytest
from src.agents import SimpleAgent


def test_agent_init():
    agent = SimpleAgent()
    assert agent.client is not None
    assert agent.messages == []


@pytest.mark.live
def test_agent_run():
    agent = SimpleAgent()
    response = agent.run("Say hello in one word.")
    assert isinstance(response, str)
    assert len(response) > 0
