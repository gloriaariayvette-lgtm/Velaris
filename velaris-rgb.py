#!/usr/bin/env python3
"""Velaris RGB — Syncs Aegis lighting to avatar color"""
import json, time, os
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

AVATAR_LOG = os.path.expanduser("~/.openclaw/workspace/memory/avatar-log.json")
OPENRGB_HOST = "172.18.16.1"
OPENRGB_PORT = 6742

# Calibrated colors for Aegis LEDs — tune these by eye
COLORS = {
    "ember":     RGBColor(50, 10, 3),
    "glacier":   RGBColor(6, 25, 35),
    "moss":      RGBColor(8, 20, 6),
    "storm":     RGBColor(8, 10, 14),
    "gold":      RGBColor(45, 25, 3),
    "twilight":  RGBColor(15, 8, 35),
    "bone":      RGBColor(40, 35, 28),
    "midnight":  RGBColor(2, 2, 6),
    "coral":     RGBColor(42, 10, 10),
    "silver":    RGBColor(25, 28, 30),
    "rust":      RGBColor(39, 6, 3),
    "dawn":      RGBColor(42, 28, 8),
}

def get_current_color():
    try:
        with open(AVATAR_LOG) as f:
            log = json.load(f)
        if log:
            return log[-1].get("chosen_color", "storm")
    except:
        pass
    return "storm"

def push_color(color_name):
    rgb = COLORS.get(color_name, COLORS["storm"])
    try:
        c = OpenRGBClient(OPENRGB_HOST, OPENRGB_PORT)
        for d in c.devices:
            d.set_color(rgb)
        print(f"[Velaris RGB] Set Aegis to {color_name} ({rgb.red},{rgb.green},{rgb.blue})")
        c.disconnect()
    except Exception as e:
        print(f"[Velaris RGB] Failed: {e}")

if __name__ == "__main__":
    last_color = None
    print("[Velaris RGB] Watching avatar changes...")
    while True:
        color = get_current_color()
        if True:  # always push to override MSI Center
            push_color(color)
            last_color = color
        time.sleep(30)
