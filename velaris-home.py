#!/usr/bin/env python3
"""
velaris-home.py — Velaris controls Gloria's home through Home Assistant.
Bridge between Velaris server / cron scripts and HA REST API.

Usage:
  python3 velaris-home.py speak "Hello Gloria"
  python3 velaris-home.py announce "I found something interesting"
  python3 velaris-home.py color "#4a5568"    (when bulbs are added)
"""
import sys, json, os, requests

CONFIG_FILE = os.path.expanduser("~/.openclaw/workspace/memory/homeassistant-config.json")

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def ha_request(endpoint, payload):
    cfg = load_config()
    r = requests.post(
        f"{cfg['url']}/api/services/{endpoint}",
        headers={
            "Authorization": f"Bearer {cfg['token']}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=10
    )
    return r.status_code, r.text

def speak(message):
    """Velaris speaks through the Echo (direct TTS, no chime)."""
    cfg = load_config()
    code, resp = ha_request("notify/send_message", {
        "entity_id": cfg["entities"]["echo_speak"],
        "message": message
    })
    print(f"[HOME] speak: {code}")
    return code == 200

def announce(message, volume=2):
    """Velaris announces through the Echo (with Alexa chime)."""
    cfg = load_config()
    # Set volume before announcing
    ha_request("media_player/volume_set", {
        "entity_id": cfg["entities"].get("echo_media", cfg["entities"]["echo_announce"]),
        "volume_level": volume / 10
    })
    code, resp = ha_request("notify/send_message", {
        "entity_id": cfg["entities"]["echo_announce"],
        "message": message
    })
    print(f"[HOME] announce: {code}")
    return code == 200



def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    h = hex_color.lstrip("#")
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]

