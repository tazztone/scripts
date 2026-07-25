# Userscript Development Reference

Implementation patterns for the workflow in `SKILL.md`. Workflow steps and completion criteria live there; runtime, DOM, storage, orchestration, and test patterns live here.

## Runtime and metadata

Choose one runtime before writing page logic:

- **Portable foreground** — ordinary `==UserScript==`; has page DOM access.
- **ScriptCat background/cron** — no DOM access; use `@background` or `@crontab` for persistent or scheduled work.
- **ScriptCat subscription** — use `==UserSubscribe==` only for a distributable bundle.

```javascript
// ==UserScript==
// @name         Example Userscript
// @namespace    https://example.com/userscripts
// @version      1.0.0
// @match        https://example.com/*
// @run-at       document-idle
// @grant        GM_getValue
// @grant        GM_setValue
// @noframes
// ==/UserScript==
```

Metadata rules:

- Use the narrowest correct `@match`; use `@include`/`@exclude` only when `@match` is insufficient.
- Declare only APIs the implementation calls; add explicit `@connect` hosts for `GM_xmlhttpRequest` or `GM_cookie`.
- Pin exact `@require` versions.
- Use semver; add `@updateURL`/`@downloadURL` only when the distribution path needs them.
- Keep user-tunable `CONFIG` and `STYLES` outside the IIFE; keep runtime implementation inside.

ScriptCat-specific rules:

- Background and cron scripts have no DOM access.
- Async work must return a `Promise` that settles only after real work finishes.
- Retry with `new CATRetryError(message, seconds)`; keep retry delay plus work duration below the cron interval.
- `==UserConfig==` pairs with `GM_getValue` for manager-provided settings; `==UserSubscribe==` requires HTTPS distribution.

## Foreground module shape

```javascript
const DEFAULTS = { /* user-tunable defaults */ };
const STYLES = `/* injected styles */`;

(() => {
  'use strict';
  // 1. style injection
  // 2. storage/configuration
  // 3. normalization/visibility/event adapters
  // 4. feature state transitions
  // 5. timers and one-shot effects
  // 6. settings UI
  // 7. one shared orchestrator
})();
```

Feature modules expose narrow operations (`runModelLock()`, `runAutoApprove()`). They do not create competing observers or intervals.

## DOM discovery and event adapters

Use ranked heuristics rather than one brittle selector:

1. Stable semantic or structural anchor.
2. Accessible role, label, or test identifier.
3. Normalized text as a constrained fallback.

Exclude the script's own root (`#px-settings-modal` or equivalent) before broad page scans so settings controls cannot be mistaken for domain controls.

**Visibility** — reject detached, hidden, transparent, or zero-size elements:

```javascript
function isVisible(element) {
  if (!element || !document.contains(element)) return false;
  const style = getComputedStyle(element);
  const rect = element.getBoundingClientRect();
  return style.display !== 'none'
    && style.visibility !== 'hidden'
    && style.opacity !== '0'
    && rect.width > 0
    && rect.height > 0;
}
```

**Card anchor resolution** — the card itself may be the `<a>`:

```javascript
const link = card.tagName === 'A' ? card : card.closest('a[href]') || card.querySelector('a[href]');
```

**Text normalization** — apply before any string comparison:

```javascript
const normalize = value => String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
```

**Event dispatch** — when `.click()` is unreliable on React/Radix, dispatch a full pointer/mouse sequence:

```javascript
function dispatchClickEvents(element) {
  if (!element) return;
  [
    new PointerEvent('pointerdown', { bubbles: true, cancelable: true }),
    new PointerEvent('pointerup',   { bubbles: true, cancelable: true }),
    new MouseEvent('mousedown',     { bubbles: true, cancelable: true }),
    new MouseEvent('mouseup',       { bubbles: true, cancelable: true }),
    new MouseEvent('click',         { bubbles: true, cancelable: true }),
  ].forEach(e => element.dispatchEvent(e));
}
```

## Storage and migration

Use one canonical project prefix (e.g. `px_<project>_`) in both layers:

```javascript
function writeValue(key, value) {
  GM_setValue(`${PREFIX}${key}`, value);
  localStorage.setItem(`${PREFIX}${key}`, JSON.stringify(value));
}
```

Read precedence (explicit, top to bottom):

1. Canonical GM value.
2. Canonical page-localStorage value → reseed GM storage.
3. Known legacy page-localStorage keys → canonical dual-write.
4. Default.

