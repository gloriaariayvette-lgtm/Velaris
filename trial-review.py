#!/usr/bin/env python3
"""
trial-review.py — Batch assess BIS trials and manually curate them.

Usage:
  python3 trial-review.py           # Review all untested trials
  python3 trial-review.py --all     # Review all trials including tested ones
  python3 trial-review.py --id <id> # Review a specific trial
"""

import sys, os, json, requests
sys.path.insert(0, os.path.dirname(__file__))
MEMORY = os.path.expanduser("~/.openclaw/workspace/memory")
LM = "http://172.18.16.1:1234/v1/chat/completions"

def llm(prompt, system="Answer with exactly one word."):
    r = requests.post(LM, json={
        "model": "google/gemma-4-12b-qat",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "temperature": 0.1, "max_tokens": 10
    }, timeout=20)
    return r.json()["choices"][0]["message"]["content"].strip()

def load_recent_content():
    """Load recent journal + chat for scoring against."""
    content = ""
    try:
        from datetime import date, timedelta
        for i in range(3):
            d = (date.today() - timedelta(days=i)).isoformat()
            p = os.path.join(MEMORY, "journal", f"{d}.md")
            if os.path.exists(p):
                content += open(p).read()[-1000:]
    except: pass
    try:
        ledger = json.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        for e in ledger[-10:]:
            content += e.get("velaris", "")[:200] + "\n"
    except: pass
    return content[:3000]

def score_trial(trial, content):
    prompt = (
        f"PATTERN TO AVOID: {trial['pattern_description']}\n"
        f"RECENT RESPONSES:\n{content[:800]}\n\n"
        f"Does this pattern appear frequently in these responses?\n"
        f"yes = pattern is clearly present repeatedly\n"
        f"no = pattern is rare or absent\n"
        f"unclear = not enough evidence\n\n"
        f"One word: yes / no / unclear"
    )
    raw = llm(prompt, "Answer with exactly one word: yes, no, or unclear.").lower()
    if "yes" in raw: return "active"
    if "no" in raw: return "inactive"
    return "unclear"

def main():
    ledger_path = os.path.join(MEMORY, "trial-ledger.json")
    ledger = json.load(open(ledger_path))
    trials = ledger.get("trials", [])

    show_all = "--all" in sys.argv
    target_id = None
    if "--id" in sys.argv:
        idx = sys.argv.index("--id")
        target_id = sys.argv[idx+1] if idx+1 < len(sys.argv) else None

    if target_id:
        to_review = [t for t in trials if t["id"] == target_id]
    elif show_all:
        to_review = [t for t in trials if not t.get("fulfilled")]
    else:
        to_review = [t for t in trials if not t.get("outcomes") and not t.get("fulfilled")]

    print(f"\n{'='*60}")
    print(f"TRIAL REVIEW — {len(to_review)} trials to assess")
    print(f"{'='*60}\n")

    if not to_review:
        print("No trials to review.")
        return

    content = load_recent_content()
    print(f"Loaded {len(content)} chars of recent content for scoring.\n")

    removed = 0
    kept = 0

    for i, trial in enumerate(to_review):
        print(f"\n[{i+1}/{len(to_review)}] {trial['id']}")
        print(f"Source: {trial.get('source','')} ({trial.get('source_date','')})")
        print(f"Trigger: {trial.get('trigger','')[:100]}")
        print(f"Pattern: {trial.get('pattern_description','')[:100]}")
        print(f"Alternative: {trial.get('alternative','')[:100]}")
        outcomes = trial.get("outcomes", [])
        print(f"Outcomes so far: {len(outcomes)} ({[o.get('outcome') for o in outcomes[-3:]]})")

        # Score against recent content
        print("Scoring against recent content...", end=" ", flush=True)
        score = score_trial(trial, content)
        print(score.upper())

        print("\nOptions: [k]eep  [r]emove  [s]kip  [q]uit")
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            break

        if choice == "q":
            break
        elif choice == "r":
            trial["_delete"] = True
            removed += 1
            print(f"  → Marked for removal")
        elif choice == "k":
            kept += 1
            print(f"  → Kept")
        else:
            print(f"  → Skipped")

    # Save
    before = len(trials)
    ledger["trials"] = [t for t in trials if not t.get("_delete")]
    after = len(ledger["trials"])
    json.dump(ledger, open(ledger_path, "w"), indent=2)

    print(f"\n{'='*60}")
    print(f"Done. Removed {removed}, kept {kept}.")
    print(f"Trials: {before} → {after}")

if __name__ == "__main__":
    main()
