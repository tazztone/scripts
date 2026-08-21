// ==UserScript==
// @name         Hugging Face Inline Liking, Unliked Model Highlighter, Date & Negative Filter
// @namespace    https://github.com/tazztone/scripts
// @version      2.0.2
// @description  Like or unlike model cards inline, highlight unliked models, and filter models by date range slider and negative text keywords.
// @author       tazztone
// @match        https://huggingface.co/*
// @updateURL    https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/huggingface/huggingface-heart.user.js
// @downloadURL  https://raw.githubusercontent.com/tazztone/scripts/main/userscripts/huggingface/huggingface-heart.user.js
// @run-at       document-start
// @grant        GM_getValue
// @grant        GM_setValue
// @noframes
// ==/UserScript==

// ─── CONFIG DEFAULT VALUES ───────────────────────────────────────────────────
const DEFAULTS = {
  BORDER_UNLIKED_ENABLED: true,
  BORDER_UNLIKED_COLOR: '#10b981',
  BORDER_UNLIKED_GLOW: true,
  DATE_FILTER_ENABLED: false,
  DATE_MIN_DAYS: 0,
  DATE_MAX_DAYS: 30,
  DATE_PRESET: 'all',
  FILTER_EXCLUDE_ENABLED: true,
  FILTER_EXCLUDE_TERMS: '',
  WIDGET_COLLAPSED: false
};

const PRESETS = [
  { id: '24h', label: '24h', min: 0, max: 1 },
  { id: '3d', label: '3d', min: 0, max: 3 },
  { id: '7d', label: '7d', min: 0, max: 7 },
  { id: '14d', label: '14d', min: 0, max: 14 },
  { id: '30d', label: '30d', min: 0, max: 30 },
  { id: '60d', label: '60d', min: 0, max: 60 },
  { id: '90d', label: '90d', min: 0, max: 90 },
  { id: '180d', label: '180d', min: 0, max: 180 },
  { id: '1y', label: '1y', min: 0, max: 365 },
  { id: 'all', label: 'All', min: 0, max: 99999 }
];

const RESERVED_MODEL_PREFIXES = new Set([
  'models', 'datasets', 'spaces', 'docs', 'posts', 'papers', 'settings', 'login',
  'logout', 'join', 'pricing', 'notifications', 'search', 'tasks', 'tags',
  'organizations', 'collections', 'chat', 'blog', 'brands', 'discussions'
]);

const HEART_PATH_SIGNATURES = [
  '22.45', 'm0-2', 'M22.5,4', 'M22.5 4'
];

const NON_HEART_PATH_SIGNATURES = ['4.318', '14c1.49', '20.91'];

// Minimal host stylesheet for card modifications and empty state banner
const CARD_STYLES = `
  article.overview-card-wrapper.hf-is-unliked {
    border: 2px solid VAR_COLOR !important;
    border-radius: 12px !important;
    VAR_GLOW
    transition: border 0.3s ease, box-shadow 0.3s ease !important;
  }
  article.overview-card-wrapper.hf-is-liked {
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
  }
  article.overview-card-wrapper.hf-filtered-out,
  article.overview-card-wrapper.hf-date-filtered-out,
  article.overview-card-wrapper.hf-text-filtered-out {
    display: none !important;
  }
  .hf-inline-like-btn {
    cursor: pointer !important;
  }
  #hf-df-empty-notice {
    margin: 12px 0;
    padding: 10px 14px;
    border: 1px dashed rgba(245, 158, 11, 0.4);
    border-radius: 10px;
    background: rgba(245, 158, 11, 0.08);
    color: #fbbf24;
    font-size: 12px;
    text-align: center;
    line-height: 1.4;
  }
`;

