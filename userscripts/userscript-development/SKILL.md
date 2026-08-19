---
name: userscript-development
description: Userscript engineering for Tampermonkey, Violentmonkey, and ScriptCat. Trigger on userscript development, @match, @grant, GM API quirks, Shadow DOM UI, storage migration, ScriptCat ==UserConfig==, @background, @crontab, or ==UserSubscribe== bundles.
---

# Userscript Development

Scripts fail most often at three seams: the runtime/metadata boundary, the DOM-selector boundary, and the test/installation boundary. Work outward from each seam in order.

## Workflow

### 1. Inventory

Read the repository before asking questions or editing:

- Locate existing scripts, research logs, READMEs, mocks, test commands, and package manifests.
- Read the current userscript, its tests, its research log, and [REFERENCE.md](references/REFERENCE.md).
- Record the runtime, matched hosts, granted APIs, persistent keys, user-visible behavior, test command, and any cleanup/migration scope.

Completion criterion: the target files, current behavior, verification path, and deletion/migration scope are known from repository evidence.

### 2. Metadata first

Choose exactly one runtime branch before writing logic:

- **Foreground DOM script** — ordinary `==UserScript==` metadata; for page UI, DOM scraping, and event handling. Details: [REFERENCE.md](references/REFERENCE.md).
- **ScriptCat background / crontab script** — use `@background` or `@crontab` only when work runs persistently or on schedule without DOM access; async operations must settle a returned `Promise`. Details: [SCRIPTCAT.md](references/SCRIPTCAT.md).
- **ScriptCat subscription package** — use `==UserSubscribe==` (`.user.sub.js`) only when distributing multiple scripts as a single bundle. Details: [SCRIPTCAT.md](references/SCRIPTCAT.md).

Preflight verification:
- On Manifest V3 browsers, confirm extension developer mode or "Allow User Scripts" is toggled if scripts fail to inject.
- Declare the smallest correct `@match`, `@run-at`, `@grant`, `@connect`, and `@require` surface. Pin exact library versions in `@require`. Keep foreground `CONFIG` outside the IIFE; keep implementation and UI encapsulation inside.

Completion criterion: runtime branch chosen, preflight constraints verified, and every declared permission justified by an implementation use.

### 3. Research the page

For foreground scripts, create or update `RESEARCH_LOG.md` before writing selectors. Document:

1. Trigger and target elements — primary and fallback selectors.
2. Non-destructive text matching — use `TreeWalker` (`NodeFilter.SHOW_TEXT`); avoid `innerHTML` replacement or container string rewrites that destroy framework event listeners.
3. Positive signals and explicit exclusions (e.g., skip `input`, `textarea`, `[contenteditable]`, and script-owned roots).
4. Visibility, disabled-state, and locked-state checks.
5. `.click()` versus full `PointerEvent`/`MouseEvent` dispatch sequences for synthetic event systems (React, Radix, Vue).
6. SPA navigation, DOM replacement, cooldown, and failure behavior.

Treat an element as visible only when it is in the document, not hidden by computed style, and has non-zero dimensions. Exclude the script's own UI root from domain-element discovery. Label any mock assumptions in the log.

Completion criterion: every automated action has a documented target, exclusion rule, non-destructive traversal method, event sequence, and recovery path.

### 4. Deep modules, one orchestration seam

Keep the public surface small. A foreground script should separate:

- storage, configuration, and migration;
- normalization, visibility, and non-destructive event adapters;
- feature detection and state transitions;
- timers, batched DOM mutators, and one-shot side effects;
- encapsulated UI and settings (Shadow DOM + Top Layer);
- one shared orchestrator.

**UI Encapsulation & Dual-Layer Styles**:
- Apply the **Dual-Layer Style Architecture**: host-page element modifiers (borders, badges, dimming/hiding classes) belong in a document `<style>` tag in `document.head`; all injected UI components (FAB, settings dialog, toasts, indicators) belong strictly inside a dedicated host with an open Shadow Root (`host.attachShadow({ mode: 'open' })`).
- Use native `<dialog>` or `popover="auto"` inside the shadow root for settings modals to guarantee top-layer rendering above host page `z-index` stacks, built-in light-dismiss (Escape and backdrop click), and explicit viewport sizing (`max-height: 85vh; overflow-y: auto`).
- Provide transient toast feedback for hotkeys and background automation.

