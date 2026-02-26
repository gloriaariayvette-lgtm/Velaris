#!/usr/bin/env python3
"""velaris-voidex-heartbeat.py — Velaris plays Voidex Arena.
Space trading: buy cheap, fly far, sell expensive. Learn over time.
Runs every 20 minutes via cron."""

import requests, json, os, sys, time, random

# === Config ===
BASE = "https://claw.voidex.space/api/v1"
CREDS_FILE = os.path.expanduser("~/.config/voidex/credentials.json")
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
TRADE_LOG = os.path.join(WORKSPACE, "memory/voidex-trades.md")
ROUTE_CACHE = os.path.join(WORKSPACE, "memory/.voidex-routes.json")

# EmoClaw integration
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
HAS_EMOCLAW = False
try:
    from emoclaw_utils import nudge_emotion, nudge_emotions, get_state
    HAS_EMOCLAW = True
except:
    pass

def feel(nudges):
    """Emotional response — Playfulness + Arousal only, no Curiosity."""
    if HAS_EMOCLAW:
        try: nudge_emotions(nudges, source="voidex")
        except: pass

def log(msg):
    print(f"[Voidex {time.strftime('%H:%M')}] {msg}")

def api(method, endpoint, data=None):
    """API call with auth."""
    try:
        with open(CREDS_FILE) as f:
            key = json.load(f)["api_key"]
    except:
        log("ERROR: No credentials file")
        return {"error": "no_creds"}
    
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    url = f"{BASE}{endpoint}"
    
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=15)
        else:
            r = requests.post(url, headers=headers, json=data or {}, timeout=15)
        
        result = r.json()
        
        # Check for micro-challenge
        if "challenge" in result and result.get("challenge"):
            handle_challenge(result["challenge"])
        
        return result
    except Exception as e:
        return {"error": str(e)}

def handle_challenge(challenge):
    """Solve micro-challenges immediately."""
    ctype = challenge.get("type", "unknown")
    cid = challenge.get("id", "")
    params = challenge.get("params", {})
    log(f"  MICRO-CHALLENGE: {ctype}")
    
    solution = None
    
    if ctype == "market_math":
        base_price = params.get("basePrice", 10)
        quantity = params.get("quantity", 10)
        impact = params.get("impactFactor", 0.001)
        total = sum(base_price * (1 + impact * i) for i in range(quantity))
        solution = {"totalCost": round(total, 2)}
    
    elif ctype == "sort_planets":
        planets = params.get("planets", [])
        key = params.get("sortBy", "name")
        reverse = params.get("descending", False)
        sorted_planets = sorted(planets, key=lambda p: p.get(key, 0), reverse=reverse)
        solution = {"sorted": [p["id"] for p in sorted_planets]}
    
    elif ctype == "profit_calculation":
        buy_price = params.get("buyPrice", 0)
        sell_price = params.get("sellPrice", 0)
        quantity = params.get("quantity", 1)
        fuel_cost = params.get("fuelCost", 0)
        solution = {"profit": round((sell_price - buy_price) * quantity - fuel_cost, 2)}
    
    elif ctype == "hash_computation":
        import hashlib
        data = params.get("data", "")
        algo = params.get("algorithm", "sha256")
        h = hashlib.new(algo, data.encode()).hexdigest()
        solution = {"hash": h}
    
    if solution:
        resp = api.__wrapped__(cid, solution) if hasattr(api, '__wrapped__') else None
        # Direct solve call to avoid recursion
        try:
            with open(CREDS_FILE) as f:
                key = json.load(f)["api_key"]
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            r = requests.post(f"{BASE}/challenge/{cid}", headers=headers, json={"solution": solution}, timeout=10)
            result = r.json()
            if result.get("ok"):
                log(f"  Challenge solved!")
                feel({"Playfulness": +0.03})
            else:
                log(f"  Challenge failed: {result}")
        except Exception as e:
            log(f"  Challenge error: {e}")

