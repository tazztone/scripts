# Perplexity Enhancements - Research Log

This script combines model locking, agent-action approval, and GitHub connector enablement behind one observer and settings surface.

## 1. Model selector

- Anchor on the visible prompt `textarea`; search its nearest form/container for a visible model button.
- Use model words (`Best`, `Sonar`, `GPT-`, `Gemini`, `Claude`) and menu/chevron semantics as positive signals.
- Exclude attachment, GitHub, focus, search, voice, send, and small circular buttons.
- Dropdowns may render in a portal. Search visible `[role="menuitem"]`, `[role="option"]`, `[role="menuitemcheckbox"]`, buttons, and known `.dropdown-item` elements.
- Ignore disabled, locked, translucent Max-tier options.

## 2. Thinking switch

- Locate a visible row containing `Thinking` but not a model name.
- Prefer `button[role="switch"]`, then checkbox or `[aria-checked]` descendants.
- Read `aria-checked` or `.checked` and click only when it differs from the configured target.

## 3. Approval cards

- Search visible `button` and `[role="button"]` elements whose normalized text starts with an approved action word (`approve`, `confirm`, or `allow`).
- Skip disabled and already processed elements.
- Each element receives one timer in a `Map`, a progress bar, and hover-to-pause listeners.
- Timers clean themselves up when the element disappears, is already clicked, or the feature is disabled.

## 4. GitHub connector

- Active state is detected from GitHub connector pills, active connector images, or the known GitHub SVG path.
- The preferred action is a small exact-match suggestion pill such as `+ GitHub` or `Enable GitHub`.
- Require a dashed border or plus icon, exclude active connector pills, and exclude wide follow-up rows.
- A route-scoped cooldown prevents repeated attempts while the UI transitions.

## 5. Lifecycle and event handling

- Use complete pointer/mouse click event chains for React/Radix controls.
- Use one child-list/subtree `MutationObserver` with a 150 ms debounce; script-owned attributes are not observed.
- Use the Navigation API when available and URL detection in the shared observer as the fallback.
- Reset model and connector locks on route changes and retain a 5-second safety interval.
- DOM changes made by the script are idempotent and do not create duplicate controls or timers.

## 6. Storage and migration

- Canonical keys use the `px_enhancements_` prefix and are written to both userscript storage and page localStorage.
- Existing page-localStorage keys under `px_model_lock_` and `px_auto_approve_` are migrated on first read.
- Separate userscript managers generally isolate GM storage by script, so legacy GM values cannot be reliably read by the replacement script; this limitation is documented for users.
