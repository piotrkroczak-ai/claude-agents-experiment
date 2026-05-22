"""Configuration du projet."""
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY non trouvée dans .env")

# Optimization constants live in src/token_optimization.py (with full justification).
# Config re-exports them for backward compatibility with SimpleAgent.
from src.token_optimization import (
    MODEL_ORCHESTRATOR,
    MODEL_WORKER,
    MAX_TOKENS_ORCHESTRATOR,
    MAX_TOKENS_WORKER,
)

MODEL = MODEL_ORCHESTRATOR
MAX_TOKENS = MAX_TOKENS_ORCHESTRATOR