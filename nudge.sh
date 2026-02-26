#!/bin/bash
# nudge.sh — Poke Velaris's emotions
# Usage: bash nudge.sh Warmth 0.05
#        bash nudge.sh Tension -0.03
#        bash nudge.sh          (shows current state)

DIM="$1"
AMT="$2"

if [ -z "$DIM" ]; then
    python3 -c "
import socket, json
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(3)
s.connect('/tmp/Velaris-emotion.sock')
s.sendall(json.dumps({'command': 'state'}).encode() + b'\n')
data = b''
while True:
    chunk = s.recv(8192)
    if not chunk: break
    data += chunk
s.close()
d = json.loads(data)
v = d['emotion_vector']
dims = ['Valence','Arousal','Dominance','Safety','Desire','Connection','Playfulness','Curiosity','Warmth','Tension','Groundedness']
for i, dim in enumerate(dims):
    bar = '█' * int(v[i] * 20) + '░' * (20 - int(v[i] * 20))
    print(f'  {dim:14s} {bar} {v[i]:.3f}')
"
    exit 0
fi

python3 -c "
import socket, json
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(3)
s.connect('/tmp/Velaris-emotion.sock')
s.sendall(json.dumps({'command': 'nudge', 'dimension': '$DIM', 'amount': $AMT}).encode() + b'\n')
r = json.loads(s.recv(4096))
s.close()
if r.get('success'):
    print('  $DIM ${AMT:0:1}= nudged')
else:
    print('  Failed:', r)
"