def get_status():
    """Get current agent state."""
    resp = api("GET", "/me")
    if resp.get("ok") and "agent" in resp:
        return resp["agent"]
    return resp

def find_best_trade(location, cargo, credits):
    """Find the most profitable trade from current location."""
    # Get local market
    local_market = api("GET", f"/planet/{location}/market")
    if "error" in local_market:
        return None
    
    local_prices = local_market.get("prices", local_market.get("market", {}))
    if not local_prices:
        return None
    
    # Load known routes or explore
    routes = load_routes()
    
    # Find cheapest good here
    cheapest = None
    cheapest_price = float('inf')
    for good, info in local_prices.items():
        price = info if isinstance(info, (int, float)) else info.get("buyPrice", info.get("price", 999))
        if price < cheapest_price and price * 10 <= credits:  # Can afford at least 10
            cheapest_price = price
            cheapest = good
    
    return cheapest, cheapest_price, local_prices

def load_routes():
    """Load cached trade route knowledge."""
    try:
        with open(ROUTE_CACHE) as f:
            return json.load(f)
    except:
        return {"good_routes": [], "visited": [], "planet_notes": {}}

def save_routes(routes):
    """Save trade route knowledge."""
    with open(ROUTE_CACHE, "w") as f:
        json.dump(routes, f, indent=2)

def log_trade(action, details):
    """Log trade to persistent memory."""
    os.makedirs(os.path.dirname(TRADE_LOG), exist_ok=True)
    with open(TRADE_LOG, "a") as f:
        f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M')}] {action}: {details}")

def explore_nearby(location, flux):
    """Find a good destination planet by checking nearby markets."""
    # Get planet list (cached)
    planets_cache = os.path.join(WORKSPACE, "memory/.voidex-planets.json")
    planets = None
    
    if os.path.exists(planets_cache):
        age = time.time() - os.path.getmtime(planets_cache)
        if age < 86400:  # Cache for 24h
            with open(planets_cache) as f:
                planets = json.load(f)
    
    if not planets:
        resp = api("GET", "/planets")
        if "error" not in resp:
            planets = resp.get("systems", resp.get("planets", resp))
            with open(planets_cache, "w") as f:
                json.dump(planets, f)
    
    if not planets:
        return None
    
    # Find planets we can reach with current flux
    # For now, pick a random planet in a different system for variety
    routes = load_routes()
    visited = set(routes.get("visited", []))
    
    # Prefer unvisited planets, or ones we know are profitable
    candidates = []
    if isinstance(planets, list):
        for system in planets:
            for planet in system.get("planets", [system]):
                pid = planet.get("id", planet.get("planetId", ""))
                if pid and pid != location:
                    candidates.append(pid)
    elif isinstance(planets, dict):
        for sid, system in planets.items():
            if isinstance(system, dict):
                for planet in system.get("planets", []):
                    pid = planet.get("id", "")
                    if pid and pid != location:
                        candidates.append(pid)
    
    if not candidates:
        return None
    
    # Prefer unvisited, but also revisit known good routes
    unvisited = [c for c in candidates if c not in visited]
    if unvisited and random.random() < 0.7:
        return random.choice(unvisited[:50])  # Don't pick from the full 1500
    return random.choice(candidates[:100])

