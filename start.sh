#!/usr/bin/env bash
set -euo pipefail

# Fallback password if VNC_PASSWORD is not explicitly provided
VNC_PASSWORD="${VNC_PASSWORD:-vncpassword123}"

# Port fallback: handles Railway ($PORT / 8080) and Render ($PORT / 10000)
PORT="${PORT:-${RAILWAY_PORT:-8080}}"
DASHBOARD_URL="https://dash.pingless.org/dashboard"
AFK_URL="https://dash.pingless.org/afk"
RESTART_INTERVAL="${RESTART_INTERVAL:-14400}" # 4 hours = 14400 seconds

# Disable container sandbox limits that cause network socket drops
export MOZ_DISABLE_CONTENT_SANDBOX=1
export MOZ_DISABLE_GPU_SANDBOX=1
export MOZ_DISABLE_RDD_SANDBOX=1
export MOZ_DISABLE_GMP_SANDBOX=1

# System-wide enterprise policies
mkdir -p /etc/firefox/policies
cat << 'EOF' > /etc/firefox/policies/policies.json
{
  "policies": {
    "DisableAppUpdate": true,
    "DisableTelemetry": true,
    "DisableFirefoxStudies": true,
    "OverrideFirstRunPage": "",
    "OverridePostUpdatePage": "",
    "DontCheckDefaultBrowser": true,
    "Preferences": {
      "network.dns.disableIPv6": true,
      "network.trr.mode": 5,
      "security.sandbox.content.level": 0,
      "security.sandbox.gpu.level": 0
    }
  }
}
EOF

# Set up Firefox profile with tuned network & background execution preferences
PROFILE_DIR="/tmp/firefox-profile"
mkdir -p "$PROFILE_DIR"

cat << 'EOF' > "$PROFILE_DIR/user.js"
// Disable IPv6 lookups to prevent Docker/cloud network DNS timeouts
user_pref("network.dns.disableIPv6", true);

// Disable DNS-over-HTTPS (DoH) so Firefox uses standard host/container DNS resolvers
user_pref("network.trr.mode", 5);

// Direct connection (no proxy auto-detection delays)
user_pref("network.proxy.type", 0);

// Disable speculative pre-connections
user_pref("network.http.speculative-parallel-limit", 0);

// Disable internal sandbox levels inside container
user_pref("security.sandbox.content.level", 0);
user_pref("security.sandbox.gpu.level", 0);

// Prevent throttling background tabs so AFK timer/websocket runs without pausing
user_pref("dom.min_background_timeout_value", 100);
user_pref("browser.tabs.unloadOnLowMemory", false);
user_pref("widget.windows.window_occlusion_tracking.enabled", false);

// Disable telemetry, first run pages, and update popups
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.enabled", false);
user_pref("app.update.auto", false);
user_pref("app.update.enabled", false);
user_pref("extensions.pocket.enabled", false);

// Set default startup homepage to Pingless dashboard and AFK tab
user_pref("browser.startup.page", 1);
user_pref("browser.startup.homepage", "https://dash.pingless.org/dashboard|https://dash.pingless.org/afk");
EOF

# Initialize virtual X display
mkdir -p /tmp/.X11-unix
Xvfb :1 -screen 0 1366x768x24 -ac +extension GLX +render -noreset &
export DISPLAY=:1
sleep 2

# Start lightweight window manager
fluxbox &
sleep 1

# Setup VNC server
x11vnc -storepasswd "$VNC_PASSWORD" /tmp/vnc.pass >/dev/null
x11vnc -display :1 -forever -shared -rfbauth /tmp/vnc.pass -listen 127.0.0.1 -rfbport 5900 &
sleep 1

# Start noVNC proxy in the background
websockify --web=/usr/share/novnc --heartbeat=30 "$PORT" 127.0.0.1:5900 &
sleep 1

