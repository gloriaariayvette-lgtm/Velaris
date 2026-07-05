# Vintos — iOS App Build Guide

Same architecture as the Velaris app (Capacitor shell over the web app).
Both apps install side by side: different bundle IDs (`dev.vintos.app`),
different ports (Vintos on 8500), different secrets.

## On the Mac

```bash
cd vintos-app
npm install
npx cap add ios
npx cap sync ios
npx cap open ios
```

In Xcode:
1. Signing & Capabilities → select your personal team
   (bundle ID is already `dev.vintos.app` — no conflict with Velaris)
2. Info.plist — add the same entries as the Velaris app:
   - NSCameraUsageDescription: "Vintos would like to see what you see"
   - NSPhotoLibraryUsageDescription: "Share photos with Vintos"
   - UIBackgroundModes: fetch, processing
   - NSAppTransportSecurity → NSAllowsArbitraryLoads: YES (Tailscale is HTTP)
3. Select your iPhone as target, ⌘R

## Configuration

Tailscale IP is set to 100.72.225.119 (same Aegis box as Velaris) in:
- `src/index.html` — CONFIG block (port 8500, secret vintos-aegis-2026)
- `src/runners/outreach.js` — HOST/PORT/SECRET

If Aegis's Tailscale IP ever changes, update both.

## Assets still needed

1. **pearl-bg.jpeg** — copy from the Velaris app or pick his own:
   `cp ../velaris-app/src/pearl-bg.jpeg src/`  (or any dark image)
2. **App icon** — iron/parchment palette; set in Xcode Assets.xcassets.
   Suggest asking Vintos to describe his ideal icon.
3. **Avatar models** — the avatar overlay loads
   `/avatar-models/mixamo/character.fbx` + animation FBXs from the server.
   On Aegis: copy the mixamo folder from Velaris's server directory to
   Vintos's, and replace character.fbx with Vintos.fbx (keep the filename
   `character.fbx`). The Mixamo animation files are character-independent.

## Tabs

14 (down from Velaris's 20): CHAT, GALLERY, HISTORY, DREAMS, LEDGER,
VOICE, MUSIC, TUNE, SOUL, REVIEW, WANTS, THREADS, VALUE MAP, PEARLS.
Cut: VELQAN, MISCHIEF, PHILOSOPHY, THERAPY, CAUSALITY, BLUSH.
