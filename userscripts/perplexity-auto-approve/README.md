# Perplexity Auto Approve

A [Violentmonkey](https://violentmonkey.github.io/) userscript that automatically clicks the **Approve** button on Perplexity agent action cards. It includes safety features like a visual countdown and auto-enables the GitHub connector.

## Features

- **Auto-Approve**: Automatically clicks "Approve" or "Confirm" buttons.
- **Visual Countdown**: A green progress bar appears on the button before it clicks.
- **Hover-to-Pause**: Hovering over the button pauses the countdown (bar turns orange), giving you time to read or manually intervene.
- **GitHub Auto-Enable**: Ensures the GitHub connector is active in your chat session automatically.

## Requirements

- Firefox (or any Chromium browser) with [Violentmonkey](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/) installed
- A Perplexity account with agent/tool features enabled

## Installation

1. Install [Violentmonkey](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
2. Click **New Script** in the Violentmonkey dashboard
3. Paste the contents of [`perplexity-auto-approve.user.js`](perplexity-auto-approve.user.js)
4. Save (`Ctrl+S`)

## Configuration

All options are at the top of the script in the `CONFIG` object:

| Variable | Default | Description |
|---|---|---|
| `AUTO_APPROVE` | `true` | Set to `false` to disable auto-click |
| `AUTO_ENABLE_GITHUB` | `true` | Set to `false` to stop auto-enabling the GitHub connector |
| `CLICK_DELAY_MS` | `3000` | Delay in ms before clicking (3s) |
| `APPROVE_TEXTS` | `['approve', 'confirm']` | Keywords to match on buttons |

## Development & Testing

We use [Playwright](https://playwright.dev/) to test the script against a mock Perplexity DOM.

1. **Install Dependencies**:
   ```bash
   pip install -r tests/requirements.txt
   playwright install chromium
   ```

2. **Run Tests**:
   ```bash
   pytest tests/test_userscript.py
   ```

The tests verify auto-clicking, visual feedback, hover-to-pause logic, and the multi-step connector enablement sequence.

## License

MIT — see [LICENSE](../../LICENSE).
