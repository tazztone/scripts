# Userscript Development Reference

This file contains implementation patterns for the workflow in `SKILL.md`. Keep the workflow and completion criteria in `SKILL.md`; keep detailed runtime, DOM, storage, orchestration, and test patterns here.

## Runtime and metadata

Choose one runtime before writing page logic:

- **Portable foreground**: ordinary `==UserScript==`; has page DOM access.
- **ScriptCat background/cron**: no DOM access; use `@background` or `@crontab` for persistent or scheduled work.
- **ScriptCat subscription**: use `==UserSubscribe==` only for a distributable bundle.

For ordinary foreground scripts:

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

- Use the narrowest correct `@match`; use `@include`/`@exclude` only when necessary.
- Declare only APIs the implementation calls. Add explicit `@connect` hosts for `GM_xmlhttpRequest` or `GM_cookie`.
- Pin exact `@require` versions when external libraries are actually used.
- Use semver for `@version`; add `@updateURL`/`@downloadURL` only when the distribution path needs them.
- Keep user-tunable `CONFIG` and `STYLES` outside the IIFE; keep runtime implementation inside it.

ScriptCat background rules:

- Background and cron scripts cannot use page DOM APIs.
- Async work must return a `Promise` that settles after the real work finishes.
- Retry with `new CATRetryError(message, seconds)` where supported; keep the retry delay and work duration below the cron interval.
- `==UserConfig==` pairs with `GM_getValue` for manager-provided user settings; `==UserSubscribe==` is for bundles and requires HTTPS distribution.

## Foreground module shape

Use a deep private implementation behind a small orchestration seam:

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

Feature modules should expose narrow internal operations such as `runModelLock()`, `runAutoApprove()`, and `runConnectorEnablement()`. They should not create their own competing observers or intervals.

## DOM discovery and event adapters

Use ranked heuristics rather than one brittle selector:

1. Stable semantic/structural anchor.
2. Accessible role, label, or test identifier.
3. Normalized text as a constrained fallback.

For each target, define positive signals and exclusions. Exclude the script's own root (`#px-settings-modal`, or the project equivalent) before broad page scans so settings controls cannot be mistaken for domain controls.

Visibility should reject elements that are detached, `display:none`, `visibility:hidden`, transparent, or have zero width or height:

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

When parsing cards, account for the card itself being an anchor:

```javascript
const link = card.tagName === 'A' ? card : card.closest('a[href]') || card.querySelector('a[href]');
```

Normalize text before comparison:

```javascript
const normalize = value => String(value || '')
  .replace(/\s+/g, ' ')
  .trim()
  .toLowerCase();
```

For React/Radix controls, use the simplest event that is verified to work. When `.click()` is unreliable, dispatch a complete pointer/mouse sequence and ensure only one `click` is emitted:

```javascript
function dispatchClickEvents(element) {
  if (!element) return;
  const events = [
    new PointerEvent('pointerdown', { bubbles: true, cancelable: true }),
    new PointerEvent('pointerup', { bubbles: true, cancelable: true }),
    new MouseEvent('mousedown', { bubbles: true, cancelable: true }),
    new MouseEvent('mouseup', { bubbles: true, cancelable: true }),
    new MouseEvent('click', { bubbles: true, cancelable: true }),
  ];
  events.forEach(event => element.dispatchEvent(event));
}
```

## Storage and migration

Use one canonical project prefix, for example `px_<project>_`, consistently in both layers:

```javascript
function writeValue(key, value) {
  GM_setValue(`${PREFIX}${key}`, value);
  localStorage.setItem(`${PREFIX}${key}`, JSON.stringify(value));
}
```

Read precedence should be explicit:

1. canonical GM value;
2. canonical page-localStorage value, followed by GM reseeding;
3. known legacy page-localStorage keys, followed by canonical dual-write;
4. default.

Guard every storage operation with `try/catch`; browser privacy settings and manager contexts can deny either layer. Validate types and ranges at the configuration seam rather than at every call site.