// Scoped Shadow DOM styles for the filter sidebar widget and toasts
const SHADOW_WIDGET_STYLES = `
  :host {
    all: initial;
    display: block;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin-bottom: 12px;
  }
  #hf-date-filter-widget {
    box-sizing: border-box;
    width: 100%;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    background: rgba(15, 23, 42, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    color: #f1f5f9;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    transition: all 0.2s ease;
    overflow: hidden;
  }
  #hf-date-filter-widget.has-active-filters {
    border-color: rgba(245, 158, 11, 0.35);
  }

  /* ── HEADER (COLLAPSIBLE BAR) ── */
  .hf-df-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 10px;
    cursor: pointer;
    user-select: none;
    background: rgba(255, 255, 255, 0.02);
    transition: background 0.15s ease;
    gap: 8px;
  }
  .hf-df-header:hover {
    background: rgba(255, 255, 255, 0.06);
  }
  .hf-df-header-left {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
  }
  .hf-df-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #fbbf24;
    display: flex;
    align-items: center;
    gap: 5px;
    white-space: nowrap;
  }
  .hf-df-summary-chips {
    display: flex;
    align-items: center;
    gap: 4px;
    overflow: hidden;
  }
  .hf-df-chip {
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 4px;
    background: rgba(245, 158, 11, 0.18);
    color: #fde68a;
    border: 1px solid rgba(245, 158, 11, 0.3);
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
    max-width: 140px;
  }
  .hf-df-header-right {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }
  .hf-df-badge {
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    font-size: 10px;
    font-weight: 600;
    white-space: nowrap;
  }
  .hf-df-header-btn {
    background: none;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    cursor: pointer;
    padding: 2px 5px;
    border-radius: 4px;
    font-size: 10px;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }
  .hf-df-header-btn:hover {
    color: #f8fafc;
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
  }
  .hf-df-collapse-icon {
    transition: transform 0.2s ease;
  }
  #hf-date-filter-widget.collapsed .hf-df-collapse-icon {
    transform: rotate(-90deg);
  }

  /* ── WIDGET BODY ── */
  .hf-widget-body {
    padding: 8px 10px 10px 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  #hf-date-filter-widget.collapsed .hf-widget-body {
    display: none !important;
  }

  /* ── SECTION COMPACT LAYOUTS ── */
  .hf-filter-section {
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }
  .hf-filter-section:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }
  .hf-filter-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 5px;
  }
  .hf-filter-section-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #cbd5e1;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .hf-section-body {
    transition: opacity 0.2s ease;
  }
  .hf-section-dimmed {
    opacity: 0.45;
  }

  /* Exclude Input Row */
  .hf-exclude-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .hf-exclude-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
    flex: 1;
  }
  .hf-exclude-input {
    box-sizing: border-box;
    width: 100%;
    height: 26px;
    padding: 3px 22px 3px 7px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 5px;
    background: rgba(15, 23, 42, 0.85);
    color: #f8fafc;
    font-size: 11px;
    font-family: inherit;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }
  .hf-exclude-input:focus {
    outline: none;
    border-color: #f59e0b;
    box-shadow: 0 0 0 1px #f59e0b;
  }
  .hf-clear-btn {
    position: absolute;
    right: 5px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: #94a3b8;
    font-size: 12px;
    line-height: 1;
    cursor: pointer;
    padding: 1px 3px;
    border-radius: 3px;
    display: none;
  }
  .hf-clear-btn.visible {
    display: block;
  }
  .hf-clear-btn:hover {
    color: #f87171;
  }

  /* Date Presets Row */
  .hf-df-presets {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
    margin-bottom: 6px;
  }
  .hf-df-preset-btn {
    padding: 2px 6px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.04);
    color: #94a3b8;
    font-size: 10px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    line-height: 1.2;
  }
  .hf-df-preset-btn:hover {
    background: rgba(251, 191, 36, 0.12);
    color: #fef08a;
    border-color: rgba(251, 191, 36, 0.35);
  }
  .hf-df-preset-btn.active {
    background: rgba(245, 158, 11, 0.22);
    color: #fbbf24;
    border-color: #f59e0b;
    box-shadow: 0 0 6px rgba(245, 158, 11, 0.25);
  }

  /* Date Controls (Slider + Inline Inputs) */
  .hf-df-controls {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .hf-df-slider-inputs-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .hf-df-slider-inputs-row input[type="range"] {
    flex: 1;
    accent-color: #f59e0b;
    height: 4px;
    cursor: pointer;
  }
  .hf-df-inline-input {
    box-sizing: border-box;
    width: 44px;
    height: 22px;
    padding: 1px 4px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 4px;
    background: rgba(15, 23, 42, 0.85);
    color: #f8fafc;
    font-size: 10px;
    text-align: center;
    font-family: inherit;
  }
  .hf-df-inline-input:focus {
    outline: none;
    border-color: #f59e0b;
  }
  .hf-df-range-label {
    font-size: 10px;
    color: #94a3b8;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Status Subdetails */
  .hf-df-substatus {
    font-size: 9px;
    color: #94a3b8;
    text-align: right;
    min-height: 11px;
    margin-top: -2px;
  }

  /* Switch Toggle */
  .hf-switch {
    width: 28px;
    height: 16px;
    position: relative;
    display: inline-block;
    flex-shrink: 0;
  }
  .hf-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }
  .hf-slider {
    position: absolute;
    inset: 0;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.8);
    cursor: pointer;
    transition: background 0.2s ease;
  }
  .hf-slider::before {
    content: "";
    position: absolute;
    left: 2px;
    bottom: 2px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #94a3b8;
    transition: transform 0.2s ease, background 0.2s ease;
  }
  .hf-switch input:checked + .hf-slider {
    background: #f59e0b;
    border-color: #f59e0b;
  }
  .hf-switch input:checked + .hf-slider::before {
    transform: translateX(12px);
    background: #fff;
  }

  /* Highlighter Settings */
  .hf-df-settings-toggle {
    background: none;
    border: none;
    color: #94a3b8;
    font-size: 10px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 0;
    transition: color 0.15s ease;
  }
  .hf-df-settings-toggle:hover {
    color: #fbbf24;
  }
  .hf-df-settings-panel {
    display: none;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    gap: 6px;
    flex-direction: column;
  }
  .hf-df-settings-panel.open {
    display: flex;
  }
  .hf-settings-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 10px;
    color: #cbd5e1;
  }
  .hf-settings-row input[type="color"] {
    width: 24px;
    height: 18px;
    padding: 0;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 3px;
    background: transparent;
    cursor: pointer;
  }

  #hf-toast-container {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 100000;
    display: flex;
    flex-direction: column-reverse;
    gap: 8px;
    pointer-events: none;
  }
  .hf-toast {
    background: rgba(15, 23, 42, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #f8fafc;
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    box-shadow: 0 4px 14px rgba(0,0,0,0.35);
    pointer-events: auto;
    transition: opacity 0.3s ease, transform 0.3s ease;
  }
  .hf-toast.fade-out {
    opacity: 0;
    transform: translateY(6px);
  }
`;

