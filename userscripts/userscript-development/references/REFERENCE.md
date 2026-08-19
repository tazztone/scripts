# Userscript Development Reference

Implementation patterns for the workflow in `SKILL.md`. Workflow steps and completion criteria live there; runtime, DOM, storage, orchestration, and test patterns live here.

## Runtime and metadata

Choose one runtime before writing page logic:

- **Portable foreground** — ordinary `==UserScript==`; has page DOM access.
- **ScriptCat background/cron** — no DOM access; use `@background` or `@crontab` for persistent or scheduled work.
- **ScriptCat subscription** — use `==UserSubscribe==` (`.user.sub.js`) for a multi-script distributable bundle.

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
- Keep user-tunable `CONFIG` outside the IIFE; keep runtime implementation and UI encapsulation inside.

Manifest V3 manager nuances (Chrome 120+, Tampermonkey/Violentmonkey MV3):
- Script managers execute under the `chrome.userScripts` backend.
- In Chrome 138+, users must toggle **"Allow User Scripts"** on the extension details page (`chrome://extensions`) if user scripts fail to run.
- `@grant none` scripts run directly in `MAIN` world (sharing JS variables with the page); `@grant GM_*` scripts run in `USER_SCRIPT` isolated world (exempt from page CSP).

## ScriptCat advanced runtime features

ScriptCat provides specialized extensions that do not run in Violentmonkey or Tampermonkey:
- Declarative in-manager settings UI (`==UserConfig==` YAML blocks).
- Headless background workers (`@background`) and scheduled jobs (`@crontab`) with `CATRetryError` backoff.
- Multi-script subscription bundles (`==UserSubscribe==` / `.user.sub.js`).
- Serverless cloud execution (CloudCat FaaS).

For complete syntax, YAML schemas, and lifecycle patterns, consult the dedicated reference: **[SCRIPTCAT.md](SCRIPTCAT.md)**.

## Cross-manager GM API quirks and compatibility

| API / Feature | Tampermonkey / Violentmonkey | ScriptCat | Practical rule |
| :--- | :--- | :--- | :--- |
| `GM_setValue(k, undefined)` | Stores string `"undefined"` or errors | **Deletes the key** | Use `GM_deleteValue(k)` explicitly for cross-manager consistency. |
| Storage async timing | Synchronous in-memory cache | Asynchronous under the hood | If a page may close immediately after saving, prefer `await GM.setValue(...)`. |
| `GM_setClipboard` | Supports callback parameter | No callback parameter support | Avoid relying on completion callbacks for clipboard writes. |
| `GM_openInTab` | `loadInBackground: boolean` | `active: boolean` | Prefer `{ active: true/false }` over deprecated `loadInBackground`. |
| `GM_xmlhttpRequest` | Host headers restricted by browser | Supports `origin`, `referer`, `cookie`, `host`, `user-agent` | Declare explicit `@connect` for every target host across all engines. |
| Response types | `text`, `json`, `blob`, `arraybuffer`, `document` | Same + `stream` support | Check manager compatibility before using streaming responses. |
| `GM_info` metadata | Exposes `GM_info.runAt`, `sandboxMode` | `runAt` unsupported; `sandboxMode` raw | Guard access to engine-specific `GM_info` properties. |

## Foreground module shape

```javascript
const DEFAULTS = { /* user-tunable defaults */ };

(() => {
  'use strict';
  // 1. shadow DOM host & style encapsulation
  // 2. storage / configuration
  // 3. normalization / visibility / non-destructive event adapters
  // 4. batched DOM mutators & yielding
  // 5. feature state transitions
  // 6. timers & one-shot side effects
  // 7. encapsulated settings UI & toasts (Top Layer)
  // 8. one shared orchestrator
})();
```

Feature modules expose narrow operations (`runModelLock()`, `runAutoApprove()`). They do not create competing observers or intervals.

## DOM discovery and event adapters

Use ranked heuristics rather than one brittle selector:

1. Stable semantic or structural anchor.
2. Accessible role, label, or test identifier.
3. Non-destructive text matching with `TreeWalker`.

**Non-destructive text matching** — avoid `innerHTML` manipulation or container regex matching, which destroys framework virtual DOM fibers and event listeners:

```javascript
function findTextNodes(root, pattern) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue?.trim()) return NodeFilter.FILTER_REJECT;
      const parent = node.parentElement;
      if (!parent || parent.closest('#px-root, script, style, textarea, input, [contenteditable="true"]')) {
        return NodeFilter.FILTER_REJECT;
      }
      return pattern.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
    }
  });
  const matches = [];
  while (walker.nextNode()) matches.push(walker.currentNode);
  return matches;
}
```

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

**Event dispatch** — when `.click()` is unreliable on React/Radix synthetic event managers, dispatch a full pointer/mouse sequence:

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

## Performance and main-thread yielding

