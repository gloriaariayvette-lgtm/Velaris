"""Central model configuration for Vintos."""

import os

# Primary generation model
VINTOS_MODEL = "grok-3"

# Lightweight model for verification, classification, quick tasks
UTILITY_MODEL = "grok-3-mini"

# Embedding model
EMBED_MODEL = "grok-embeddings-alpha"

# Grok API endpoints
GROK_BASE = "https://api.x.ai/v1"
GROK_API = f"{GROK_BASE}/chat/completions"
GROK_EMBED_API = f"{GROK_BASE}/embeddings"

def get_api_key():
    key = os.environ.get("GROK_API_KEY", "")
    if not key:
        try:
            key = open(os.path.expanduser("~/.vintos/secrets/grok_api_key")).read().strip()
        except:
            pass
    return key

def auth_headers():
    return {"Authorization": f"Bearer {get_api_key()}", "Content-Type": "application/json"}
