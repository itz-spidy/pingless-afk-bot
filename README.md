<h1 align="center">⚡ Pingless Direct AFK Bot</h1>

<p align="center">
  <a href="https://github.com/itz-spidy">
    <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=28&pause=1000&color=FFB703&center=true&vCenter=true&width=900&lines=24%2F7+Direct+AFK+Rewards+Bot+for+dash.pingless.org;No+VNC+Needed+%7C+Low+Memory+%7C+Zero+Browser+Crash;Direct+WebSocket+Protocol+%7C+Auto+Keepalive;Deployable+to+Render%2C+Railway+%26+VPS" alt="Typing SVG" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Pingless-AFK%20Bot-FFB703?style=for-the-badge">
  <img src="https://img.shields.io/badge/Direct%20Protocol-WebSocket-023E8A?style=for-the-badge">
  <img src="https://img.shields.io/badge/Render%20%26%20Railway-Cloud%20Ready-46E3B7?style=for-the-badge">
  <img src="https://img.shields.io/badge/Python-AsyncIO-3776AB?style=for-the-badge&logo=python&logoColor=white">
</p>

---

## 🎬 Bot Execution Showcase & Video Guide

<div align="center">
  <img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />
  <br><br>
  <img src="https://media.giphy.com/media/26tn33aiTi1jkl6H6/giphy.gif" width="700" alt="AFK Bot In Action" style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);" />
  <br><br>
  <img src="https://img.shields.io/badge/%E2%96%B6%EF%B8%8F%20WATCH%20TUTORIAL-AFK%20BOT%20DEPLOYMENT%20GUIDE-FFB703?style=for-the-badge&logo=youtube&logoColor=black" />
</div>

---

# 🚀 Why Direct Mode (No VNC)?

Unlike traditional setups that run heavy Chrome and X11/VNC instances eating 1GB+ RAM, this bot connects **directly** to the Pingless AFK WebSockets:
- 📉 Uses less than **30MB RAM**.
- 🚫 Zero browser memory leaks, blank screens, or canvas crashes.
- 🔄 Automatic session keepalive every 10 minutes.
- 🛡️ Auto-reconnect handling on network disconnects.

---

# ☁️ One-Click Cloud Deploy

Deploy to Render or Railway using the included `Dockerfile` and `render.yaml`.

### Environment Variables
Configure your session cookies in environment variables or within `app.py`:
- `PORT`: Set automatically by Render/Railway (defaults to `8080`).

---

# 📦 Local Run

```bash
git clone https://github.com/itz-spidy/pingless-afk-bot.git
cd pingless-afk-bot

pip install -r requirements.txt
python app.py
```

---

# 👤 Author
Developed by [@itz-spidy](https://github.com/itz-spidy).
