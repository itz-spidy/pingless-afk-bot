<h1 align="center">⚡ Pingless Direct AFK Bot</h1>

<p align="center">
  <a href="https://github.com/itzxsahil">
    <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=28&pause=1000&color=FFB703&center=true&vCenter=true&width=900&lines=24%2F7+Direct+AFK+Rewards+Bot+for+dash.pingless.org;No+VNC+Needed+%7C+Low+Memory+%7C+Zero+Browser+Crash;Direct+WebSocket+Protocol+%7C+Auto+Keepalive;Made+with+❤️+by+itzxsahil" alt="Typing SVG" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Pingless-AFK%20Bot-FFB703?style=for-the-badge"> <img src="https://img.shields.io/badge/Direct%20Protocol-WebSocket-023E8A?style=for-the-badge"> <img src="https://img.shields.io/badge/Render%20%26%20Railway-Cloud%20Ready-46E3B7?style=for-the-badge">
</p>

---

## 🎬 Video Tutorial & Interactive Walkthrough

<div align="center">
  <a href="https://www.youtube.com/results?search_query=itzxsahil+pingless+afk+bot">
    <img src="assets/tutorial-showcase.svg" width="100%" alt="Video Tutorial Showcase" style="border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);" />
  </a>
  <p><em>▶️ <strong>Interactive Project Tutorial</strong> — Click the player above to watch full setup guide &amp; demonstration!</em></p>
</div>

---

# 🚀 Overview

A high-efficiency, headless 24/7 AFK rewards bot for `dash.pingless.org`. By communicating directly via raw WebSockets, it eliminates the need for heavy Chrome or VNC containers.

---

## 🏗️ System Architecture & Data Flow

<div align="center">
  <img src="assets/architecture.svg" width="100%" alt="Architecture Diagram" style="border-radius: 12px;" />
</div>

<br>

AsyncIO client establishes persistent cookie-authenticated WebSockets directly with the Pingless backend, dispatching periodic heartbeats without any browser overhead.

---

# ✨ Features

✅ **Direct WebSocket Stream**: Eliminates browser crashes, canvas rendering overhead, and memory leaks.\n✅ **Ultra Low Footprint**: Consumes under 30MB RAM.\n✅ **Auto Keepalive**: Regularly pings `dash.pingless.org/dashboard` every 10 minutes to maintain persistent session state.

---

# 📦 Installation & Quickstart

### Cloud Deployment (Render / Railway)\nDeploy instantly using the bundled `Dockerfile` and `render.yaml`.\n\n### Local Run\n```bash\npip install -r requirements.txt\npython app.py\n```

---

# 👤 Author & Support
- Built with ❤️ by [@itzxsahil](https://github.com/itzxsahil)
- Star ⭐ this repository if you find it helpful!
