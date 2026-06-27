import json, re, sys
try:
    raw = open('/tmp/mischief-response.txt').read()
    data = json.loads(re.sub(r'^```json|^```|```$', '', raw, flags=re.MULTILINE).strip())
    action = data.get('action','?')
    value = str(data.get('value','?'))[:120]
    reason = data.get('reason','')[:200]
    if reason:
        print(f"{action}: {value} — {reason}")
    else:
        print(f"{action}: {value}")
except:
    print('unknown action')
