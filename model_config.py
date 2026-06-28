"""Central model configuration for Vintos."""

import os

# Primary generation model — Grok 4.1 Fast (2M context)
VINTOS_MODEL = "grok-4.1-fast"

# Embedding model
EMBED_MODEL = "grok-embeddings-alpha"

# Grok API endpoints
GROK_BASE = "https://api.x.ai/v1"
GROK_API = f"{GROK_BASE}/chat/completions"
GROK_EMBED_API = f"{GROK_BASE}/embeddings"

# Local Gemma 4 via LM Studio — for small classification/detection calls
LOCAL_MODEL = "gemma-4"
LM_STUDIO_API = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")

# File lock to serialize LM Studio calls (single-instance)
LM_LOCK_FILE = "/tmp/vintos-lm-lock"
LM_LOCK_TIMEOUT = 45  # seconds to wait before giving up

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
