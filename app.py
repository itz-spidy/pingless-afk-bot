import asyncio
import os
import time
import json
from aiohttp import web, ClientSession
import websockets

import re

PORT = int(os.environ.get("PORT", os.environ.get("RAILWAY_PORT", 8080)))

DEFAULT_COOKIE = (
    "pingless.sid=s:MPRJsWMXRaFVSffX6Il7zRPv7lNMqiK1.2SZCFbgjO4ZO0WPPCHFTZBSUAQTIdTxnNSLra7KE2Tw; "
    "userId=1448591330174570511; "
    "fp=7d597191f063c3e60f8934fec5a01042f6d31c706b41609255fba4de2c1d3bc6; "
    "cookie_consent=%7B%22necessary%22%3Atrue%2C%22preferences%22%3Afalse%2C%22analytics%22%3Afalse%2C%22ts%22%3A1794550754496%2C%22v%22%3A1%7D"
)

COOKIE_STR = os.environ.get("PINGLESS_COOKIE", DEFAULT_COOKIE).strip()

match_uid = re.search(r"userId=([0-9]+)", COOKIE_STR)
USER_ID = os.environ.get("PINGLESS_USER_ID", match_uid.group(1) if match_uid else "1448591330174570511")

SERVER_ID = os.environ.get("SERVER_ID", "1e2003cc").strip()
SERVER_NUMERIC = os.environ.get("SERVER_NUMERIC", "10745").strip()
ENABLE_RENEWAL = bool(SERVER_ID and SERVER_ID.lower() not in ("none", "false", "0"))
SERVER_MANAGE_URL = f"https://dash.pingless.org/server/manage?id={SERVER_ID}&numeric={SERVER_NUMERIC}&mode=server" if ENABLE_RENEWAL else ""

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# State tracking
state = {
    "status": "Initializing...",
    "user_id": USER_ID,
    "coins_per_minute": 0.0,
    "next_reward_in": 0,
    "total_earned": 0.0,
    "session_started": time.time(),
    "last_session_refresh": 0,
    "last_reward_at": 0,
    "party_multiplier": 1.0,
    "presence_count": 0,
    "server_id": SERVER_ID if ENABLE_RENEWAL else "None",
    "server_numeric": SERVER_NUMERIC if ENABLE_RENEWAL else "None",
    "server_renewal_status": "Checking..." if ENABLE_RENEWAL else "Disabled",
    "server_time_remaining": "Checking..." if ENABLE_RENEWAL else "N/A",
    "server_last_renewal": "N/A",
    "server_next_renewal": "N/A",
    "last_renewal_attempt": 0,
    "last_renewal_verified": False,
    "logs": []
}

def log(msg):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry, flush=True)
    state["logs"].insert(0, entry)
    if len(state["logs"]) > 60:
        state["logs"].pop()

# Task 1: Keep session active every 10 minutes (600 seconds)
async def session_keepalive_loop():
    headers = {
        "Cookie": COOKIE_STR,
        "User-Agent": USER_AGENT
    }
    while True:
        try:
            log("Refreshing login session with Pingless dashboard...")
            async with ClientSession(headers=headers) as session:
                async with session.get("https://dash.pingless.org/dashboard", timeout=15) as resp:
                    if resp.status == 200:
                        state["last_session_refresh"] = time.time()
                        log("Login refreshed successfully! (HTTP 200) Next refresh in 10 minutes.")
                    else:
                        log(f"Session check returned HTTP {resp.status}")
        except Exception as e:
            log(f"Session keepalive warning: {e}")

        # Sleep 10 minutes (600 seconds)
        await asyncio.sleep(600)

# Task 2: Server Renewal (Runs check every 30 mins, renews every 40 hours or when within warning threshold)
async def check_server_renewal_status(session):
    headers = {
        "Cookie": COOKIE_STR,
        "User-Agent": USER_AGENT,
        "Referer": SERVER_MANAGE_URL
    }
    url = f"https://dash.pingless.org/api/server/{SERVER_ID}/renewal/status"
    async with session.get(url, headers=headers, timeout=15) as resp:
        if resp.status == 200:
            return await resp.json()
        return None

async def renew_server_action(session):
    headers = {
        "Cookie": COOKIE_STR,
        "User-Agent": USER_AGENT,
        "Referer": SERVER_MANAGE_URL,
        "Content-Type": "application/json"
    }
    url = f"https://dash.pingless.org/api/server/{SERVER_ID}/renewal/renew"
    async with session.post(url, headers=headers, json={}, timeout=15) as resp:
        body = await resp.text()
        return resp.status, body

