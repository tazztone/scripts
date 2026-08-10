# Hugging Face Unliked Model Highlighter & Date Filter

A clean, high-performance userscript for Hugging Face (`https://huggingface.co/models` and user/organization model lists like `https://huggingface.co/lightx2v/models`) that highlights unliked models with a glowing green border and adds client-side **Date Range Slider filtering**.

![Hugging Face Unliked Model Highlighter & Date Filter](Screenshot.webp)

## Features

- **Unliked Model Highlighter**: Adds a distinct emerald green border (`#10b981`) with soft glow around unliked models in search and listing cards.
- **Dynamic Liked State Detection**: Real-time heart detection that updates immediately when you like or unlike models without needing page reloads.
- **Date Range Slider Filter**: Restrict models by update age using interactive sliders, numeric min/max day inputs, and quick presets (`24h`, `3d`, `7d`, `14d`, `30d`, `60d`, `90d`, `180d`, `1y`, `All`).
- **Unified Sidebar Widget**: Injects a native-styled filter widget into the left sidebar showing exact date range labels, live model counters (`Showing X / Y models`), and expandable **Highlighter Options** (color picker, glow toggle, highlight switch).
- **Performance Optimized**: MutationObserver feedback shielding and debounced storage IO for zero lag during slider dragging and infinite scroll.

## Requirements

Requires Violentmonkey (or a compatible userscript manager):
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
- [Chrome / Brave](https://chromewebstore.google.com/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)

## Installation

**One-click install** — open the raw script URL in your browser while Violentmonkey is active:

> [`huggingface-heart.user.js` (raw)](https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/huggingface/huggingface-heart.user.js)

Violentmonkey will detect the `.user.js` file and show an install dialog automatically. Click **Confirm Installation**.

<details>
<summary>Manual install (copy-paste)</summary>

1. Open the Violentmonkey dashboard
2. Click **New Script**
3. Paste the contents of [`huggingface-heart.user.js`](huggingface-heart.user.js)
4. Save (`Ctrl+S`)

</details>

## Configuration

You can customize both date filtering and highlighter options directly inside the left sidebar widget under **Highlighter Options**:

| Key | Default Value | Description |
| :--- | :--- | :--- |
| `BORDER_UNLIKED_ENABLED` | `true` | Enable green border highlighting around unliked models. |
| `BORDER_UNLIKED_COLOR` | `'#10b981'` | Border color for unliked model cards. |
| `BORDER_UNLIKED_GLOW` | `true` | Enable soft box-shadow glow around unliked model cards. |
| `DATE_FILTER_ENABLED` | `false` | Enable client-side date range filtering. |
| `DATE_MIN_DAYS` | `0` | Minimum update age in days (0 = Today). |
| `DATE_MAX_DAYS` | `30` | Maximum update age in days. |
| `DATE_PRESET` | `'all'` | Selected quick preset (`24h`, `3d`, `7d`, `14d`, `30d`, `60d`, `90d`, `180d`, `1y`, `all`). |