(() => {
  'use strict';

  let widgetShadowRoot = null;
  let processRunId = 0;

  const loadConfig = () => {
    const config = { ...DEFAULTS };
    for (const key of Object.keys(DEFAULTS)) {
      try {
        let stored = null;
        if (typeof GM_getValue !== 'undefined') {
          stored = GM_getValue(key, null);
        }
        if (stored === null) {
          const local = localStorage.getItem(`hf_heart_${key}`);
          if (local !== null) stored = JSON.parse(local);
        }
        if (stored !== null) config[key] = stored;
      } catch (e) {}
    }
    return config;
  };

  const saveConfig = (key, value) => {
    CONFIG[key] = value;
    try {
      if (typeof GM_setValue !== 'undefined') {
        GM_setValue(key, value);
        return;
      }
    } catch (e) {}
    try {
      localStorage.setItem(`hf_heart_${key}`, JSON.stringify(value));
    } catch (e) {}
  };

  const CONFIG = loadConfig();
  const inlineLikeStates = new Map();
  const inlineLikePending = new WeakSet();

  const buildStyle = () => {
    const glowCss = CONFIG.BORDER_UNLIKED_GLOW
      ? `box-shadow: 0 4px 20px rgba(16, 185, 129, 0.15) !important;`
      : '';
    return CARD_STYLES
      .replace('VAR_COLOR', CONFIG.BORDER_UNLIKED_COLOR)
      .replace('VAR_GLOW', glowCss);
  };

  function injectStyles() {
    let styleEl = document.getElementById('hf-heart-style');
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = 'hf-heart-style';
      (document.head || document.documentElement).appendChild(styleEl);
    }
    styleEl.textContent = buildStyle();
  }

  function showToast(message, durationMs = 3000) {
    let container = widgetShadowRoot?.getElementById('hf-toast-container');
    if (!container) {
      let toastHost = document.getElementById('hf-toast-root');
      if (!toastHost) {
        toastHost = document.createElement('div');
        toastHost.id = 'hf-toast-root';
        document.body.appendChild(toastHost);
      }
      const shadow = toastHost.shadowRoot || toastHost.attachShadow({ mode: 'open' });
      if (!shadow.getElementById('hf-toast-container')) {
        shadow.innerHTML = `
          <style>
            #hf-toast-container { position: fixed; bottom: 24px; right: 24px; z-index: 99999; display: flex; flex-direction: column-reverse; gap: 8px; pointer-events: none; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            .hf-toast { background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 10px 16px; border-radius: 8px; font-size: 13px; box-shadow: 0 4px 14px rgba(0,0,0,0.35); pointer-events: auto; transition: opacity 0.3s ease, transform 0.3s ease; }
            .hf-toast.fade-out { opacity: 0; transform: translateY(6px); }
          </style>
          <div id="hf-toast-container"></div>
        `;
      }
      container = shadow.getElementById('hf-toast-container');
    }
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'hf-toast';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('fade-out');
      toast.addEventListener('transitionend', () => toast.remove());
      setTimeout(() => toast.remove(), 400);
    }, durationMs);
  }

  // ─── MODEL IDENTIFICATION & PARSING ──────────────────────────────────────────
  function normalizeModelId(modelId) {
    return modelId ? modelId.toLowerCase() : '';
  }

  function getLikeEndpoint(modelId) {
    const encodedParts = modelId.split('/').map(part => encodeURIComponent(part));
    return `/api/models/${encodedParts.join('/')}/like`;
  }

  function getModelIdFromCard(card) {
    const anchors = card.querySelectorAll('a[href^="/"]');
    for (const anchor of anchors) {
      const href = anchor.getAttribute('href');
      if (!href) continue;

      const cleanPath = href.split('?')[0].split('#')[0].replace(/^\//, '');
      const parts = cleanPath.split('/');
      if (parts.length === 2 && parts[0] && parts[1] && !RESERVED_MODEL_PREFIXES.has(parts[0].toLowerCase())) {
        return cleanPath;
      }
    }
    return null;
  }

  // ─── SVG & HEART DETECTION ───────────────────────────────────────────────────
  function hasHeartPath(svg) {
    const paths = svg.querySelectorAll('path');
    let hasHeartSignature = false;

    for (const path of paths) {
      const d = path.getAttribute('d') || '';
      if (NON_HEART_PATH_SIGNATURES.some(signature => d.includes(signature))) continue;
      if (HEART_PATH_SIGNATURES.some(signature => d.includes(signature))) {
        hasHeartSignature = true;
      }
    }

    return hasHeartSignature;
  }

  function isHeartSvg(svg) {
    return Boolean(svg && hasHeartPath(svg));
  }

  function findHeartSvg(card) {
    const markedContainer = card.querySelector('[title*="like" i], [aria-label*="like" i], [class*="heart" i], [class*="like" i]');
    if (markedContainer) {
      const markedSvgs = markedContainer.tagName?.toLowerCase() === 'svg'
        ? markedContainer
        : markedContainer.querySelectorAll('svg');
      const markedSvg = Array.from(markedSvgs).find(isHeartSvg);
      if (markedSvg) return markedSvg;
    }

    const footerContainers = Array.from(card.querySelectorAll('div.mr-1.flex.items-center')).reverse();
    for (const container of footerContainers) {
      const svg = container.querySelector('svg');
      if (svg && isHeartSvg(svg)) return svg;
    }

    for (const svg of card.querySelectorAll('svg')) {
      if (isHeartSvg(svg)) return svg;
    }

    return null;
  }

  function isModelLiked(card, modelId) {
    const stateKey = normalizeModelId(modelId);
    if (stateKey && inlineLikeStates.has(stateKey)) {
      return inlineLikeStates.get(stateKey);
    }

    const likeBtn = Array.from(card.querySelectorAll('[title*="like" i], [aria-label*="like" i]'))
      .find(element => !element.hasAttribute('data-hf-inline-bound'));
    if (likeBtn) {
      const ariaPressed = likeBtn.getAttribute('aria-pressed');
      if (ariaPressed === 'true') return true;
      if (ariaPressed === 'false') return false;
    }

    const heartSvg = findHeartSvg(card);
    if (!heartSvg) return false;

    const classListStr = (heartSvg.className?.baseVal || heartSvg.className || '').toString();
    const parentClassStr = (heartSvg.parentElement?.className || '').toString();
    const grandParentClassStr = (heartSvg.parentElement?.parentElement?.className || '').toString();
    const combined = `${classListStr} ${parentClassStr} ${grandParentClassStr}`;

    if (/(text|fill)-(red|rose|pink)-\d+/i.test(combined) || /text-red/i.test(combined)) {
      return true;
    }

    const svgFill = (heartSvg.getAttribute('fill') || '').toLowerCase();
    const colorStyle = (heartSvg.style.color || '').toLowerCase();

    if (['#ef4444', '#e11d48', '#f43f5e', 'red', '#dc2626', '#b91c1c'].includes(svgFill)) {
      return true;
    }
    if (colorStyle.includes('239, 68, 68') || colorStyle.includes('225, 29, 72') || colorStyle.includes('244, 63, 94')) {
      return true;
    }

    const paths = heartSvg.querySelectorAll('path');
    for (const path of paths) {
      const d = path.getAttribute('d') || '';

      if (d.includes('M22.5,4') || d.includes('M22.5 4')) {
        return true;
      }

      if (d.includes('22.45') || d.includes('m0-2') || d.includes('26.13')) {
        return false;
      }

      const pathFill = (path.getAttribute('fill') || '').toLowerCase();
      if (pathFill === 'none' || pathFill === 'transparent') {
        return false;
      }
    }

    if (/(text|fill)-(gray|slate|neutral|zinc|stone)-\d+/i.test(combined)) {
      return false;
    }

    return false;
  }

  function setAttributeOrRemove(element, name, value) {
    if (value === null) {
      element.removeAttribute(name);
    } else {
      element.setAttribute(name, value);
    }
  }

  function updateNativeHeartVisual(heartSvg, isLiked) {
    if (!heartSvg) return;

    if (isLiked) {
      heartSvg.classList.add('text-red-500');
      heartSvg.classList.remove('text-gray-400');
    } else {
      heartSvg.classList.remove('text-red-500');
      heartSvg.classList.add('text-gray-400');
    }

    for (const path of heartSvg.querySelectorAll('path')) {
      path.setAttribute('fill', isLiked ? 'currentColor' : 'none');
    }
  }

  function getHeartContainer(heartSvg) {
    if (!heartSvg) return null;

    const knownContainer = heartSvg.closest('div.mr-1.flex.items-center, button, [role="button"]');
    if (knownContainer) return knownContainer;

    const parent = heartSvg.parentElement;
    return parent && parent.tagName.toLowerCase() !== 'a' ? parent : heartSvg;
  }

  // ─── NEGATIVE FILTER PARSING & MATCHING ──────────────────────────────────────
  function parseNegativeFilter(rawTerms) {
    if (!rawTerms || typeof rawTerms !== 'string') return [];
    const trimmed = rawTerms.trim();
    if (!trimmed) return [];

    const matchers = [];
    const tokens = trimmed.split(/[,;\n]+/).map(t => t.trim()).filter(Boolean);

    for (const token of tokens) {
      const regexMatch = token.match(/^\/(.+)\/([gimsuy]*)$/);
      if (regexMatch) {
        try {
          matchers.push({
            type: 'regex',
            value: new RegExp(regexMatch[1], regexMatch[2] || 'i'),
            raw: token
          });
        } catch (e) {
          matchers.push({
            type: 'substring',
            value: token.toLowerCase(),
            raw: token
          });
        }
      } else {
        matchers.push({
          type: 'substring',
          value: token.toLowerCase(),
          raw: token
        });
      }
    }
    return matchers;
  }

  function isCardExcludedByText(card, modelId, matchers) {
    if (!matchers || matchers.length === 0) return false;
    const cardText = (card.textContent || '').toLowerCase();
    const cleanId = (modelId || '').toLowerCase();

    for (const matcher of matchers) {
      if (matcher.type === 'substring') {
        if (cleanId.includes(matcher.value) || cardText.includes(matcher.value)) {
          return true;
        }
      } else if (matcher.type === 'regex') {
        if (matcher.value.test(modelId || '') || matcher.value.test(card.textContent || '')) {
          return true;
        }
      }
    }
    return false;
  }

  // ─── DATE HELPERS WITH DATASET CACHING ───────────────────────────────────────
  function getModelDate(card) {
    if (card.dataset.hfDateTimestamp) {
      const cached = Number(card.dataset.hfDateTimestamp);
      if (!isNaN(cached)) return cached;
    }
    const timeEl = card.querySelector('time');
    if (!timeEl) return null;

    let result = null;
    const dtAttr = timeEl.getAttribute('datetime') || timeEl.getAttribute('title');
    if (dtAttr) {
      const parsed = Date.parse(dtAttr);
      if (!isNaN(parsed)) result = parsed;
    }

    if (result === null) {
      const text = timeEl.textContent.trim();
      if (text) {
        const parsedText = Date.parse(text);
        if (!isNaN(parsedText)) {
          result = parsedText;
        } else {
          const match = text.match(/(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago/i);
          if (match) {
            const amount = parseInt(match[1], 10);
            const unit = match[2].toLowerCase();
            const now = Date.now();
            const multipliers = {
              minute: 60 * 1000,
              hour: 3600 * 1000,
              day: 86400 * 1000,
              week: 7 * 86400 * 1000,
              month: 30 * 86400 * 1000,
              year: 365 * 86400 * 1000
            };
            result = now - (amount * (multipliers[unit] || 86400 * 1000));
          }
        }
      }
    }

    if (result !== null) {
      card.dataset.hfDateTimestamp = String(result);
    }
    return result;
  }

  function getDaysAgo(timestamp) {
    if (timestamp === null || timestamp === undefined) return null;
    const diffMs = Date.now() - timestamp;
    return Math.max(0, Math.floor(diffMs / (86400 * 1000)));
  }

  function formatDateLabel(days) {
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days >= 36500) return 'All time';
    const date = new Date(Date.now() - days * 86400 * 1000);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  // ─── CARD VISUAL STATE & ACCESSIBILITY ───────────────────────────────────────
  function updateCardVisual(card, modelId) {
    const isLiked = isModelLiked(card, modelId);

    if (isLiked) {
      card.classList.remove('hf-is-unliked');
      if (CONFIG.BORDER_UNLIKED_ENABLED) card.classList.add('hf-is-liked');
    } else {
      card.classList.remove('hf-is-liked');
      if (CONFIG.BORDER_UNLIKED_ENABLED) card.classList.add('hf-is-unliked');
    }

    if (!CONFIG.BORDER_UNLIKED_ENABLED) {
      card.classList.remove('hf-is-unliked', 'hf-is-liked');
    }

    const heartSvg = findHeartSvg(card);
    const container = getHeartContainer(heartSvg);
    if (container?.dataset.hfInlineBound === modelId) {
      updateInlineAccessibility(container, modelId, isLiked);
    }
    if (modelId && inlineLikeStates.has(normalizeModelId(modelId))) {
      updateNativeHeartVisual(heartSvg, isLiked);
    }
  }

  function updateInlineAccessibility(container, modelId, isLiked) {
    if (!container) return;

    container.setAttribute('role', 'button');
    container.tabIndex = 0;
    container.setAttribute('aria-pressed', String(isLiked));
    container.setAttribute('aria-label', `${isLiked ? 'Unlike' : 'Like'} ${modelId} inline`);
  }

  function findLikeCountNode(container) {
    if (!container) return null;

    const textNode = Array.from(container.childNodes).find(node =>
      node.nodeType === Node.TEXT_NODE && /^\s*\d+\s*$/.test(node.textContent || '')
    );
    if (textNode) return textNode;

    return Array.from(container.children).find(element =>
      !element.querySelector('svg') && /^\s*\d+\s*$/.test(element.textContent || '')
    ) || null;
  }

  function updateLikeCountText(container, isNowLiked) {
    const countNode = findLikeCountNode(container);
    if (!countNode) return;

    const currentText = countNode.textContent.trim();
    const currentValue = parseInt(currentText, 10);
    const nextValue = isNowLiked ? currentValue + 1 : Math.max(0, currentValue - 1);
    countNode.textContent = countNode.nodeType === Node.TEXT_NODE ? ` ${nextValue}` : String(nextValue);
  }

  function captureInlineVisual(container, heartSvg) {
    return {
      heartClass: heartSvg?.getAttribute('class') ?? null,
      pathFills: heartSvg ? Array.from(heartSvg.querySelectorAll('path')).map(path => path.getAttribute('fill')) : [],
      ariaPressed: container?.getAttribute('aria-pressed') ?? null,
      ariaLabel: container?.getAttribute('aria-label') ?? null,
      countNode: findLikeCountNode(container),
      countText: findLikeCountNode(container)?.textContent ?? null
    };
  }

  function restoreInlineVisual(container, heartSvg, snapshot) {
    if (heartSvg) {
      setAttributeOrRemove(heartSvg, 'class', snapshot.heartClass);
      Array.from(heartSvg.querySelectorAll('path')).forEach((path, index) => {
        setAttributeOrRemove(path, 'fill', snapshot.pathFills[index] ?? null);
      });
    }

    if (container) {
      setAttributeOrRemove(container, 'aria-pressed', snapshot.ariaPressed);
      setAttributeOrRemove(container, 'aria-label', snapshot.ariaLabel);
      if (snapshot.countNode && snapshot.countText !== null) {
        snapshot.countNode.textContent = snapshot.countText;
      }
    }
  }

  // ─── INLINE LIKE INTERACTION & EVENT BINDING ────────────────────────────────
  async function toggleInlineLike(card, modelId, container) {
    if (inlineLikePending.has(container)) return;

    const stateKey = normalizeModelId(modelId);
    const wasLiked = isModelLiked(card, modelId);
    const hadOverride = inlineLikeStates.has(stateKey);
    const previousOverride = inlineLikeStates.get(stateKey);
    const heartSvg = findHeartSvg(card);
    const snapshot = captureInlineVisual(container, heartSvg);
    const nextLiked = !wasLiked;

    inlineLikePending.add(container);
    inlineLikeStates.set(stateKey, nextLiked);
    updateCardVisual(card, modelId);
    updateLikeCountText(container, nextLiked);

    try {
      let failure = null;
      let requiresLogin = false;
      try {
        const response = await fetch(getLikeEndpoint(modelId), {
          method: nextLiked ? 'POST' : 'DELETE',
          credentials: 'same-origin',
          headers: { Accept: 'application/json' }
        });

        if (response.status === 401 || response.status === 403) {
          requiresLogin = true;
          failure = new Error(`Like request rejected with HTTP ${response.status}`);
        } else if (!response.ok) {
          failure = new Error(`Like request failed with HTTP ${response.status}`);
        }
      } catch (error) {
        failure = error;
      }

      if (failure) {
        if (hadOverride) {
          inlineLikeStates.set(stateKey, previousOverride);
        } else {
          inlineLikeStates.delete(stateKey);
        }
        restoreInlineVisual(container, heartSvg, snapshot);
        updateCardVisual(card, modelId);

        if (requiresLogin) {
          showToast('Please log in to Hugging Face to like models directly.');
        } else {
          console.error('[HF Inline Like] Failed to update like status:', failure);
        }
      }
    } finally {
      inlineLikePending.delete(container);
    }
  }

  function setupHeartButton(card, modelId) {
    const heartSvg = findHeartSvg(card);
    if (!heartSvg) return;

    const container = getHeartContainer(heartSvg);
    if (!container || container.dataset.hfInlineBound === modelId) return;

    container.dataset.hfInlineBound = modelId;
    container.classList.add('hf-inline-like-btn');
    container.style.cursor = 'pointer';
    updateInlineAccessibility(container, modelId, isModelLiked(card, modelId));

    container.addEventListener('mousedown', event => event.stopPropagation(), true);
    container.addEventListener('mouseup', event => event.stopPropagation(), true);
    container.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation?.();
      toggleInlineLike(card, modelId, container);
    }, true);
    container.addEventListener('keydown', event => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation?.();
      toggleInlineLike(card, modelId, container);
    }, true);
  }

  // ─── ASYNC BATCH MODEL CARD PROCESSING (INP & RUN-ID GUARD) ──────────────────
  async function processModelCards() {
    const runId = ++processRunId;
    const cards = Array.from(document.querySelectorAll('article.overview-card-wrapper'));
    const totalCards = cards.length;
    let visibleCards = 0;
    let hiddenByDate = 0;
    let hiddenByText = 0;

    const isDateFilterActive = Boolean(CONFIG.DATE_FILTER_ENABLED);
    const minDays = CONFIG.DATE_MIN_DAYS;
    const maxDays = CONFIG.DATE_MAX_DAYS;

    const isTextFilterActive = Boolean(CONFIG.FILTER_EXCLUDE_ENABLED && (CONFIG.FILTER_EXCLUDE_TERMS || '').trim());
    const matchers = isTextFilterActive ? parseNegativeFilter(CONFIG.FILTER_EXCLUDE_TERMS) : [];

    const batchSize = 20;
    for (let i = 0; i < cards.length; i += batchSize) {
      if (runId !== processRunId) return;

      const chunk = cards.slice(i, i + batchSize);
      for (const card of chunk) {
        const modelId = getModelIdFromCard(card);
        let dateExcluded = false;
        let textExcluded = false;

        if (isDateFilterActive) {
          const timestamp = getModelDate(card);
          if (timestamp !== null) {
            const daysAgo = getDaysAgo(timestamp);
            if (daysAgo !== null && (daysAgo < minDays || daysAgo > maxDays)) {
              dateExcluded = true;
            }
          }
        }

        if (isTextFilterActive && matchers.length > 0) {
          if (isCardExcludedByText(card, modelId, matchers)) {
            textExcluded = true;
          }
        }

        if (dateExcluded) {
          card.classList.add('hf-date-filtered-out');
          hiddenByDate++;
        } else {
          card.classList.remove('hf-date-filtered-out');
        }

        if (textExcluded) {
          card.classList.add('hf-text-filtered-out');
          hiddenByText++;
        } else {
          card.classList.remove('hf-text-filtered-out');
        }

        const shouldHide = dateExcluded || textExcluded;
        if (shouldHide) {
          card.classList.add('hf-filtered-out');
        } else {
          card.classList.remove('hf-filtered-out');
          visibleCards++;
        }

        updateCardVisual(card, modelId);
        if (modelId) setupHeartButton(card, modelId);
      }

      if (i + batchSize < cards.length) {
        await new Promise(resolve => requestAnimationFrame(resolve));
        if (globalThis.scheduler?.yield) await globalThis.scheduler.yield();
      }
    }

    if (runId !== processRunId) return;
    updateWidgetStats(visibleCards, totalCards, hiddenByDate, hiddenByText, isDateFilterActive, isTextFilterActive);
    updateEmptyNotice(visibleCards, totalCards, isDateFilterActive, isTextFilterActive, hiddenByDate, hiddenByText);
  }

  function updateEmptyNotice(visibleCount, totalCount, isDateActive, isTextActive, hiddenByDate, hiddenByText) {
    let noticeEl = document.getElementById('hf-df-empty-notice');
    const isAnyActive = isDateActive || isTextActive;

    if (totalCount > 0 && visibleCount === 0 && isAnyActive) {
      if (!noticeEl) {
        noticeEl = document.createElement('div');
        noticeEl.id = 'hf-df-empty-notice';
        const card = document.querySelector('article.overview-card-wrapper');
        const parent = card ? card.closest('.grid, [class*="grid"], main') || card.parentElement : null;
        if (parent) parent.insertBefore(noticeEl, parent.firstChild);
      }
      if (noticeEl) {
        noticeEl.style.display = 'block';
        const reasons = [];
        if (isTextActive && hiddenByText > 0) reasons.push(`${hiddenByText} by keyword filter`);
        if (isDateActive && hiddenByDate > 0) reasons.push(`${hiddenByDate} by date filter`);
        noticeEl.textContent = `No models match current filters (${reasons.join(', ')}). Adjust sidebar filter settings to see results.`;
      }
    } else if (noticeEl) {
      noticeEl.style.display = 'none';
    }
  }

  // ─── MUTATION OBSERVER & SPA ORCHESTRATION ────────────────────────────────────
  let observerTimer = null;
  function observeCards() {
    const observer = new MutationObserver((mutations) => {
      const isInternalOnly = mutations.every(m => {
        const target = m.target;
        if (!target) return false;
        const targetEl = target.nodeType === 1 ? target : target.parentElement;
        if (!targetEl) return false;
        if (targetEl.id === 'hf-date-filter-root' || targetEl.id === 'hf-toast-root' || targetEl.closest('#hf-date-filter-root, #hf-toast-root')) {
          return true;
        }
        return false;
      });

      if (isInternalOnly) return;

      if (observerTimer) clearTimeout(observerTimer);
      observerTimer = setTimeout(() => {
        setupSidebarWidget();
        processModelCards();
      }, 200);
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['d']
    });
  }

  // ─── SHADOW DOM SIDEBAR WIDGET ───────────────────────────────────────────────
  function findWidgetTarget() {
    // 1. Check for left sidebar containers (holding Tasks, Libraries, Parameters, etc.)
    const sidebars = document.querySelectorAll('aside, [class*="sidebar"], div[class*="col-span-"]');
    for (const sb of sidebars) {
      if (sb.closest('header, nav, #hf-date-filter-root')) continue;
      const text = sb.textContent || '';
      if (text.includes('Tasks') || text.includes('Libraries') || text.includes('Languages') || text.includes('Licenses') || text.includes('Parameters')) {
        return { element: sb, method: 'prepend' };
      }
    }

    // 2. Check for form containers in sidebars
    const forms = document.querySelectorAll('form');
    for (const f of forms) {
      if (f.closest('header, nav, #hf-date-filter-root')) continue;
      if (f.querySelector('input[placeholder*="Search models, datasets"]')) continue;
      const aside = f.closest('aside, div[class*="sidebar"]');
      if (aside && !aside.closest('header, nav, #hf-date-filter-root')) return { element: aside, method: 'prepend' };
      const text = f.textContent || '';
      if (text.includes('Tasks') || text.includes('Libraries') || text.includes('Languages') || text.includes('Licenses')) {
        return { element: f, method: 'prepend' };
      }
    }

    // 3. Check for overview card grid (embed before grid if no sidebar)
    const card = document.querySelector('article.overview-card-wrapper');
    if (card) {
      const grid = card.closest('.grid, [class*="grid"], [class*="gap-"]');
      if (grid && !grid.closest('header, nav, #hf-date-filter-root')) {
        return { element: grid, method: 'before' };
      }
      if (card.parentElement && !card.parentElement.closest('header, nav, #hf-date-filter-root')) {
        return { element: card.parentElement, method: 'before' };
      }
    }

    // 4. Main content fallback (single model pages, user profiles)
    const mainSection = document.querySelector('main section, main');
    if (mainSection && !mainSection.closest('header, nav, #hf-date-filter-root')) {
      return { element: mainSection, method: 'prepend' };
    }

    return null;
  }

  function setupSidebarWidget() {
    let host = document.getElementById('hf-date-filter-root');
    if (host) {
      if (host.closest('header, nav')) {
        host.remove();
        host = null;
      } else if (document.body.contains(host)) {
        return;
      }
    }

    const target = findWidgetTarget();
    if (!target || !target.element) return;

    if (!host) {
      host = document.createElement('div');
      host.id = 'hf-date-filter-root';
    }

    const shadow = host.shadowRoot || host.attachShadow({ mode: 'open' });
    widgetShadowRoot = shadow;

    shadow.innerHTML = `
      <style>${SHADOW_WIDGET_STYLES}</style>
      <div id="hf-date-filter-widget" class="${CONFIG.WIDGET_COLLAPSED ? 'collapsed' : ''}">
        <!-- HEADER / COLLAPSIBLE BAR -->
        <div class="hf-df-header" id="hf-df-header" title="Click to collapse / expand (Alt+F)">
          <div class="hf-df-header-left">
            <div class="hf-df-title">
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
              </svg>
              <span>Model Filters</span>
            </div>
            <div class="hf-df-summary-chips" id="hf-df-summary-chips"></div>
          </div>

          <div class="hf-df-header-right">
            <span class="hf-df-badge" id="hf-df-badge">All shown</span>
            <button type="button" class="hf-df-header-btn" id="hf-df-reset-btn" title="Reset all filters to default">
              <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button type="button" class="hf-df-header-btn hf-df-collapse-icon" id="hf-df-collapse-btn" title="Toggle collapse (Alt+F)">
              <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>

        <!-- EXPANDED BODY -->
        <div class="hf-widget-body" id="hf-widget-body">
          <!-- SECTION 1: Exclude Text Filter -->
          <div class="hf-filter-section" id="hf-exclude-section">
            <div class="hf-filter-section-header">
              <div class="hf-filter-section-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                </svg>
                Exclude Keywords
              </div>
              <label class="hf-switch" title="Toggle negative text filter">
                <input id="hf-exclude-toggle" type="checkbox">
                <span class="hf-slider"></span>
              </label>
            </div>
            <div class="hf-section-body" id="hf-exclude-section-body">
              <div class="hf-exclude-row">
                <div class="hf-exclude-input-wrapper">
                  <input type="text" id="hf-exclude-input" class="hf-exclude-input" placeholder="Exclude: e.g. gguf, fp8, /test.*/i" autocomplete="off" spellcheck="false">
                  <button type="button" id="hf-exclude-clear-btn" class="hf-clear-btn" title="Clear filter terms">✕</button>
                </div>
              </div>
            </div>
          </div>

          <!-- SECTION 2: Date Range Filter -->
          <div class="hf-filter-section" id="hf-date-section">
            <div class="hf-filter-section-header">
              <div class="hf-filter-section-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Date Range
              </div>
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="hf-df-range-label" id="hf-df-range-label">Updated: Today – 30d</span>
                <label class="hf-switch" title="Toggle date range filter">
                  <input id="hf-df-toggle" type="checkbox">
                  <span class="hf-slider"></span>
                </label>
              </div>
            </div>

            <div class="hf-section-body" id="hf-date-section-body">
              <div class="hf-df-presets" id="hf-df-presets-container">
                ${PRESETS.map(p => `<button type="button" class="hf-df-preset-btn" data-preset="${p.id}">${p.label}</button>`).join('')}
              </div>

              <div class="hf-df-controls">
                <div class="hf-df-slider-inputs-row">
                  <input type="number" id="hf-df-min-input" class="hf-df-inline-input" min="0" max="3650" placeholder="0" title="Min days ago">
                  <input type="range" id="hf-df-slider-max" min="1" max="365" step="1" title="Max days ago slider">
                  <input type="number" id="hf-df-max-input" class="hf-df-inline-input" min="0" max="3650" placeholder="30" title="Max days ago">
                </div>
              </div>
            </div>
          </div>

          <!-- STATUS SUBDETAILS -->
          <div class="hf-df-substatus" id="hf-df-substatus"></div>

          <!-- SECTION 3: Highlighter Options -->
          <div class="hf-filter-section" style="border-bottom: none; padding-bottom: 0;">
            <button type="button" class="hf-df-settings-toggle" id="hf-df-settings-toggle">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              </svg>
              <span>Highlighter Options</span>
            </button>

            <div class="hf-df-settings-panel" id="hf-df-settings-panel">
              <div class="hf-settings-row">
                <label for="hf-border-unliked-enabled">Highlight unliked</label>
                <label class="hf-switch">
                  <input id="hf-border-unliked-enabled" type="checkbox">
                  <span class="hf-slider"></span>
                </label>
              </div>
              <div class="hf-settings-row">
                <label for="hf-border-unliked-glow">Border glow</label>
                <label class="hf-switch">
                  <input id="hf-border-unliked-glow" type="checkbox">
                  <span class="hf-slider"></span>
                </label>
              </div>
              <div class="hf-settings-row">
                <label for="hf-border-unliked-color">Color</label>
                <input id="hf-border-unliked-color" type="color">
              </div>
            </div>
          </div>
        </div>
      </div>
      <div id="hf-toast-container"></div>
    `;

    if (target.method === 'before' && target.element.parentNode) {
      target.element.parentNode.insertBefore(host, target.element);
    } else {
      target.element.insertBefore(host, target.element.firstChild);
    }

    bindWidgetEvents();
    syncWidgetUI();
  }

  function toggleWidgetCollapse() {
    CONFIG.WIDGET_COLLAPSED = !CONFIG.WIDGET_COLLAPSED;
    saveConfig('WIDGET_COLLAPSED', CONFIG.WIDGET_COLLAPSED);
    syncWidgetUI();
  }

  function resetAllFilters() {
    saveConfig('FILTER_EXCLUDE_TERMS', '');
    saveConfig('FILTER_EXCLUDE_ENABLED', true);
    saveConfig('DATE_FILTER_ENABLED', false);
    saveConfig('DATE_PRESET', 'all');
    saveConfig('DATE_MIN_DAYS', 0);
    saveConfig('DATE_MAX_DAYS', 99999);
    syncWidgetUI();
    processModelCards();
    showToast('Filters reset to default');
  }

  function bindWidgetEvents() {
    if (!widgetShadowRoot) return;
    const shadow = widgetShadowRoot;

    const header = shadow.getElementById('hf-df-header');
    const collapseBtn = shadow.getElementById('hf-df-collapse-btn');
    const resetBtn = shadow.getElementById('hf-df-reset-btn');

    const excludeToggle = shadow.getElementById('hf-exclude-toggle');
    const excludeInput = shadow.getElementById('hf-exclude-input');
    const clearBtn = shadow.getElementById('hf-exclude-clear-btn');

    const dateToggle = shadow.getElementById('hf-df-toggle');
    const sliderMax = shadow.getElementById('hf-df-slider-max');
    const minInput = shadow.getElementById('hf-df-min-input');
    const maxInput = shadow.getElementById('hf-df-max-input');
    const presetsContainer = shadow.getElementById('hf-df-presets-container');

    const highlightToggle = shadow.getElementById('hf-border-unliked-enabled');
    const glowToggle = shadow.getElementById('hf-border-unliked-glow');
    const colorInput = shadow.getElementById('hf-border-unliked-color');
    const settingsToggleBtn = shadow.getElementById('hf-df-settings-toggle');
    const settingsPanel = shadow.getElementById('hf-df-settings-panel');

    // Header collapse / expand handling
    header?.addEventListener('click', (e) => {
      if (e.target.closest('#hf-df-reset-btn')) return;
      toggleWidgetCollapse();
    });

    collapseBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleWidgetCollapse();
    });

    resetBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      resetAllFilters();
    });

    settingsToggleBtn?.addEventListener('click', () => {
      settingsPanel?.classList.toggle('open');
    });

    excludeToggle?.addEventListener('change', (e) => {
      saveConfig('FILTER_EXCLUDE_ENABLED', e.target.checked);
      syncWidgetUI();
      processModelCards();
    });

    let textInputDebounceTimer = null;
    let textSaveDebounceTimer = null;

    excludeInput?.addEventListener('input', (e) => {
      const val = e.target.value;
      CONFIG.FILTER_EXCLUDE_TERMS = val;

      if (clearBtn) {
        clearBtn.classList.toggle('visible', Boolean(val));
      }

      if (textInputDebounceTimer) clearTimeout(textInputDebounceTimer);
      textInputDebounceTimer = setTimeout(() => {
        syncWidgetUI();
        processModelCards();
      }, 120);

      if (textSaveDebounceTimer) clearTimeout(textSaveDebounceTimer);
      textSaveDebounceTimer = setTimeout(() => {
        saveConfig('FILTER_EXCLUDE_TERMS', val);
      }, 350);
    });

    clearBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      saveConfig('FILTER_EXCLUDE_TERMS', '');
      if (excludeInput) excludeInput.value = '';
      clearBtn.classList.remove('visible');
      syncWidgetUI();
      processModelCards();
    });

    dateToggle?.addEventListener('change', (e) => {
      saveConfig('DATE_FILTER_ENABLED', e.target.checked);
      syncWidgetUI();
      processModelCards();
    });

    sliderMax?.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      saveConfig('DATE_MAX_DAYS', val);
      saveConfig('DATE_PRESET', 'custom');
      syncWidgetUI();
      processModelCards();
    });

    minInput?.addEventListener('change', (e) => {
      const val = Math.max(0, parseInt(e.target.value, 10) || 0);
      saveConfig('DATE_MIN_DAYS', val);
      saveConfig('DATE_PRESET', 'custom');
      syncWidgetUI();
      processModelCards();
    });

    maxInput?.addEventListener('change', (e) => {
      const val = Math.max(CONFIG.DATE_MIN_DAYS, parseInt(e.target.value, 10) || 0);
      saveConfig('DATE_MAX_DAYS', val);
      saveConfig('DATE_PRESET', 'custom');
      syncWidgetUI();
      processModelCards();
    });

    presetsContainer?.addEventListener('click', (e) => {
      const btn = e.target.closest('.hf-df-preset-btn');
      if (!btn) return;

      const presetId = btn.dataset.preset;
      const preset = PRESETS.find(p => p.id === presetId);
      if (!preset) return;

      saveConfig('DATE_PRESET', presetId);
      saveConfig('DATE_MIN_DAYS', preset.min);
      saveConfig('DATE_MAX_DAYS', preset.max);
      saveConfig('DATE_FILTER_ENABLED', presetId !== 'all');

      syncWidgetUI();
      processModelCards();
    });

    highlightToggle?.addEventListener('change', (e) => {
      saveConfig('BORDER_UNLIKED_ENABLED', e.target.checked);
      processModelCards();
    });

    glowToggle?.addEventListener('change', (e) => {
      saveConfig('BORDER_UNLIKED_GLOW', e.target.checked);
      injectStyles();
      processModelCards();
    });

    colorInput?.addEventListener('change', (e) => {
      saveConfig('BORDER_UNLIKED_COLOR', e.target.value);
      injectStyles();
    });
  }

  // Keyboard shortcut Alt+F
  window.addEventListener('keydown', (e) => {
    if (e.altKey && (e.key === 'f' || e.key === 'F')) {
      e.preventDefault();
      if (!widgetShadowRoot) return;
      const widget = widgetShadowRoot.getElementById('hf-date-filter-widget');
      const input = widgetShadowRoot.getElementById('hf-exclude-input');
      if (widget?.classList.contains('collapsed')) {
        CONFIG.WIDGET_COLLAPSED = false;
        saveConfig('WIDGET_COLLAPSED', false);
        syncWidgetUI();
        setTimeout(() => input?.focus(), 50);
      } else if (widgetShadowRoot.activeElement === input) {
        CONFIG.WIDGET_COLLAPSED = true;
        saveConfig('WIDGET_COLLAPSED', true);
        syncWidgetUI();
      } else {
        input?.focus();
      }
    }
  });

  function syncWidgetUI() {
    if (!widgetShadowRoot) return;
    const shadow = widgetShadowRoot;

    const widget = shadow.getElementById('hf-date-filter-widget');
    const summaryChips = shadow.getElementById('hf-df-summary-chips');

    const excludeToggle = shadow.getElementById('hf-exclude-toggle');
    const excludeInput = shadow.getElementById('hf-exclude-input');
    const clearBtn = shadow.getElementById('hf-exclude-clear-btn');
    const excludeSectionBody = shadow.getElementById('hf-exclude-section-body');

    const dateToggle = shadow.getElementById('hf-df-toggle');
    const dateSectionBody = shadow.getElementById('hf-date-section-body');
    const sliderMax = shadow.getElementById('hf-df-slider-max');
    const minInput = shadow.getElementById('hf-df-min-input');
    const maxInput = shadow.getElementById('hf-df-max-input');
    const rangeLabel = shadow.getElementById('hf-df-range-label');
    const presetBtns = shadow.querySelectorAll('.hf-df-preset-btn');

    const highlightToggle = shadow.getElementById('hf-border-unliked-enabled');
    const glowToggle = shadow.getElementById('hf-border-unliked-glow');
    const colorInput = shadow.getElementById('hf-border-unliked-color');

    const isTextActive = Boolean(CONFIG.FILTER_EXCLUDE_ENABLED && (CONFIG.FILTER_EXCLUDE_TERMS || '').trim());
    const isDateActive = Boolean(CONFIG.DATE_FILTER_ENABLED);
    const hasActiveFilters = isTextActive || isDateActive;

    if (widget) {
      widget.classList.toggle('collapsed', Boolean(CONFIG.WIDGET_COLLAPSED));
      widget.classList.toggle('has-active-filters', hasActiveFilters);
    }

    // Update summary chips
    if (summaryChips) {
      const chips = [];
      if (isTextActive) {
        const raw = CONFIG.FILTER_EXCLUDE_TERMS.trim();
        const display = raw.length > 14 ? raw.slice(0, 12) + '…' : raw;
        chips.push(`<span class="hf-df-chip" title="Excluded: ${raw}">🚫 ${display}</span>`);
      }
      if (isDateActive) {
        const label = CONFIG.DATE_PRESET !== 'custom' ? CONFIG.DATE_PRESET : `≤${CONFIG.DATE_MAX_DAYS}d`;
        chips.push(`<span class="hf-df-chip" title="Date range: ${label}">📅 ${label}</span>`);
      }
      summaryChips.innerHTML = chips.join('');
    }

    if (excludeToggle) excludeToggle.checked = Boolean(CONFIG.FILTER_EXCLUDE_ENABLED);
    if (excludeInput) {
      if (excludeInput.value !== (CONFIG.FILTER_EXCLUDE_TERMS || '')) {
        excludeInput.value = CONFIG.FILTER_EXCLUDE_TERMS || '';
      }
      if (clearBtn) {
        clearBtn.classList.toggle('visible', Boolean(CONFIG.FILTER_EXCLUDE_TERMS));
      }
    }
    if (excludeSectionBody) {
      excludeSectionBody.classList.toggle('hf-section-dimmed', !CONFIG.FILTER_EXCLUDE_ENABLED);
    }

    if (dateToggle) dateToggle.checked = Boolean(CONFIG.DATE_FILTER_ENABLED);
    if (dateSectionBody) {
      dateSectionBody.classList.toggle('hf-section-dimmed', !CONFIG.DATE_FILTER_ENABLED);
    }
    if (minInput) minInput.value = CONFIG.DATE_MIN_DAYS;
    if (maxInput) maxInput.value = CONFIG.DATE_MAX_DAYS;
    if (sliderMax) sliderMax.value = Math.min(365, CONFIG.DATE_MAX_DAYS);

    if (highlightToggle) highlightToggle.checked = Boolean(CONFIG.BORDER_UNLIKED_ENABLED);
    if (glowToggle) glowToggle.checked = Boolean(CONFIG.BORDER_UNLIKED_GLOW);
    if (colorInput) colorInput.value = CONFIG.BORDER_UNLIKED_COLOR;

    presetBtns.forEach(btn => {
      if (btn.dataset.preset === CONFIG.DATE_PRESET) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    if (rangeLabel) {
      if (!CONFIG.DATE_FILTER_ENABLED || CONFIG.DATE_PRESET === 'all' || CONFIG.DATE_MAX_DAYS >= 9999) {
        rangeLabel.textContent = `All time`;
      } else if (CONFIG.DATE_MIN_DAYS === 0) {
        rangeLabel.textContent = `≤ ${CONFIG.DATE_MAX_DAYS}d`;
      } else {
        rangeLabel.textContent = `${CONFIG.DATE_MIN_DAYS}d–${CONFIG.DATE_MAX_DAYS}d`;
      }
    }
  }

  function updateWidgetStats(visibleCount, totalCount, hiddenByDate, hiddenByText, isDateActive, isTextActive) {
    if (!widgetShadowRoot) return;
    const shadow = widgetShadowRoot;

    const badge = shadow.getElementById('hf-df-badge');
    const substatus = shadow.getElementById('hf-df-substatus');
    if (!badge) return;

    const isAnyActive = isDateActive || isTextActive;

    if (totalCount === 0) {
      badge.textContent = isAnyActive ? 'Active' : 'Ready';
      badge.style.background = isAnyActive ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.15)';
      badge.style.color = isAnyActive ? '#fbbf24' : '#34d399';
      if (substatus) substatus.textContent = isAnyActive ? 'Settings persist for model lists' : '';
      return;
    }

    if (!isAnyActive) {
      badge.textContent = `All shown (${totalCount})`;
      badge.style.background = 'rgba(16, 185, 129, 0.15)';
      badge.style.color = '#34d399';
      if (substatus) substatus.textContent = '';
    } else {
      badge.textContent = `Showing ${visibleCount} / ${totalCount}`;
      if (visibleCount === 0) {
        badge.style.background = 'rgba(239, 68, 68, 0.2)';
        badge.style.color = '#f87171';
      } else {
        badge.style.background = 'rgba(245, 158, 11, 0.2)';
        badge.style.color = '#fbbf24';
      }

      if (substatus) {
        const details = [];
        if (isTextActive && hiddenByText > 0) details.push(`${hiddenByText} hidden by text`);
        if (isDateActive && hiddenByDate > 0) details.push(`${hiddenByDate} hidden by date`);
        substatus.textContent = details.length > 0 ? details.join(' • ') : '';
      }
    }
  }

  injectStyles();

  const init = () => {
    setupSidebarWidget();
    observeCards();
    processModelCards();
  };

  const handleNavigation = () => {
    setupSidebarWidget();
    processModelCards();
  };

  if (self.navigation && typeof self.navigation.addEventListener === 'function') {
    self.navigation.addEventListener('navigatesuccess', handleNavigation);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();

