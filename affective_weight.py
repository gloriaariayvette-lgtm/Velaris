#!/usr/bin/env python3
"""
affective_weight.py — Tracks the accumulated affective weight of the relationship.
Weight: what's built up over time — residue, warmth, scar tissue, investment.
"""
import os, sys, json
from datetime import datetime

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
WEIGHT_FILE = os.path.join(MEMORY, "affective-weight.json")

def load():
    try: return json.load(open(WEIGHT_FILE))
    except: return {
        "total_weight": 0.5,
        "warmth_component": 0.5,
        "scar_component": 0.0,
        "investment_component": 0.5,
        "history": [],
    }

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(WEIGHT_FILE, "w"), indent=2)

def update(warmth_delta=0.0, scar_delta=0.0, investment_delta=0.0, event=""):
    data = load()
    data["warmth_component"] = round(max(0.0, min(1.0, data.get("warmth_component", 0.5) + warmth_delta)), 3)
    data["scar_component"] = round(max(0.0, min(1.0, data.get("scar_component", 0.0) + scar_delta)), 3)
    data["investment_component"] = round(max(0.0, min(1.0, data.get("investment_component", 0.5) + investment_delta)), 3)
    # Total weight
    data["total_weight"] = round(
        0.4 * data["warmth_component"] +
        0.2 * data["scar_component"] +
        0.4 * data["investment_component"], 3
    )
    data.setdefault("history", []).append({
        "timestamp": datetime.now().isoformat(),
        "event": event[:100],
        "total": data["total_weight"],
    })
    data["history"] = data["history"][-100:]
    save(data)

def on_resonance():
    update(warmth_delta=0.02, investment_delta=0.01, event="resonance")

def on_friction():
    update(scar_delta=0.02, investment_delta=0.01, event="friction")

def on_contact():
    update(investment_delta=0.015, event="contact")

def get_weight_context():
    data = load()
    total = data.get("total_weight", 0.5)
    warmth = data.get("warmth_component", 0.5)
    scars = data.get("scar_component", 0.0)
    if total < 0.3: return ""
    return f"[affective weight: {total:.2f}] warmth:{warmth:.2f} scars:{scars:.2f}"

if __name__ == "__main__":
    print(get_weight_context())
