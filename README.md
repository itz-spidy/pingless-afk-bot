# Pingless Direct AFK Bot (No VNC Needed)

A lightweight, 24/7 direct AFK rewards bot for `dash.pingless.org`.

## Features:
1. **Direct Mode (No VNC)**: Connects directly to Pingless AFK WebSockets, eliminating heavy X11/VNC overhead, memory crashes, and WebSocket disconnects.
2. **Auto Keepalive (Every 10 mins)**: Pings `https://dash.pingless.org/dashboard` every 10 minutes with session cookies to keep the login active 24/7.
3. **Live Web Dashboard**: Opens directly in any browser on phone or PC showing live earning rate, party boost, countdown, total credits, and live logs.
4. **Auto-Reconnect**: Seamlessly reconnects if network drops.

## Deploying:
Upload `Dockerfile`, `requirements.txt`, `app.py`, `render.yaml`, and `README.md` to your GitHub repository.
Render and Railway will automatically build and start the direct dashboard.
