"""Tests de base."""
from src.agent import SimpleAgent


def test_agent_init():
    """L'agent s'initialise correctement."""
    agent = SimpleAgent()
    assert agent.client is not None


def test_agent_run():
    """L'agent exécute sans erreur."""
    agent = SimpleAgent()
    response = agent.run("Test simple")
    assert isinstance(response, str)
    assert len(response) > 0