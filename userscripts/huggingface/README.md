# Hugging Face Yellow Hearts

A lightweight, zero-JS-observer userscript to make the heart/like icons on the Hugging Face models page larger, pop out in a warm golden yellow, and feature premium micro-animations.

## Features

-   **Golden Yellow Themes**: Replaces default grey unliked hearts with a vibrant golden yellow (`#fbbf24`).
-   **Enlarged SVGs**: Increases the heart size by 35% by default.
-   **Pop-Out Hover Effect**: Magnifies the heart to 1.6x on hover and adds a beautiful, warm glowing drop shadow.
-   **Zero Performance Impact**: Leverages pure CSS injection and modern CSS `:has()` selector matching against the SVG path. Does not use JavaScript `MutationObserver` loops, avoiding CPU thrashing.
-   **Single Page Application Resiliency**: Since styling is applied via browser CSS matching, it naturally handles dynamic page transitions and lazy loaded elements instantly.

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

You can customize the scaling, colors, and behaviors by editing the `CONFIG` object at the top of the script:

| Key | Default Value | Description |
| :--- | :--- | :--- |
| `ENABLED` | `true` | Turn the script on or off. |
| `COLOR_IDLE` | `'#fbbf24'` | Color of the heart SVG when idle (CSS color). |
| `COLOR_HOVER` | `'#f59e0b'` | Color of the heart SVG when hovered. |
| `SCALE_IDLE` | `'1.35'` | Scale multiplier of the heart SVG when idle. |
| `SCALE_HOVER` | `'1.6'` | Scale multiplier of the heart SVG when hovered. |
