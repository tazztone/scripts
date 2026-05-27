---
name: userscript-development
description: Build, debug, or refactor robust browser userscripts (Violentmonkey/Tampermonkey). Triggers whenever the user mentions "userscript", "Tampermonkey", "Violentmonkey", "user script", browser automation via JS injection, or wants to automate interactions on a web page using client-side JavaScript. It ensures high reliability against dynamic SPAs, rigorous DOM research, and clean architecture.
---

# Userscript Development

Follow this workflow to create production-grade browser userscripts that are resilient to DOM changes, compatible with modern Single Page Applications (SPAs), and well-documented.

## The Workflow

Always produce or maintain these three core artifacts:

1.  **`RESEARCH_LOG.md`**: Do this first. Document the target site's DOM structure, selectors, behavioral nuances, and edge cases.
2.  **`[name].user.js`**: The script itself. Must follow the architectural standards below.
3.  **`README.md`**: Clear user guide for installation and configuration.

---

## 1. Research-First DOM Analysis

Before writing the main script logic, create or update `RESEARCH_LOG.md`. This ensures robust selection logic that doesn't break on small UI updates.

### Research Structure

Use numbered sections that mirror the script's logical phases:

1. **Trigger & Target Elements**: Document the exact selectors used. Provide Primary and Fallback options (e.g., check `aria-label`, then specific SVG paths, then text node content).
2. **Element Selectors**: Catalog every interactive element the script touches — inputs, buttons, toggles, containers — with primary and fallback selectors.
3. **Exclusion Logic**: Explicitly define what NOT to interact with (e.g., "Ignore full-width elements as they are search suggestions, not buttons"; "Skip elements inside `[aria-hidden='true']` containers").
4. **Event Management**: Document how to reliably trigger actions on the target. Note whether standard `.click()` suffices or if a full `PointerEvent` + `MouseEvent` chain is required (common with Radix/React).
5. **Lifecycle & SPA Behavior**: How does the site handle navigation? Does it reset state on route changes? What mutation patterns trigger re-renders? Document debounce and cooldown requirements.

### Automated Extraction (Agent-Assisted)

If the target site uses heavy dynamic AJAX rendering or cookie-guarded sessions that block static fetching:
- **Headless Execution**: Do not waste time brute-forcing raw HTTP headers. Use a headless engine (like Playwright) to perform a live render and dump the DOM.
- **Bypass Constraints**: Use raw JS evaluation (`document.querySelector().click()`) during verification runs to force interactions past hidden responsive overlaps.
- **Centralized Tooling**: Maintain a shared `venv` containing automated extraction libraries in the root `/userscripts/` folder to optimize analysis speed and avoid bloat.
- **Virtual Environment Maintenance**: OS-level Python upgrades will break virtual environments because internal symlinks redirect to the new interpreter, while existing binary C-extensions remain compiled for the older ABI version. When this occurs, recreate the environment using `uv`:
  ```bash
  uv venv --clear --python <new-version> venv
  uv pip install -r <project>/tests/requirements.txt
  ```

---

## 2. Implementation Architecture

Structure your `.user.js` files strictly as follows.

### Metadata Block

Use comprehensive headers compatible with standard engines:
```javascript
// ==UserScript==
// @name         [Descriptive Name]
// @namespace    https://github.com/tazztone/scripts
// @version      1.0.0
// @description  [Action-oriented description]
// @author       tazztone
// @match        [Match specific URLs]
// @run-at       document-idle
// @grant        none
// @noframes
// ==/UserScript==
```

**Versioning (semver)**: Use `MAJOR.MINOR.PATCH`.
- `PATCH` (1.0.**1**): bug fixes, selector updates, typo corrections.
- `MINOR` (1.**1**.0): new optional features, new CONFIG keys with defaults.
- `MAJOR` (**2**.0.0): breaking changes to CONFIG structure, behaviour reversals, or complete rewrites.

Always bump the version on every commit that touches the `.user.js` file so Violentmonkey/Tampermonkey can offer users an update prompt.

**Grants — required additions**:
- Add `@grant GM_setValue` / `@grant GM_getValue` when using persistent storage.
- Add `@grant GM_xmlHttpRequest` **and** `@connect [hostname]` for every external domain you fetch. Missing `@connect` causes silent request failures even when `@grant` is present.
- Add `@require https://cdn.example.com/lib.min.js` to bundle a trusted external library at install time. **Pin to an exact version** in the URL — never use `@latest` or a major-only alias, as upstream changes can silently break the script. Declare the library's global (e.g., `/* global dayjs */`) as a comment so linters don't flag it as undefined.

### Component Separation & Scope

Place **CONFIG** and **STYLES** constants *outside* the IIFE, directly after the metadata block. This gives users a clear, unfenced area to edit without scrolling into logic. Everything else lives inside the IIFE:

```javascript
// ==UserScript== ... ==/UserScript==

// ─── CONFIG ──────────────────────────────────────────────
const CONFIG = { /* user-tunable values */ };

// ─── STYLES ──────────────────────────────────────────────
const STYLE = ` /* injected CSS */ `;

// ─────────────────────────────────────────────────────────

(() => {
  'use strict';

  // 1. STYLE INJECTION — mount CSS into the page
  // 2. UTILITIES       — isVisible, normalize, log, dispatchClickEvents
  // 3. CORE LOGIC      — feature-centric functions (findButtons, performAction)
  // 4. ORCHESTRATION   — MutationObserver, SPA navigation, bootstrap
})();
```

