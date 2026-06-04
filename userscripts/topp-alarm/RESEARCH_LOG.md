# Toppreise Alarm Automation - Research Log

This document details the DOM structure and selection strategies used to automate setting price alarms on Toppreise.ch.

## 1. Trigger & Verification Selectors

### Modal Container
- **Selector**: `.Plugin_NewInfoMailForm`
- **Inside**: `.AbstractDialog.AbstractDialog_NewInfoMailFormDialog`
- **Visibility Detection**: The form is injected dynamically via AJAX into `.AbstractDialog_Content`. Detecting the presence of `.Plugin_NewInfoMailForm` ensures the modal content is fully loaded.

### State Marker
To prevent infinite loops of processing the same open modal, we inject an attribute:
- `[data-tp-alarm-processed="true"]`

---

## 2. Element Selectors

### Present Value Extraction
- **Price Text Selector**: `.Plugin_NewInfoMailForm .shippingPrice .Plugin_Price`
- **Fallback**: `.Plugin_NewInfoMailForm .productPrice .Plugin_Price`
- **Processing**: Extract text, remove formatting like `'` (thousands) and replace `,` if present, parse as Float.

### Target Price Input
- **Selector**: `input#f_NewInfoMailForm_priceFrom`
- **Fallback**: `input[name="im_nimf_pvf"]`

### Duration Configuration
- **Hidden Input**: `input[name="im_nimf_du"]`
- **Action**: Set value to `"730"` (corresponds to 2 years).
- **Visual UI Enhancement**: The visual selector is a list item `li[data-value="730"]` inside a custom dropdown. Simulating a click on this item guarantees visual and internal state synchronization.

### Terms / Privacy Confirmation
- **Selector**: `input#im_nimf_prtrm`
- **Action**: Must be checked (`.checked = true`) before submission.

### Confirmation Button
- **Selector**: `.Plugin_NewInfoMailForm input.f_submitbtn`
- **Verification**: Has `value="Übernehmen"` or `value="Übernehmen / Hinzufügen"`.

---

## 3. Event Management

- **Input Simulation**: When changing `input#f_NewInfoMailForm_priceFrom`, fire an `'input'` and `'change'` event so internal validation triggers correctly.
- **Submit Action**: A direct `.click()` on the button is safe.

---

## 4. Lifecycle & SPA

The script employs a `MutationObserver` tracking insertions to the DOM. 
- **Enter Loop**: Detects `.Plugin_NewInfoMailForm`.
- **Condition**: Modal not already marked processed.
- **Action**:
  1. Mark modal as processed (`dataset.tpAlarmProcessed = true`).
  2. Read current base price.
  3. Calculate 60% value -> Set value -> Dispatch events.
  4. Trigger the duration click or value set.
  5. Ensure GDPR checkbox is checked.
  6. Click submit.

---

## 5. Overview List & Search Pages

On overview list pages (e.g. `/produktsuche/*` or search lists):
- **Bell Icon (Trigger)**: Hovering over any product row reveals a bell icon (`A.Plugin_NewInfoMailButton.Plugin_Button.icon-notify`).
- **Modal Dialog**: Clicking the bell icon mounts the exact same dynamic modal container (`.Plugin_NewInfoMailForm`) under `#tmpAbstractDialogContainer`.
- **Price Element**: The modal contains `.shippingPrice .Plugin_Price` or `.productPrice .Plugin_Price` representing the specific clicked product's price, ensuring the script successfully parses and configures the alarm target for that product.
- **Global Fallback Safeguard**: The global fallback selector (`document.querySelector('.pageContent .priceContainer .Plugin_Price')`) is restricted to product pages only. This prevents list/search pages from incorrectly picking up a global price container of an unrelated product.
- **Auto-Close Confirmation Screen**: After form submission, a polling loop runs every 200ms checking if the form has been removed from the document tree (which occurs when the AJAX submission replaces the content, detaching the original form elements). To avoid `closest()` queries returning `null` on detached elements, references to the dialog and close button (`.AbstractDialog_CloseButton`) are resolved *before* submission, and `document.contains(modalContainer)` is used as the detachment detector. Once the form is detached, the script clicks the close button. If a validation error occurs and the form remains attached, the loop times out after 3 seconds without closing.
