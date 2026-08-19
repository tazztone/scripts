# Hugging Face Model Helper - Research Log

This document records the DOM structures, event models, network behavior, and encapsulation architecture for Hugging Face inline liking and model filtering.

## 1. Model Card DOM Structure

Hugging Face model cards render as `<article class="overview-card-wrapper">`:
- Model ID is derived from the main card link `a[href^="/"]` (e.g. `/tiiuae/falcon-180B`).
- Non-model URLs (`/docs`, `/spaces`, `/datasets`, `/models`, etc.) are ignored using `RESERVED_MODEL_PREFIXES`.
- Heart icon SVGs are differentiated from task badges (e.g. image-to-text, translation) using path signatures (`HEART_PATH_SIGNATURES` vs `NON_HEART_PATH_SIGNATURES`).
- Liked state is detected via Tailwind red text/fill classes (`text-red-500`, `fill-red-500`), path attributes, or active override states in `inlineLikeStates`.

## 2. Inline Liking & Optimistic UI

- Inline liking attaches event listeners (`click`, `keydown` Enter/Space) to the heart container element with `dataset.hfInlineBound` for idempotency.
- State updates are applied optimistically, incrementing/decrementing the count and updating card border styling immediately.
- If the network request fails (e.g. HTTP 401/403 unauthorized or network disconnect), the UI restores the captured snapshot (`restoreInlineVisual`) and displays a non-blocking toast notification inside the shadow container.

## 3. UI Encapsulation (Shadow DOM & Toasts)

- The filter controls and settings panel are mounted inside `<div id="hf-date-filter-root">` with an open Shadow Root (`shadowRoot`).
- Scoped Shadow DOM CSS shields the widget controls, presets, sliders, and inputs from Hugging Face's Tailwind resets.
- Card highlight styles (`.hf-is-unliked`, `.hf-filtered-out`, `.hf-inline-like-btn`) remain in the host document `<style>` tag.
- Non-blocking toasts are rendered inside `#hf-toast-container` in the shadow root.

## 4. INP Protection & Asynchronous Batching

- `processModelCards()` batches card inspection in slices of 20 using `requestAnimationFrame` + `globalThis.scheduler?.yield()`.
- Each invocation generates a unique `processRunId` sequence token to cancel stale in-flight batches when users drag the slider rapidly or mutations fire.
- Extracted dates from `<time>` elements are cached on `card.dataset.hfDateTimestamp` to prevent repeated parsing during scroll debouncing.

## 5. SPA Navigation & Observer Loop

- `MutationObserver` watches `childList` and `subtree` on `document.body`, filtering out internal mutations on `#hf-date-filter-root` or `#hf-toast-root`.
- The script listens to `self.navigation.addEventListener('navigatesuccess')` for client-side route changes.
