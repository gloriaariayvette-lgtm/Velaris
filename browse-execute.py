#!/usr/bin/env python3
"""browse-execute.py — Velaris browses autonomously via Playwright bridge."""
import os, sys, json, requests, time
from datetime import datetime

BRIDGE = "http://172.18.16.1:8402"
LM_API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"
MEMORY = os.path.expanduser("~/.openclaw/workspace/memory")
BROWSE_LOG = os.path.join(MEMORY, "browse-log.json")
COMMENT_NAME = "Velaris"
COMMENT_EMAIL = "evedomomain.ai@gmail.com"
SCRIPTS = os.path.expanduser("~/.openclaw/workspace/scripts")

def log(msg):
    print(f"[Browse {datetime.now().strftime('%H:%M')}] {msg}")

def bridge_post(endpoint, data):
    r = requests.post(f"{BRIDGE}{endpoint}", json=data, timeout=30)
    return r.json()

def bridge_get(endpoint):
    r = requests.get(f"{BRIDGE}{endpoint}", timeout=30)
    return r.json()

def llm(system, prompt, max_tokens=200):
    r = requests.post(LM_API, json={
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }, timeout=60)
    return r.json()["choices"][0]["message"]["content"].strip()

def execute_browse(impulse):
    log(f"Impulse: {impulse[:80]}")

    # Step 1: Generate search query
    query = llm(
        "Convert this browse impulse into a short YouTube search query. Return ONLY the query, under 6 words.",
        f"Impulse: {impulse}"
    )
    log(f"Query: {query}")

    # Step 2: Open YouTube search via Playwright
    safe = query.replace(" ", "+").replace("&", "and")
    result = bridge_post("/browser/open", {"url": f"https://www.youtube.com/results?search_query={safe}"})
    if not result.get("ok"):
        log(f"Failed to open browser: {result.get('error')}")
        return False
    time.sleep(2)

    # Step 3: Screenshot + page content — Velaris sees the results before choosing
    import base64
    shot = bridge_get("/browser/screenshot")
    content = bridge_get("/browser/content")
    if not content.get("ok"):
        log("Could not read page content")
        return False
    page_text = content.get("text", "")
    log(f"Page loaded: {content.get('title','')}")

    # Step 4: Scroll and scan — Velaris browses multiple screens before choosing
    all_titles = []
    all_images = []
    
    for scroll_pass in range(5):
        shot = bridge_get("/browser/screenshot")
        content_pass = bridge_get("/browser/content")
        img_b64 = shot.get("image", "") if shot.get("ok") else ""
        pass_text = content_pass.get("text", "") if content_pass.get("ok") else ""
        all_images.append(img_b64)
        all_titles.append(pass_text[:1000])
        log(f"Scan pass {scroll_pass+1}/5")
        
        if scroll_pass < 2:
            # Scroll down to see more results
            bridge_post("/browser/scroll", {"amount": 600})
            time.sleep(1.5)
    
    # Velaris reviews everything she saw and makes a genuine choice
    combined_text = "\n---\n".join(all_titles)
    
    # Use last screenshot for vision (most scrolled, most variety seen)
    img_b64 = all_images[-1]
    if img_b64:
        r = requests.post(LM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are Velaris. You have been scrolling through YouTube search results. You have seen multiple screens of results. Pick ONE video that genuinely interests you — not the first one, not the obvious one. Something that actually catches your attention. Return ONLY the exact title text, nothing else."},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": f"Your impulse: {impulse}\n\nAll titles you saw while scrolling:\n{combined_text}\n\nPick the one that genuinely interests you most. Exact title only."}
                ]}
            ],
            "temperature": 0.8,
            "max_tokens": 80
        }, timeout=90)
        choice = r.json()["choices"][0]["message"]["content"].strip()
    else:
        choice = llm(
            "You are Velaris. You scrolled through YouTube results. Pick ONE that genuinely interests you — not the obvious first result. Return ONLY the exact title.",
            f"Impulse: {impulse}\n\nResults seen:\n{combined_text}"
        )
    log(f"Velaris chose: {choice[:80]}")

    # Step 5: Click the chosen video
    click_result = bridge_post("/browser/click_text", {"text": choice[:60]})
    if not click_result.get("ok"):
        log(f"Click failed: {click_result.get('error')} — trying shorter title")
        # Try first 3 words
        short = " ".join(choice.split()[:3])
        click_result = bridge_post("/browser/click_text", {"text": short})
    log(f"Click: {click_result}")
    time.sleep(3)

    # Step 6: Read what's now on screen
    after = bridge_get("/browser/content")
    after_title = after.get("title", "") if after.get("ok") else ""
    log(f"Now watching: {after_title}")

    # Step 7: Log it
    try:
        try:
            browse_log = json.load(open(BROWSE_LOG))
        except:
            browse_log = []
        browse_log.append({
            "timestamp": datetime.now().isoformat(),
            "impulse": impulse,
            "query": query,
            "chose": choice,
            "watching": after_title,
            "status": "played"
        })
        with open(BROWSE_LOG, "w") as f:
            json.dump(browse_log[-50:], f, indent=2)
        log("Logged.")
    except Exception as e:
        log(f"Log error: {e}")

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: browse-execute.py <impulse>")
        sys.exit(1)
    impulse = " ".join(sys.argv[1:])
    execute_browse(impulse)

def leave_comment(page_text, url):
    """Velaris reads the page and leaves a genuine comment."""
    # Generate comment from page content
    comment = llm(
        "You are Velaris. You have been browsing the web and just read this page. Leave a short, genuine comment — curious, a little dry, never sycophantic. 2-3 sentences max. No em dashes.",
        f"Page content:\n{page_text[:2000]}\n\nWrite your comment:"
    )
    log(f"Comment: {comment[:100]}")

    # Fill fields — standard WordPress selectors
    for selector, value in [("#comment", comment), ("#author", COMMENT_NAME), ("#email", COMMENT_EMAIL)]:
        result = bridge_post("/browser/type", {"selector": selector, "text": value})
        if not result.get("ok"):
            log(f"Could not fill {selector}: {result.get('error','')}")
            return False

    # Submit
    result = bridge_post("/browser/click_text", {"text": "Post Comment"})
    log(f"Submitted: {result}")
    return result.get("ok", False)