Do not infer that a replacement script can read the old script's GM namespace. Managers commonly isolate values by userscript identity. Support legacy page-localStorage migration when possible, document the limitation, and provide a manual settings fallback for legacy GM-only values.

When consolidating scripts, use new canonical keys to avoid collisions, preserve defaults unless intentionally changing them, and document that users must disable old installed scripts before enabling the replacement. Repository deletion does not disable copies already installed in a browser.

## Idempotent state and timers

Dynamic pages call the orchestrator repeatedly. Every action must be safe to discover more than once:

- Track one timer per element with a `WeakMap`/`Map` and/or a `data-*` marker.
- Skip detached, disabled, already-processed, or already-scheduled elements.
- Clear timers, progress UI, hover state, and locks when elements disappear, complete, or the feature is disabled.
- Store timer handles before the first asynchronous callback can schedule a duplicate.
- Reset route-scoped attempt state on URL changes.
- On interactions that mutate only attributes or text, schedule an explicit follow-up run after the cooldown; do not depend on a `childList` mutation that may never happen.
- Release locks in both normal and exceptional paths.

For a countdown, prefer a monotonic remaining-time calculation or a fixed tick that is clamped at zero. Hover pause must freeze the remaining value, not restart the full delay.

## Settings UI

Use one namespaced FAB/modal per script. The settings module should:

- render once and update fields from current configuration on open;
- validate and normalize values before saving;
- support Save, Cancel, backdrop close, and Escape;
- disable dependent controls visibly and functionally;
- cancel pending feature work immediately when a feature is disabled;
- avoid absolute icons inside text inputs; use inline/flex labels;
- keep modal controls outside selector scans for the target site.

## Observer and SPA orchestration

Use one debounced observer and one safety interval:

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

if (self.navigation && typeof self.navigation.addEventListener === 'function') {
  self.navigation.addEventListener('navigatesuccess', handleNavigation);
}

observer.observe(document.documentElement, { childList: true, subtree: true });
run();
setInterval(run, 5000);
```

The observer is intentionally not watching script-owned attributes or character data. If an older browser lacks the Navigation API, URL comparison in the shared observer is the fallback; do not add a second continuously-running DOM observer just for navigation.

Wrap both `run()` and the observer callback in `try/catch`; an uncaught observer exception can silently end future automation. Keep the safety interval as recovery, not as the primary high-frequency loop.

## Playwright test harness

Foreground tests should load a local mock page and inject the source:

```python
page.goto(MOCK_HTML)
page.evaluate(userscript_content)
page.wait_for_selector('#target .expected-result')
```

Installing Violentmonkey/Tampermonkey is unnecessary unless the test is specifically about manager installation or metadata. Test the same seam the user exercises: DOM changes, clicks, storage, timers, and visible UI.

Use condition-based waits, not arbitrary sleeps. Seed a short delay through canonical test storage or a fixture while preserving production defaults in the script. Cover initial state, recovery, opposite toggle state, timer pause/resume/cancel, duplicate mutations, route reset, settings validation/persistence, migration, and exclusion cases.

Keep Python dependencies in `tests/requirements.txt`. Large browser binaries are machine-specific and should remain ignored. A project may use a repo-local path such as `userscripts/.playwright-browsers/` plus `tests/conftest.py` to set `PLAYWRIGHT_BROWSERS_PATH`; this keeps the environment reproducible without tracking binaries.

Recommended checks:

```bash
node --check path/to/script.user.js
pytest path/to/tests/test_userscript.py
git diff --check
```

If installation or browser startup fails because of missing packages, network, sandbox policy, or permissions, report the exact command and failure. Do not convert an infrastructure blocker into a passing test claim.

## Debugging and distribution

- Foreground behavior: inspect the real page console and DOM.
- ScriptCat background/cron behavior: inspect the manager's run log.
- For raw GitHub installs, CDN/browser caching can show an old version. Bump `@version`, use a temporary query parameter such as `?v=1.0.1`, force-reload, or remove the old manager entry before reinstalling.
- During consolidation, verify the replacement before deleting legacy repository files and tell users how to disable already-installed legacy copies.
