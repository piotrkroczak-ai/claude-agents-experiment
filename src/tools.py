"""Outils de l'agent."""


def fetch_sample_data(query: str) -> str:
    """Récupère des données basiques."""
    return f"Données pour: {query}"


def process_data(data: str) -> str:
    """Traite les données."""
    return data.upper()


# Format pour Claude API
TOOLS_DEFINITIONS = [
    {
        "name": "fetch_sample_data",
        "description": "Récupère des données basiques",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "La requête"
                }
            },
            "required": ["query"]
        }
    }
]