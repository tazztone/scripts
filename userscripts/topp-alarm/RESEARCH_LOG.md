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