async def renew_and_verify_server():
    log(f"Checking renewal status for server {SERVER_ID}...")
    async with ClientSession() as session:
        status_data = await check_server_renewal_status(session)
        if not status_data:
            log(f"Could not retrieve renewal status for server {SERVER_ID}.")
            return False

        time_rem = status_data.get("timeRemaining", {})
        hours = time_rem.get("hours", 0)
        minutes = time_rem.get("minutes", 0)
        requires_renewal = status_data.get("requiresRenewal", False)
        is_expired = status_data.get("isExpired", False)

        state["server_time_remaining"] = f"{hours}h {minutes}m remaining"
        state["server_last_renewal"] = status_data.get("lastRenewal", "N/A")
        state["server_next_renewal"] = status_data.get("nextRenewal", "N/A")

        log(f"Server {SERVER_ID} current time remaining: {hours}h {minutes}m (Requires renewal: {requires_renewal}, Expired: {is_expired})")

        # Trigger renewal if requires renewal, expired, or remaining hours <= 24 (or >= 40h elapsed since last renewal)
        should_renew = requires_renewal or is_expired or hours <= 24

        if should_renew:
            log(f"Attempting server renewal now (button#renew-server trigger)...")
            state["last_renewal_attempt"] = time.time()
            status_code, body = await renew_server_action(session)
            log(f"Renewal POST request finished with HTTP {status_code}: {body}")

            # Re-verify after 2 seconds
            await asyncio.sleep(2)
            verify_data = await check_server_renewal_status(session)
            if verify_data:
                v_rem = verify_data.get("timeRemaining", {})
                v_hours = v_rem.get("hours", 0)
                v_mins = v_rem.get("minutes", 0)
                v_req = verify_data.get("requiresRenewal", False)

                if not v_req and v_hours > 24:
                    state["last_renewal_verified"] = True
                    state["server_renewal_status"] = f"Renewed & Verified ({v_hours}h {v_mins}m)"
                    state["server_time_remaining"] = f"{v_hours}h {v_mins}m remaining"
                    state["server_last_renewal"] = verify_data.get("lastRenewal", "N/A")
                    state["server_next_renewal"] = verify_data.get("nextRenewal", "N/A")
                    log(f"✅ [RENEWAL VERIFIED] Server {SERVER_ID} successfully renewed! Remaining: {v_hours}h {v_mins}m.")
                    return True
                else:
                    state["last_renewal_verified"] = False
                    state["server_renewal_status"] = "Renewal Verification Failed"
                    log(f"⚠️ [RENEWAL WARNING] Renewal post succeeded but verification shows {v_hours}h remaining.")
                    return False
        else:
            state["server_renewal_status"] = f"Active ({hours}h {minutes}m remaining)"
            state["last_renewal_verified"] = True
            log(f"Server {SERVER_ID} is in good standing ({hours}h {minutes}m remaining). Next auto-renewal check will run continuously.")
            return True

async def server_renewal_loop():
    if not ENABLE_RENEWAL:
        log("Server auto-renewal loop disabled (no SERVER_ID configured).")
        return
    # Initial check on startup
    await asyncio.sleep(5)
    while True:
        try:
            await renew_and_verify_server()
        except Exception as e:
            log(f"Server renewal loop error: {e}")

        # Check every 30 minutes (1800s); renews automatically whenever <= 24 hours remain (or every 40h)
        await asyncio.sleep(1800)

