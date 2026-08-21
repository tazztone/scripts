# Hugging Face Inline Liking, Unliked Model Highlighter, Date & Negative Filter

A clean, high-performance userscript for Hugging Face (`https://huggingface.co/models` and user/organization model lists) that lets you like or unlike model cards inline, highlights unliked models with a glowing green border, filters models by client-side **Date Range Slider**, and excludes unwanted models via a **Negative Text / Keyword Filter**.

![Hugging Face inline liking, unliked model highlighter, and date filter](Screenshot.webp)

## 🚀 Installation

Requires Violentmonkey (or a compatible userscript manager):
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
- [Chrome / Brave](https://chromewebstore.google.com/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT (v2.0.2)**](https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/huggingface/huggingface-heart.user.js?v=2.0.0)

---

## ⚡ Features

1. **💚 Unliked Model Highlighter**: Adds a distinct emerald green border (`#10b981`) with soft glow around unliked models in search and listing cards.
2. **❤️ Inline Model Liking**: Click or keyboard-activate the heart/count area on a model card to like or unlike it without opening the model page. The native Hugging Face heart appearance is preserved and failed requests roll back immediately with non-blocking toast alerts.
3. **🔎 Dynamic Liked State Detection**: Detects native outline and filled heart states and updates the green card border as cards load or change.
4. **🚫 Negative Text / Keyword Filter**: Hide unwanted models by typing keywords or regex patterns (e.g. `gguf, fp8, /test.*/i`). Includes live 120ms debounced filtering, a quick clear (`✕`) button, and an independent toggle switch.
5. **📅 Date Range Slider Filter**: Restrict models by update age using interactive sliders, numeric min/max day inputs, and quick presets (`24h`, `3d`, `7d`, `14d`, `30d`, `60d`, `90d`, `180d`, `1y`, `All`).
6. **🛡️ Encapsulated Shadow DOM Sidebar Widget & Collapsible Bar**:
   - **Collapsible / Compact Design**: Click the header or press `Alt+F` to collapse into a slim 34px bar showing active filter pills (`🚫 qwen3.`, `📅 ≤180d`, `Showing 13/30`).
   - **Ultra-Condensed Layout**: >60% vertical height reduction when expanded.
   - **One-Click Reset (`↺`)**: Instantly resets all filters back to default.
   - **Smart Sidebar Docking**: Docks into Hugging Face's left sidebar on `/models` and functions everywhere with full settings access.
7. **⚡ INP & Yield Protection**: Asynchronous chunked DOM processing with `requestAnimationFrame`, `scheduler.yield()`, date caching via `dataset`, and Run-ID cancellation guards for zero UI jank during infinite scrolling.

---

## 🚀 Instant Auto-Installer Tool & Auto-Updates

### 1. Direct Install Link
Install directly via your userscript manager using the raw GitHub link above.

### 2. Automatic Background Updates (`@updateURL`)
The script includes embedded `@updateURL` and `@downloadURL` metadata headers. Violentmonkey, Tampermonkey, and ScriptCat will check GitHub automatically in the background and keep your installed userscript updated without requiring manual reinstalls.

---

## ⚙️ Configuration & Persistence

You can customize negative keywords, date filtering, and highlighter options directly inside the widget:

| Key | Default Value | Description |
| :--- | :--- | :--- |
| `FILTER_EXCLUDE_ENABLED` | `true` | Enable negative text/keyword filtering. |
| `FILTER_EXCLUDE_TERMS` | `''` | Comma-separated keywords or `/regex/` patterns to exclude. |
| `BORDER_UNLIKED_ENABLED` | `true` | Enable green border highlighting around unliked models. |
| `BORDER_UNLIKED_COLOR` | `'#10b981'` | Border color for unliked model cards. |
| `BORDER_UNLIKED_GLOW` | `true` | Enable soft box-shadow glow around unliked model cards. |
| `DATE_FILTER_ENABLED` | `false` | Enable client-side date range filtering. |
| `DATE_MIN_DAYS` | `0` | Minimum update age in days (0 = Today). |
| `DATE_MAX_DAYS` | `30` | Maximum update age in days. |
| `DATE_PRESET` | `'all'` | Selected quick preset (`24h`, `3d`, `7d`, `14d`, `30d`, `60d`, `90d`, `180d`, `1y`, `all`). |
| `WIDGET_COLLAPSED` | `false` | Collapsed state of the filter widget (toggled by header or `Alt+F`). |

> [!NOTE]
> All settings and configuration options are saved **permanently** via `GM_setValue` / `GM_getValue` in userscript storage and persist indefinitely across browser sessions and site reloads.

---

## 🧪 Development Checks

```bash
node --check huggingface-heart.user.js
pytest tests/test_userscript.py
```
