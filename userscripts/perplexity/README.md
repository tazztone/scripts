# Perplexity Enhancements: Model Lock, Auto-Approve & GitHub Connector

All-in-one productivity suite for Perplexity AI that locks your preferred LLM model & Thinking mode, automates agent action-card approvals with pause protection, and enables GitHub connectors.

## 🚀 Installation

Requires Violentmonkey (or a compatible userscript manager):
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
- [Chrome / Brave](https://chromewebstore.google.com/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT (v1.1.0)**](https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/perplexity/perplexity-enhancements.user.js)

> [!IMPORTANT]
> Before installing, disable old standalone `Perplexity Model Lock` or `Perplexity Auto Approve` scripts if previously installed. Running multiple scripts simultaneously can duplicate click events.

---

## ⚡ Features

1. **Model Lock & Thinking Mode**: Automatically keeps your preferred model (e.g. `Claude Sonnet 4.6`) and Thinking toggle selected, instantly recovering if Perplexity resets it during chats.
2. **Safe Action-Card Auto-Approval**: Visually counts down and clicks "Approve", "Confirm", or "Allow" buttons on agent cards. Hovering over the button instantly pauses the timer.
3. **Automatic GitHub Connector Enablement**: Detects and activates the GitHub connector suggestion pill when working with repository actions.
4. **Shadow DOM & Native Top Layer Encapsulation**: All injected UI (FAB, settings dialog, toasts) runs in an isolated Shadow Root (`#px-root`) with `<dialog popover="auto">` ensuring top-layer elevation without z-index conflicts or page CSS leaks.

---

## 🚀 Instant Auto-Installer Tool & Auto-Updates

### 1. Direct Install Link
Install directly via your userscript manager using the raw GitHub link above.

### 2. Automatic Background Updates (`@updateURL`)
The script includes embedded `@updateURL` and `@downloadURL` metadata headers. Violentmonkey, Tampermonkey, and ScriptCat will check GitHub automatically in the background and keep your installed userscript updated without requiring manual reinstalls.

---

## ⚙️ Configuration & Persistence

Click the floating **Gear Icon (⚙️)** in the bottom-right corner of Perplexity to open the settings panel:

| Setting | Default | Description |
|---|---:|---|
| Model lock | `On` | Re-applies the configured model after Perplexity resets it. |
| Target model | `Claude Sonnet 4.6` | Case-insensitive model label to select. |
| Thinking mode | `On` | Ensures Thinking mode switch matches the desired state. |
| Auto-approve | `On` | Schedules matching action-card approval buttons. |
| Auto-enable GitHub | `On` | Enables a visible GitHub suggestion pill. |
| Approval countdown | `3` seconds | Valid range is 1–30 seconds; hovering over button pauses the timer. |

> [!NOTE]
> All settings and configuration options are saved **permanently** via `GM_setValue` / `GM_getValue` dual-synced to domain `localStorage` under `px_enhancements_` and persist indefinitely across browser sessions and site reloads. Legacy settings from former scripts are migrated automatically.

---

## 🛠️ Development and Testing

```bash
# Run syntax verification
node --check perplexity-enhancements.user.js

# Run automated Playwright test suite
pytest tests/test_userscript.py
```
