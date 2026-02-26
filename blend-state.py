#!/usr/bin/env python3
"""
blend-state.py — Merge EmoClaw state with existing state.

Usage: python3 blend-state.py <emoclaw_file> <existing_file> <emoclaw_weight>

EmoClaw drives emotions (80%), somatic/existing state preserved (20%).
This prevents emoclaw-sync from wiping somatic breathing nudges.
"""
import sys

DIMS = ['Valence', 'Arousal', 'Dominance', 'Safety', 'Desire',
        'Connection', 'Playfulness', 'Curiosity', 'Warmth', 'Tension', 'Groundedness']


def read_state(path):
    state = {}
    with open(path) as f:
        for line in f:
            if ':' in line:
                k, v = line.split(':', 1)
                try:
                    state[k.strip()] = float(v.strip().split()[0])
                except ValueError:
                    pass
    return state


def main():
    if len(sys.argv) < 4:
        print("Usage: blend-state.py <emoclaw_file> <existing_file> <weight>")
        sys.exit(1)

    emoclaw_file = sys.argv[1]
    existing_file = sys.argv[2]
    weight = float(sys.argv[3])  # EmoClaw weight (0.8)

    emo = read_state(emoclaw_file)
    existing = read_state(existing_file)

    blended = []
    for dim in DIMS:
        e_val = emo.get(dim, 0.5)
        s_val = existing.get(dim, e_val)
        b_val = round(e_val * weight + s_val * (1 - weight), 4)
        b_val = max(0.01, min(0.99, b_val))
        blended.append(f"{dim}: {b_val}")

    with open(existing_file, 'w') as f:
        f.write("\n".join(blended) + "\n")

    print(f"BLENDED: EmoClaw {weight:.0%} + somatic {1-weight:.0%}")


if __name__ == "__main__":
    main()
