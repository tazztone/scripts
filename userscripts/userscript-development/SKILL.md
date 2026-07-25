---
name: userscript-development
description: Build, refactor, debug, test, or document browser userscripts for Tampermonkey, Violentmonkey, or ScriptCat, including tasks involving @match, @grant, @require, ==UserConfig==, ==UserSubscribe==, or @background.
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

Choose exactly one runtime branch:

- **Foreground DOM script** — ordinary `==UserScript==` metadata; use when the script interacts with a page.
- **ScriptCat background/cron** — use `@background` or `@crontab` only when work must run without DOM access; return a `Promise` for async work.
- **ScriptCat subscription** — use `==UserSubscribe==` only when distributing a bundle.

For every branch, declare the smallest correct `@match`, `@run-at`, `@grant`, `@connect`, and `@require` surface. Pin exact library versions in `@require`. Keep foreground `CONFIG` and `STYLES` outside the IIFE; keep implementation inside.

Completion criterion: every declared permission is justified by an implementation use.

### 3. Research the page

For foreground scripts, create or update `RESEARCH_LOG.md` before writing selectors. Document:

1. Trigger and target elements — primary and fallback selectors.
2. Positive signals and explicit exclusions for every automated interaction.
3. Visibility, disabled-state, and locked-state checks.
4. `.click()` versus full PointerEvent/MouseEvent dispatch requirements.
5. SPA navigation, DOM replacement, cooldown, and failure behavior.

Treat an element as visible only when it is in the document, not hidden by computed style, and has non-zero dimensions. Exclude the script's own UI from domain-element discovery. Label any mock assumptions in the log.

Completion criterion: every automated action has a documented target, exclusion rule, event method, and recovery path.

### 4. Deep modules, one orchestration seam

Keep the public surface small. A foreground script should separate:

- storage, configuration, and migration;
- normalization, visibility, and event adapters;
- feature detection and state transitions;
- timers and one-shot side effects;
- settings UI;
- one shared orchestrator.

The orchestrator owns one debounced `MutationObserver`, one navigation listener with a URL-change fallback, and one safety interval. Feature modules expose narrow operations (`runModelLock()`, `runAutoApprove()`); they do not create competing observers or intervals.

Make dynamic behavior **idempotent**:

- Track one timer per element with a `WeakMap`; mark completed elements.
- Cancel timers when an element disappears, is acted on, or its feature is disabled.
- Reset route-scoped locks on SPA navigation.
- Observe `childList`/`subtree`; avoid observing script-owned attributes or styles.
- Release locks on both success and exceptions; schedule a follow-up run after a cooldown.

Completion criterion: repeated `run()` calls, duplicate mutation events, route changes, and feature toggles cannot create duplicate controls, clicks, timers, or stuck locks.

### 5. Storage migration

Use canonical, namespaced keys. Dual-write to GM storage and page `localStorage`; if a canonical local value exists and GM storage is empty, reseed GM storage. Read legacy keys once and write their values to canonical keys.

Do not claim cross-script GM migration unless the target manager demonstrably exposes the old namespace — separate installations commonly isolate GM storage. Document this limitation and provide a manual fallback.

When consolidating scripts: preserve existing defaults, namespace new keys, document that users must disable old scripts before enabling the replacement, and verify the replacement before deleting legacy directories.

Completion criterion: each setting has a canonical key, default, type/range validation, read precedence, write behavior, migration source, and documented limitation.

### 6. Tests

Maintain an integrated mock page under `tests/` and inject the userscript source directly with Playwright. Do not install Violentmonkey or Tampermonkey in the test browser unless the behavior under test is the extension manager itself.

Cover behavior, not implementation:

- Initial discovery and state application.
- Manual deviation and recovery.
- Already-correct and opposite toggle states.
- Countdown, hover pause/resume, completion, removal, and cancellation.
- Duplicate mutation events and duplicate scheduling.
- Route reset and connector fallback.
- Settings save/cancel/Escape, validation, persistence, and feature disablement.
- Legacy storage migration and canonical persistence.
- Exclusion cases: follow-up text, locked options, disabled controls, script-owned UI.

Use condition-based waits (`wait_for_selector`, `wait_for_function`), not arbitrary sleeps. Seed a short test-only delay through storage or a fixture; keep production defaults in the userscript. Keep Python dependencies in `tests/requirements.txt`.

Completion criterion: the suite proves each user-visible feature and its important failure modes, and runs from the documented command.

### 7. Verify and clean up

```bash
node --check path/to/script.user.js
pytest path/to/tests/test_userscript.py
git diff --check
```

Verify the README, research log, root inventory, and final file list. If a test is blocked by missing dependencies, network, or permissions, report the exact blocked command — do not describe the suite as passing.

Remove legacy files only after the replacement passes syntax and behavior checks. State what was removed and whether browser-installed copies still need manual disabling.

Completion criterion: syntax checks pass, tests pass or have an explicit blocker, every modified artifact is documented, and cleanup matches the requested scope.

## References

- Metadata, DOM heuristics, storage, observers, Playwright patterns: [REFERENCE.md](references/REFERENCE.md)
- Reference foreground script: [example.user.js](references/example.user.js)
- Research-log template: [example_research_log.md](references/example_research_log.md)