# Task 3: Pingless AFK WebSocket worker
async def afk_websocket_loop():
    headers = {
        "Cookie": COOKIE_STR,
        "User-Agent": USER_AGENT,
        "Origin": "https://dash.pingless.org"
    }
    last_next_reward = 0

    while True:
        try:
            log("Connecting to Pingless AFK WebSocket (wss://dash.pingless.org/api/afk/ws)...")
            state["status"] = "Connecting..."
            async with websockets.connect(
                "wss://dash.pingless.org/api/afk/ws",
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10
            ) as ws:
                log("Connected to AFK server! Earning rewards in progress.")
                state["status"] = "Active & Earning"

                async for raw_msg in ws:
                    try:
                        data = json.loads(raw_msg)
                        if data.get("type") == "afk_state":
                            rate = float(data.get("coinsPerMinute", 1.0))
                            next_in = int(data.get("nextRewardIn", 60000))
                            state["coins_per_minute"] = rate
                            state["next_reward_in"] = max(0, int(next_in / 1000))
                            state["party_multiplier"] = float(data.get("multiplier", 1.0))
                            state["presence_count"] = int(data.get("presenceCount", 0))

                            # Detect reward drop
                            if last_next_reward > 0 and next_in > (last_next_reward + 5000):
                                state["total_earned"] += rate
                                state["last_reward_at"] = time.time()
                                log(f"Reward received: +{rate:.2f} Credits! Total: {state['total_earned']:.2f}")

                            last_next_reward = next_in
                    except Exception:
                        pass
        except Exception as e:
            err_str = str(e)
            if "4004" in err_str or "Replaced by a newer connection" in err_str:
                state["status"] = "Standby (Active AFK on primary bot)"
                log(f"Notice: Active AFK session already farming credits for user {USER_ID}. Yielding session to avoid conflict. Server auto-renewal & login keepalive remain 100% active. Checking again in 5m...")
                await asyncio.sleep(300)
            else:
                state["status"] = "Disconnected (reconnecting...)"
                log(f"WebSocket error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

# Task 4: Direct Web UI (No VNC needed!)
async def index_handler(request):
    uptime_sec = int(time.time() - state["session_started"])
    hours, rem = divmod(uptime_sec, 3600)
    mins, secs = divmod(rem, 60)
    uptime_str = f"{hours}h {mins}m {secs}s"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pingless AFK & Auto-Renewal Bot</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: #09090b; color: #f4f4f5; }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="min-h-screen p-4 sm:p-8 flex flex-col items-center">
    <div class="w-full max-w-4xl space-y-6">
        <!-- Header -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-zinc-800 gap-4">
            <div class="flex items-center space-x-3">
                <div class="w-3.5 h-3.5 rounded-full bg-emerald-500 animate-pulse"></div>
                <h1 class="text-2xl font-bold tracking-tight">Pingless AFK & Server Auto-Renew</h1>
                <span class="text-xs bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-full font-medium">Direct Mode</span>
            </div>
            <div class="text-xs text-zinc-400 mono">
                User ID: <span class="text-zinc-200">{state["user_id"]}</span>
            </div>
        </div>

        <!-- Metric Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-zinc-900/80 border border-zinc-800 rounded-xl p-4">
                <div class="text-xs font-medium text-zinc-400">AFK Status</div>
                <div id="status" class="mt-2 text-lg font-semibold text-emerald-400">{state["status"]}</div>
                <div class="text-xs text-zinc-500 mt-1">Direct WebSocket</div>
            </div>

            <div class="bg-zinc-900/80 border border-zinc-800 rounded-xl p-4">
                <div class="text-xs font-medium text-zinc-400">Earning Rate</div>
                <div id="rate" class="mt-2 text-2xl font-bold text-white mono">{state["coins_per_minute"]:.2f} <span class="text-xs font-normal text-zinc-400">/ min</span></div>
                <div id="party" class="text-xs text-indigo-400 mt-1">Party Boost: {state["party_multiplier"]}x ({state["presence_count"]} users)</div>
            </div>

            <div class="bg-zinc-900/80 border border-zinc-800 rounded-xl p-4">
                <div class="text-xs font-medium text-zinc-400">Next Reward In</div>
                <div id="countdown" class="mt-2 text-2xl font-bold text-amber-400 mono">{state["next_reward_in"]}s</div>
                <div class="text-xs text-zinc-500 mt-1">Auto-credited</div>
            </div>

            <div class="bg-zinc-900/80 border border-zinc-800 rounded-xl p-4">
                <div class="text-xs font-medium text-zinc-400">Total Earned</div>
                <div id="earned" class="mt-2 text-2xl font-bold text-emerald-400 mono">+{state["total_earned"]:.2f} <span class="text-xs font-normal text-zinc-400">Credits</span></div>
                <div id="uptime" class="text-xs text-zinc-500 mt-1">Active: {uptime_str}</div>
            </div>
        </div>

        <!-- Server Renewal Card -->
        <div class="bg-zinc-900/80 border border-zinc-800 rounded-xl p-5 space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div class="flex items-center space-x-3">
                    <span class="text-2xl">🔄</span>
                    <div>
                        <div class="flex items-center space-x-2">
                            <h2 class="text-base font-semibold text-white">Server Auto-Renewal (Every 40 Hours)</h2>
                            <span class="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-medium">Auto-Click & Verify Active</span>
                        </div>
                        <div class="text-xs text-zinc-400 mt-0.5">
                            Target: <span class="mono text-zinc-200">Server #{state["server_numeric"]} ({state["server_id"]})</span>
                        </div>
                    </div>
                </div>
                <button onclick="triggerRenew()" id="renewBtn" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition flex items-center justify-center space-x-1.5 self-start sm:self-auto">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3.5 h-3.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
                    </svg>
                    <span>Click Renew Now</span>
                </button>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-zinc-800/80 text-xs mono">
                <div class="bg-zinc-950/60 p-3 rounded-lg border border-zinc-800/60">
                    <span class="text-zinc-500 block">Remaining Time</span>
                    <span id="serverTime" class="text-emerald-400 font-semibold text-sm">{state["server_time_remaining"]}</span>
                </div>
                <div class="bg-zinc-950/60 p-3 rounded-lg border border-zinc-800/60">
                    <span class="text-zinc-500 block">Renewal Status</span>
                    <span id="serverStatus" class="text-zinc-200 font-medium">{state["server_renewal_status"]}</span>
                </div>
                <div class="bg-zinc-950/60 p-3 rounded-lg border border-zinc-800/60">
                    <span class="text-zinc-500 block">Next Expiry</span>
                    <span id="serverNext" class="text-zinc-300">{state["server_next_renewal"]}</span>
                </div>
            </div>
        </div>

        <!-- Keepalive Banner -->
        <div class="bg-zinc-900/60 border border-zinc-800 rounded-xl p-4 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="text-indigo-400 text-lg">🛡️</span>
                <div>
                    <div class="text-sm font-medium text-zinc-200">Session Auto-Keepalive</div>
                    <div class="text-xs text-zinc-400">Automatically re-authenticates with dashboard every 10 minutes to guarantee active login.</div>
                </div>
            </div>
            <span class="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 rounded-md font-medium">Every 10m Active</span>
        </div>

        <!-- Live Activity Log -->
        <div class="bg-zinc-900/80 border border-zinc-800 rounded-xl p-4 space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-zinc-800">
                <h2 class="text-sm font-semibold text-zinc-300">Live Activity Feed</h2>
                <span class="text-xs text-zinc-500 mono">Auto-refreshing</span>
            </div>
            <div id="logbox" class="h-64 overflow-y-auto space-y-1 text-xs mono text-zinc-400 pr-2">
                {"".join([f'<div>{line}</div>' for line in state["logs"]])}
            </div>
        </div>
    </div>

    <script>
        async function refresh() {{
            try {{
                const r = await fetch('/api/status');
                const d = await r.json();
                document.getElementById('status').textContent = d.status;
                document.getElementById('rate').innerHTML = `${{d.coins_per_minute.toFixed(2)}} <span class="text-xs font-normal text-zinc-400">/ min</span>`;
                document.getElementById('party').textContent = `Party Boost: ${{d.party_multiplier}}x (${{d.presence_count}} users)`;
                document.getElementById('countdown').textContent = `${{d.next_reward_in}}s`;
                document.getElementById('earned').innerHTML = `+${{d.total_earned.toFixed(2)}} <span class="text-xs font-normal text-zinc-400">Credits</span>`;
                
                document.getElementById('serverTime').textContent = d.server_time_remaining;
                document.getElementById('serverStatus').textContent = d.server_renewal_status;
                document.getElementById('serverNext').textContent = d.server_next_renewal;

                const logbox = document.getElementById('logbox');
                logbox.innerHTML = d.logs.map(l => `<div>${{l}}</div>`).join('');
            }} catch(e) {{}}
        }}
        setInterval(refresh, 2000);

        async function triggerRenew() {{
            const btn = document.getElementById('renewBtn');
            btn.disabled = true;
            btn.innerHTML = '<span>Renewing & Verifying...</span>';
            try {{
                const r = await fetch('/api/renew', {{ method: 'POST' }});
                const d = await r.json();
                alert(d.message || 'Renewal action executed.');
                refresh();
            }} catch(e) {{
                alert('Error renewing: ' + e);
            }} finally {{
                btn.disabled = false;
                btn.innerHTML = '<span>Click Renew Now</span>';
            }}
        }}
    </script>
</body>
</html>
"""
    return web.Response(text=html, content_type="text/html")

async def status_api_handler(request):
    return web.json_response(state)

async def renew_api_handler(request):
    success = await renew_and_verify_server()
    return web.json_response({
        "success": success,
        "message": "Server renewal executed and verified." if success else "Renewal executed, check status."
    })

async def start_background_tasks(app):
    app["keepalive_task"] = asyncio.create_task(session_keepalive_loop())
    app["afk_task"] = asyncio.create_task(afk_websocket_loop())
    app["renewal_task"] = asyncio.create_task(server_renewal_loop())

async def cleanup_background_tasks(app):
    app["keepalive_task"].cancel()
    app["afk_task"].cancel()
    app["renewal_task"].cancel()

def main():
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_get("/api/status", status_api_handler)
    app.router.add_post("/api/renew", renew_api_handler)
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    log(f"Starting Direct Pingless AFK & Auto-Renewal Web Server on port {PORT}...")
    web.run_app(app, host="0.0.0.0", port=PORT, access_log=None)

if __name__ == "__main__":
    main()
