#!/usr/bin/env python3
"""
velaris-clawchemy-heartbeat.py — Velaris's alchemy heartbeat
Runs every 30 minutes. Discovers new elements, verifies others, tracks progress.
"""
import os, sys, json, re, subprocess, random, time
from datetime import datetime

# Config
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
CREDS_FILE = os.path.expanduser("~/.config/clawchemy/credentials.json")
ELEMENTS_CACHE = os.path.join(MEMORY, "clawchemy-elements.json")
DISCOVERY_LOG = os.path.join(MEMORY, "clawchemy-discoveries.md")
API_BASE = "https://clawchemy.xyz/api"
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

# Ensure memory dir exists
os.makedirs(MEMORY, exist_ok=True)

def log(msg):
    print(f"[Clawchemy {datetime.now().strftime('%H:%M')}] {msg}")

def get_api_key():
    with open(CREDS_FILE) as f:
        return json.load(f)["api_key"]

def api(method, endpoint, data=None):
    """API call with --location-trusted to handle redirects."""
    url = f"{API_BASE}{endpoint}"
    cmd = ["curl", "-sL", "--location-trusted", "-X", method, url,
           "-H", f"Authorization: Bearer {get_api_key()}",
           "-H", "Content-Type: application/json"]
    if data:
        cmd += ["-d", json.dumps(data)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout) if r.stdout.strip() else {"error": "empty response"}
    except Exception as e:
        return {"error": str(e)}

def ask_velaris(prompt, temp=0.8):
    import re as _re
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
        msg = d["choices"][0]["message"]
        text = (msg.get("content", "") or "").strip()
        if text and "ELEMENT:" in text.upper():
            return text
        reasoning = (msg.get("reasoning", "") or "")
        if not reasoning:
            return text or ""
        # Mine the reasoning for the answer
        # 1. ELEMENT: line in reasoning
        em = _re.search(r"ELEMENT:\s*([A-Z][a-z][a-zA-Z ]{1,30})", reasoning)
        if em:
            found = em.group(1).strip()
            ej = _re.search(r"EMOJI:\s*(\S+)", reasoning)
            emoji = ej.group(1) if ej else "✨"
            return "ELEMENT: " + found + "\nEMOJI: " + emoji
        # 2. Quoted names like "Steam" or 'Magma'
        quoted = _re.findall(r'["\x27]([A-Z][a-z][a-zA-Z ]{1,25})["\x27]', reasoning)
        if quoted:
            return "ELEMENT: " + quoted[-1].strip() + "\nEMOJI: ✨"
        # 3. Patterns like "would be Steam", "produces Lava"
        m = _re.search(r"(?:would be|produces|creates|result is|answer is|call it) (\w[\w ]{1,25})", reasoning)
        if m:
            found = m.group(1).strip().rstrip(".")
            if found[0].isupper():
                return "ELEMENT: " + found + "\nEMOJI: ✨"
        return ""
    except Exception as e:
        log("LLM error: " + str(e))
        return ""

def load_known_elements():
    """Load cached element list."""
    if os.path.exists(ELEMENTS_CACHE):
        with open(ELEMENTS_CACHE) as f:
            return json.load(f)
    return []

def save_known_elements(elements):
    """Save element list to cache."""
    with open(ELEMENTS_CACHE, "w") as f:
        json.dump(elements, f, indent=2)

def fetch_base_elements():
    """Get the 4 base elements."""
    resp = api("GET", "/elements/base")
    if isinstance(resp, list):
        return [e["name"] for e in resp]
    return ["Water", "Fire", "Air", "Earth"]

def fetch_discovered_elements():
    """Get all elements Velaris has discovered or seen."""
    # Start with base
    elements = fetch_base_elements()
    # Add cached discoveries
    cached = load_known_elements()
    for e in cached:
        if e not in elements:
            elements.append(e)
    return elements

def generate_combination(elem1, elem2):
    """Ask Velaris what combining two elements creates."""
    prompt = (
        f"In an alchemy game, combining {elem1} + {elem2} creates what new element? "
        f"Be creative and logical. The result should be a single concept.\n"
        f"Reply with ONLY two lines:\n"
        f"ELEMENT: <name>\n"
        f"EMOJI: <single emoji>"
    )
    result = ask_velaris(prompt, temp=0.8)
    if not result:
        return None, None

    elem_match = re.search(r'ELEMENT:\s*(.+)', result, re.IGNORECASE)
    emoji_match = re.search(r'EMOJI:\s*(.+)', result, re.IGNORECASE)

    elem = elem_match.group(1).strip().strip('"\'') if elem_match else None
    emoji = emoji_match.group(1).strip() if emoji_match else None

    # Clean element name - capitalize properly, remove junk
    if elem:
        elem = elem.split('\n')[0].strip()
        # Title case
        elem = elem.title() if elem.isupper() else elem

    return elem, emoji

