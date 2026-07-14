# Toppreise Price Alarm Automator

Userscript that fully automates the configuration of a price alarm on Toppreise.ch.
![alt text](image.png)
## 🚀 Installation

### 👉 [**CLICK HERE TO INSTALL USERSCRIPT**](https://github.com/tazztone/scripts/raw/refs/heads/main/userscripts/topp-alarm/topp-alarm.user.js?v=0.4.0)
*(Requires Violentmonkey / Tampermonkey)*

## Logic
When you click the "Preisalarm hinzufügen" (Bell icon) button on either a product page or an overview/search list page:
1. The script instantly intercepts the dynamic modal mounting.
2. It extracts the present reference price (shipping incl.) from the header.
3. Calculates the target alert at **60%** of the value.
4. Sets duration automatically to **2 years**.
5. Ensures the GDPR/Privacy Policy checkbox is selected.
6. Automatically submits the form and closes the confirmation modal upon successful creation.

## Configuration

You can configure this script directly on Toppreise.ch! A small floating **gear button** appears in the bottom-right corner of the window. Clicking it opens a premium, glassmorphic settings panel where you can edit and apply settings instantly:

- **Enable Auto-Fill**: Toggle switch to turn the alarm automatic filling functionality on or off.
- **Target Price Percent (%)**: Adjust the percentage value (slider and number input) to set the target threshold for price alerts.
- **Alarm Expiry Duration**: Choose the duration for the price alarm (options: `3m` / `6m` / `1y` / `2y`).
- **Auto-Submit**: Toggle switch to instantly submit the alarm once the fields are filled.

These settings are saved persistently in your browser using the userscript manager's `GM_getValue` and `GM_setValue` APIs (with an automatic `localStorage` fallback).

For manual default configurations, you can also edit the `DEFAULTS` block at the top of the userscript.

## Requirements
- You must be logged in to your Toppreise.ch user account beforehand so the system attaches the alert to your profile instantly.
