# Perplexity Enhancements - Research Log

This script combines model locking, agent-action approval, and GitHub connector enablement behind one orchestrator, isolated Shadow DOM UI, and native Top Layer popovers.

## 1. Model Selector & Thinking Switch

- Anchor on the visible prompt `textarea`; search its nearest form/container for a visible model button.
- Use model words (`Best`, `Sonar`, `GPT-`, `Gemini`, `Claude`) and menu/chevron semantics as positive signals.
- Exclude attachment, GitHub, focus, search, voice, send, and small circular buttons.
- Dropdowns render in portal overlays. Search visible `[role="menuitem"]`, `[role="option"]`, `[role="menuitemcheckbox"]`, buttons, and known `.dropdown-item` elements.
- Exclude the script's own `#px-root` shadow container and disabled/translucent Max-tier options.
- Thinking switch detection identifies the row containing `Thinking` and toggles the inner `role="switch"` or checkbox when the current state differs from configuration.

## 2. Action Approval Cards & Pause Protection

- Search visible `button` and `[role="button"]` elements whose normalized text starts with an approved action word (`approve`, `confirm`, or `allow`).
- Exclude elements inside `#px-root`, disabled controls, and already-clicked elements (`dataset.pxClicked`).
- Each element receives one timer in a `Map`, a top progress bar, and hover-to-pause event listeners (`mouseenter`, `mouseover`, `pointerenter`, `button.matches(':hover')`).
- Timers clean themselves up when the element is removed from DOM, is clicked, or the feature is toggled off.

## 3. GitHub Connector Enablement

- Active state is detected from GitHub connector pills, active connector images, or the known GitHub SVG path.
- The preferred action is a small exact-match suggestion pill such as `+ GitHub` or `Enable GitHub`.
- Require a dashed border or plus icon, exclude active connector pills, and exclude wide follow-up rows.
- A route-scoped cooldown prevents repeated attempts while the UI transitions.

## 4. UI Encapsulation & Top Layer

- Mounts `#px-settings-fab`, `<dialog id="px-settings-dialog" popover="auto">`, and `#px-toast-container` inside `#px-root` with an open Shadow Root.
- Uses native `<dialog popover="auto">` for Top Layer rendering above all host `z-index` stacks and native light-dismiss on Escape and backdrop click.
- Transient non-blocking toasts provide user feedback on settings save and automation actions.
- In-page element styles (`.px-model-lock-indicator`, `.px-progress-bar`) are injected as minimal host styles.

## 5. Lifecycle and Orchestration

- Use complete pointer/mouse click event chains for React/Radix synthetic event managers.
- Use one child-list/subtree `MutationObserver` with a 150 ms debounce; script-owned attributes are not observed.
- Listen to `self.navigation.addEventListener('navigatesuccess')` with URL comparison fallback.
- Reset route-scoped locks on navigation and retain a 5-second safety interval.
- All DOM mutations are guarded and idempotent.

## 6. Storage & Migration

- Canonical keys use the `px_enhancements_` prefix, dual-writing to `GM_setValue` and page `localStorage`.
- Existing page-localStorage keys under `px_model_lock_` and `px_auto_approve_` are migrated automatically on first read.
- Cross-script GM storage is isolated by script managers; migration notes and defaults are documented for users.
