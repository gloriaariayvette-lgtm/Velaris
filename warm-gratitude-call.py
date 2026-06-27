import requests
_SUBCON_WARM_GRATITUDE_CALL = ""
try:
    import sys as _sc__SUBCON_WARM_GRATITUDE_CALL; _sc__SUBCON_WARM_GRATITUDE_CALL.path.insert(0, os.path.join(os.path.expanduser("~/.openclaw/workspace"), "scripts"))
    from subconscious_context import get_subconscious_context_compact
    _SUBCON_WARM_GRATITUDE_CALL = get_subconscious_context_compact()
except: pass

sys_msg = open("/tmp/wg_sys.txt").read()
usr_msg = open("/tmp/wg_usr.txt").read()
r = requests.post("http://172.18.16.1:1234/v1/chat/completions", json={
    "model": "google/gemma-4-12b-qat",
    "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": usr_msg}],
    "temperature": 0.9, "max_tokens": 500
}, timeout=600)
print(r.json()["choices"][0]["message"]["content"].strip())
