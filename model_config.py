"""Central model configuration for Velaris."""

# Primary generation model — update this when switching models
VELARIS_MODEL = "google/gemma-4-12b-qat"

# Lightweight model for verification, classification, quick tasks
UTILITY_MODEL = "google/gemma-4-12b-qat"

# Embedding model
EMBED_MODEL = "nomic-embed-text-v1.5"

# LM Studio endpoint
LM_STUDIO_URL = "http://172.18.16.1:1234"
LM_API = f"{LM_STUDIO_URL}/v1/chat/completions"