### Standard Utilities

Every script should include these foundational helpers inside the IIFE:

```javascript
// Debug-gated logging — controlled by CONFIG.DEBUG
const log = (...args) => { if (CONFIG.DEBUG) console.log('[ScriptName]', ...args); };
const err = (...args) => { console.error('[ScriptName] Error:', ...args); };

// Whitespace-normalized, lowercase text for reliable comparisons
const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();

// Comprehensive visibility check — catches hidden duplicates on responsive sites
function isVisible(el) {
  if (!document.contains(el)) return false;
  const style = window.getComputedStyle(el);
  return (
    style.display !== 'none' &&
    style.visibility !== 'hidden' &&
    style.opacity !== '0' &&
    el.getBoundingClientRect().width > 0
  );
}
```

### Resiliency Principles

- **Visibility Verification**: Always check `isVisible()` before interacting. Be extra vigilant on responsive sites which often duplicate elements (e.g., one for Desktop, one for Mobile).
- **Event Fidelity**: For modern UI libraries (React, Radix), simple `.click()` may fail. Fire complete chains of events (`PointerEvent` + `MouseEvent`) for hovers and clicks. Document the required chain in `RESEARCH_LOG.md`.
- **Locks and Cooldowns**: Use flag locks (`isInteracting`) when handling multi-step menu sequences. Use timestamp-based throttles (`lastActionTime`) to enforce cooldowns that survive re-entrant observer callbacks:
  ```javascript
  let lastActionTime = 0;
  function run() {
    if (Date.now() - lastActionTime < CONFIG.COOLDOWN_MS) return;
    // ... perform action ...
    lastActionTime = Date.now();
  }
  ```
- **Processed Markers**: For one-shot actions on dynamically injected elements (modals, cards), mark the element with a `dataset` attribute immediately to prevent duplicate processing. This is critical for idempotency:
  ```javascript
  if (modal.dataset.processed) return;
  modal.dataset.processed = 'true';
  ```
- **State Resets**: Monitor `location.href` and clear logic locks/state trackers when URL changes, supporting SPA navigation.
- **Observer Error Guards**: Wrap the body of every `MutationObserver` callback and the `run()` function in `try/catch`. An uncaught exception inside an observer silently kills it — the script will appear to stop working with no visible error.
- **Safety Interval**: Add a periodic `setInterval(run, 5000)` as a fallback alongside the MutationObserver. Observers can be killed by uncaught errors or edge-case browser behavior; the interval guarantees eventual recovery.
- **Cleanup / Teardown**: When the script should stop operating (e.g., user navigates away from the target path), call `observer.disconnect()` and remove any event listeners. This prevents memory leaks in long-lived SPA sessions.

### User Feedback

Give the user visual confirmation that the script is active and working:

- **Indicator dots**: Append a small glowing `<span>` to the target element (green = locked/active, amber = syncing). Useful for continuous-state scripts.
- **Toast notifications**: For one-shot actions (form fills, auto-clicks), inject a temporary toast with the result. Use `position: fixed`, `z-index: 999999`, `backdrop-filter: blur()`, and slide-in animations for a premium feel.
- Always inject feedback styles via the `STYLE` constant — never inline.

---

## 3. Orchestration Patterns

### Debounced MutationObserver

The primary execution driver. Debounce prevents thrashing on highly dynamic SPAs:

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
observer.observe(document.documentElement, { childList: true, subtree: true });
```

### Reliable SPA Navigation

Use the Navigation API with a MutationObserver fallback for browsers that lack support:

```javascript
function handleUrlChange() {
  log('URL changed:', location.href);
  logicLock = false;
  lastActionTime = 0;
  run();
}

if (self.navigation) {
  navigation.addEventListener('navigatesuccess', handleUrlChange);
} else {
  let lastPath = location.href;
  new MutationObserver(() => {
    if (lastPath !== location.href) {
      lastPath = location.href;
      handleUrlChange();
    }
  }).observe(document, { subtree: true, childList: true });
}
```

### Bootstrap Sequence

Always end the IIFE with:

```javascript
// Primary: reactive observer
observer.observe(document.documentElement, { childList: true, subtree: true });

// Immediate: handle already-present DOM state
run();

// Safety net: periodic fallback if the observer dies
setInterval(run, 5000);
```

---

## 4. Testing

Real scripts should include a `tests/` directory with automated verification:

- **Playwright Tests**: Use a headless browser to load the target page, inject the userscript via `page.addScriptTag()` or `page.evaluate()`, and assert the expected DOM mutations occurred.
- **Selector Validation**: Test that every primary and fallback selector from `RESEARCH_LOG.md` resolves to the expected element on a live page snapshot.
- **Centralized Dependencies**: Keep test dependencies in the shared `/userscripts/venv` environment to avoid per-script bloat.

---

## 5. Documentation Standard

The `README.md` should facilitate quick user onboarding:
- **Installation**: Must provide direct links to the raw script URL for one-click Violentmonkey installs.
  Format: `https://github.com/tazztone/scripts/raw/refs/heads/main/userscripts/[folder]/[name].user.js`
- **Configuration Mapping**: A Markdown table mapping `CONFIG` keys from the script to their descriptions and effects.
- **Testing notes**: Mention verification steps or mock testing environments if applicable.

---

## Example Templates

Refer to the following established standards for implementation patterns:
- `references/example.user.js` for the modular architecture.
- `references/example_research_log.md` for the selector taxonomy.