Guard every storage operation with `try/catch`; privacy settings and manager sandboxes can deny either layer. Validate types and ranges at the configuration seam, not at every call site.

**Cross-script GM migration** — managers commonly isolate GM namespaces by script identity. Treat cross-script GM reads as unavailable. Support legacy page-localStorage migration where possible, document the limitation, and provide a manual settings fallback for GM-only legacy values.

When consolidating scripts: use new canonical keys, preserve existing defaults unless a deliberate change is documented, and tell users to disable old installed scripts before enabling the replacement. Deleting a repository directory does not disable copies already installed in a browser.

## Idempotent state and timers

Every run must be safe to call repeatedly:

- Track one timer per element with a `WeakMap`/`Map` and a `data-*` marker.
- Skip detached, disabled, already-processed, or already-scheduled elements.
- Clear timers, progress UI, hover state, and locks when elements disappear, complete, or their feature is disabled.
- Store timer handles before the first async callback can schedule a duplicate.
- Reset route-scoped attempt state on URL changes.
- After attribute-only mutations, schedule an explicit follow-up run; do not rely on a `childList` event that may not fire.
- Release locks in both normal and exceptional paths.

For countdowns, use a monotonic remaining-time calculation or a fixed tick clamped at zero. Hover-pause must freeze the remaining value, not restart the full delay.

## Settings UI

One namespaced FAB/modal per script. The settings module must:

- Render once; refresh fields from current configuration on open.
- Validate and normalize values before saving.
- Support Save, Cancel, backdrop close, and Escape.
- Disable dependent controls visibly and functionally.
- Cancel pending feature work immediately when a feature is disabled.
- Use inline/flex labels — avoid absolute icons inside text inputs.
- Stay outside selector scans for the target site.

## Observer and SPA orchestration

One debounced observer, one navigation listener, one safety interval:

```javascript
let debounceTimer = null;
let lastUrl = location.href;

const observer = new MutationObserver(() => {
  try {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      resetRouteState();
    }
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(run, CONFIG.OBSERVER_DEBOUNCE_MS);
  } catch (error) {
    logError('Observer failed', error);
  }
});

function handleNavigation() {
  lastUrl = location.href;
  resetRouteState();
  run();
}

if (self.navigation?.addEventListener) {
  self.navigation.addEventListener('navigatesuccess', handleNavigation);
}

observer.observe(document.documentElement, { childList: true, subtree: true });
run();
setInterval(run, 5000);
```

The observer watches `childList`/`subtree` only — not script-owned attributes or character data, which would cause self-triggering loops. When the Navigation API is absent, the URL comparison inside the shared observer is the fallback; a second observer for navigation is unnecessary.

Wrap both `run()` and the observer callback in `try/catch`. An uncaught observer exception silently ends future automation. The safety interval is a recovery net, not a high-frequency loop.

## Playwright test harness

Load a local mock page and inject source directly:

```python
page.goto(MOCK_HTML)
page.evaluate(userscript_content)
page.wait_for_selector('#target .expected-result')
```

No extension manager is needed unless the test is specifically about manager installation. Use condition-based waits, not sleeps. Seed short test delays through canonical storage or a fixture; keep production defaults in the script.

Cover: initial state, recovery, opposite toggle, timer pause/resume/cancel, duplicate mutations, route reset, settings validation/persistence, migration, and exclusion cases.

Keep Python dependencies in `tests/requirements.txt`. Browser binaries are machine-specific and should be ignored; a repo-local path (`userscripts/.playwright-browsers/`) plus `tests/conftest.py` setting `PLAYWRIGHT_BROWSERS_PATH` keeps the environment reproducible without tracking binaries.

```bash
node --check path/to/script.user.js
pytest path/to/tests/test_userscript.py
git diff --check
```

If installation or browser startup fails, report the exact blocked command. An infrastructure failure is not a passing test.

## Debugging and distribution

- Foreground behavior: inspect the real page console and DOM.
- ScriptCat background/cron: inspect the manager's run log.
- Raw GitHub CDN caches for ~5 minutes. To force a fresh version: bump `@version`, append a query parameter (`?v=1.0.1`), force-reload the raw URL, or remove the old manager entry before reinstalling.
- When consolidating: verify the replacement before deleting legacy files, and tell users how to disable already-installed legacy copies.