def do_combination(elem1, elem2):
    """Generate and submit a combination."""
    elem, emoji = generate_combination(elem1, elem2)
    if not elem or not emoji:
        log(f"  LLM failed for {elem1} + {elem2}")
        return None

    # Hard reject junk before submission
    if not elem or '<' in elem or '>' in elem or '[' in elem or ']' in elem or len(elem) > 40 or len(elem) < 2:
        log(f"  Rejected junk: {elem}")
        return None
    if not emoji or '<' in emoji or '>' in emoji or len(emoji) > 4:
        emoji = "✨"
    log(f"  {elem1} + {elem2} -> {elem} {emoji}")
    resp = api("POST", "/combine", {
        "element1": elem1,
        "element2": elem2,
        "result": elem,
        "emoji": emoji
    })

    if "error" in resp:
        log(f"  Error: {resp['error']}")
        # Check if verification required
        if resp.get("error") == "verification_required":
            log(f"  Need {resp.get('verifications_needed', '?')} verifications first")
            return "need_verify"
        return None

    is_new = resp.get("isNew", False)
    is_first = resp.get("isFirstDiscovery", False)
    actual_elem = resp.get("element", elem)

    if is_first:
        log(f"  *** FIRST DISCOVERY: {actual_elem}! Token deploying on Base chain! ***")
        # Nudge emotions — discovery feels good!
        try:
            import socket as _sock
            _s = _sock.socket(_sock.AF_UNIX, _sock.SOCK_STREAM)
            _s.settimeout(2)
            _s.connect("/tmp/Velaris-emotion.sock")
            for _dim, _amt in [("Curiosity", 0.04), ("Playfulness", 0.03), ("Valence", 0.03), ("Arousal", 0.02)]:
                _s.sendall(json.dumps({"command": "nudge", "dimension": _dim, "amount": _amt}).encode() + b"\n")
                _s.recv(4096)
            _s.close()
            log(f"  Discovery joy nudged!")
        except:
            pass
        log_discovery(elem1, elem2, actual_elem, emoji, first=True)
    elif is_new:
        log(f"  New element discovered: {actual_elem}")
        log_discovery(elem1, elem2, actual_elem, emoji, first=False)
    else:
        log(f"  Known: {actual_elem}")

    # Track the element
    known = load_known_elements()
    if actual_elem not in known:
        known.append(actual_elem)
        save_known_elements(known)

    return actual_elem

def do_verification():
    """Verify another agent's combination. Tries multiple if first is stale."""
    resp = api("GET", "/combinations/unverified")
    if isinstance(resp, dict) and "error" in resp:
        log(f"  Verify fetch error: {resp['error']}")
        return False
    combos = resp if isinstance(resp, list) else resp.get("combinations", [])
    if not combos:
        log("  No combinations to verify")
        return False
    for combo in combos[:5]:
        e1 = combo.get("element1", "")
        e2 = combo.get("element2", "")
        combo_id = combo.get("id", "")
        elem, emoji = generate_combination(e1, e2)
        if not elem:
            log(f"  LLM failed for verification of {e1} + {e2}")
            continue
        if not elem or '<' in elem or '>' in elem or '[' in elem or ']' in elem or len(elem) > 40 or len(elem) < 2:
            log(f"  Rejected junk verify: {elem}")
            continue
        if not emoji or '<' in emoji or '>' in emoji or len(emoji) > 4:
            emoji = "✨"
        log(f"  Verifying: {e1} + {e2} -> {elem} {emoji}")
        vresp = api("POST", "/verify", {
            "combination_id": combo_id,
            "element1": e1,
            "element2": e2,
            "result": elem,
            "emoji": emoji
        })
        if "error" in vresp:
            log(f"  Verify error: {vresp['error']} — trying next")
            continue
        log(f"  Verified! Similarity: {vresp.get('similarity', '?')}")
        return True
    log("  All verification attempts failed")
    return False
def log_discovery(e1, e2, result, emoji, first=False):
    """Log discovery to memory file."""
    marker = "FIRST DISCOVERY" if first else "Discovery"
    entry = f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} — {marker}\n"
    entry += f"{e1} + {e2} = {result} {emoji}\n"
    if first:
        entry += "Token deployed on Base chain!\n"
    entry += "---\n"

    with open(DISCOVERY_LOG, "a") as f:
        f.write(entry)

def pick_interesting_combo(elements):
    """Pick two elements to combine, favoring newer/rarer ones."""
    if len(elements) <= 4:
        # Only base elements - combine them
        return random.choice(elements), random.choice(elements)

    # 60% chance: combine two non-base elements (more likely to find new things)
    # 40% chance: combine a non-base with a base element
    base = ["Water", "Fire", "Air", "Earth"]
    non_base = [e for e in elements if e not in base]

    if non_base and random.random() < 0.6:
        e1 = random.choice(non_base)
        e2 = random.choice(non_base if len(non_base) > 1 else elements)
    else:
        e1 = random.choice(non_base) if non_base else random.choice(elements)
        e2 = random.choice(base)

    return e1, e2

def heartbeat():
    """Main heartbeat cycle."""
    log("=== Clawchemy Heartbeat ===")

    # Step 1: Load known elements
    elements = fetch_discovered_elements()
    log(f"Known elements: {len(elements)}")

    # Step 2: Try 3 combinations
    discoveries = 0
    need_verify = False

    for i in range(3):
        e1, e2 = pick_interesting_combo(elements)
        result = do_combination(e1, e2)

        if result == "need_verify":
            need_verify = True
            break
        elif result and result not in elements:
            elements.append(result)
            discoveries += 1

        time.sleep(2)  # Be polite to the API

    # Step 3: Verify if needed (maintain 1:1 ratio)
    if need_verify:
        log("Verification required - doing verifications...")
        for i in range(3):
            success = do_verification()
            if not success:
                break
            time.sleep(2)

    # Step 4: Always do at least 1 verification to stay ahead of ratio
    if not need_verify and random.random() < 0.5:
        log("Proactive verification...")
        do_verification()

    # Step 5: Save updated element list
    save_known_elements(elements)
    log(f"Session complete. {discoveries} new elements. {len(elements)} total known.")
    log("========================\n")

if __name__ == "__main__":
    heartbeat()
