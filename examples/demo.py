"""Démo simple de l'agent."""
from src.agent import SimpleAgent


def main():
    agent = SimpleAgent()
    
    response = agent.run("Récupère les données pour 'python agents' et traite-les")
    print("Agent response:", response)


if __name__ == "__main__":
    main()