# Claude Agents Experiment

Exploration des patterns d'agents expérimentaux avec Claude.

## Objectif

- [X] Configuration initiale UV + structure
- [ ] Implémenter agent basique avec outils
- [ ] Ajouter orchestration multi-agents
- [ ] Tests et validation

## Architecture

### Agent Pattern
```python
Agent
├── System Prompt
├── Tools (list)
└── Context Budget Management
```

### Outils Disponibles
- `fetch_data()` : Récupère des données
- `process_data()` : Traite les données
- `save_result()` : Sauvegarde le résultat

## Quick Start

```bash
uv sync
uv run python examples/demo.py
```

## Apprentissages

(À remplir au fur et à mesure)

claude-agents-experiment\
├── pyproject.toml              # Dépendances et config
├── uv.lock                     # Lock file (À COMMITER)
├── SETUP.md                    # Instructions setup
├── .gitignore                  # Ignore .venv/, __pycache__, etc
├── README.md                   # Présentation du projet
├── src/
│   ├── __init__.py
│   ├── agent.py               # Logique principale du/des agents
│   ├── tools.py               # Outils/functions de l'agent
│   └── config.py              # Variables d'env, clés API, etc
├── tests/
│   ├── __init__.py
│   └── test_agent.py          # Tests unitaires
└── examples/
    └── demo.py                # Exemple d'utilisation