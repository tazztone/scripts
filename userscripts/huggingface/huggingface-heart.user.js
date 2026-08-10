// ==UserScript==
// @name         Hugging Face Unliked Model Highlighter & Date Filter
// @namespace    https://github.com/tazztone/scripts
// @version      1.7.3
// @description  Highlight unliked models with a green border and filter models by date range slider.
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
  DATE_PRESET: 'all'
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

const WIDGET_STYLES = `
  /* Card highlighting */
  article.overview-card-wrapper.hf-is-unliked {
    border: 2px solid VAR_COLOR !important;
    border-radius: 12px !important;
    VAR_GLOW
    transition: border 0.3s ease, box-shadow 0.3s ease !important;
  }
  article.overview-card-wrapper.hf-is-liked {
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
  }
  article.overview-card-wrapper.hf-date-filtered-out {
    display: none !important;
  }

  /* Sidebar Date Filter Widget Styles */
  #hf-date-filter-widget {
    box-sizing: border-box;
    width: 100%;
    margin-bottom: 24px;
    padding: 14px 16px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.65);
    backdrop-filter: blur(8px);
    color: #f1f5f9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
  }
  #hf-date-filter-widget .hf-df-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  #hf-date-filter-widget .hf-df-title {
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #fbbf24;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  #hf-date-filter-widget .hf-df-presets {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 12px;
  }
  .hf-df-preset-btn {
    padding: 3px 8px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.05);
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .hf-df-preset-btn:hover {
    background: rgba(251, 191, 36, 0.15);
    color: #fef08a;
    border-color: rgba(251, 191, 36, 0.4);
  }
  .hf-df-preset-btn.active {
    background: rgba(245, 158, 11, 0.25);
    color: #fbbf24;
    border-color: #f59e0b;
    box-shadow: 0 0 8px rgba(245, 158, 11, 0.3);
  }
  .hf-df-controls {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .hf-df-range-container {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .hf-df-inputs {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .hf-df-input-group {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
  }
  .hf-df-input-group label {
    font-size: 10px;
    color: #94a3b8;
    text-transform: uppercase;
  }
  .hf-df-input-group input[type="number"] {
    box-sizing: border-box;
    width: 100%;
    height: 28px;
    padding: 2px 6px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    background: rgba(15, 23, 42, 0.8);
    color: #f8fafc;
    font-size: 12px;
  }
  .hf-df-slider-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .hf-df-slider-row input[type="range"] {
    flex: 1;
    accent-color: #f59e0b;
  }
  .hf-df-range-label {
    font-size: 11px;
    color: #cbd5e1;
    line-height: 1.3;
    background: rgba(0, 0, 0, 0.2);
    padding: 6px 8px;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }
  .hf-df-status {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 8px;
    font-size: 11px;
    color: #94a3b8;
  }
  .hf-df-badge {
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    font-weight: 600;
  }

  /* Toggle Switches */
  .hf-switch {
    width: 40px;
    height: 22px;
    position: relative;
    display: inline-block;
  }
  .hf-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }
  .hf-slider {
    position: absolute;
    inset: 0;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 22px;
    background: rgba(15, 23, 42, 0.6);
    cursor: pointer;
  }
  .hf-slider::before {
    content: "";
    position: absolute;
    left: 3px;
    bottom: 3px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #94a3b8;
    transition: transform 0.3s ease;
  }
  .hf-switch input:checked + .hf-slider {
    background: #f59e0b;
  }
  .hf-switch input:checked + .hf-slider::before {
    transform: translateX(18px);
    background: #fff;
  }

  /* Settings Accordion Panel */
  .hf-df-settings-toggle {
    background: none;
    border: none;
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 0;
    margin-top: 12px;
    transition: color 0.2s ease;
  }
  .hf-df-settings-toggle:hover {
    color: #fbbf24;
  }
  .hf-df-settings-panel {
    display: none;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    gap: 10px;
    flex-direction: column;
  }
  .hf-df-settings-panel.open {
    display: flex;
  }
  .hf-settings-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
    color: #cbd5e1;
  }
  .hf-settings-row input[type="color"] {
    width: 32px;
    height: 24px;
    padding: 1px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 4px;
    background: transparent;
    cursor: pointer;
  }

  #hf-df-empty-notice {
    margin: 16px 0;
    padding: 14px 16px;
    border: 1px dashed rgba(245, 158, 11, 0.4);
    border-radius: 12px;
    background: rgba(245, 158, 11, 0.08);
    color: #fbbf24;
    font-size: 13px;
    text-align: center;
  }
`;

