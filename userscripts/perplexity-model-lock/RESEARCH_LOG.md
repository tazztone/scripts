# Perplexity Model Lock - Research Log

This document outlines the DOM structure, selectors, and behavioral nuances analyzed for locking the model and enabling Thinking mode on Perplexity.ai.

## 1. Model Selector Button (Trigger)

### Target Selector
The model selector is embedded inside the search/prompt input area at the bottom of the Perplexity query interface.

*   **Primary Identification Method**: Search for all visible `button` elements on the page whose text content matches or contains any of Perplexity's standard AI models:
    - `"best"` (e.g. "Best")
    - `"sonar"` (e.g. "Sonar 2")
    - `"gpt-"` (e.g. "GPT-5.4", "GPT-5.5")
    - `"gemini"` (e.g. "Gemini 3.1 Pro")
    - `"claude"` (e.g. "Claude Sonnet 4.6", "Claude Opus 4.7")
*   **Fallback Heuristic**: Look for buttons that contain a chevron/down-arrow icon inside the prompt box container, specifically inside the same form/container as the textarea prompt input.

### Target State Detection
If the text content of the button contains both:
1.  Our configured model name, e.g. `"Claude Sonnet 4.6"`
2.  Our target thinking state, e.g. `"Thinking"` (since the button text updates to `"Claude Sonnet 4.6 Thinking"` when active)

...then the target state is already fully active, and no interaction is performed.

---

## 2. Dropdown Menu & Model Selection

Once the Model Selector Button is clicked, a Radix-based portal-rendered dropdown menu is mounted to the DOM.

### Target Item Selection
- **Heuristic**: Search for all visible elements with `role="menuitem"`, `role="option"`, or standard clickable elements (`div`, `button`, `span`) inside the visible portal dropdown containing the exact string `"Claude Sonnet 4.6"`.
- **Exclusion**: Ignore locked options (they have a lock icon or contain text/attributes implying lock/premium lock like `"Max"` and are not selectable without a paid tier).
- **Click Behavior**: Clicking the model option (e.g., "Claude Sonnet 4.6") will set it as the active model and typically close the dropdown.

---

## 3. "Thinking" Toggle Switch

The "Thinking" toggle option is inside the same dropdown menu.

### Identification
- **Row Locator**: Find the element (e.g., `div` or row container) that contains the text `"Thinking"` (case-insensitive).
- **Switch Element**: Inside or adjacent to the `"Thinking"` row, find the switch component:
  - Typically a Radix primitive: `button[role="switch"]`
  - Alternately a standard `<input type="checkbox">` or a clickable toggle wrapper.
- **State Check**:
  - Radix switch buttons use the attribute `aria-checked="true"` or `aria-checked="false"`.
  - Checkboxes use the `.checked` property.
  - If the state is `"false"` (or unchecked), we click it to toggle it **ON**.
  - If it is already `"true"`, we leave it alone.

---

## 4. SPA State & Orchestration Challenges

- **Dynamic Navigation**: Perplexity is a Single Page Application. Thread changes, initial loads, or query submissions can silently re-create or reset the model state to "Best" or another default.
- **Debounced Observer**: We must observe DOM changes using `MutationObserver`. To avoid thrashing the browser or causing lag, we debounce the observer's callback by `150ms`.
- **Lock & Cooldown**: Executing the click events (clicking the button, clicking the model option, clicking the toggle switch) takes multiple ticks and fires DOM mutation events. We implement a boolean lock (`isInteracting`) and a cooldown to ensure we don't open/close menus infinitely.
- **Click Event Fidelity**: Standard element `.click()` is preferred, but for stubborn Radix items, we will support synthetic PointerEvents and MouseEvents to ensure compliance with modern React event listeners.
