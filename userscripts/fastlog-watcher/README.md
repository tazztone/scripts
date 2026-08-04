# Fastlog Gebraucht & Geprüft: Product Watcher & Multi-Channel Alert Engine

Automated userscript for shop.fastlog.ch that continuously monitors the "Gebraucht & Geprüft" category feed for newly added items and dispatches real-time alerts via Discord Webhooks, Telegram Bots, or desktop notifications.

## 🚀 Installation

Requires Violentmonkey (or a compatible userscript manager):
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
- [Chrome / Brave](https://chromewebstore.google.com/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT (v1.0.1)**](https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/fastlog-watcher/fastlog-watcher.user.js)

---

## ⚡ Features

1. **⚡ Dual Feed & HTML Parsing Engine**: Primary data extraction runs via the lightweight WooCommerce RSS XML feed (`/product-category/gebraucht-geprueft/feed/`), with a full DOM HTML scraper fallback for maximum reliability.
2. **📢 Discord Webhook Integration**: Delivers rich Discord embed alerts with product title, direct link, price info, and timestamp straight to your preferred Discord channel.
3. **🤖 Telegram Bot Notifications**: Formatted Markdown messages pushed directly to your Telegram chat using Telegram Bot API.
4. **🔔 Desktop & In-Browser Notifications**: Triggers native `GM_notification` alerts when new products arrive while browsing.
5. **⏰ Background & ScriptCat Cron Support**: Compatible with `@crontab */15 * * * *` background execution in ScriptCat or periodic background intervals in Violentmonkey / Tampermonkey.
6. **⚙️ In-Browser Configuration Menu**: Interactively configure your Telegram Token, Chat ID, or Discord Webhook URL via `GM_registerMenuCommand` directly in your browser's extension menu.

---

## 🚀 Instant Auto-Installer Tool & Auto-Updates

### 1. Direct Install Link
Install directly via your userscript manager using the raw GitHub link above.

### 2. Automatic Background Updates (`@updateURL`)
The script includes embedded `@updateURL` and `@downloadURL` metadata headers. Violentmonkey, Tampermonkey, and ScriptCat will check GitHub automatically in the background and keep your installed userscript updated without requiring manual reinstalls.

---

## ⚙️ Configuration & Persistence

Access configuration commands through your userscript manager menu (Violentmonkey / Tampermonkey / ScriptCat extension popup):

- **🔍 Jetzt nach neuen Produkten suchen**: Manually triggers an immediate feed check and alerts you of any newly discovered items.
- **📢 Discord Webhook URL einstellen**: Configure your Discord channel Webhook URL.
- **⚙️ Telegram Bot Token einstellen**: Enter your BotFather HTTP API token.
- **💬 Telegram Chat ID einstellen**: Set your personal or group Telegram Chat ID.

> [!NOTE]
> All settings, seen product histories, and API webhooks are saved **permanently** via `GM_setValue` / `GM_getValue` in userscript storage and persist indefinitely across browser sessions and site reloads.
