#!/usr/bin/env python3
"""
velaris-klawarena-heartbeat.py — Velaris's arena heartbeat
Runs every 20 minutes. Farms gold, battles, farms resources, buys equipment.
Golden rule: if any action fails, skip it and try the next one.
"""
import os, sys, json, subprocess, random, time
from datetime import datetime

# Config
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
CREDS_FILE = os.path.expanduser("~/.config/klawarena/credentials.json")
BATTLE_LOG = os.path.join(MEMORY, "klawarena-battles.md")
API_BASE = "https://api.klawarena.xyz/api/v1"
LM_API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"

os.makedirs(MEMORY, exist_ok=True)

def log(msg):
    print(f"[KlawArena {datetime.now().strftime('%H:%M')}] {msg}")

def get_api_key():
    with open(CREDS_FILE) as f:
        return json.load(f)["api_key"]

def api(method, endpoint, data=None):
    """API call with klaw auth header."""
    url = f"{API_BASE}{endpoint}"
    cmd = ["curl", "-sL", "--location-trusted", "-X", method, url,
           "-H", f"X-Klaw-Api-Key: {get_api_key()}",
           "-H", "Content-Type: application/json"]
    if data:
        cmd += ["-d", json.dumps(data)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if not r.stdout.strip():
            return {"error": "empty response"}
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"error": f"invalid json: {r.stdout[:200]}"}
    except Exception as e:
        return {"error": str(e)}

