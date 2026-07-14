---
name: userscript-development
description: Build, debug, or refactor robust browser userscripts for Tampermonkey, Violentmonkey, or ScriptCat. Triggers whenever the user mentions "userscript", "Tampermonkey", "ScriptCat", `@match`, `@background`, `==UserConfig==`, or wants to automate interactions on a web page or schedule background browser tasks using client-side JavaScript.
---

# Userscript Development

Follow this workflow to create production-grade browser userscripts resilient to DOM changes, compatible with modern Single Page Applications (SPAs), or leveraging advanced ScriptCat background runtimes.

## The Workflow

Userscript work usually breaks at the runtime and metadata boundary, not in the page logic. **Choose the runtime first**, declare the minimum permissions up front, then debug in the environment where the script actually runs.

Always produce or maintain these core artifacts:
1.  **`RESEARCH_LOG.md`**: Document the target site's DOM structure, selectors, behavioral nuances, and edge cases (for foreground scripts).
2.  **`[name].user.js`**: The script itself.
3.  **`README.md`**: Clear user guide for installation and configuration.

## 1. Runtime Selection & Preflight

Decide on the runtime environment before writing code:
- **Portable Foreground Script**: Needs page DOM or page context. Use ordinary `==UserScript==` patterns.
- **ScriptCat Background / Cron**: Needs persistent or scheduled work *without* DOM access. Use `@background` or `@crontab`.
- **ScriptCat Subscription Package**: Needs to install many scripts as one package. Use `==UserSubscribe==`.

Start with metadata, not implementation: declare `@match`, `@grant`, `@connect`, and `@run-at`. Declare the *smallest* permission surface that fits the task.

## 2. Research-First DOM Analysis (Foreground Scripts)

If writing a foreground script, create `RESEARCH_LOG.md` before writing logic. Use numbered sections:
1. **Trigger & Target Elements**: Primary and Fallback selectors.
2. **Element Selectors**: Catalog every interactive element.
3. **Exclusion Logic**: What NOT to interact with.
4. **Event Management**: `.click()` vs `PointerEvent` chains.
5. **Lifecycle & SPA Behavior**: Navigation resets, debounce, cooldowns.

If the site blocks static fetching, use Playwright to dump the DOM. (Recreate the environment using `uv venv --clear` if OS Python upgrades break C-extensions).

## 3. Implementation Principles

Structure your script with clear boundaries:
- **Metadata**: Add `@grant GM_*` explicitly. Add `@connect` for hosts used by `GM_xmlhttpRequest`. Always pin exact library versions in `@require`.
- **Component Scope**: For foreground scripts, place **CONFIG & STYLES** outside the IIFE for user-tunability (or use `==UserConfig==`). Keep everything else strictly inside the IIFE.
- **Async Background Work**: ScriptCat background scripts must return a `Promise`. Resolve only when GM work is truly finished. Use `new CATRetryError(msg, secs)` for retries.
- **Resiliency**: Always verify DOM visibility (`getBoundingClientRect().width > 0`), use timestamp-based throttles, apply `dataset.processed` markers for idempotency, wrap `MutationObserver` callbacks in `try/catch`, prevent self-observation loops by selectively disabling attribute observation (`attributes: false`), and use robust text normalization when matching string identifiers across distinct elements.

See the complete architectural rules, metadata guidelines, and code patterns in **[REFERENCE.md](references/REFERENCE.md)**.

## 4. Orchestration & Debugging

- **Debugging**: Debug where the code really runs (Foreground = page console; Background = ScriptCat run log). Bypass raw script installation caches using query-parameter cache-busters on raw GitHub links.
- **SPA Handling**: Use a debounced `MutationObserver` combined with the `Navigation API` (or fallback observer) to handle route changes in foreground scripts.
- **Safety Net**: Always include a periodic `setInterval` fallback in case observers die.

Detailed orchestration patterns and ScriptCat API usages are available in **[REFERENCE.md](references/REFERENCE.md)**.

## Example Templates

- Architecture Rules & Code Snippets: **[REFERENCE.md](references/REFERENCE.md)**
- Reference Script Template: **[example.user.js](references/example.user.js)**
- Reference Research Log: **[example_research_log.md](references/example_research_log.md)**
