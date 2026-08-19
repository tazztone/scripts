# ScriptCat Runtime Extensions

Reference for ScriptCat-specific runtime features and manifest blocks. Consult this reference when building background workers, scheduled crontab tasks, native in-manager settings UIs, or subscription bundles.

For portable foreground scripts compatible with Violentmonkey and Tampermonkey, see [REFERENCE.md](REFERENCE.md).

---

## 1. `==UserConfig==` Declarative Settings UI

ScriptCat supports declarative in-manager configuration using YAML. Place the `==UserConfig==` block immediately after `==UserScript==`:

```javascript
// ==UserScript==
// @name         Configurable Automation
// @namespace    https://example.com/
// @version      1.0.0
// @match        https://example.com/*
// @grant        GM_getValue
// @grant        GM_setValue
// ==/UserScript==

/* ==UserConfig==
settings:
  apiToken:
    title: API Token
    type: text
    password: true
    default: ""
  enableAutomation:
    title: Enable Automation
    type: checkbox
    default: true
  syncInterval:
    title: Sync Interval (seconds)
    type: number
    default: 60
    min: 10
    max: 3600
==/UserConfig== */

// Values are accessed with GM_getValue via the "group.key" namespace:
const enabled = GM_getValue("settings.enableAutomation", true);
const apiToken = GM_getValue("settings.apiToken", "");
const interval = GM_getValue("settings.syncInterval", 60);
```

### Config Rules & Types
- **Block placement**: Must be placed directly after `==UserScript==` in a multi-line comment.
- **Namespacing**: Values are stored and read under `group.key` (e.g. `settings.apiToken`).
- **Supported types**: `text` (supports `password: true`), `checkbox`, `number` (`min`, `max`), `select` (`values: [...]`).
- **Violentmonkey / Tampermonkey fallback**: Other managers ignore this block as a comment; always provide a fallback default in `GM_getValue("group.key", fallbackDefault)`.

---

## 2. `@background` and `@crontab` Async Lifecycle

ScriptCat executes background and crontab scripts in an isolated background sandbox without DOM or page `window` access.

### Async Settling Contract
Background scripts **must return a `Promise`** for asynchronous work. The worker terminates immediately when the promise settles (resolves or rejects); any asynchronous `GM_*` calls triggered after resolution will fail silently.

### Engine Retry with `CATRetryError`
To request an engine-managed retry on failure, reject the returned promise with `new CATRetryError(message, seconds)` (minimum retry delay is 5 seconds):

```javascript
// ==UserScript==
// @name         Periodic Sync Worker
// @namespace    https://example.com/
// @version      1.0.0
// @crontab      */15 * * * *
// @grant        GM_xmlhttpRequest
// @grant        GM_notification
// @grant        GM_getValue
// @grant        GM_setValue
// @connect      api.example.com
// ==/UserScript==

return new Promise(async (resolve, reject) => {
  try {
    const response = await fetchUpdate();
    GM_notification({ title: "Sync Complete", text: `Updated ${response.items} records` });
    resolve();
  } catch (err) {
    // Retry in 30 seconds if network or rate limited
    reject(new CATRetryError(`Sync failed: ${err.message}`, 30));
  }
});
```

### `@crontab` Rules & Syntax
- **Single directive**: Only the **first** `@crontab` directive in the script header is evaluated.
- **5-field format**: Prefer standard 5-field cron syntax (`minute hour day-of-month month day-of-week`).
- **Deduplication**: Use `once` or `once(expr)` modifiers to avoid repeated execution within the same time window.
- **Timing guard**: Ensure single execution runtime + retry delay is strictly less than the cron interval to prevent overlapping worker instances.

---

## 3. `==UserSubscribe==` Multi-Script Bundles

To distribute a suite of scripts as a single, auto-updating subscription package, create a manifest ending in `.user.sub.js`:

```javascript
// ==UserSubscribe==
// @name         Developer Tool Suite
// @author       tazztone
// @version      1.0.0
// @connect      api.example.com
// @connect      cdn.example.com
// @scriptUrl    https://example.com/scripts/core-enhancer.user.js
// @scriptUrl    https://example.com/scripts/table-export.user.js
// @scriptUrl    https://example.com/scripts/api-logger.user.js
// ==/UserSubscribe==
```

### Subscription Rules
- **Header**: Must start with `==UserSubscribe==` (not `==UserScript==`).
- **File extension & protocol**: Must use the `.user.sub.js` filename extension and be served over HTTPS.
- **Permissions**: The user confirms permissions once upon subscription. Subsequent script updates install silently unless declared `@connect` hosts expand.
- **Connect inheritance**: Subscription-level `@connect` rules cascade to and override individual child scripts.
- **Version tracking**: Include `@version` for clean cache-busting and update detection.

---

## 4. CloudCat FaaS Execution Caveats

When deploying ScriptCat background or cron tasks to CloudCat (serverless cloud execution):
- **Restricted API subset**: Only `GM_xmlhttpRequest`, `GM_notification`, `GM_log`, and exported `GM_getValue` are supported.
- **State migration**: Use `@exportValue key1, key2` and `@exportCookie domain` headers to explicitly authorize variables and session cookies to sync to the cloud worker.
