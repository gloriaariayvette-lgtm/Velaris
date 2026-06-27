import json, os
M = os.path.expanduser("~/.openclaw/workspace/memory")
try:
    ledger = json.load(open(M + "/interaction-ledger.json"))
    for e in ledger[-5:]:
        print("Gloria: " + e.get("gloria","")[:100] + " | Velaris: " + e.get("velaris","")[:100])
except:
    pass
