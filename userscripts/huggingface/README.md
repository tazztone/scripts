# Hugging Face Yellow Hearts & Model Date Range Filter

A feature-rich userscript for Hugging Face (`https://huggingface.co/models`) that adds client-side **Date Range Slider filtering**, highlights unliked models with a glowing green border and yellow outline heart, shows native red hearts for liked models, and enables direct inline model liking from list cards.

![Hugging Face Unliked Model Highlighter & Inline Liking](Screenshot.webp)

## Features

- **Date Range Slider Filter**: Restrict models by update age using interactive sliders, numeric min/max day inputs, and quick presets (`24h`, `3d`, `7d`, `14d`, `30d`, `60d`, `90d`, `180d`, `1y`, `All`).
- **Sidebar Widget & Live Status**: Injects a native-styled filter widget into the left sidebar showing exact date range labels and live model counters (`Showing X / Y models`).
- **Unliked Model Highlighter**: Adds a distinct emerald green border (`#10b981`) with soft glow around unliked models in search and listing cards.
- **Yellow Outline Unliked Hearts**: Unliked model heart icons stand out with a customizable golden yellow outline (`#fbbf24`).
- **Native Red Liked Hearts**: Liked models display with HF native red filled hearts (`#ef4444`) and clean borders.
- **Direct Inline Liking**: Click the heart icon on any model card in the list to instantly like/unlike the model inline without opening its page.
- **Micro-animations**: Magnifies unliked heart icons on hover with drop-shadow glow effects.
- **Configurable Floating FAB**: Interactive settings modal (FAB at bottom-right) allows customizing colors, scales, date filter options, and toggling borders on/off.
- **Single Page Application Resiliency**: Uses debounced MutationObservers and CSS rules to handle dynamic page transitions and infinite scroll seamlessly.

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

You can customize date filtering, scaling, colors, and behaviors using the floating gear icon in the bottom right corner or the left sidebar widget, or by editing the `CONFIG` object at the top of the script:

| Key | Default Value | Description |
| :--- | :--- | :--- |
| `DATE_FILTER_ENABLED` | `false` | Enable client-side date range filtering. |
| `DATE_MIN_DAYS` | `0` | Minimum update age in days (0 = Today). |
| `DATE_MAX_DAYS` | `30` | Maximum update age in days. |
| `DATE_PRESET` | `'all'` | Selected quick preset (`24h`, `3d`, `7d`, `14d`, `30d`, `60d`, `90d`, `180d`, `1y`, `all`). |
| `ENABLED` | `true` | Turn overall heart styling on or off. |
| `COLOR_IDLE` | `'#fbbf24'` | Color of unliked heart SVG outline when idle. |
| `COLOR_HOVER` | `'#f59e0b'` | Color of unliked heart SVG outline when hovered. |
| `SCALE_IDLE` | `1` | Scale multiplier of unliked heart SVG when idle. |
| `SCALE_HOVER` | `1.2` | Scale multiplier of unliked heart SVG when hovered. |
| `BORDER_UNLIKED_ENABLED` | `true` | Enable green border highlighting around unliked models. |
| `BORDER_UNLIKED_COLOR` | `'#10b981'` | Border color for unliked model cards. |
| `BORDER_UNLIKED_GLOW` | `true` | Enable soft box-shadow glow around unliked model cards. |