# Function to inject Pingless cookies into Firefox profile SQLite database
inject_pingless_cookies() {
    python3 - "$PROFILE_DIR" << 'PY'
import sys
import os
import sqlite3
import time

profile_dir = sys.argv[1]
db_path = os.path.join(profile_dir, "cookies.sqlite")

cookies = [
    {
        "name": "pingless.sid",
        "value": "s%3AMPRJsWMXRaFVSffX6Il7zRPv7lNMqiK1.2SZCFbgjO4ZO0WPPCHFTZBSUAQTIdTxnNSLra7KE2Tw",
        "domain": "dash.pingless.org",
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "expiry": 1797148656
    },
    {
        "name": "userId",
        "value": "1448591330174570511",
        "domain": "dash.pingless.org",
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "expiry": 1797142928
    },
    {
        "name": "fp",
        "value": "7d597191f063c3e60f8934fec5a01042f6d31c706b41609255fba4de2c1d3bc6",
        "domain": "dash.pingless.org",
        "path": "/",
        "secure": True,
        "httpOnly": False,
        "expiry": 1826086916
    },
    {
        "name": "cookie_consent",
        "value": "%7B%22necessary%22%3Atrue%2C%22preferences%22%3Afalse%2C%22analytics%22%3Afalse%2C%22ts%22%3A1794550754496%2C%22v%22%3A1%7D",
        "domain": "dash.pingless.org",
        "path": "/",
        "secure": True,
        "httpOnly": False,
        "expiry": 1826086754
    }
]

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Ensure table exists matching standard Firefox schema
cur.execute("""
CREATE TABLE IF NOT EXISTS moz_cookies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseDomain TEXT,
    originAttributes TEXT NOT NULL DEFAULT '',
    name TEXT,
    value TEXT,
    host TEXT,
    path TEXT,
    expiry INTEGER,
    lastAccessed INTEGER,
    creationTime INTEGER,
    isSecure INTEGER,
    isHttpOnly INTEGER,
    inBrowserElement INTEGER DEFAULT 0,
    sameSite INTEGER DEFAULT 0,
    rawSameSite INTEGER DEFAULT 0,
    schemeMap INTEGER DEFAULT 0,
    CONSTRAINT moz_uniqueid UNIQUE (name, host, path, originAttributes)
);
""")

cur.execute("PRAGMA table_info(moz_cookies)")
existing_cols = {row[1] for row in cur.fetchall()}
now_us = int(time.time() * 1000000)

for c in cookies:
    hosts = [c["domain"], "." + c["domain"].lstrip(".")]
    for h in set(hosts):
        row_data = {
            "baseDomain": "pingless.org",
            "originAttributes": "",
            "name": c["name"],
            "value": c["value"],
            "host": h,
            "path": c["path"],
            "expiry": int(c["expiry"]),
            "lastAccessed": now_us,
            "creationTime": now_us,
            "isSecure": 1 if c.get("secure") else 0,
            "isHttpOnly": 1 if c.get("httpOnly") else 0,
            "sameSite": 1,
            "rawSameSite": 1,
            "schemeMap": 2
        }
        cols = [k for k in row_data.keys() if k in existing_cols]
        vals = [row_data[k] for k in cols]
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        cur.execute(f"INSERT OR REPLACE INTO moz_cookies ({col_names}) VALUES ({placeholders})", vals)

conn.commit()
conn.close()
print("Pingless session cookies injected successfully into profile.")
PY
}

echo "=== Initializing Pingless AFK automation ==="

# Continuous loop: runs Firefox for 4 hours, then cleanly restarts
while true; do
    echo "[$(date -u)] Injecting fresh cookies into Firefox profile..."
    inject_pingless_cookies

    echo "[$(date -u)] Launching Firefox with Pingless Dashboard..."
    firefox \
      --profile "$PROFILE_DIR" \
      --no-remote \
      --width 1366 \
      --height 768 \
      "$DASHBOARD_URL" &
    FF_PID=$!

    # Wait 8 seconds for dashboard authentication session to establish
    sleep 8

    echo "[$(date -u)] Navigating to Pingless AFK page ($AFK_URL)..."
    firefox --profile "$PROFILE_DIR" "$AFK_URL" &

    echo "[$(date -u)] Firefox is now running AFK. Waiting 4 hours ($RESTART_INTERVAL seconds) before next restart..."
    sleep "$RESTART_INTERVAL"

    echo "[$(date -u)] 4 hours elapsed. Gracefully restarting Firefox..."
    kill "$FF_PID" 2>/dev/null || true
    sleep 3
    kill -9 "$FF_PID" 2>/dev/null || true
    sleep 2
done
