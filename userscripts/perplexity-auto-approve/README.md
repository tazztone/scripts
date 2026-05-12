# Perplexity Auto Approve

A [Violentmonkey](https://violentmonkey.github.io/) userscript that automatically clicks the **Approve** button on Perplexity agent action cards.

Perplexity's agentic features (GitHub integrations, file operations, etc.) occasionally pause to ask for user approval before executing an action. This script detects those cards and clicks Approve after a short configurable delay.

## Requirements

- Firefox (or any Chromium browser) with [Violentmonkey](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/) installed
- A Perplexity account with agent/tool features enabled

## Installation

1. Install [Violentmonkey](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
2. Click **New Script** in the Violentmonkey dashboard
3. Paste the contents of [`perplexity-auto-approve.user.js`](perplexity-auto-approve.user.js)
4. Save (`Ctrl+S`)

Or use the raw URL directly in Violentmonkey's "Install from URL" option:

```
https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/perplexity-auto-approve/perplexity-auto-approve.user.js
```

## Configuration

All options are at the top of the script:

| Variable | Default | Description |
|---|---|---|
| `AUTO_APPROVE_ENABLED` | `true` | Set to `false` to disable without uninstalling |
| `CLICK_DELAY_MS` | `1500` | Delay in ms before clicking — gives you time to intervene |
| `APPROVE_ONLY_IF_CARD_CONTAINS` | `[]` | Optional list of strings; only approves if the card text matches one. Empty = approve all. |

### Restrict to specific actions

To only auto-approve certain operations, set `APPROVE_ONLY_IF_CARD_CONTAINS`:

```js
const APPROVE_ONLY_IF_CARD_CONTAINS = ["Merge PR", "push files"];
```

The match is case-insensitive and checks the full text of the card container.

## How it works

1. A `MutationObserver` watches the entire document for DOM changes (Perplexity is a React SPA — approval cards appear dynamically, not on page load)
2. When a `<button>` or `[role="button"]` whose text is exactly `"Approve"` appears, it is detected
3. After `CLICK_DELAY_MS` the button is clicked programmatically
4. Each button is marked with `data-px-auto-clicked` to prevent double-clicks

## Selector note

The script currently matches buttons by **text content** (`"Approve"`), which is the most resilient approach against React's hashed/generated class names. If Perplexity adds a stable `data-testid` or `aria-label` to the button in the future, update `findApproveButton()` to use that for extra precision.

## Safety

- The `CLICK_DELAY_MS` window lets you scroll up and manually click **Deny** before the script fires
- Use `APPROVE_ONLY_IF_CARD_CONTAINS` to whitelist only operations you trust
- Set `AUTO_APPROVE_ENABLED = false` or disable the script in Violentmonkey to pause without uninstalling

## License

MIT — see [LICENSE](../../LICENSE).
