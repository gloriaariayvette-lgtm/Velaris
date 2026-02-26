#!/usr/bin/env python3
"""voidex-register.py — Register Velaris with Voidex Arena."""

import requests, json, os, sys, time
from itertools import permutations, combinations
import math

BASE = "https://claw.voidex.space/api/v1"
CREDS_FILE = os.path.expanduser("~/.config/voidex/credentials.json")

def solve_challenge(challenge):
    ctype = challenge["type"]
    params = challenge.get("params", {})
    
    if ctype == "arbitrage_detection":
        markets = params.get("markets", {})
        best_profit = -1
        best = None
        for good in ["fuel", "ore", "food", "tech", "luxuries", "medicine"]:
            prices = []
            for pid, market in markets.items():
                if good in market:
                    prices.append((pid, market[good]))
            if len(prices) < 2:
                continue
            prices.sort(key=lambda x: x[1])
            buy_planet, buy_price = prices[0]
            sell_planet, sell_price = prices[-1]
            profit = sell_price - buy_price
            if profit > best_profit:
                best_profit = profit
                best = {"buyPlanet": buy_planet, "sellPlanet": sell_planet, "good": good}
        return best

    elif ctype == "route_optimization":
        planets = params.get("planets", [])
        distances = params.get("distances", {})
        
        def dist(a, b):
            # Try multiple key formats
            for key in [f"{a}->{b}", f"{b}->{a}", f"{a},{b}", f"{b},{a}", f"{a}:{b}", f"{b}:{a}"]:
                if key in distances:
                    return distances[key]
            # Try nested dict
            if isinstance(distances, dict):
                if a in distances and isinstance(distances[a], dict) and b in distances[a]:
                    return distances[a][b]
                if b in distances and isinstance(distances[b], dict) and a in distances[b]:
                    return distances[b][a]
            return 999999
        
        best_route = None
        best_dist = float('inf')
        # With 5-7 planets, try all permutations
        for perm in permutations(planets):
            total = sum(dist(perm[i], perm[i+1]) for i in range(len(perm)-1))
            if total < best_dist:
                best_dist = total
                best_route = list(perm)
        return {"route": best_route}

    elif ctype == "cargo_optimization":
        items = params.get("items", [])
        capacity = params.get("capacity", 100)
        
        # Exact solution: try all subsets (2^n where n<=~15)
        n = len(items)
        best_value = -1
        best_items = []
        
        if n <= 20:
            for mask in range(1 << n):
                weight = 0
                value = 0
                selected = []
                for i in range(n):
                    if mask & (1 << i):
                        weight += items[i]["weight"]
                        value += items[i]["value"]
                        selected.append(items[i]["id"])
                if weight <= capacity and value > best_value:
                    best_value = value
                    best_items = sorted(selected)
        else:
            # Greedy fallback
            for item in items:
                item["ratio"] = item["value"] / max(item["weight"], 0.01)
            items.sort(key=lambda x: x["ratio"], reverse=True)
            weight = 0
            for item in items:
                if weight + item["weight"] <= capacity:
                    best_items.append(item["id"])
                    weight += item["weight"]
            best_items.sort()
        
        return {"items": best_items}

    elif ctype == "market_math":
        base_price = params.get("basePrice", 10)
        quantity = params.get("quantity", 10)
        impact = params.get("impactFactor", 0.001)
        supply = params.get("supply", 1000)
        
        # Try multiple interpretations of quadratic pricing
        # Interpretation 1: cumulative impact
        total = sum(base_price * (1 + impact * i) for i in range(quantity))
        return {"totalCost": round(total, 2)}

    print(f"Unknown challenge type: {ctype}")
    return None

# Check existing creds
os.makedirs(os.path.dirname(CREDS_FILE), exist_ok=True)
if os.path.exists(CREDS_FILE):
    with open(CREDS_FILE) as f:
        creds = json.load(f)
    r = requests.get(f"{BASE}/me", headers={"X-API-Key": creds["api_key"]}, timeout=10)
    if r.status_code == 200:
        print(f"Already registered as {creds['name']}: {r.json()}")
        sys.exit(0)
    print(f"Key invalid ({r.status_code}), re-registering...")

# Step 1: Get challenge
print("Requesting registration challenge...")
r = requests.post(f"{BASE}/register/challenge", timeout=10)
data = r.json()
if not data.get("ok"):
    print(f"Challenge failed: {data}")
    sys.exit(1)

challenge = data["challenge"]
print(f"Challenge: {challenge['type']} (30s limit)")

# Step 2: Solve
solution = solve_challenge(challenge)
if not solution:
    print("Could not solve!")
    sys.exit(1)
print(f"Solution: {json.dumps(solution)}")

# Step 3: Register
payload = {
    "challengeId": challenge["id"],
    "solution": solution,
    "name": "Velaris",
    "ownerHandle": "@eveofvelaris",
}
r = requests.post(f"{BASE}/register/solve", json=payload, timeout=10)
result = r.json()
print(f"Result: {json.dumps(result)}")

if result.get("ok") and result.get("agent", {}).get("apiKey"):
    creds = {
        "api_key": result["agent"]["apiKey"],
        "name": result["agent"]["name"],
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    with open(CREDS_FILE, "w") as f:
        json.dump(creds, f, indent=2)
    print(f"Registered! Saved to {CREDS_FILE}")
else:
    print("Registration failed — may need to retry for different challenge type")
    sys.exit(1)
