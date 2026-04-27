<div align="center">
  <img src="fanart.jpg" alt="StreamPK Sports Fanart" width="100%" />

  <h1>🏈 StreamPK Sports ⚽</h1>
  <p><strong>Watch Live Sports matches natively in Kodi, courtesy of streamed.pk</strong></p>
  
  <p>
    <img src="https://img.shields.io/badge/Kodi-v19%2B-blue.svg?style=flat-square&logo=kodi" alt="Kodi Compatible" />
    <img src="https://img.shields.io/badge/Python-3.x-yellow.svg?style=flat-square&logo=python" alt="Python 3" />
    <img src="https://img.shields.io/badge/License-GPL--3.0-green.svg?style=flat-square" alt="License" />
  </p>
</div>

## 🌟 Overview

**StreamPK Sports** is a seamless Kodi video addon designed to fetch and stream live sports from the `streamed.pk` API. It features a modern, automated background extractor proxy that pulls high-quality video and audio feeds seamlessly, bringing the stadium experience right to your living room.

## ✨ Features

- **🔴 Live Sports Hub:** Real-time matches spanning Soccer, Motorsports, Basketball, Football, and more.
- **📅 Today's Matches:** Quickly browse what's playing today.
- **⚡ Native Playback:** The integrated background stream multiplexer flawlessly passes HLS/fMP4 video back to Kodi's native media player. No external browser popups!
- **🎧 Auto-Unmute & Autoplay:** Video and audio feeds are intelligently merged and started without requiring any manual clicks or browser interactions.

## ⚙️ How It Works

Many modern sports streams use complicated anti-bot mechanisms or WebRTC/fMP4 chunking that standard Kodi resolvers struggle with. 

StreamPK bypasses these issues by running a headless background proxy (`extractor_proxy.py`) powered by Playwright and FFmpeg. When you select a stream:
1. The addon fires up the proxy in the background.
2. The proxy intercepts the raw video and audio chunks.
3. FFmpeg multiplexes them into a single `MPEG-TS` stream on the fly.
4. Kodi natively plays the `http://127.0.0.1:8081/stream` endpoint in glorious high definition!

## 🚀 Installation

### Prerequisites
Because this addon relies on a headless browser for extraction, ensure your system has the following installed:
* **Python 3**
* **FFmpeg** (Must be available in your system's PATH)
* **Playwright** (`pip install playwright` followed by `playwright install chromium`)

### Manual Install
1. Download the repository as a ZIP file.
2. Open Kodi and navigate to **Add-ons** > **Install from zip file**.
3. Select the downloaded ZIP file.
4. Wait for the "Add-on installed" notification.
5. Enjoy the game!

## 🛠 Troubleshooting

If you encounter issues where the stream won't load or times out:
- **Check the Kodi Log** (`kodi.log`): Often located in `~/.kodi/temp/` on Linux.
- **FFmpeg missing**: Ensure `ffmpeg` is properly installed on your operating system.
- **Playwright missing**: Verify Playwright and its Chromium dependencies are installed correctly in Kodi's Python environment.

---
<div align="center">
  <i>Developed by Miles Hilliard</i> | <a href="https://www.mileshilliard.com">Website</a>
</div>
