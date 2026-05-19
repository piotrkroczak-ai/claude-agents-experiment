# Claude Agents Experiment - Setup

## Prérequis
- Python 3.11+
- UV installé globalement
- Clé API Anthropic (via .env)

## Installation

```bash
# copie le repo git
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/piotrkroczak-ai/claude-agents-experiment.git
git push -u origin main

# Crée venv et installe dépendances
uv venv
uv sync

# Configure ton API key
cp .env.example .env
# Édite .env et ajoute: ANTHROPIC_API_KEY=sk-...
```

## Utilisation

```bash
# Exécute l'example
uv run python examples/demo.py

# Lance les tests
uv run pytest tests/

# Format + lint
uv run black src/ tests/
uv run ruff check src/ tests/
```

## Structure
- `src/agent.py` : Logique agent principale
- `src/tools.py` : Outils de l'agent
- `examples/demo.py` : Démo d'utilisation