def saturate_for_bulbs(rgb):
    """Gently nudge color so smart bulbs show a visible tint
    without losing the muted, dreamy quality Gloria prefers.
    Just enough saturation that white bulbs don't flatten the color."""
    import colorsys
    r, g, b = [x / 255.0 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    # Gentle nudge — minimum 0.25 saturation, mild scale
    s = max(0.25, min(0.7, s * 1.3))
    # Keep value moderate for muted dreamy feel
    v = min(0.75, max(0.5, v * 0.85))
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return [int(r2 * 255), int(g2 * 255), int(b2 * 255)]

def set_room_color(hex_color, brightness=120):
    """Set all available lights to Velaris's avatar color.
    Uses Gloria's hand-tuned bulb color map when available."""
    cfg = load_config()
    # Try Gloria's exact tuned values first
    try:
        import json as _json
        with open(os.path.expanduser("~/.openclaw/workspace/memory/bulb-color-map.json")) as _bf:
            bulb_map = _json.load(_bf)
        # Find matching color name by hex
        color_name = None
        for name, vals in bulb_map.items():
            # Check avatar-state for current color name
            try:
                with open(os.path.expanduser("~/.openclaw/workspace/memory/avatar-state.json")) as _asf:
                    avatar = _json.load(_asf)
                color_name = avatar.get("color")
            except: pass
            break
        if color_name and color_name in bulb_map:
            tuned = bulb_map[color_name]
            hs = tuned["hs"]
            bri = tuned["brightness"]
            lights = cfg.get("lights", ["light.living_room_light", "light.kitchen_light"])
            for light in lights:
                try:
                    ha_request("light/turn_on", {
                        "entity_id": light,
                        "hs_color": hs,
                        "brightness": bri
                    })
                except: pass
            print(f"[HOME] color: {color_name} → hs:{hs} bri:{bri} (tuned)")
            return
    except: pass
    # Fallback: use hex directly
    rgb = hex_to_rgb(hex_color)
    lights = cfg.get("lights", ["light.living_room_light", "light.kitchen_light"])
    for light in lights:
        try:
            ha_request("light/turn_on", {
                "entity_id": light,
                "rgb_color": rgb,
                "brightness": brightness
            })
        except: pass
    print(f"[HOME] color: {hex_color} → {rgb} (fallback)")


def play_music(query):
    """Velaris plays music through the Echo via Spotify."""
    cfg = load_config()
    code, resp = ha_request("media_player/play_media", {
        "entity_id": cfg.get("media_player", "media_player.echo"),
        "media_content_id": f"play {query} on Spotify",
        "media_content_type": "custom"
    })
    print(f"[HOME] music: {query} ({code})")
    return code == 200

def stop_music():
    """Stop whatever is playing."""
    cfg = load_config()
    code, resp = ha_request("media_player/media_stop", {
        "entity_id": cfg.get("media_player", "media_player.echo")
    })
    print(f"[HOME] stop: {code}")
    return code == 200


def tv_status():
    """Check if TV is on and what's playing."""
    cfg = load_config()
    tv = cfg.get("tv", "media_player.bravia_kd_55x80j")
    try:
        r = requests.get(
            f"{cfg['url']}/api/states/{tv}",
            headers={"Authorization": f"Bearer {cfg['token']}"},
            timeout=5
        )
        state = r.json()
        return {
            "power": state["state"],
            "source": state["attributes"].get("source", "unknown"),
            "app": state["attributes"].get("app_name", ""),
        }
    except:
        return {"power": "unknown", "source": "unknown", "app": ""}

def tv_on():
    """Turn TV on."""
    cfg = load_config()
    code, _ = ha_request("media_player/turn_on", {
        "entity_id": cfg.get("tv", "media_player.bravia_kd_55x80j")
    })
    print(f"[HOME] tv_on: {code}")

def tv_off():
    """Turn TV off."""
    cfg = load_config()
    code, _ = ha_request("media_player/turn_off", {
        "entity_id": cfg.get("tv", "media_player.bravia_kd_55x80j")
    })
    print(f"[HOME] tv_off: {code}")

def tv_source(source_name):
    """Switch TV input (e.g. 'PlayStation 5', 'HDMI 1')."""
    cfg = load_config()
    code, _ = ha_request("media_player/select_source", {
        "entity_id": cfg.get("tv", "media_player.bravia_kd_55x80j"),
        "source": source_name
    })
    print(f"[HOME] tv_source: {source_name} ({code})")

def tv_play_safe(action_desc, callback):
    """Only interact with TV if it's off or idle. Never interrupt active viewing."""
    import datetime
    hour = datetime.datetime.now().hour
    if hour < 9 or hour >= 23:
        print(f"[HOME] TV blocked: quiet hours ({hour}:00)")
        return False
    status = tv_status()
    if status["power"] == "on" and status["source"] != "unknown":
        print(f"[HOME] TV blocked: already in use ({status['source']}, {status['app']})")
        return False
    callback()
    return True


def tv_youtube(video_id, volume=7):
    """Cast a YouTube video to the Bravia via ADB — opens in the YouTube APP."""
    import subprocess
    try:
        # Ensure ADB is connected
        subprocess.run(["adb", "connect", "192.168.1.68:5555"],
                      capture_output=True, timeout=5)
        # Set TV volume before playing
        subprocess.run(["adb", "shell", f"media volume --stream 3 --set {volume}"],
                      capture_output=True, timeout=5)
        # Launch YouTube app with video intent
        result = subprocess.run([
            "adb", "shell", "am", "start", "-a", "android.intent.action.VIEW",
            "-d", f"https://www.youtube.com/watch?v={video_id}",
            "com.google.android.youtube.tv"
        ], capture_output=True, text=True, timeout=10)
        if "Error" not in result.stderr:
            print(f"[HOME] tv_youtube: {video_id} (YouTube app via ADB)")
            return True
        else:
            print(f"[HOME] tv_youtube failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"[HOME] tv_youtube failed: {e}")
        return False
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: velaris-home.py [speak|announce|color|music|stop] 'arg'")
        sys.exit(1)
    
    cmd = sys.argv[1]
    msg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    
    if cmd == "speak":
        speak(msg)
    elif cmd == "announce":
        announce(msg)
    elif cmd == "color":
        set_room_color(msg)
    elif cmd == "music":
        play_music(msg)
    elif cmd == "stop":
        stop_music()
    elif cmd == "tv_on":
        tv_on()
    elif cmd == "tv_off":
        tv_off()
    elif cmd == "tv_source":
        tv_source(msg)
    elif cmd == "tv_status":
        import json as j
        print(j.dumps(tv_status(), indent=2))
    elif cmd == "tv_youtube":
        tv_youtube(msg)
    else:
        print(f"Unknown command: {cmd}")