(() => {
  'use strict';

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

  const buildStyle = () => {
    const glowCss = CONFIG.BORDER_UNLIKED_GLOW
      ? `box-shadow: 0 4px 20px rgba(16, 185, 129, 0.15) !important;`
      : '';
    return WIDGET_STYLES
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

  // ─── DATE HELPERS ────────────────────────────────────────────────────────────
  function getModelDate(card) {
    const timeEl = card.querySelector('time');
    if (!timeEl) return null;

    const dtAttr = timeEl.getAttribute('datetime') || timeEl.getAttribute('title');
    if (dtAttr) {
      const parsed = Date.parse(dtAttr);
      if (!isNaN(parsed)) return parsed;
    }

    const text = timeEl.textContent.trim();
    if (text) {
      const parsedText = Date.parse(text);
      if (!isNaN(parsedText)) return parsedText;

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
        return now - (amount * (multipliers[unit] || 86400 * 1000));
      }
    }

    return null;
  }

  function getDaysAgo(timestamp) {
    if (!timestamp) return null;
    const diffMs = Date.now() - timestamp;
    return Math.max(0, diffMs / (1000 * 60 * 60 * 24));
  }

  function formatDateLabel(daysAgo) {
    if (daysAgo >= 9999) return 'Beginning of time';
    if (daysAgo === 0) return 'Today';
    const date = new Date(Date.now() - daysAgo * 86400 * 1000);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  // ─── DOM CARD LIKED STATE INSPECTION ──────────────────────────────────────────
  function isModelLiked(card) {
    // 1. Look for explicit like button/link by title/aria-label inside card
    const likeBtn = card.querySelector('[title*="like" i], [aria-label*="like" i]');
    if (likeBtn) {
      const ariaPressed = likeBtn.getAttribute('aria-pressed');
      if (ariaPressed === 'true') return true;

      const combinedClasses = `${likeBtn.className?.baseVal || likeBtn.className || ''} ${likeBtn.parentElement?.className || ''}`;
      if (/(text|fill)-(red|rose|pink)-\d+/i.test(combinedClasses) || /text-red/i.test(combinedClasses)) {
        return true;
      }

      const svg = likeBtn.querySelector('svg') || (likeBtn.tagName?.toLowerCase() === 'svg' ? likeBtn : null);
      if (svg) {
        const fillAttr = svg.getAttribute('fill') || svg.querySelector('path')?.getAttribute('fill') || '';
        if (['#ef4444', '#e11d48', '#f43f5e', 'red'].includes(fillAttr.toLowerCase())) {
          return true;
        }
        const colorStyle = svg.style.color || '';
        if (colorStyle.includes('239, 68, 68') || colorStyle.includes('225, 29, 72') || colorStyle.includes('244, 63, 94')) {
          return true;
        }
      }
    }

    // 2. Fallback: inspect SVGs inside card for red/pink styling or explicit heart paths
    const svgs = card.querySelectorAll('svg');
    for (const svg of svgs) {
      const classStr = (svg.className?.baseVal || svg.className || '').toString();
      const parentClass = (svg.parentElement?.className || '').toString();
      const combined = `${classStr} ${parentClass}`;

      if (/(text|fill)-(red|rose|pink)-\d+/i.test(combined)) {
        return true;
      }

      const path = svg.querySelector('path');
      const d = path ? (path.getAttribute('d') || '') : '';

      // Match precise heart SVG paths used by HF (e.g. M12 21.35, M20.84 4.61, M12 21, M21 8.25)
      if (d.includes('21.35') || d.includes('20.84') || d.includes('M12 21') || d.includes('M21 8.25') || d.includes('M12 4.5')) {
        const fill = path.getAttribute('fill') || svg.getAttribute('fill') || '';
        if (fill && fill !== 'none' && fill !== 'transparent') {
          if (!/(text|fill)-(gray|slate|neutral|zinc|stone)-\d+/i.test(combined)) {
            return true;
          }
        }
      }
    }

    return false;
  }

  function updateCardVisual(card) {
    if (!CONFIG.BORDER_UNLIKED_ENABLED) {
      card.classList.remove('hf-is-unliked', 'hf-is-liked');
      return;
    }

    const isLiked = isModelLiked(card);
    if (isLiked) {
      card.classList.remove('hf-is-unliked');
      card.classList.add('hf-is-liked');
    } else {
      card.classList.remove('hf-is-liked');
      card.classList.add('hf-is-unliked');
    }
  }

  function processModelCards() {
    const cards = document.querySelectorAll('article.overview-card-wrapper');
    let totalCards = cards.length;
    let visibleCards = 0;

    const isDateFilterActive = CONFIG.DATE_FILTER_ENABLED;
    const minDays = CONFIG.DATE_MIN_DAYS;
    const maxDays = CONFIG.DATE_MAX_DAYS;

    cards.forEach(card => {
      if (isDateFilterActive) {
        const timestamp = getModelDate(card);
        if (timestamp !== null) {
          const daysAgo = getDaysAgo(timestamp);
          if (daysAgo !== null && (daysAgo < minDays || daysAgo > maxDays)) {
            card.classList.add('hf-date-filtered-out');
          } else {
            card.classList.remove('hf-date-filtered-out');
            visibleCards++;
          }
        } else {
          card.classList.remove('hf-date-filtered-out');
          visibleCards++;
        }
      } else {
        card.classList.remove('hf-date-filtered-out');
        visibleCards++;
      }

      updateCardVisual(card);
    });

    updateWidgetStats(visibleCards, totalCards);
    updateEmptyNotice(visibleCards, totalCards, isDateFilterActive);
  }

  function updateEmptyNotice(visibleCount, totalCount, isActive) {
    let noticeEl = document.getElementById('hf-df-empty-notice');
    if (isActive && totalCount > 0 && visibleCount === 0) {
      if (!noticeEl) {
        noticeEl = document.createElement('div');
        noticeEl.id = 'hf-df-empty-notice';
        const main = document.querySelector('main') || document.querySelector('article')?.parentElement || document.body;
        main.insertBefore(noticeEl, main.firstChild);
      }
      noticeEl.textContent = `No models match the active date filter on the currently loaded list (${totalCount} models scanned). Scroll down to load more models or expand the date range slider.`;
      noticeEl.style.display = 'block';
    } else if (noticeEl) {
      noticeEl.style.display = 'none';
    }
  }

  let observerTimer = null;
  function observeCards() {
    const observer = new MutationObserver((mutations) => {
      const isInternalOnly = mutations.every(m => {
        const target = m.target;
        if (!target) return false;
        if (target.id === 'hf-date-filter-widget' || target.id === 'hf-df-empty-notice' || target.closest('#hf-date-filter-widget')) {
          return true;
        }
        if (m.type === 'childList') {
          const addedInternal = Array.from(m.addedNodes).every(n => n.id === 'hf-date-filter-widget' || n.id === 'hf-df-empty-notice');
          const removedInternal = Array.from(m.removedNodes).every(n => n.id === 'hf-date-filter-widget' || n.id === 'hf-df-empty-notice');
          if (addedInternal && removedInternal) return true;
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

    observer.observe(document.body, { childList: true, subtree: true });
  }

  // ─── SIDEBAR / CONTAINER WIDGET ──────────────────────────────────────────────
  function findWidgetTarget() {
    const sidebars = document.querySelectorAll('aside, [class*="sidebar"]');
    for (const sb of sidebars) {
      if (sb.closest('header, nav')) continue;
      const text = sb.textContent;
      if (text.includes('Tasks') || text.includes('Libraries') || text.includes('Languages') || text.includes('Licenses') || text.includes('Parameters')) {
        return { element: sb, method: 'prepend' };
      }
    }

    const forms = document.querySelectorAll('form');
    for (const f of forms) {
      if (f.closest('header, nav')) continue;
      if (f.querySelector('input[placeholder*="Search models, datasets"]')) continue;
      const aside = f.closest('aside');
      if (aside && !aside.closest('header, nav')) return { element: aside, method: 'prepend' };
      const text = f.textContent;
      if (text.includes('Tasks') || text.includes('Libraries') || text.includes('Languages') || text.includes('Licenses')) {
        return { element: f, method: 'prepend' };
      }
    }

    const card = document.querySelector('article.overview-card-wrapper');
    if (card) {
      const grid = card.closest('.grid, [class*="grid"], [class*="gap-"]');
      if (grid && !grid.closest('header, nav')) {
        return { element: grid, method: 'before' };
      }
      if (card.parentElement && !card.parentElement.closest('header, nav')) {
        return { element: card.parentElement, method: 'before' };
      }
    }

    const mainSection = document.querySelector('main section, main');
    if (mainSection && !mainSection.closest('header, nav')) {
      return { element: mainSection, method: 'prepend' };
    }

    return null;
  }

  function setupSidebarWidget() {
    const existingWidget = document.getElementById('hf-date-filter-widget');
    if (existingWidget) {
      if (existingWidget.closest('header, nav')) {
        existingWidget.remove();
      } else if (document.body.contains(existingWidget)) {
        return;
      }
    }

    const target = findWidgetTarget();
    if (!target || !target.element) return;

    const widget = document.createElement('div');
    widget.id = 'hf-date-filter-widget';

    widget.innerHTML = `
      <div class="hf-df-header">
        <div class="hf-df-title">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Date Range
        </div>
        <label class="hf-switch" title="Toggle date range filter">
          <input id="hf-df-toggle" type="checkbox">
          <span class="hf-slider"></span>
        </label>
      </div>

      <div class="hf-df-presets" id="hf-df-presets-container">
        ${PRESETS.map(p => `<button type="button" class="hf-df-preset-btn" data-preset="${p.id}">${p.label}</button>`).join('')}
      </div>

      <div class="hf-df-controls">
        <div class="hf-df-range-container">
          <div class="hf-df-slider-row">
            <input type="range" id="hf-df-slider-max" min="1" max="365" step="1" title="Max days ago (Updated recently)">
          </div>
          <div class="hf-df-inputs">
            <div class="hf-df-input-group">
              <label for="hf-df-min-input">Min Days</label>
              <input type="number" id="hf-df-min-input" min="0" max="3650" placeholder="0">
            </div>
            <div class="hf-df-input-group">
              <label for="hf-df-max-input">Max Days</label>
              <input type="number" id="hf-df-max-input" min="0" max="3650" placeholder="30">
            </div>
          </div>
        </div>

        <div class="hf-df-range-label" id="hf-df-range-label">
          Updated: Today – 30 days ago
        </div>

        <div class="hf-df-status">
          <span>Filter Status</span>
          <span class="hf-df-badge" id="hf-df-badge">All shown</span>
        </div>
      </div>

      <button type="button" class="hf-df-settings-toggle" id="hf-df-settings-toggle">
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        </svg>
        Highlighter Options
      </button>

      <div class="hf-df-settings-panel" id="hf-df-settings-panel">
        <div class="hf-settings-row">
          <label for="hf-border-unliked-enabled">Highlight unliked models</label>
          <label class="hf-switch">
            <input id="hf-border-unliked-enabled" type="checkbox">
            <span class="hf-slider"></span>
          </label>
        </div>
        <div class="hf-settings-row">
          <label for="hf-border-unliked-glow">Enable border glow</label>
          <label class="hf-switch">
            <input id="hf-border-unliked-glow" type="checkbox">
            <span class="hf-slider"></span>
          </label>
        </div>
        <div class="hf-settings-row">
          <label for="hf-border-unliked-color">Border color</label>
          <input id="hf-border-unliked-color" type="color">
        </div>
      </div>
    `;

    if (target.method === 'before' && target.element.parentNode) {
      target.element.parentNode.insertBefore(widget, target.element);
    } else {
      target.element.insertBefore(widget, target.element.firstChild);
    }

    bindWidgetEvents();
    syncWidgetUI();
  }

  function bindWidgetEvents() {
    const toggle = document.getElementById('hf-df-toggle');
    const sliderMax = document.getElementById('hf-df-slider-max');
    const minInput = document.getElementById('hf-df-min-input');
    const maxInput = document.getElementById('hf-df-max-input');
    const presetsContainer = document.getElementById('hf-df-presets-container');

    const highlightToggle = document.getElementById('hf-border-unliked-enabled');
    const glowToggle = document.getElementById('hf-border-unliked-glow');
    const colorInput = document.getElementById('hf-border-unliked-color');
    const settingsToggleBtn = document.getElementById('hf-df-settings-toggle');
    const settingsPanel = document.getElementById('hf-df-settings-panel');

    settingsToggleBtn?.addEventListener('click', () => {
      settingsPanel?.classList.toggle('open');
    });

    toggle?.addEventListener('change', (e) => {
      saveConfig('DATE_FILTER_ENABLED', e.target.checked);
      syncWidgetUI();
      processModelCards();
    });

    sliderMax?.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      CONFIG.DATE_MAX_DAYS = val;
      CONFIG.DATE_PRESET = 'custom';
      syncWidgetUI();
      processModelCards();
    });

    sliderMax?.addEventListener('change', (e) => {
      const val = parseInt(e.target.value, 10);
      saveConfig('DATE_MAX_DAYS', val);
      saveConfig('DATE_PRESET', 'custom');
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

  function syncWidgetUI() {
    const toggle = document.getElementById('hf-df-toggle');
    const sliderMax = document.getElementById('hf-df-slider-max');
    const minInput = document.getElementById('hf-df-min-input');
    const maxInput = document.getElementById('hf-df-max-input');
    const rangeLabel = document.getElementById('hf-df-range-label');
    const presetBtns = document.querySelectorAll('.hf-df-preset-btn');

    const highlightToggle = document.getElementById('hf-border-unliked-enabled');
    const glowToggle = document.getElementById('hf-border-unliked-glow');
    const colorInput = document.getElementById('hf-border-unliked-color');

    if (toggle) toggle.checked = CONFIG.DATE_FILTER_ENABLED;
    if (minInput) minInput.value = CONFIG.DATE_MIN_DAYS;
    if (maxInput) maxInput.value = CONFIG.DATE_MAX_DAYS;
    if (sliderMax) sliderMax.value = Math.min(365, CONFIG.DATE_MAX_DAYS);

    if (highlightToggle) highlightToggle.checked = CONFIG.BORDER_UNLIKED_ENABLED;
    if (glowToggle) glowToggle.checked = CONFIG.BORDER_UNLIKED_GLOW;
    if (colorInput) colorInput.value = CONFIG.BORDER_UNLIKED_COLOR;

    presetBtns.forEach(btn => {
      if (btn.dataset.preset === CONFIG.DATE_PRESET) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    if (rangeLabel) {
      const minStr = formatDateLabel(CONFIG.DATE_MIN_DAYS);
      const maxStr = formatDateLabel(CONFIG.DATE_MAX_DAYS);
      if (CONFIG.DATE_MAX_DAYS >= 9999) {
        rangeLabel.textContent = `Updated: ${minStr} and older`;
      } else if (CONFIG.DATE_MIN_DAYS === 0) {
        rangeLabel.textContent = `Updated: Last ${CONFIG.DATE_MAX_DAYS} days (${maxStr} – Today)`;
      } else {
        rangeLabel.textContent = `Updated: ${CONFIG.DATE_MIN_DAYS} to ${CONFIG.DATE_MAX_DAYS} days ago (${maxStr} – ${minStr})`;
      }
    }
  }

  function updateWidgetStats(visibleCount, totalCount) {
    const badge = document.getElementById('hf-df-badge');
    if (!badge) return;

    if (!CONFIG.DATE_FILTER_ENABLED) {
      badge.textContent = `All shown (${totalCount})`;
      badge.style.background = 'rgba(16, 185, 129, 0.15)';
      badge.style.color = '#34d399';
    } else {
      badge.textContent = `Showing ${visibleCount} / ${totalCount}`;
      if (visibleCount === 0) {
        badge.style.background = 'rgba(239, 68, 68, 0.2)';
        badge.style.color = '#f87171';
      } else {
        badge.style.background = 'rgba(245, 158, 11, 0.2)';
        badge.style.color = '#fbbf24';
      }
    }
  }

  injectStyles();

  const init = () => {
    setupSidebarWidget();
    observeCards();
    processModelCards();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
