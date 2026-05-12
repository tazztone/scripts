# Perplexity Connector Logic - Research Log

This document details the DOM structure and selection strategies used to automate the GitHub connector enablement on Perplexity.

## 1. Triggering the Menu (The "+" Button)
**Selector**: `button[aria-label="Add files or tools"]`
**Fallback**: `button[aria-label^="Add"][aria-haspopup="menu"]` or `button:has(svg path[d*="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"])`.

**Findings**:
- The button consistently has a `plus` icon but the `aria-label` has evolved from "Attach" to "Add" to "Add files or tools".
- It is a trigger for a Radix-based menu.

## 2. Suggestion Pills (Reactive Enablement)
**Logic**: Find a button containing "GitHub" that is NOT an active connector and NOT a search suggestion.

**Selection Criteria**:
- **Include**: Buttons containing "github" (case-insensitive).
- **Exclude (Active)**: Buttons with `aria-haspopup="menu"` or `aria-expanded`. These are active connectors; clicking them opens settings.
- **Exclude (Follow-ups)**: Buttons inside containers with "Follow-ups" text or those with broad suggestion classes (`interactable w-full`).

## 3. Menu Sequence (The Fallback)
**Steps**:
1. Click the "+" button.
2. Find "Connectors and sources".
    - **Selector**: `[role="menuitem"]` or `div` containing "Connectors".
    - **Note**: Use the shortest matching text to avoid containers.
3. Hover/Enter to open the flyout.
    - **Event**: Requires `PointerEvent` (`pointerenter`, `pointermove`) + `MouseEvent` (`mouseenter`) for React synthetic event compatibility.
4. Find the GitHub toggle.
    - **Selector**: `[role="menuitemcheckbox"]` or `div` containing "GitHub".
    - **State Check**: Verify `aria-checked="false"` before clicking to avoid disabling an already enabled connector.

## 4. Active State Detection
**Selectors**:
- `button[aria-label="GitHub"]` (The pill in the input box).
- `img[alt="GitHub"]` or `img[src*="github.webp"]`.
- Any `button` containing "GitHub" with `aria-haspopup="menu"`.

## 5. Implementation Notes
- **MutationObserver**: Logic is triggered by DOM changes but gated by a 2-second cooldown (`connectorLogicLock`) to prevent infinite loops during menu transitions.
- **SPA Resilience**: The `githubEnableAttempted` flag is reset on `location.href` change to handle single-page navigation.