When mutating multiple DOM nodes (e.g. search feeds, infinite lists), chunk operations with `requestAnimationFrame` and yield using `globalThis.scheduler?.yield()` to prevent main-thread freezing and protect Interaction to Next Paint (INP):

```javascript
async function batchProcessElements(elements, processFn, batchSize = 20) {
  for (let i = 0; i < elements.length; i += batchSize) {
    const chunk = elements.slice(i, i + batchSize);
    await new Promise(resolve => requestAnimationFrame(() => {
      chunk.forEach(processFn);
      resolve();
    }));
    if (globalThis.scheduler?.yield) {
      await scheduler.yield();
    }
  }
}
```

## Shadow DOM & Top Layer UI

Encapsulate all injected userscript UI (FAB, modal, toasts, badges) in a single host element with an open Shadow Root. This prevents host page CSS resets from distorting script controls and prevents userscript CSS from leaking into the page.

```javascript
function initUI(styles) {
  let host = document.getElementById('px-root');
  if (!host) {
    host = document.createElement('div');
    host.id = 'px-root';
    document.body.appendChild(host);
  }

  const shadow = host.shadowRoot || host.attachShadow({ mode: 'open' });
  shadow.innerHTML = `
    <style>
      ${styles}
      :host { all: initial; }
      dialog[popover], .px-modal {
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        background: #1e293b;
        color: #f8fafc;
        padding: 20px;
      }
      dialog::backdrop {
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(4px);
      }
    </style>
    <div id="px-ui-container">
      <button id="px-fab" title="Open Settings">⚙️</button>
      <dialog id="px-settings-dialog" popover="auto">
        <!-- Settings Controls -->
      </dialog>
      <div id="px-toast-container"></div>
    </div>
  `;
  return shadow;
}
```

**Top Layer modals (`popover="auto"` or `<dialog>`)**:
- Mounts directly into the browser top layer, rendering above all host `z-index` stacks without `z-index: 99999999` wars.
- Built-in light dismiss: clicking outside the dialog or pressing `Escape` closes it automatically without manual backdrop event listeners.

**Transient toasts**:
```javascript
function showToast(shadow, message, durationMs = 2500) {
  const container = shadow.getElementById('px-toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'px-toast';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('fade-out');
    toast.addEventListener('transitionend', () => toast.remove());
  }, durationMs);
}
```

## Chrome built-in AI / Prompt API

In modern Chromium (Chrome 130+), userscripts can leverage local on-device Gemini Nano via `LanguageModel` / `ai.languageModel` for fast, offline text processing without external API keys or `@grant GM_xmlhttpRequest`:

```javascript
async function getPromptSession(systemPrompt) {
  const aiHost = globalThis.ai || (typeof unsafeWindow !== 'undefined' && unsafeWindow.ai);
  if (!aiHost?.languageModel) return null;

  try {
    const capabilities = await aiHost.languageModel.capabilities();
    if (capabilities.available === 'no') return null;
    return await aiHost.languageModel.create({ systemPrompt });
  } catch (err) {
    console.warn('[Userscript AI] Local model unavailable:', err);
    return null;
  }
}
```

## Storage and migration

Use one canonical project prefix (e.g. `px_<project>_`) in both layers:

```javascript
function writeValue(key, value) {
  if (typeof GM_setValue === 'function') GM_setValue(`${PREFIX}${key}`, value);
  try { localStorage.setItem(`${PREFIX}${key}`, JSON.stringify(value)); } catch (_) {}
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

# Shadow DOM piercing selector
page.locator('#px-root >> #px-fab').click()
expect(page.locator('#px-root >> #px-settings-dialog')).to_be_visible()
```

No extension manager is needed unless the test is specifically about manager installation. Use condition-based waits, not sleeps. Seed short test delays through canonical storage or a fixture; keep production defaults in the script.

Cover: initial state, recovery, opposite toggle, timer pause/resume/cancel, duplicate mutations, route reset, shadow DOM interactions, settings validation/persistence, migration, and exclusion cases.

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

## Standard README Structure

All userscript package `README.md` files must follow the unified repository layout (modeled on `toppreise/README.md` and template `example_readme.md`):

1. **Title & Tagline**: `# <Script Title>: <Subtitle / Tagline>` followed by a concise 1-2 sentence description.
2. **🚀 Installation**: Direct Violentmonkey links and prominent `CLICK HERE TO INSTALL USERSCRIPT` raw link with version tag.
3. **⚡ Features**: Numbered list detailing core capabilities.
4. **🚀 Instant Auto-Installer Tool & Auto-Updates**: Instructions for direct installation and `@updateURL` background auto-updates.
5. **⚙️ Configuration & Persistence**: Guide on setting values via settings panels or `GM_registerMenuCommand` menu items, ending with a standard `[!NOTE]` callout regarding `GM_setValue` persistence.
