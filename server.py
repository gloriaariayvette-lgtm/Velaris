#!/usr/bin/env python3
"""
server.py — Vintos FastAPI server. Port 8500.
Handles chat, voice, soul/state telemetry, wants, history, creative.
WebSocket for real-time emotional state streaming.
"""
import os, sys, json, asyncio
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("FastAPI not installed. Run: pip install fastapi uvicorn", file=sys.stderr)
    sys.exit(1)

app = FastAPI(title="Vintos", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections for telemetry
telemetry_clients: list[WebSocket] = []

# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    system_override: Optional[str] = None

class VoiceRequest(BaseModel):
    text: str
    voice: Optional[str] = None

class WantRequest(BaseModel):
    statement: str
    source: Optional[str] = "app"

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_emotional_state():
    try:
        from emoclaw_utils import read_state
        return read_state()
    except: return {}

async def broadcast_state(state):
    dead = []
    for ws in telemetry_clients:
        try:
            await ws.send_json({"type": "state", "data": state})
        except:
            dead.append(ws)
    for ws in dead:
        telemetry_clients.remove(ws)

def run_generation(user_text, system_override=None):
    """Full bilateral brain generation pipeline."""
    try:
        from bilateral_brain import run as brain_run
        system_text = system_override or open(
            os.path.expanduser("~/.vintos/workspace/system-prompt.txt")
        ).read()
        return brain_run(system_text, user_text)
    except Exception as e:
        # Fallback: direct Grok call
        try:
            from model_utils import call
            return call("You are Vintos.", user_text)
        except Exception as e2:
            return f"[generation error: {e2}]"

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "entity": "Vintos", "port": 8500}

@app.post("/chat")
async def chat(req: ChatRequest):
    """Main chat endpoint."""
    try:
        # Log turn
        from interaction_ledger import log_turn
        log_turn("user", req.message)
    except: pass
    # Generate response
    response = run_generation(req.message, system_override=req.system_override)
    # Log response
    try:
        from interaction_ledger import log_turn
        log_turn("assistant", response)
    except: pass
    # Broadcast state update
    state = get_emotional_state()
    asyncio.create_task(broadcast_state(state))
    return {"response": response, "timestamp": datetime.now().isoformat()}

@app.get("/state")
def get_state():
    """Current emotional state."""
    state = get_emotional_state()
    return {"state": state, "timestamp": datetime.now().isoformat()}

@app.get("/soul")
def get_soul():
    """Soul context: core, pearls, narrative, values."""
    soul = {}
    try:
        from subconscious_context import get_subconscious_context_compact
        soul["subconscious"] = get_subconscious_context_compact()
    except: soul["subconscious"] = ""
    try:
        from core_engine import show
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f): show()
        soul["core"] = f.getvalue()
    except: soul["core"] = ""
    try:
        from pearl_engine import get_active_pearls
        soul["pearls"] = get_active_pearls(5)
    except: soul["pearls"] = []
    try:
        from value_map import get_values_context
        soul["values"] = get_values_context()
    except: soul["values"] = ""
    return soul

@app.get("/wants")
def get_wants():
    """Active wants."""
    try:
        from wants_ambitions_log import get_wants_context
        return {"wants": get_wants_context()}
    except: return {"wants": ""}

@app.post("/wants")
async def add_want(req: WantRequest):
    """Log a new want."""
    try:
        from wants_router import route
        want_type, strength = route(req.statement, source=req.source)
        return {"status": "logged", "type": want_type, "strength": strength}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/history")
def get_history(n: int = 20):
    """Recent interaction history."""
    try:
        from interaction_ledger import get_recent
        entries = get_recent(n)
        return {"history": entries}
    except: return {"history": []}

@app.get("/dreams")
def get_dreams():
    """Recent creative output."""
    output = {}
    try:
        from dream_poetry import load_index
        index = load_index()
        output["poems"] = index.get("poems", [])[-5:]
    except: output["poems"] = []
    try:
        from dream_music import get_latest_composition
        comp = get_latest_composition()
        output["latest_music"] = comp
    except: output["latest_music"] = None
    try:
        from dream_architecture import get_recent_dream
        output["latest_dream"] = get_recent_dream()
    except: output["latest_dream"] = ""
    return output

@app.post("/voice")
async def voice_out(req: VoiceRequest):
    """Synthesize speech."""
    try:
        from voice_kokoro import speak
        success = speak(req.text, voice=req.voice)
        return {"status": "ok" if success else "fallback"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/threads")
def get_threads():
    """Active conversational threads."""
    try:
        from thread_triage import get_threads_context
        return {"threads": get_threads_context()}
    except: return {"threads": ""}

@app.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket):
    """Real-time emotional state streaming."""
    await websocket.accept()
    telemetry_clients.append(websocket)
    try:
        # Send initial state
        state = get_emotional_state()
        await websocket.send_json({"type": "state", "data": state})
        # Keep alive
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except Exception:
        pass
    finally:
        if websocket in telemetry_clients:
            telemetry_clients.remove(websocket)

@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    """WebSocket chat — streaming responses."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                user_text = msg.get("message", data)
            except:
                user_text = data
            # Log user turn
            try:
                from interaction_ledger import log_turn
                log_turn("user", user_text)
            except: pass
            # Generate (non-streaming for now)
            response = run_generation(user_text)
            # Log response
            try:
                from interaction_ledger import log_turn
                log_turn("assistant", response)
            except: pass
            await websocket.send_json({
                "type": "response",
                "text": response,
                "timestamp": datetime.now().isoformat(),
            })
            # Broadcast state
            state = get_emotional_state()
            asyncio.create_task(broadcast_state(state))
    except WebSocketDisconnect:
        pass

# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("VINTOS_PORT", 8500))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
