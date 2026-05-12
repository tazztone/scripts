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
- **Target Elements**: Document the exact selectors used. Provide Primary and Fallback options (e.g., check `aria-label`, then specific SVG paths, then text node content).
- **Visual Detection**: Note the specific visual heuristics (e.g., "Dashed borders usually denote suggestion pills").
- **Inclusions & Exclusions**: Explicitly define what NOT to click or interact with (e.g., "Ignore full-width elements as they are search suggestions, not buttons").
- **Application State**: How to handle SPAs? (e.g., resets on `location.href` change, `MutationObserver` cooldowns).

### Automated Extraction (Agent-Assisted)
If the target leverages heavy dynamic AJAX rendering or cookie-guarded sessions that block static fetching:
- **Headless Execution**: Do not waste time brute-forcing raw HTTP headers. Use a headless engine (like Playwright) to perform a live render and dump the DOM.
- **Bypass Constraints**: Use raw JS evaluation (`document.querySelector().click()`) during verification runs to force interactions past hidden responsive overlaps.
- **Centralized Tooling**: Maintain a shared `venv` containing automated extraction libraries in the root `/userscripts/` folder to optimize analysis speed and avoid bloat.

---

## 2. Implementation Architecture

Structure your `.user.js` files strictly as follows:

### Metadata Block
Use comprehensive headers compatible with standard engines:
```javascript
// ==UserScript==
// @name         [Descriptive Name]
// @namespace    https://github.com/tazztone/scripts
// @version      0.1.0
// @description  [Action-oriented description]
// @author       tazztone
// @match        [Match specific URLs]
// @run-at       document-idle
// @grant        none
// @noframes
// ==/UserScript==
```

### Component Separation
1.  **CONFIG**: A clear constant object at the top for user tuning.
2.  **STYLES**: CSS injected via code for UI additions (e.g., countdown bars, indicator dots).
3.  **UTILITIES**: Standardized helpers for DOM parsing (`isVisible`, `normalize`).
4.  **CORE LOGIC**: Feature-centric logic functions (e.g., `findButtons`, `performAction`).
5.  **ORCHESTRATION**: A debounced `MutationObserver` governing the `run()` loop to handle dynamic SPAs without thrashing.

### Resiliency Principles
- **Visibility Verification**: Always check `getBoundingClientRect().width > 0` and computed styles (`display`, `visibility`, `opacity`) before interacting. Be extra vigilant on responsive sites which often duplicate elements (e.g., one for Desktop, one for Mobile).
- **Event Fidelity**: For modern UI libraries (React, Radix), simple `.click()` might fail. Fire complete chains of events (e.g., `PointerEvent` + `MouseEvent`) for hovers and clicks.
- **Locks and Cooldowns**: Use flag locks (`isAttempting`, `cooldown`) when handling multi-step menu sequences or dynamic insertion to prevent infinite loop traps.
- **State Resets**: Monitor `location.href` in the main loop and clear logic locks/state trackers when URL changes, supporting Single Page Applications navigation.

---

## 3. Advanced Framework Integration

Leverage modern UserScript APIs for smoother operations:

### Reliable SPA Navigation
Instead of manually checking `location.href` in polling loops, use explicit event hooks for navigation events:
```javascript
if (self.navigation) {
  navigation.addEventListener('navigatesuccess', handleUrlChange);
} else {
  // Fallback observer for browsers/contexts without Navigation API
  let lastPath = location.href;
  new MutationObserver(() => {
    if (lastPath !== location.href) {
      lastPath = location.href;
      handleUrlChange();
    }
  }).observe(document, { subtree: true, childList: true });
}
```

### Persistent Storage & Networking
When your script needs cross-page data memory or bypassing CORS:
- **Headers**: Must add `@grant GM_setValue`, `@grant GM_getValue`, or `@grant GM_xmlHttpRequest`.
- **Storage**: Use `GM_setValue(key, value)` and `GM_getValue(key, defaultValue)` for user preferences that survive sessions.
- **Async Network**: Modern engines support async fetching: `const res = await GM.xmlHttpRequest({ url });`.

---

## 4. Documentation Standard

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
