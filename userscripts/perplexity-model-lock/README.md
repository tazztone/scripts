# Perplexity Model Lock

A production-grade, highly resilient Violentmonkey/Tampermonkey userscript for Perplexity.ai that automatically locks the active AI model to **Claude Sonnet 4.6** and ensures **Thinking** mode is enabled.

Perplexity frequently resets the active model back to a platform default (like "Best") during page transitions, new threads, or session updates. This script detects those changes reactively and silently restores your exact configuration.

## Requirements

Requires Violentmonkey (or a compatible userscript manager):
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/violentmonkey/)
- [Chrome / Brave](https://chromewebstore.google.com/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)

---

## Direct Installation

Click the link below to load and install the script automatically in your userscript manager:

👉 [Install Perplexity Model Lock](https://github.com/tazztone/scripts/raw/refs/heads/main/userscripts/perplexity-model-lock/perplexity-model-lock.user.js)

---

## Features

- **Seamless Model Locking**: Locks selections to Claude Sonnet 4.6 (or any model configured).
- **Thinking Mode Enforcement**: Ensures the new reasoning/thinking capability is turned ON.
- **SPA Resiliency**: Fully responsive to Single Page Application navigation and thread changes.
- **Visual Feedback**: Appends a premium glowing indicator dot (🟢 Green when Locked, 🟠 Amber when Syncing) inside the model selector button so you know at a glance it's active.
- **Loop Prevention**: Implements interaction locking and debounced `MutationObserver` cooldowns to avoid interface thrashing or multi-click loops.

---

## Configuration

You can easily modify the script's behavior by editing the `CONFIG` object at the top of the userscript:

| Key | Default Value | Description |
| :--- | :--- | :--- |
| `TARGET_MODEL` | `'Claude Sonnet 4.6'` | Case-insensitive name of the model you wish to lock to (e.g. `Gemini 3.1 Pro`). |
| `ENABLE_THINKING` | `true` | Set to `true` to ensure Thinking mode is enabled. |
| `OBSERVER_DEBOUNCE_MS` | `150` | Debounce delay in milliseconds before the script reacts to DOM changes. |
| `COOLDOWN_MS` | `3000` | Cooldown period after selecting/locking to avoid infinite click recursion. |
| `DEBUG` | `true` | Enables/disables rich logging to the developer console. |

---

## Operational Mechanics

The script executes within an IIFE and utilizes a reactive state engine:
1. **Detection**: Listens to mutations on the document subtree. When changes stop, it locates the active model button.
2. **Evaluation**: Compares the button's text against `CONFIG.TARGET_MODEL` and the "Thinking" keyword. If they match, the active visual indicator glows green, and the script goes to sleep.
3. **Execution**: If the state is incorrect, the script:
   - Sets a temporary execution lock.
   - Dispatches a mouse/pointer event chain to open the selector menu.
   - Reactively toggles the "Thinking" Radix switch if disabled.
   - Clicks the target model row to select it, which automatically closes the menu.
   - Starts a 3-second cooldown to let the Perplexity server commit the state change.
