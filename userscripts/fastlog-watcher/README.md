# Fastlog Gebraucht & Geprüft Product Watcher

A browser userscript (Tampermonkey / Violentmonkey / ScriptCat) that watches [Fastlog Gebraucht & Geprüft](https://shop.fastlog.ch/product-category/gebraucht-geprueft/) for newly listed items and sends instant notifications via Telegram, Discord, or native browser notifications.

---

## Features

- ⚡ **Dual Feed & HTML Parsing**: Checks both the category RSS feed (`/feed/`) and the category page HTML as fallback.
- 🤖 **Telegram Bot Integration**: Direct POST messages to your Telegram Chat when a new product is added.
- 💬 **Discord Webhook Support**: Rich embeds delivered straight to a Discord channel.
- 🔔 **Native Browser Notifications**: Desktop notifications when new items appear while your browser is open.
- ⏰ **Background Cron execution**: Compatible with ScriptCat `@crontab` (runs every 15 minutes).
- ⚙️ **In-Browser Configuration**: Set Telegram Token, Chat ID, or Discord Webhook URL directly via the Userscript manager menu (`GM_registerMenuCommand`).

---

## Installation

1. Make sure you have a Userscript manager installed (e.g. **Violentmonkey**, **Tampermonkey**, or **ScriptCat**).
2. Install `fastlog-watcher.user.js`.

---

## Free Hosting & Bot Options Overview

If you want 24/7 background watching without keeping your browser/PC running:

| Solution | Hosting Platform | Cost | How it works |
| :--- | :--- | :--- | :--- |
| **Userscript (This script)** | Your local Browser / ScriptCat | **Free** | Runs periodically via `@crontab` or `setInterval` in your browser. |
| **Cloudflare Worker** | Cloudflare Workers | **Free** (100k req/day) | Serverless JS function triggered by Cron (`scheduled`), stores seen product IDs in Cloudflare KV, notifies Telegram/Discord. |
| **GitHub Actions** | GitHub Workflows | **Free** (2k mins/mo) | Cron job running a 20-line Node.js / Python script every 15 min, storing state in Gist or Cache. |

---

## Setting Up Telegram Bot (Optional)

1. Talk to [@BotFather](https://t.me/BotFather) on Telegram and send `/newbot` to create a bot. Copy the **HTTP API Token**.
2. Talk to [@userinfobot](https://t.me/userinfobot) to get your **Chat ID**.
3. In your Userscript extension menu, click **⚙️ Telegram Bot Token einstellen** and **💬 Telegram Chat ID einstellen**.
4. Test with **🔍 Jetzt nach neuen Produkten suchen**.
