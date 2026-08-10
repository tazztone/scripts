// ==UserScript==
// @name         Hugging Face Unliked Model Highlighter & Date Filter
// @namespace    https://github.com/tazztone/scripts
// @version      1.5.1
// @description  Highlight unliked models with a green border and filter models by date range slider.
// @author       tazztone
// @match        https://huggingface.co/*
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

const MODAL_STYLES = `
  #hf-settings-fab {
    position: fixed;
    bottom: 2px;
    right: 2px;
    width: 50px;
    height: 50px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 50%;
    background: rgba(30, 41, 59, 0.8);
    color: #f1f5f9;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    cursor: pointer;
    z-index: 99999;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
  }
  #hf-settings-fab svg {
    display: block;
    width: 24px;
    height: 24px;
  }
  #hf-settings-fab:hover {
    background: rgba(245, 158, 11, 0.9);
    box-shadow: 0 0 15px rgba(245, 158, 11, 0.5);
    transform: scale(1.1);
  }
  #hf-settings-modal-backdrop {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(15, 23, 42, 0.5);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 99998;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease;
  }
  #hf-settings-modal-backdrop.open {
    opacity: 1;
    pointer-events: auto;
  }
  #hf-settings-modal {
    width: 90%;
    max-width: 520px;
    max-height: 85vh;
    overflow-y: auto;
    padding: 24px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    background: rgba(30, 41, 59, 0.95);
    color: #f8fafc;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    transform: scale(0.95) translateY(10px);
    transition: transform 0.3s ease;
  }
  #hf-settings-modal-backdrop.open #hf-settings-modal {
    transform: scale(1) translateY(0);
  }
  #hf-settings-modal h3 {
    margin: 0 0 20px;
    color: #fbbf24;
    font-size: 18px;
  }
  .hf-settings-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 18px;
  }
  .hf-settings-group label {
    color: #cbd5e1;
    font-size: 13px;
    font-weight: 600;
  }
  .hf-settings-group input[type="color"] {
    box-sizing: border-box;
    width: 100%;
    min-height: 34px;
    padding: 3px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    background: rgba(15, 23, 42, 0.6);
    color: #fff;
    font-size: 13px;
  }
  .hf-switch-container {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
  .hf-switch {
    width: 44px;
    height: 24px;
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
    border-radius: 24px;
    background: rgba(15, 23, 42, 0.6);
    cursor: pointer;
  }
  .hf-slider::before {
    content: "";
    position: absolute;
    left: 3px;
    bottom: 3px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #94a3b8;
    transition: transform 0.3s ease;
  }
  .hf-switch input:checked + .hf-slider {
    background: #f59e0b;
  }
  .hf-switch input:checked + .hf-slider::before {
    transform: translateX(20px);
    background: #fff;
  }
  .hf-modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
  }
  .hf-btn {
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }
  .hf-btn-secondary {
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: transparent;
    color: #94a3b8;
  }
  .hf-btn-primary {
    border: 0;
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    color: #451a03;
  }

  /* ─── SIDEBAR DATE FILTER WIDGET STYLES ───────────────────────────────── */
  article.overview-card-wrapper.hf-date-filtered-out {
    display: none !important;
  }

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

  const saveAllConfig = () => {
    for (const [key, val] of Object.entries(CONFIG)) {
      saveConfig(key, val);
    }
  };

  const CONFIG = loadConfig();

  let currentUser = null;
  const likedModelIds = new Set();
  let isFetchingLikes = false;

  const buildStyle = () => `
    article.overview-card-wrapper.hf-is-unliked {
      border: 2px solid ${CONFIG.BORDER_UNLIKED_COLOR} !important;
      border-radius: 12px !important;
      ${CONFIG.BORDER_UNLIKED_GLOW ? `box-shadow: 0 4px 20px rgba(16, 185, 129, 0.15) !important;` : ''}
      transition: border 0.3s ease, box-shadow 0.3s ease !important;
    }
    article.overview-card-wrapper.hf-is-liked {
      border: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
  `;

  function injectStyles() {
    let styleEl = document.getElementById('hf-heart-style');
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = 'hf-heart-style';
      (document.head || document.documentElement).appendChild(styleEl);
    }
    styleEl.textContent = buildStyle();

    if (!document.getElementById('hf-settings-style')) {
      const modalStyle = document.createElement('style');
      modalStyle.id = 'hf-settings-style';
      modalStyle.textContent = MODAL_STYLES;
      (document.head || document.documentElement).appendChild(modalStyle);
    }
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

  // ─── USER LIKES & CARDS ──────────────────────────────────────────────────────
  async function initUserLikes() {
    try {
      const res = await fetch('/api/whoami');
      if (res.ok) {
        const data = await res.json();
        currentUser = data.name || data.username || null;
        if (currentUser) await refreshLikesList();
      }
    } catch (e) {
      console.warn('[HF Highlighter] Could not detect user session via /api/whoami:', e);
    }
  }

  async function refreshLikesList() {
    if (!currentUser || isFetchingLikes) return;
    isFetchingLikes = true;
    try {
      const res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/likes`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          data.forEach(item => {
            let repo = null;
            if (typeof item === 'string') {
              repo = item;
            } else if (item && typeof item === 'object') {
              repo = item.repo?.name || item.repo?.id || (typeof item.repo === 'string' ? item.repo : null) || item.repoName || item.name || item.id || item._id;
            }
            if (repo && typeof repo === 'string') {
              likedModelIds.add(repo.toLowerCase());
            }
          });
        }
        processModelCards();
      }
    } catch (e) {
      console.warn('[HF Highlighter] Error fetching likes:', e);
    } finally {
      isFetchingLikes = false;
    }
  }

  const RESERVED_PREFIXES = new Set([
    'models', 'datasets', 'spaces', 'docs', 'posts', 'papers', 'settings', 'login', 'logout', 'join', 'pricing', 'notifications', 'search', 'tasks', 'tags', 'organizations', 'collections', 'chat', 'blog', 'brands', 'discussions'
  ]);

  function getModelIdFromCard(card) {
    const anchors = card.querySelectorAll('a[href^="/"]');
    for (const anchor of anchors) {
      const href = anchor.getAttribute('href');
      if (!href) continue;
      const cleanPath = href.split('?')[0].split('#')[0].replace(/^\//, '');
      const parts = cleanPath.split('/');
      if (parts.length === 2 && parts[0] && parts[1] && !RESERVED_PREFIXES.has(parts[0])) {
        return cleanPath;
      }
    }
    return null;
  }

  function isModelLiked(card, modelId) {
    if (!modelId) return false;
    const lower = modelId.toLowerCase();

    if (likedModelIds.has(lower)) return true;
    if (card.dataset.hfNativeLiked === 'true') return true;

    const heartSvg = card.querySelector('button[aria-label*="like" i] svg, [title*="like" i] svg, svg.text-red-500, svg.text-gray-400');
    if (heartSvg && !heartSvg.dataset.hfProcessed) {
      const classListStr = (heartSvg.className?.baseVal || heartSvg.className || '').toString();
      const parentClassStr = (heartSvg.parentElement?.className || '').toString();
      const fillAttr = heartSvg.getAttribute('fill') || '';
      const colorStyle = heartSvg.style.color || '';

      const isRed = (
        classListStr.includes('text-red') ||
        parentClassStr.includes('text-red') ||
        fillAttr === '#ef4444' ||
        colorStyle === 'rgb(239, 68, 68)' ||
        colorStyle === '#ef4444'
      );

      if (isRed) {
        card.dataset.hfNativeLiked = 'true';
        likedModelIds.add(lower);
        return true;
      }
    }

    return false;
  }

  function updateCardVisual(card, modelId) {
    if (!CONFIG.BORDER_UNLIKED_ENABLED) {
      card.classList.remove('hf-is-unliked', 'hf-is-liked');
      return;
    }

    const isLiked = isModelLiked(card, modelId);
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
      const modelId = getModelIdFromCard(card);

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

      if (modelId) {
        updateCardVisual(card, modelId);
      }
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
    const observer = new MutationObserver(() => {
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
      if (sb.closest('header, nav, #hf-settings-modal')) continue;
      const text = sb.textContent;
      if (text.includes('Tasks') || text.includes('Libraries') || text.includes('Languages') || text.includes('Licenses') || text.includes('Parameters')) {
        return { element: sb, method: 'prepend' };
      }
    }

    const forms = document.querySelectorAll('form');
    for (const f of forms) {
      if (f.closest('header, nav, #hf-settings-modal')) continue;
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
      } else {
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
        <label class="hf-switch">
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

    toggle?.addEventListener('change', (e) => {
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
  }

  function syncWidgetUI() {
    const toggle = document.getElementById('hf-df-toggle');
    const sliderMax = document.getElementById('hf-df-slider-max');
    const minInput = document.getElementById('hf-df-min-input');
    const maxInput = document.getElementById('hf-df-max-input');
    const rangeLabel = document.getElementById('hf-df-range-label');
    const presetBtns = document.querySelectorAll('.hf-df-preset-btn');

    if (toggle) toggle.checked = CONFIG.DATE_FILTER_ENABLED;
    if (minInput) minInput.value = CONFIG.DATE_MIN_DAYS;
    if (maxInput) maxInput.value = CONFIG.DATE_MAX_DAYS;
    if (sliderMax) sliderMax.value = Math.min(365, CONFIG.DATE_MAX_DAYS);

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

  // ─── FAB SETTINGS MODAL ─────────────────────────────────────────────────────
  function setupUI() {
    if (document.getElementById('hf-settings-fab')) return;

    const container = document.createElement('div');
    container.innerHTML = `
      <button id="hf-settings-fab" type="button" title="Configure Hugging Face highlighter" aria-label="Configure Hugging Face highlighter">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>
      <div id="hf-settings-modal-backdrop">
        <div id="hf-settings-modal" role="dialog" aria-modal="true" aria-labelledby="hf-settings-title">
          <h3 id="hf-settings-title">Hugging Face Highlighter Settings</h3>

          <div class="hf-settings-group hf-switch-container">
            <label for="hf-border-unliked-enabled">Highlight unliked models</label>
            <label class="hf-switch">
              <input id="hf-border-unliked-enabled" type="checkbox">
              <span class="hf-slider"></span>
            </label>
          </div>
          <div class="hf-settings-group">
            <label for="hf-border-unliked-color">Unliked border color</label>
            <input id="hf-border-unliked-color" type="color">
          </div>
          <div class="hf-settings-group hf-switch-container">
            <label for="hf-border-unliked-glow">Enable border glow</label>
            <label class="hf-switch">
              <input id="hf-border-unliked-glow" type="checkbox">
              <span class="hf-slider"></span>
            </label>
          </div>

          <div class="hf-modal-actions">
            <button type="button" class="hf-btn hf-btn-secondary" id="hf-btn-close">Cancel</button>
            <button type="button" class="hf-btn hf-btn-primary" id="hf-btn-save">Save Settings</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(container);

    const fab = document.getElementById('hf-settings-fab');
    const backdrop = document.getElementById('hf-settings-modal-backdrop');
    const borderUnlikedEnabled = document.getElementById('hf-border-unliked-enabled');
    const borderUnlikedColor = document.getElementById('hf-border-unliked-color');
    const borderUnlikedGlow = document.getElementById('hf-border-unliked-glow');

    const syncFields = () => {
      borderUnlikedEnabled.checked = CONFIG.BORDER_UNLIKED_ENABLED;
      borderUnlikedColor.value = CONFIG.BORDER_UNLIKED_COLOR;
      borderUnlikedGlow.checked = CONFIG.BORDER_UNLIKED_GLOW;
    };

    const close = () => backdrop.classList.remove('open');
    fab.addEventListener('click', () => {
      syncFields();
      backdrop.classList.add('open');
    });
    document.getElementById('hf-btn-close').addEventListener('click', close);
    backdrop.addEventListener('click', event => {
      if (event.target === backdrop) close();
    });
    document.getElementById('hf-btn-save').addEventListener('click', () => {
      CONFIG.BORDER_UNLIKED_ENABLED = borderUnlikedEnabled.checked;
      CONFIG.BORDER_UNLIKED_COLOR = borderUnlikedColor.value;
      CONFIG.BORDER_UNLIKED_GLOW = borderUnlikedGlow.checked;

      saveAllConfig();

      injectStyles();
      syncWidgetUI();
      processModelCards();
      close();
    });
  }

  injectStyles();

  const init = async () => {
    setupUI();
    setupSidebarWidget();
    observeCards();
    await initUserLikes();
    processModelCards();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
