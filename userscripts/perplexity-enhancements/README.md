# Perplexity Enhancements

A [Violentmonkey](https://violentmonkey.github.io/) userscript that combines three Perplexity helpers:

- Keeps a configured model and Thinking mode active.
- Counts down and clicks agent action-card approval buttons.
- Enables the GitHub connector from the small suggestion pill when available.

## Installation

Install directly through Violentmonkey:

[`perplexity-enhancements.user.js` (raw)](https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/perplexity-enhancements/perplexity-enhancements.user.js)

Before installing, disable the old `Perplexity Model Lock` and `Perplexity Auto Approve` scripts. The replacement cannot disable scripts already installed in a browser, and running all three would duplicate clicks and UI.

## Configuration

Open the gear button in the bottom-right corner of Perplexity.

| Setting | Default | Description |
|---|---:|---|
| Model lock | On | Re-applies the configured model after Perplexity resets it. |
| Target model | `Claude Sonnet 4.6` | Case-insensitive model label to select. |
| Thinking mode | On | Ensures Thinking matches the selected state. |
| Auto-approve | On | Schedules matching action-card buttons. |
| Auto-enable GitHub | On | Enables a visible GitHub suggestion pill. |
| Approval countdown | 3 seconds | Valid range is 1–30 seconds; hovering pauses it. |

Settings are stored with the `px_enhancements_` prefix in both userscript storage and page localStorage. Legacy page-localStorage values from the two former scripts are migrated automatically. Legacy GM storage is isolated by userscript managers and cannot be migrated reliably across script installations.

## Development and testing

```bash
pip install -r tests/requirements.txt
playwright install chromium
node --check perplexity-enhancements.user.js
pytest tests/test_userscript.py
```

The test configuration stores the Playwright browser under the ignored `userscripts/.playwright-browsers/` directory.

The Playwright suite runs against the integrated mock DOM and covers model recovery, Thinking state, approval timing and pause behavior, duplicate-timer protection, GitHub enablement, settings persistence, and legacy storage migration.

MIT — see [LICENSE](../../LICENSE).
