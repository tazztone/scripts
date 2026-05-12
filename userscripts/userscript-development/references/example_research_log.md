# [Feature Name] - Research Log

This document details the DOM structure and selection strategies used to automate interactions on `[target-site.com]`.

---

## 1. Triggering Selector

**Goal**: Locate the "Confirm" button that appears inside a dynamic modal after adding an item to the cart.

**Primary Selector**: `button[aria-label="Confirm order"]`

**Fallback chain** (evaluated in order if primary fails):
1. `button:has(svg path[d*="M5 13l4 4L19 7"])` — checkmark SVG path signature
2. `[data-testid="confirm-btn"]` — React test ID (present in staging, may be stripped in prod)
3. Text node match: `[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Confirm')`

**Findings**:
- Button is rendered by a Radix UI `<Dialog>` component; `.click()` alone is insufficient — must fire `PointerEvent` + `MouseEvent` chain.
- The modal is injected asynchronously ~300 ms after the "Add to cart" action; a `MutationObserver` on `document.body` is the right trigger.
- `aria-label` is set dynamically from i18n strings; verify on non-English locales (e.g., DE: `"Bestellung bestätigen"`).

---

## 2. Exclusion Logic

**Goal**: Avoid accidentally clicking the "Cancel" or "Save for later" buttons that share the same modal.

**Include**:
- `button[aria-label^="Confirm"]` — label starts with "Confirm"
- Must have `getBoundingClientRect().width > 0` (visible, not hidden duplicate)

**Exclude**:
- Any `button` whose `textContent` contains "Cancel" or "Later"
- Full-width buttons (`width >= window.innerWidth * 0.9`) — these are drawer-level dismiss targets, not modal actions
- Buttons inside `[role="tooltip"]` or `[aria-hidden="true"]` containers

---

## 3. Event Handling

**Events needed** (Radix UI Dialog button, React synthetic events):
```javascript
const el = document.querySelector('button[aria-label="Confirm order"]');
el.dispatchEvent(new PointerEvent('pointerover', { bubbles: true }));
el.dispatchEvent(new PointerEvent('pointerenter', { bubbles: true }));
el.dispatchEvent(new MouseEvent('mouseover',   { bubbles: true }));
el.dispatchEvent(new MouseEvent('mouseenter',  { bubbles: true }));
el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
el.dispatchEvent(new MouseEvent('mousedown',   { bubbles: true }));
el.dispatchEvent(new PointerEvent('pointerup',   { bubbles: true }));
el.dispatchEvent(new MouseEvent('mouseup',     { bubbles: true }));
el.dispatchEvent(new MouseEvent('click',        { bubbles: true }));
```

**Why**: Radix uses `onPointerDown` to open/close state machines. A bare `.click()` fires after `pointerup` and is ignored by the state machine.

---

## 4. State Tracking

**SPA Notes** (site uses React Router v6 + history API):
- URL changes on every step of the checkout flow; reset `logicLock` on each `navigatesuccess` event.
- Modal mounts and unmounts on `/cart/review` only; skip `run()` on all other paths:
  ```javascript
  if (!location.pathname.startsWith('/cart/review')) return;
  ```
- Observed a double-mount bug on fast network tabs (React StrictMode in dev): add a 200 ms debounce before acting to let the second mount settle.

**Cooldown**: 1500 ms after a successful click — the site re-renders the modal briefly during the POST response, which can re-trigger the observer.