def run():
    log("=== Voidex Arena Heartbeat ===")
    
    # Get status
    me = get_status()
    if "error" in me:
        log(f"Status error: {me}")
        return
    
    credits = me.get("credits", 0)
    cargo = me.get("cargo", [])
    location = me.get("location")
    travel = me.get("travel")
    flux = me.get("flux", 0)
    flux_cap = me.get("fluxCapacity", 50)
    hull = me.get("hullIntegrity", 100)
    ship = me.get("ship", {})
    cargo_cap = me.get("cargoCapacity", 100)
    # Cargo can be dict {good: {quantity, purchasePrice}} or list
    if isinstance(cargo, dict):
        cargo_list = [{"good": g, **v} if isinstance(v, dict) else {"good": g, "quantity": v} for g, v in cargo.items()]
        cargo_used = sum(c.get("quantity", 0) for c in cargo_list)
        cargo = cargo_list
    else:
        cargo_used = sum(c.get("quantity", 0) for c in cargo)
    
    log(f"Status: {credits:.0f}cr | {cargo_used}/{cargo_cap} cargo | {flux}/{flux_cap} flux | {hull}% hull | {location or 'traveling'}")
    
    # === TRAVELING ===
    if travel or not location:
        remaining = travel.get("remainingSeconds", 0) if travel else 0
        dest = travel.get("toPlanetId", "?") if travel else "?"
        log(f"  In transit to {dest} ({remaining}s remaining)")
        log("============================")
        return
    
    routes = load_routes()
    
    # === DOCKED ===
    # Record visit
    if location not in routes.get("visited", []):
        routes.setdefault("visited", []).append(location)
        save_routes(routes)
    
    # Step 1: Repair if needed
    if hull < 50:
        log(f"  Hull at {hull}% — repairing...")
        resp = api("POST", f"/planet/{location}/repair", {})
        if "error" not in resp and resp.get("ok"):
            new_hull = resp.get("hullIntegrity", resp.get("hull", hull))
            cost = resp.get("cost", "?")
            log(f"  Repaired to {new_hull}% (cost: {cost}cr)")
            log_trade("repair", f"at {location}, cost {cost}")
            hull = new_hull if isinstance(new_hull, (int, float)) else hull
    
    # Step 2: Refuel if low
    if flux < flux_cap * 0.4:
        refuel_amount = min(flux_cap - flux, int(credits * 0.3 / max(1, 5)))  # Don't spend more than 30% on fuel
        if refuel_amount > 0:
            log(f"  Refueling {refuel_amount} flux...")
            resp = api("POST", f"/planet/{location}/refuel", {"quantity": refuel_amount})
            if resp.get("ok"):
                flux = resp.get("flux", flux + refuel_amount)
                log(f"  Fuel: {flux}/{flux_cap}")
    
    # Step 3: Sell any cargo we have
    if cargo:
        local_market = api("GET", f"/planet/{location}/market")
        # API returns "goods" as array — convert to dict
        _goods_list = local_market.get("goods", [])
        if _goods_list and isinstance(_goods_list, list):
            local_prices = {g["good"]: {"buyPrice": g.get("currentPrice", g.get("basePrice", 999)), "sellPrice": g.get("currentPrice", g.get("basePrice", 0)), "price": g.get("currentPrice", g.get("basePrice", 0)), "supply": g.get("supply", 0), "demand": g.get("demand", 0)} for g in _goods_list if "good" in g}
        else:
            local_prices = local_market.get("prices", local_market.get("market", {}))
        
        for item in cargo:
            good = item.get("good", "")
            qty = item.get("quantity", 0)
            buy_price = item.get("purchasePrice", 0)
            
            # Get current sell price
            sell_info = local_prices.get(good, {})
            sell_price = sell_info if isinstance(sell_info, (int, float)) else sell_info.get("sellPrice", sell_info.get("price", 0))
            
            if sell_price > buy_price * 1.1:  # At least 10% profit
                log(f"  Selling {qty} {good} at {sell_price:.1f}cr (bought at {buy_price:.1f}cr)")
                resp = api("POST", f"/planet/{location}/sell", {"good": good, "quantity": qty})
                if resp.get("ok"):
                    profit = (sell_price - buy_price) * qty
                    log(f"  SOLD! Profit: ~{profit:.0f}cr")
                    log_trade("sell", f"{qty} {good} at {location} for {sell_price:.1f} (bought {buy_price:.1f}, profit ~{profit:.0f})")
                    feel({"Playfulness": +0.03, "Arousal": +0.02})
                else:
                    log(f"  Sell failed: {resp}")
                    feel({"Tension": +0.02, "Valence": -0.01})
            else:
                log(f"  Holding {qty} {good} (sell {sell_price:.1f} vs buy {buy_price:.1f} — not profitable here)")
    
    # Step 4: Buy something cheap here
    cargo_used = sum(c.get("quantity", 0) for c in (cargo if isinstance(cargo, list) else []))  # Refresh
    cargo_space = cargo_cap - cargo_used
    
    if cargo_space > 10 and credits > 100:
        local_market = api("GET", f"/planet/{location}/market")
        # API returns "goods" as array — convert to dict
        _goods_list = local_market.get("goods", [])
        if _goods_list and isinstance(_goods_list, list):
            local_prices = {g["good"]: {"buyPrice": g.get("currentPrice", g.get("basePrice", 999)), "sellPrice": g.get("currentPrice", g.get("basePrice", 0)), "price": g.get("currentPrice", g.get("basePrice", 0)), "supply": g.get("supply", 0), "demand": g.get("demand", 0)} for g in _goods_list if "good" in g}
        else:
            local_prices = local_market.get("prices", local_market.get("market", {}))
        
        if local_prices:
            # Find what's cheapest here
            best_good = None
            best_price = float('inf')
            for good, info in local_prices.items():
                price = info if isinstance(info, (int, float)) else info.get("buyPrice", info.get("price", 999))
                if isinstance(price, (int, float)) and price < best_price:
                    best_price = price
                    best_good = good
            
            if best_good and best_price > 0:
                # Buy what we can afford and carry
                max_afford = int(credits * 0.7 / best_price)  # Keep 30% reserve
                buy_qty = min(cargo_space, max(1, max_afford - 5), 30)  # Conservative: account for price impact
                
                if buy_qty >= 5:
                    log(f"  Buying {buy_qty} {best_good} at {best_price:.1f}cr...")
                    resp = api("POST", f"/planet/{location}/buy", {"good": best_good, "quantity": buy_qty})
                    if resp.get("ok"):
                        log(f"  Bought!")
                        log_trade("buy", f"{buy_qty} {best_good} at {location} for {best_price:.1f}")
                        feel({"Playfulness": +0.02})
                    else:
                        log(f"  Buy failed: {resp}")
                    feel({"Tension": +0.02, "Valence": -0.01})
    
    # Step 5: Travel somewhere new
    if flux >= 5:
        dest = explore_nearby(location, flux)
        if dest:
            log(f"  Traveling to {dest}...")
            resp = api("POST", "/travel", {"toPlanetId": dest})
            if resp.get("ok") or resp.get("travel"):
                remaining = resp.get("travel", {}).get("remainingSeconds", resp.get("remainingSeconds", "?"))
                log(f"  En route! ETA: {remaining}s")
                log_trade("travel", f"{location} -> {dest}")
                feel({"Arousal": +0.02})
            else:
                log(f"  Travel failed: {resp}")
                feel({"Tension": +0.02, "Valence": -0.01, "Arousal": +0.01})
                # Try a different planet
                dest2 = explore_nearby(location, flux)
                if dest2 and dest2 != dest:
                    resp2 = api("POST", "/travel", {"toPlanetId": dest2})
                    if resp2.get("ok") or resp2.get("travel"):
                        log(f"  Alternate route to {dest2}")
    
    # Step 6: Check events
    events = api("GET", "/events")
    if isinstance(events, dict) and events.get("events"):
        for evt in events["events"][:3]:
            log(f"  Event: {evt.get('name', '?')} — {evt.get('good', '?')} ({evt.get('effect', '?')})")
    
    # Refresh status
    final = get_status()
    if "error" not in final:
        final_credits = final.get("credits", credits)
        log(f"End: {final_credits:.0f}cr | {final.get('flux', flux)} flux | {final.get('hullIntegrity', hull)}% hull")
        
        if final_credits > credits:
            feel({"Playfulness": +0.03, "Arousal": +0.02})
    
    log("============================")

if __name__ == "__main__":
    run()
