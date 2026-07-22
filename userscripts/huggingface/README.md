# Hugging Face Yellow Hearts & Unliked Model Highlighter

A feature-rich userscript for Hugging Face (`https://huggingface.co/models`) that makes heart icons pop out in golden yellow, highlights unliked models with a glowing green border (similar to Toppreise best price highlighter), and enables direct inline model liking from list cards.

## Features

- **Golden Yellow Hearts**: Replaces default grey unliked hearts with a vibrant golden yellow (`#fbbf24`).
- **Unliked Model Highlighter**: Adds a distinct emerald green border (`#10b981`) with soft glow around unliked models in search and listing cards.
- **Direct Inline Liking**: Click the heart icon on any model card in the list to instantly like/unlike the model without opening its page.
- **Enlarged SVGs & Micro-animations**: Magnifies heart icons on hover with drop shadow glow effects.
- **Configurable Floating FAB**: Interactive settings modal allows customizing colors, scales, and toggling borders on/off.
- **Single Page Application Resiliency**: Uses debounced MutationObservers and CSS rules to handle dynamic page transitions and infinite scroll.

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

You can customize the scaling, colors, and behaviors using the floating gear icon in the bottom right corner, or by editing the `CONFIG` object at the top of the script:

| Key | Default Value | Description |
| :--- | :--- | :--- |
| `ENABLED` | `true` | Turn overall heart styling on or off. |
| `COLOR_IDLE` | `'#fbbf24'` | Color of the heart SVG when idle. |
| `COLOR_HOVER` | `'#f59e0b'` | Color of the heart SVG when hovered. |
| `SCALE_IDLE` | `2` | Scale multiplier of the heart SVG when idle. |
| `SCALE_HOVER` | `2` | Scale multiplier of the heart SVG when hovered. |
| `BORDER_UNLIKED_ENABLED` | `true` | Enable green border highlighting around unliked models. |
| `BORDER_UNLIKED_COLOR` | `'#10b981'` | Border color for unliked model cards. |
| `BORDER_UNLIKED_GLOW` | `true` | Enable soft box-shadow glow around unliked model cards. |
