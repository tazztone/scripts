// ==UserScript==
// @name         Hugging Face Yellow Hearts
// @namespace    https://github.com/tazztone/scripts
// @version      1.0.0
// @description  Make the heart icons on Hugging Face larger and pop out in yellow.
// @author       tazztone
// @match        https://huggingface.co/models*
// @run-at       document-start
// @grant        none
// @noframes
// ==/UserScript==

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const CONFIG = {
  ENABLED: true,
  COLOR_IDLE: '#fbbf24',    // Tailwind Amber 400
  COLOR_HOVER: '#f59e0b',   // Tailwind Amber 500
  SCALE_IDLE: '1.35',
  SCALE_HOVER: '1.6',
};

// ─── STYLES ──────────────────────────────────────────────────────────────────
const STYLE = `
  /* Target the heart SVG by its unique outline path */
  svg:has(path[d^="M22.45"]) {
    color: ${CONFIG.COLOR_IDLE} !important;
    fill: currentColor !important;
    transform: scale(${CONFIG.SCALE_IDLE}) !important;
    transform-origin: center !important;
    transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), color 0.2s ease, filter 0.2s ease !important;
  }

  /* Hover state for a premium micro-animation pop out */
  svg:has(path[d^="M22.45"]):hover {
    transform: scale(${CONFIG.SCALE_HOVER}) !important;
    color: ${CONFIG.COLOR_HOVER} !important;
    filter: drop-shadow(0 0 6px rgba(251, 191, 36, 0.65)) !important;
    cursor: pointer;
  }

  /* Prevent parent container from clipping the scaled SVG */
  div:has(> svg:has(path[d^="M22.45"])),
  button:has(> svg:has(path[d^="M22.45"])) {
    overflow: visible !important;
  }
`;
// ─────────────────────────────────────────────────────────────────────────────

(() => {
  'use strict';

  if (!CONFIG.ENABLED) return;

  // Inject styles immediately at document-start
  const styleEl = document.createElement('style');
  styleEl.textContent = STYLE;
  
  // Append to head or documentElement depending on DOM load state
  const target = document.head || document.documentElement;
  if (target) {
    target.appendChild(styleEl);
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      document.head.appendChild(styleEl);
    });
  }
})();
