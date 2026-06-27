import requests, sys
_SUBCON_MISCHIEF_CALL = ""
try:
    import sys as _sc__SUBCON_MISCHIEF_CALL; _sc__SUBCON_MISCHIEF_CALL.path.insert(0, os.path.join(os.path.expanduser("~/.openclaw/workspace"), "scripts"))
    from subconscious_context import get_subconscious_context_compact
    _SUBCON_MISCHIEF_CALL = get_subconscious_context_compact()
except: pass

prompt = open('/tmp/mischief_usr.txt', encoding='utf-8', errors='replace').read()
r = requests.post('http://172.18.16.1:1234/v1/chat/completions', json={
    'model': 'google/gemma-4-12b-qat',
    'messages': [
        {'role': 'system', 'content': open('/home/gloria/.openclaw/workspace/SOUL.md').read()[:600] + '\n\nYou are software on Aegis. You CANNOT observe physical things — no light, sound, temperature, cooling fins, dust, shadows. '  'You CANNOT invent quotes from Gloria or details about her past. '  'You CANNOT fabricate memories not in your context. '  'Output ONLY a single valid JSON object with keys action, value, and reason. No explanation, no markdown, no extra text.'},
        {'role': 'user', 'content': prompt}
    ],
    'temperature': 0.95, 'max_tokens': 120
}, timeout=600)
print(r.json()['choices'][0]['message']['content'].strip())