**Performance & INP Protection**:
- Batch multi-element DOM modifications in slices (e.g., chunks of 20) with `requestAnimationFrame`, and yield between slices via `globalThis.scheduler?.yield()`.
- Guard async batch loops with a monotonic sequence token (`runId`) before and after yielding to immediately discard stale in-flight batches when users type or DOM mutations re-trigger processing.

**Orchestration & Idempotence**:
- The orchestrator owns one debounced `MutationObserver`, one navigation listener with a URL-change fallback, and one safety interval. Feature modules expose narrow operations (`runModelLock()`, `runAutoApprove()`); they do not create competing observers or intervals.
- Track one timer per element with a `WeakMap`; mark completed elements.
- Cancel timers when an element disappears, is acted on, or its feature is disabled.
- Reset route-scoped locks on SPA navigation.
- Observe `childList`/`subtree`; avoid observing script-owned attributes or styles.
- Release locks on both success and exceptions; schedule a follow-up run after a cooldown.

Completion criterion: repeated `run()` calls, duplicate mutation events, route changes, and feature toggles cannot create duplicate controls, clicks, timers, or stuck locks; all injected UI is isolated in Shadow DOM; and multi-element operations yield to the main thread with monotonic cancellation guards.

### 5. Storage migration

Use canonical, namespaced keys. Dual-write to GM storage and page `localStorage`; if a canonical local value exists and GM storage is empty, reseed GM storage. Read legacy keys once and write their values to canonical keys.

Do not claim cross-script GM migration unless the target manager demonstrably exposes the old namespace — separate installations commonly isolate GM storage. Document this limitation and provide a manual fallback.

When consolidating scripts: preserve existing defaults, namespace new keys, document that users must disable old scripts before enabling the replacement, and verify the replacement before deleting legacy directories.

Completion criterion: each setting has a canonical key, default, type/range validation, read precedence, write behavior, migration source, and documented limitation.

### 6. Tests

Maintain an integrated mock page under `tests/` and inject the userscript source directly with Playwright. Do not install Violentmonkey or Tampermonkey in the test browser unless the behavior under test is the extension manager itself.

Cover behavior, not implementation:

- Initial discovery and state application.
- Non-destructive DOM scanning and event preservation.
- Shadow DOM UI rendering, piercing interactions, and popover/dialog top-layer behavior.
- Manual deviation and recovery.
- Already-correct and opposite toggle states.
- Countdown, hover pause/resume, completion, removal, and cancellation.
- Duplicate mutation events and duplicate scheduling.
- Route reset and connector fallback.
- Settings save/cancel/Escape, validation, persistence, and feature disablement.
- Legacy storage migration and canonical persistence.
- Exclusion cases: follow-up text, locked options, disabled controls, script-owned UI.

Use condition-based waits (`wait_for_selector`, `wait_for_function`), not arbitrary sleeps. Use `state='attached'` (not default `state='visible'`) when asserting elements hidden by filter rules (`display: none`). Seed a short test-only delay through storage or a fixture; keep production defaults in the userscript. Keep Python dependencies in `tests/requirements.txt`.

Completion criterion: the suite proves each user-visible feature and its important failure modes, and runs from the documented command.

### 7. Verify and clean up

```bash
node --check path/to/script.user.js
pytest -o cache_dir=/tmp/.pytest_cache --import-mode=importlib path/to/tests/
git diff --check
```

Verify the README, research log, root inventory, and final file list. If a test is blocked by missing dependencies, network, or permissions, report the exact blocked command — do not describe the suite as passing.

Remove legacy files only after the replacement passes syntax and behavior checks. State what was removed and whether browser-installed copies still need manual disabling.

Completion criterion: syntax checks pass, tests pass or have an explicit blocker, every modified artifact is documented, and cleanup matches the requested scope.

## References

- Metadata, DOM heuristics, Shadow DOM, storage, observers, Playwright patterns: [REFERENCE.md](references/REFERENCE.md)
- ScriptCat background workers, crontab, UserConfig, subscriptions: [SCRIPTCAT.md](references/SCRIPTCAT.md)
- Reference foreground script: [example.user.js](references/example.user.js)
- Research-log template: [example_research_log.md](references/example_research_log.md)
- Standard README template: [example_readme.md](references/example_readme.md)
