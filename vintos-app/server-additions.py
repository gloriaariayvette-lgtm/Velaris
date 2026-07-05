# ── Already handled by Vintos's server.py, kept for reference ──
# The app talks to http://<tailscale-ip>:8500 with X-Vintos-Secret.
# CORS for Capacitor (capacitor://localhost) — add if not present:

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "capacitor://localhost",
        "http://localhost",
        "http://localhost:8500",
        # Tailscale range
        "http://100.64.0.0/10",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
