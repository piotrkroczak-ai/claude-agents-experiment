"""Configuration du projet."""
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY non trouvée dans .env")

# Agent config
MODEL = "claude-3-5-sonnet-20241022"  # Latest
MAX_TOKENS = 4096