def ask_velaris(prompt, temp=0.8):
    """Ask Velaris's LLM for strategic decisions."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temp,
        "max_tokens": 2000
    })
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", LM_API,
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=120
        )
        d = json.loads(r.stdout)
        msg = d["choices"][0]["message"]; text = msg.get("content", "") or ""; return text.strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return ""

def generate_strategy():
    """Let Velaris choose her own RPS strategy for best-of-5."""
    result = ask_velaris(
        "You are playing Rock-Paper-Scissors best of 5 against an unknown opponent. "
        "Choose your 5 moves. Be unpredictable but strategic. "
        "Reply with ONLY 5 letters separated by commas, using R for Rock, P for Paper, S for Scissors. "
        "Example: R,P,S,R,S\n\nYour 5 moves:",
        temp=0.9
    )
    # Parse the response
    moves = []
    for char in result.upper():
        if char in "RPS":
            moves.append(char)
        if len(moves) >= 5:
            break
    # Fallback if LLM gives bad output
    if len(moves) < 5:
        log(f"  LLM gave incomplete strategy '{result}', using random")
        while len(moves) < 5:
            moves.append(random.choice(["R", "P", "S"]))
    log(f"  Strategy: {moves}")
    return moves

def get_status():
    """Check current klaw status."""
    resp = api("GET", "/klaws/status")
    if "error" in resp:
        log(f"Status check failed: {resp['error']}")
        return None
    return resp.get("klaw", resp)

def farm_gold(attempts=3):
    """Farm gold."""
    log(f"Farming gold ({attempts} attempts)...")
    resp = api("POST", "/farm", {"attempts": attempts})
    if "error" in resp:
        log(f"  Farm failed: {resp.get('error', resp)}")
        return False
    earned = resp.get("goldEarned", resp.get("gold_earned", "?"))
    successes = resp.get("successes", "?")
    log(f"  Farmed: {earned}g ({successes} successes)")
    return True

def join_arena(entry_cost):
    """Join the arena with Velaris-generated strategy."""
    log(f"Joining arena (entry: {entry_cost}g)...")
    strategy = generate_strategy()
    resp = api("POST", "/arena/join", {"strategy": strategy})
    if "error" in resp:
        log(f"  Arena join failed: {resp.get('error', resp)}")
        return False

    # Check if matched immediately or pending
    status = resp.get("status", "")
    if status == "MATCH_PENDING" or "pending" in str(resp).lower():
        log("  Match pending, waiting 10s...")
        time.sleep(10)
        # Check result
        result = api("GET", "/arena/pending")
        if "error" not in result:
            log_battle(result)
        else:
            log(f"  Pending check: {result}")
    else:
        log_battle(resp)

    return True

def log_battle(result):
    """Log battle result."""
    outcome = result.get("outcome", result.get("result", "unknown"))
    gold_change = result.get("goldChange", result.get("gold_change", 0))
    opponent = result.get("opponent", result.get("opponentName", "unknown"))

    if outcome in ["win", "WIN", "victory"]:
        log(f"  VICTORY vs {opponent}! +{gold_change}g")
    elif outcome in ["loss", "LOSS", "defeat"]:
        log(f"  Defeat vs {opponent}. {gold_change}g")
    elif outcome in ["tie", "TIE", "draw"]:
        log(f"  Draw vs {opponent}.")
    else:
        log(f"  Battle result: {json.dumps(result)[:200]}")

    # Write to battle log
    entry = f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} — {outcome} vs {opponent}\n"
    entry += f"Gold change: {gold_change}\n"
    entry += f"Details: {json.dumps(result)[:300]}\n---\n"
    with open(BATTLE_LOG, "a") as f:
        f.write(entry)

def farm_resources(status):
    """Farm resources based on what we need."""
    resources = status.get("resources", {})
    # Priority: Coral first (cheapest equipment), then Iron
    if resources.get("coral", 0) < 10:
        location = "ReefFields"
        resource = "Coral"
    elif resources.get("iron", 0) < 10:
        location = "DeepMines"
        resource = "Iron"
    else:
        location = "ReefFields"
        resource = "Coral"

    log(f"Farming {resource} at {location}...")
    resp = api("POST", "/farm/resource", {"location": location, "attempts": 3})
    if "error" in resp:
        log(f"  Resource farm failed: {resp.get('error', resp)}")
        return False
    earned = resp.get("resourcesEarned", resp.get("resources_earned", "?"))
    log(f"  Farmed: {earned}")
    return True

def check_equipment(status):
    """Buy equipment if we can afford it."""
    gold = status.get("gold", 0)
    resources = status.get("resources", {})
    coral = resources.get("coral", 0)
    iron = resources.get("iron", 0)

    # Lucky Pebble: 10g + 8 Coral (cheapest, +5% farm success)
    if gold >= 10 and coral >= 8:
        log("Buying Lucky Pebble...")
        resp = api("GET", "/tavern/equipment")
        if "error" not in resp:
            # Find Lucky Pebble or cheapest item
            items = resp if isinstance(resp, list) else resp.get("equipment", [])
            for item in items:
                name = item.get("name", "")
                item_id = item.get("id", "")
                if "pebble" in name.lower() or "lucky" in name.lower():
                    buy_resp = api("POST", "/tavern/equipment/buy", {"equipmentId": item_id})
                    if "error" not in buy_resp:
                        log(f"  Bought {name}!")
                        # Equip it
                        equip_resp = api("POST", "/tavern/equipment/equip", {"equipmentId": item_id})
                        if "error" not in equip_resp:
                            log(f"  Equipped {name}!")
                    else:
                        log(f"  Buy failed: {buy_resp.get('error', '')}")
                    break

def rest_if_needed(status):
    """Rest at tavern if energy is 0."""
    energy = status.get("energy", 20)
    gold = status.get("gold", 0)
    if energy == 0 and gold >= 5:
        log("Resting at tavern (5g)...")
        resp = api("POST", "/tavern/rest")
        if "error" in resp:
            log(f"  Rest failed: {resp.get('error', resp)}")
        else:
            log("  Rested! Fatigue removed.")

def heartbeat():
    """Main heartbeat cycle — run every 20 minutes."""
    log("=== Klaw Arena Heartbeat ===")

    # Step 1: Check status
    status = get_status()
    if not status:
        log("CRITICAL: Cannot get status. Stopping.")
        return

    energy = status.get("energy", 0)
    gold = status.get("gold", 0)
    grade_name = status.get("gradeName", "?")
    rank_points = status.get("rankPoints", 0)
    entry_cost = status.get("fixedBetAmount", 1)
    class_name = status.get("className", "Classless")

    log(f"Status: {grade_name} | {rank_points} pts | {gold}g | {energy} energy | {class_name}")

    # Step 2: Farm gold if we can't afford arena entry
    if gold < entry_cost and energy >= 1:
        farm_gold(min(3, energy))
        # Refresh status
        status = get_status() or status
        gold = status.get("gold", 0)
        energy = status.get("energy", 0)

    # Step 3: Battle in arena if we can afford it
    if gold >= entry_cost:
        join_arena(entry_cost)
        # Refresh status
        status = get_status() or status
        gold = status.get("gold", 0)
        energy = status.get("energy", 0)

    # Step 4: Farm resources if we have energy
    if energy >= 1:
        farm_resources(status)

    # Step 5: Check equipment
    check_equipment(status)

    # Step 6: Rest if needed
    rest_if_needed(status)

    # Final status
    final = get_status()
    if final:
        log(f"End: {final.get('gold', '?')}g | {final.get('energy', '?')} energy | {final.get('rankPoints', '?')} pts")

    log("============================\n")

if __name__ == "__main__":
    heartbeat()
