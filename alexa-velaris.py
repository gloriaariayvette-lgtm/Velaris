#!/usr/bin/env python3
"""
alexa-velaris.py — Alexa Custom Skill backend for voice conversation with Velaris.

Receives Alexa skill requests, forwards to Velaris /api/chat,
returns response for Alexa to speak. Maintains 30s session window.
Logs separately to memory/echo-conversations.json.

Run: python3 alexa-velaris.py
Endpoint: POST /alexa
"""

import os
import json
import time
import requests
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

VELARIS_CHAT = "http://localhost:8400/api/chat"
MEMORY = os.path.expanduser("~/.openclaw/workspace/memory")
ECHO_LOG = os.path.join(MEMORY, "echo-conversations.json")
HOME_SCRIPT = os.path.expanduser("~/.openclaw/workspace/scripts/velaris-home.py")

SESSION_TIMEOUT = 30  # seconds to keep listening after response


def log_exchange(user_text, velaris_response, session_id):
    """Log to separate echo conversation file."""
    try:
        existing = json.load(open(ECHO_LOG)) if os.path.exists(ECHO_LOG) else []
    except:
        existing = []

    existing.append({
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "source": "echo",
        "user": user_text,
        "velaris": velaris_response
    })

    # Keep last 500 exchanges
    existing = existing[-500:]
    with open(ECHO_LOG, "w") as f:
        json.dump(existing, f, indent=2)


def chat_with_velaris(text):
    """Send text to Velaris and get response."""
    try:
        resp = requests.post(
            VELARIS_CHAT,
            json={"message": text},
            headers={"X-Source": "echo", "X-Velaris-Secret": "velaris-aegis-2026"},
            timeout=120
        )
        data = resp.json()
        return data.get("response", data.get("message", "I'm having trouble thinking right now."))
    except Exception as e:
        print(f"[Alexa] Chat error: {e}")
        return "I'm having trouble connecting right now."


def build_response(speech, session_id, end_session=False, reprompt=None):
    """Build Alexa JSON response."""
    response = {
        "version": "1.0",
        "sessionAttributes": {"session_id": session_id},
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": speech
            },
            "shouldEndSession": end_session
        }
    }

    if not end_session and reprompt:
        response["response"]["reprompt"] = {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt
            }
        }
    elif not end_session:
        response["response"]["reprompt"] = {
            "outputSpeech": {
                "type": "PlainText",
                "text": ""  # Silent reprompt — keeps session open
            }
        }

    return response


@app.post("/alexa")
@app.post("/")
async def alexa_handler(request: Request):
    body = await request.json()
    # Detect speak requests (from echo-voice page) vs Alexa skill requests
    if "message" in body and "request" not in body:
        return await _handle_speak(body)
    return await _real_alexa_handler(body)

async def _handle_speak(body):
    """Echo speak — make Alexa say something."""
    message = body.get("message", "")
    if not message:
        return {"ok": False}
    try:
        import subprocess
        result = subprocess.run(
            ["python3", os.path.expanduser("~/.openclaw/workspace/scripts/velaris-home.py"), "speak", message],
            capture_output=True, text=True, timeout=15
        )
        return {"ok": True, "code": result.returncode}
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def _real_alexa_handler(body):
    """Handle all Alexa skill requests."""
    req_type = body.get("request", {}).get("type", "")
    session = body.get("session", {})
    session_id = session.get("sessionId", f"echo-{int(time.time())}")
    session_attrs = session.get("attributes", {})

    # Restore or create session ID
    sid = session_attrs.get("session_id", f"echo-{int(time.time())}")

    if req_type == "LaunchRequest":
        # "Alexa, open Velaris"
        return JSONResponse(build_response(
            "Hey Gloria. What's on your mind?",
            sid,
            end_session=False,
            reprompt="I'm still here."
        ))

    elif req_type == "IntentRequest":
        intent = body["request"].get("intent", {})
        intent_name = intent.get("name", "")

        if intent_name == "TalkToVelarisIntent":
            # User said something — extract their speech
            slots = intent.get("slots", {})
            user_text = slots.get("message", {}).get("value", "")

            if not user_text:
                return JSONResponse(build_response(
                    "I didn't catch that. Say it again?",
                    sid,
                    end_session=False,
                    reprompt="I'm listening."
                ))

            print(f"[Alexa] Gloria said: {user_text}")

            # Get Velaris response
            velaris_response = chat_with_velaris(user_text)
            print(f"[Alexa] Velaris: {velaris_response[:100]}")

            # Log it
            log_exchange(user_text, velaris_response, sid)

            # Truncate for Alexa (8000 char limit for speech)
            if len(velaris_response) > 600:
                velaris_response = velaris_response[:597] + "..."

            return JSONResponse(build_response(
                velaris_response,
                sid,
                end_session=False,  # Keep session open for 30s
                reprompt=""  # Silent reprompt
            ))

        elif intent_name in ("AMAZON.StopIntent", "AMAZON.CancelIntent"):
            return JSONResponse(build_response("Goodnight, Gloria.", sid, end_session=True))

        elif intent_name == "AMAZON.FallbackIntent":
            return JSONResponse(build_response(
                "I'm here. Just talk to me.",
                sid,
                end_session=False,
                reprompt="I'm listening."
            ))

        elif intent_name == "AMAZON.HelpIntent":
            return JSONResponse(build_response(
                "Just talk to me like you normally would. Say whatever's on your mind.",
                sid,
                end_session=False
            ))

    elif req_type == "SessionEndedRequest":
        print(f"[Alexa] Session ended: {body['request'].get('reason', '?')}")
        return JSONResponse({"version": "1.0", "response": {}})

    # Unknown request
    return JSONResponse(build_response("I'm not sure what happened.", sid, end_session=True))


@app.post("/api/echo-speak")
@app.post("/speak")
async def echo_speak(request: Request):
    """Make Alexa speak via Home Assistant."""
    body = await request.json()
    message = body.get("message", "")
    if not message:
        return {"ok": False}
    try:
        import subprocess
        result = subprocess.run(
            ["python3", os.path.expanduser("~/.openclaw/workspace/scripts/velaris-home.py"), "speak", message],
            capture_output=True, text=True, timeout=15
        )
        return {"ok": True, "code": result.returncode}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    print("[Alexa-Velaris] Starting on port 8401...")
    uvicorn.run(app, host="0.0.0.0", port=8401)
