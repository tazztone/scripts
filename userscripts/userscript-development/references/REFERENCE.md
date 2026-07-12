# Userscript Development Reference

This document provides detailed architectural guidelines, metadata choices, ScriptCat extensions, and orchestration patterns for building production-grade userscripts.

## Runtime Selection & Scope

Before writing code, decide on the runtime environment:
- **Portable Foreground Script**: Needs page DOM or page context. Ordinary `==UserScript==`.
- **ScriptCat Background / Cron**: Needs persistent or scheduled work without DOM access. Uses `@background` or `@crontab`.
- **ScriptCat Subscription Package**: Needs to install many scripts as one package. Uses `==UserSubscribe==`.

Userscript work usually breaks at the runtime and metadata boundary, not in the page logic. Declare the minimum permissions up front, then debug in the environment where the script actually runs.

---

## Metadata and API Map

Start ordinary page scripts with `==UserScript==`, `@name`, `@namespace`, `@version`, and at least one `@match`.

| Key                                           | Practical rule                                                                         |
| --------------------------------------------- | -------------------------------------------------------------------------------------- |
| `@match`                                      | Default choice for normal host and path matching.                                      |
| `@include` / `@exclude`                       | Use sparingly when `@match` is not expressive enough (legacy/broader pattern cases).   |
| `@grant`                                      | Declare only what the script actually uses so permissions stay readable and minimal.   |
| `@connect`                                    | Prefer explicit hosts first for `GM_xmlhttpRequest` or `GM_cookie`; avoid `*` unless required. |
| `@run-at`                                     | Add only when `document-start`, `document-end`, or `document-idle` timing changes behavior. |

**Versioning (semver)**: Use `MAJOR.MINOR.PATCH`. Keep update metadata simple: `@version` first, then `@updateURL` or `@downloadURL` if the distribution model actually needs them.

---

## ScriptCat Extensions

Use these features when the task goes beyond a normal portable userscript.

### `@background` & `@crontab`
- **Background scripts** are ScriptCat-specific and run in a sandbox **without DOM access**. Use for persistent workers or manager-managed state.
- **Cron scripts** are background scripts for repeated scheduled work. Only the first `@crontab` entry is effective. Prefer standard 5-field cron form. Keep single-run time plus retry delay below the cron interval to prevent overlap.

### Async Completion and `CATRetryError`
- If a ScriptCat background or cron script does async work, it **must return a Promise**.
- Resolve or reject only after the real work is finished. Once settled, ScriptCat considers the run complete.
- To request retry, reject with `new CATRetryError(message, seconds)` (minimum 5 seconds).

### `==UserConfig==` & `==UserSubscribe==`
- Use `==UserConfig==` paired with `GM_getValue` for user-editable settings UIs.
- Use `==UserSubscribe==` for silent bundle installs and updates (requires HTTPS, `user.sub.js`). Subscription `connect` overrides child scripts.

---

## Implementation Architecture

For standard foreground scripts, structure your `.user.js` files strictly as follows:

### Component Separation
Place **CONFIG** and **STYLES** constants *outside* the IIFE. Everything else lives inside the IIFE:

```javascript
// ==UserScript== ... ==/UserScript==

// ─── CONFIG ──────────────────────────────────────────────
const CONFIG = { /* user-tunable values */ };

// ─── STYLES ──────────────────────────────────────────────
const STYLE = ` /* injected CSS */ `;

// ─────────────────────────────────────────────────────────

(() => {
  'use strict';
  // 1. STYLE INJECTION, 2. UTILITIES, 3. CORE LOGIC, 4. ORCHESTRATION
})();
```

### Resiliency Principles

- **Visibility Verification**: Always check `isVisible()` before interacting. Be extra vigilant on responsive sites.
- **Event Fidelity**: For React/Radix, simple `.click()` may fail. Fire complete chains of events (`PointerEvent` + `MouseEvent`).
- **Locks and Cooldowns**: Use flag locks (`isInteracting`) and timestamp-based throttles to enforce cooldowns.
- **Processed Markers**: For one-shot actions on dynamically injected elements, mark the element with a `dataset.processed` attribute to prevent duplicate processing.
- **Observer Error Guards**: Wrap `MutationObserver` callbacks and the `run()` function in `try/catch`. An uncaught exception inside an observer silently kills it.
- **Mutation Loop Avoidance**: When modifying classes, styles, or contents of observed elements from inside a `MutationObserver` callback, those modifications trigger the observer again. Avoid infinite recursion loops by disabling attribute/character observation (`attributes: false, characterData: false`) or checking explicit processed flags to short-circuit.
- **Text Normalization**: When matching text identifiers parsed from distinct DOM elements (e.g. comparing UI filter tags to card labels), normalize names to avoid spacing, casing, and symbol mismatching:
  ```javascript
  const normalize = str => str.toLowerCase().replace(/[^a-z0-9]/g, '');
  ```

### User Feedback
- **Indicator dots**: Append a small glowing `<span>` (green = active, amber = syncing) to target elements.
- **Toast notifications**: Inject a temporary toast for one-shot actions.

---

## Orchestration Patterns

### Debounced MutationObserver & Reliable SPA Navigation
Use a debounced observer to prevent thrashing on SPAs, and combine it with the Navigation API (or a fallback observer) to handle URL changes:

```javascript
let debounceTimer = null;
const observer = new MutationObserver(() => {
  try {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(run, CONFIG.OBSERVER_DEBOUNCE_MS);
  } catch (e) {
    err('Observer error:', e);
  }
});

function handleUrlChange() {
  logicLock = false; lastActionTime = 0; run();
}
if (self.navigation) {
  navigation.addEventListener('navigatesuccess', handleUrlChange);
} // ... fallback observer for older browsers
```

### Bootstrap Sequence
End the IIFE with:
```javascript
observer.observe(document.documentElement, { childList: true, subtree: true });
run();
setInterval(run, 5000); // Safety net fallback
```

---

## Testing & Documentation

- **Debugging**: Debug where the code really runs (Foreground = page console; Background = manager run log).
- **Playwright Tests**: Use a headless browser to load the target page, inject the userscript, and assert DOM mutations.
- **README**: Provide direct installation links and a configuration mapping table.
