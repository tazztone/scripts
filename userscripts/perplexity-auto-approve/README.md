# Perplexity Auto Approve

A [Violentmonkey](https://violentmonkey.github.io/) userscript that automatically clicks the **Approve** button on Perplexity agent action cards. It includes safety features like a visual countdown and auto-enables the GitHub connector.

<img width="725" height="803" alt="image" src="https://github.com/user-attachments/assets/da5676da-5e95-4328-8df2-eb2389a8e843" />


## Features

- **Automated Clicking**: Clicks "Approve", "Confirm", or "Allow" buttons on action cards.
- **Visual Countdown**: Displays a progress bar on the button before clicking.
- **Hover to Pause**: Hovering over a button pauses the countdown.
- **GitHub Auto-Enable**: Automatically enables the GitHub connector via suggestion pills or the connectors menu.
  - See [RESEARCH_LOG.md](./RESEARCH_LOG.md) for details on the DOM selection logic.

## Requirements

- Violentmonkey installed in your browser:
  - [Firefox](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
  - [Chrome / Brave](https://chrome.google.com/webstore/detail/violent-monkey/jinjaccalgkegednnccohejagnlnfdag)
- A Perplexity account with agent/tool features enabled

## Installation

**One-click install** — open the raw script URL in your browser while Violentmonkey is active:

> [`perplexity-auto-approve.user.js` (raw)](https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/perplexity-auto-approve/perplexity-auto-approve.user.js)

Violentmonkey will detect the `.user.js` file and show an install dialog automatically. Click **Confirm Installation**.

<details>
<summary>Manual install (copy-paste)</summary>

1. Open the Violentmonkey dashboard
2. Click **New Script**
3. Paste the contents of [`perplexity-auto-approve.user.js`](perplexity-auto-approve.user.js)
4. Save (`Ctrl+S`)

</details>

## Configuration

All options are at the top of the script in the `CONFIG` object:

| Variable | Default | Description |
|---|---|---|
| `AUTO_APPROVE` | `true` | Set to `false` to disable auto-click entirely |
| `AUTO_ENABLE_GITHUB` | `true` | Set to `false` to stop auto-enabling the GitHub connector |
| `CLICK_DELAY_MS` | `3000` | Delay in ms before clicking (default: 3 s) |
| `APPROVE_TEXTS` | `['approve', 'confirm', 'allow']` | Button text keywords to match (case-insensitive) |
| `OBSERVER_DEBOUNCE_MS` | `150` | Debounce delay (ms) after a DOM change before running |

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
