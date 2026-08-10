// ==UserScript==
// @name         Hugging Face Yellow Hearts & Unliked Model Highlighter
// @namespace    https://github.com/tazztone/scripts
// @version      1.4.2
// @description  Make heart icons larger/yellow, highlight unliked models with a green border, like models directly from list cards, and filter models by date range slider.
// @author       tazztone
// @match        https://huggingface.co/*
// @run-at       document-start
// @grant        GM_getValue
// @grant        GM_setValue
// @noframes
// ==/UserScript==

// ─── CONFIG DEFAULT VALUES ───────────────────────────────────────────────────
const DEFAULTS = {
  ENABLED: true,
  COLOR_IDLE: '#fbbf24',
  COLOR_HOVER: '#f59e0b',
  SCALE_IDLE: 1,
  SCALE_HOVER: 1.2,
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
  .hf-settings-group input[type="color"],
  .hf-settings-group input[type="number"],
  .hf-settings-group select {
    box-sizing: border-box;
    width: 100%;
    min-height: 34px;
    padding: 6px 10px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    background: rgba(15, 23, 42, 0.6);
    color: #fff;
    font-size: 13px;
  }
  .hf-settings-group input[type="color"] {
    padding: 3px;
  }
  .hf-settings-group input[type="range"] {
    accent-color: #f59e0b;
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

  const getValue = (key, fallback) => {
    try {
      if (typeof GM_getValue !== 'undefined') return GM_getValue(key, fallback);
    } catch (e) {}
    try {
      const value = localStorage.getItem(`hf_heart_${key}`);
      return value === null ? fallback : JSON.parse(value);
    } catch (e) {}
    return fallback;
  };

  const setValue = (key, value) => {
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

  const CONFIG = {
    get ENABLED() { return getValue('ENABLED', DEFAULTS.ENABLED); },
    set ENABLED(value) { setValue('ENABLED', value); },
    get COLOR_IDLE() { return getValue('COLOR_IDLE', DEFAULTS.COLOR_IDLE); },
    set COLOR_IDLE(value) { setValue('COLOR_IDLE', value); },
    get COLOR_HOVER() { return getValue('COLOR_HOVER', DEFAULTS.COLOR_HOVER); },
    set COLOR_HOVER(value) { setValue('COLOR_HOVER', value); },
    get SCALE_IDLE() { return parseFloat(getValue('SCALE_IDLE', DEFAULTS.SCALE_IDLE)); },
    set SCALE_IDLE(value) { setValue('SCALE_IDLE', parseFloat(value)); },
    get SCALE_HOVER() { return parseFloat(getValue('SCALE_HOVER', DEFAULTS.SCALE_HOVER)); },
    set SCALE_HOVER(value) { setValue('SCALE_HOVER', parseFloat(value)); },
    get BORDER_UNLIKED_ENABLED() { return getValue('BORDER_UNLIKED_ENABLED', DEFAULTS.BORDER_UNLIKED_ENABLED); },
    set BORDER_UNLIKED_ENABLED(value) { setValue('BORDER_UNLIKED_ENABLED', value); },
    get BORDER_UNLIKED_COLOR() { return getValue('BORDER_UNLIKED_COLOR', DEFAULTS.BORDER_UNLIKED_COLOR); },
    set BORDER_UNLIKED_COLOR(value) { setValue('BORDER_UNLIKED_COLOR', value); },
    get BORDER_UNLIKED_GLOW() { return getValue('BORDER_UNLIKED_GLOW', DEFAULTS.BORDER_UNLIKED_GLOW); },
    set BORDER_UNLIKED_GLOW(value) { setValue('BORDER_UNLIKED_GLOW', value); },
    get DATE_FILTER_ENABLED() { return getValue('DATE_FILTER_ENABLED', DEFAULTS.DATE_FILTER_ENABLED); },
    set DATE_FILTER_ENABLED(value) { setValue('DATE_FILTER_ENABLED', value); },
    get DATE_MIN_DAYS() { return parseInt(getValue('DATE_MIN_DAYS', DEFAULTS.DATE_MIN_DAYS), 10); },
    set DATE_MIN_DAYS(value) { setValue('DATE_MIN_DAYS', Math.max(0, parseInt(value, 10) || 0)); },
    get DATE_MAX_DAYS() { return parseInt(getValue('DATE_MAX_DAYS', DEFAULTS.DATE_MAX_DAYS), 10); },
    set DATE_MAX_DAYS(value) { setValue('DATE_MAX_DAYS', Math.max(0, parseInt(value, 10) || 0)); },
    get DATE_PRESET() { return getValue('DATE_PRESET', DEFAULTS.DATE_PRESET); },
    set DATE_PRESET(value) { setValue('DATE_PRESET', value); }
  };

  let currentUser = null;
  const likedModelIds = new Set();
  let isFetchingLikes = false;

  const buildHeartStyle = () => CONFIG.ENABLED ? `
    article.overview-card-wrapper.hf-is-unliked {
      border: 2px solid ${CONFIG.BORDER_UNLIKED_COLOR} !important;
      border-radius: 12px !important;
      ${CONFIG.BORDER_UNLIKED_GLOW ? `box-shadow: 0 4px 20px rgba(16, 185, 129, 0.15) !important;` : ''}
      transition: border 0.3s ease, box-shadow 0.3s ease !important;
    }
    article.overview-card-wrapper.hf-is-liked {
      border: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    article.overview-card-wrapper.hf-is-unliked svg.hf-heart-icon,
    article.overview-card-wrapper.hf-is-unliked .hf-inline-like-btn svg {
      color: ${CONFIG.COLOR_IDLE} !important;
      fill: none !important;
      transform: scale(${CONFIG.SCALE_IDLE}) !important;
      transform-origin: center !important;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), color 0.2s ease, filter 0.2s ease !important;
    }
    article.overview-card-wrapper.hf-is-unliked svg.hf-heart-icon path,
    article.overview-card-wrapper.hf-is-unliked .hf-inline-like-btn svg path {
      fill: none !important;
      stroke: currentColor !important;
      stroke-width: 2 !important;
    }
    article.overview-card-wrapper.hf-is-unliked .hf-inline-like-btn:hover svg {
      transform: scale(${CONFIG.SCALE_HOVER}) !important;
      color: ${CONFIG.COLOR_HOVER} !important;
      filter: drop-shadow(0 0 6px rgba(251, 191, 36, 0.65)) !important;
      cursor: pointer;
    }
    .hf-inline-like-btn {
      cursor: pointer !important;
      user-select: none !important;
      display: inline-flex !important;
      align-items: center !important;
      padding: 2px 4px !important;
      margin: -2px -2px !important;
      border-radius: 4px !important;
      transition: background-color 0.2s ease !important;
    }
    .hf-inline-like-btn:hover {
      background-color: rgba(255, 255, 255, 0.1) !important;
    }
  ` : '';

  function injectStyles() {
    let styleEl = document.getElementById('hf-heart-style');
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = 'hf-heart-style';
      (document.head || document.documentElement).appendChild(styleEl);
    }
    styleEl.textContent = buildHeartStyle();

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

    const dtAttr = timeEl.getAttribute('datetime');
    if (dtAttr) {
      const parsed = Date.parse(dtAttr);
      if (!isNaN(parsed)) return parsed;
    }

    const titleAttr = timeEl.getAttribute('title');
    if (titleAttr) {
      const parsed = Date.parse(titleAttr);
      if (!isNaN(parsed)) return parsed;
    }

    const text = timeEl.textContent.trim().toLowerCase();
    const now = Date.now();

    const hourMatch = text.match(/^(\d+)\s*hours?\s*ago/);
    if (hourMatch) return now - parseInt(hourMatch[1], 10) * 3600 * 1000;

    const dayMatch = text.match(/^(\d+)\s*days?\s*ago/);
    if (dayMatch) return now - parseInt(dayMatch[1], 10) * 86400 * 1000;

    const monthMatch = text.match(/^(\d+)\s*months?\s*ago/);
    if (monthMatch) return now - parseInt(monthMatch[1], 10) * 30 * 86400 * 1000;

    const yearMatch = text.match(/^(\d+)\s*years?\s*ago/);
    if (yearMatch) return now - parseInt(yearMatch[1], 10) * 365 * 86400 * 1000;

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
      let username = null;

      // 1. Fetch /api/whoami for the most authoritative logged-in user session
      try {
        const res = await fetch('/api/whoami');
        if (res.ok) {
          const data = await res.json();
          username = data.name || data.username;
        }
      } catch (e) {}

      // 2. Check authLight or explicit logged-in user props in DOM
      if (!username) {
        const propsElements = document.querySelectorAll('[data-props]');
        for (const el of propsElements) {
          try {
            const parsed = JSON.parse(el.getAttribute('data-props'));
            if (parsed) {
              if (parsed.authLight?.u?.username) {
                username = parsed.authLight.u.username;
                break;
              }
              if (parsed.currentUser?.username || parsed.currentUser?.name) {
                username = parsed.currentUser.username || parsed.currentUser.name;
                break;
              }
            }
          } catch (e) {}
        }
      }

      // 3. Check settings link (only present for logged-in user in header menu)
      if (!username) {
        const settingsLink = document.querySelector('a[href^="/settings/"]');
        if (settingsLink) {
          const href = settingsLink.getAttribute('href');
          const parts = href.split('/').filter(Boolean);
          if (parts.length >= 2) username = parts[1];
        }
      }

      if (username) {
        currentUser = username;
        await refreshLikesList();
      }
    } catch (e) {
      console.warn('[HF Hearts] Could not detect user session:', e);
    }
  }

  async function refreshLikesList() {
    if (!currentUser || isFetchingLikes) return;
    isFetchingLikes = true;
    try {
      const res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/likes`);
      if (res.ok) {
        const data = await res.json();
        likedModelIds.clear();
        if (Array.isArray(data)) {
          data.forEach(item => {
            const repo = item.repo?.name || item.repoName || item.name;
            if (repo) likedModelIds.add(repo);
          });
        }
        processModelCards();
      }
    } catch (e) {
      console.warn('[HF Hearts] Error fetching likes:', e);
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

  function findHeartSvg(container) {
    const svgs = container.querySelectorAll('svg');
    for (const svg of svgs) {
      const path = svg.querySelector('path');
      if (!path) continue;
      const d = path.getAttribute('d') || '';
      if (
        d.includes('22.5') ||
        d.includes('22.45') ||
        (d.startsWith('M22.') && d.includes('29')) ||
        (d.includes('M16') && d.includes('29')) ||
        d.includes('M12 21.35') ||
        d.includes('M20.84 4.61') ||
        svg.closest('[title*="like" i], [aria-label*="like" i], .hf-inline-like-btn')
      ) {
        return svg;
      }
    }
    return null;
  }

  function updateCardVisual(card, modelId) {
    const isLiked = likedModelIds.has(modelId);

    if (CONFIG.ENABLED && CONFIG.BORDER_UNLIKED_ENABLED) {
      if (isLiked) {
        card.classList.remove('hf-is-unliked');
        card.classList.add('hf-is-liked');
      } else {
        card.classList.remove('hf-is-liked');
        card.classList.add('hf-is-unliked');
      }
    } else {
      card.classList.remove('hf-is-unliked', 'hf-is-liked');
    }

    const heartSvg = findHeartSvg(card);
    if (heartSvg) {
      const path = heartSvg.querySelector('path');

      if (isLiked) {
        heartSvg.classList.add('text-red-500');
        heartSvg.classList.remove('text-gray-400', 'hf-heart-icon');
        heartSvg.style.setProperty('color', '#ef4444', 'important');
        heartSvg.style.setProperty('fill', 'currentColor', 'important');
        heartSvg.style.removeProperty('filter');
        heartSvg.style.removeProperty('transform');

        if (path) {
          path.style.setProperty('fill', 'currentColor', 'important');
          path.style.removeProperty('stroke');
        }
      } else {
        heartSvg.classList.remove('text-red-500');
        heartSvg.classList.add('text-gray-400', 'hf-heart-icon');
        heartSvg.style.setProperty('color', CONFIG.COLOR_IDLE || '#fbbf24', 'important');
        heartSvg.style.setProperty('fill', 'none', 'important');

        if (path) {
          path.style.setProperty('fill', 'none', 'important');
          path.style.setProperty('stroke', 'currentColor', 'important');
          path.style.setProperty('stroke-width', '2', 'important');
        }
      }
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
        setupHeartButton(card, modelId);
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

  function setupHeartButton(card, modelId) {
    const heartSvg = findHeartSvg(card);
    if (!heartSvg) return;

    let heartContainer = heartSvg.closest('.hf-inline-like-btn');
    if (!heartContainer) {
      heartContainer = heartSvg.parentElement || heartSvg;
      heartContainer.classList.add('hf-inline-like-btn');
      heartContainer.setAttribute('title', 'Click to like/unlike model inline');
      heartContainer.style.cursor = 'pointer';
    }

    if (heartContainer.dataset.hfBound === modelId) return;
    heartContainer.dataset.hfBound = modelId;

    heartContainer.addEventListener('mousedown', (e) => {
      e.stopPropagation();
    }, true);

    heartContainer.addEventListener('mouseup', (e) => {
      e.stopPropagation();
    }, true);

    heartContainer.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.stopImmediatePropagation) e.stopImmediatePropagation();

      const isCurrentlyLiked = likedModelIds.has(modelId);
      const nextLikedState = !isCurrentlyLiked;
      const endpoint = `/api/models/${modelId}/like`;
      const method = nextLikedState ? 'POST' : 'DELETE';

      console.log(`[HF Yellow Hearts] Toggling like for ${modelId}: ${isCurrentlyLiked} -> ${nextLikedState}`);

      if (nextLikedState) {
        likedModelIds.add(modelId);
      } else {
        likedModelIds.delete(modelId);
      }

      updateCardVisual(card, modelId);
      updateLikeCountText(heartContainer, nextLikedState);

      try {
        const res = await fetch(endpoint, {
          method,
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        });

        if (res.status === 401 || res.status === 403) {
          alert('Please log in to Hugging Face to like models directly.');
          revertLikeState(card, modelId, isCurrentlyLiked, heartContainer);
          return;
        }

        if (!res.ok) {
          console.error('[HF Yellow Hearts] Like request failed, HTTP status:', res.status);
          revertLikeState(card, modelId, isCurrentlyLiked, heartContainer);
        } else {
          if (currentUser) {
            refreshLikesList();
          }
        }
      } catch (err) {
        console.error('[HF Yellow Hearts] Failed to update like status:', err);
        revertLikeState(card, modelId, isCurrentlyLiked, heartContainer);
      }
    }, true);
  }

  function revertLikeState(card, modelId, wasLiked, container) {
    if (wasLiked) {
      likedModelIds.add(modelId);
    } else {
      likedModelIds.delete(modelId);
    }
    updateCardVisual(card, modelId);
    updateLikeCountText(container, wasLiked);
  }

  function updateLikeCountText(container, isNowLiked) {
    const textNode = Array.from(container.childNodes).find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0) ||
                     container.querySelector('span');

    if (!textNode) return;
    const currentText = textNode.textContent.trim();

    if (/^\d+$/.test(currentText)) {
      let val = parseInt(currentText, 10);
      val = isNowLiked ? val + 1 : Math.max(0, val - 1);
      textNode.textContent = ' ' + val;
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
    // 1. Look for true filter sidebar (e.g. on /models page)
    const sidebars = document.querySelectorAll('aside, [class*="sidebar"]');
    for (const sb of sidebars) {
      if (sb.closest('header, nav, #hf-settings-modal')) continue;
      const text = sb.textContent;
      if (text.includes('Tasks') || text.includes('Libraries') || text.includes('Languages') || text.includes('Licenses') || text.includes('Parameters')) {
        return { element: sb, method: 'prepend' };
      }
    }

    // 2. Check sidebar filter forms that are NOT in header/nav
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

    // 3. Page without left sidebar (e.g. /lightx2v/models or user profile pages):
    // Find the grid container holding the model cards or main section
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

    // 4. Fallback for main content area (never in header/nav)
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
      CONFIG.DATE_FILTER_ENABLED = e.target.checked;
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

    minInput?.addEventListener('change', (e) => {
      const val = Math.max(0, parseInt(e.target.value, 10) || 0);
      CONFIG.DATE_MIN_DAYS = val;
      CONFIG.DATE_PRESET = 'custom';
      syncWidgetUI();
      processModelCards();
    });

    maxInput?.addEventListener('change', (e) => {
      const val = Math.max(CONFIG.DATE_MIN_DAYS, parseInt(e.target.value, 10) || 0);
      CONFIG.DATE_MAX_DAYS = val;
      CONFIG.DATE_PRESET = 'custom';
      syncWidgetUI();
      processModelCards();
    });

    presetsContainer?.addEventListener('click', (e) => {
      const btn = e.target.closest('.hf-df-preset-btn');
      if (!btn) return;

      const presetId = btn.dataset.preset;
      const preset = PRESETS.find(p => p.id === presetId);
      if (!preset) return;

      CONFIG.DATE_PRESET = presetId;
      CONFIG.DATE_MIN_DAYS = preset.min;
      CONFIG.DATE_MAX_DAYS = preset.max;
      if (presetId !== 'all') {
        CONFIG.DATE_FILTER_ENABLED = true;
      } else {
        CONFIG.DATE_FILTER_ENABLED = false;
      }

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
      <button id="hf-settings-fab" type="button" title="Configure Hugging Face hearts & date filter" aria-label="Configure Hugging Face hearts & date filter">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>
      <div id="hf-settings-modal-backdrop">
        <div id="hf-settings-modal" role="dialog" aria-modal="true" aria-labelledby="hf-settings-title">
          <h3 id="hf-settings-title">Hugging Face Enhancements</h3>

          <!-- DATE FILTER SECTION -->
          <div style="font-size: 14px; font-weight: 700; color: #fbbf24; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px;">
            Date Range Filter
          </div>
          <div class="hf-settings-group hf-switch-container">
            <label for="hf-df-modal-enabled">Enable Date Filter</label>
            <label class="hf-switch">
              <input id="hf-df-modal-enabled" type="checkbox">
              <span class="hf-slider"></span>
            </label>
          </div>
          <div class="hf-settings-group">
            <label for="hf-df-modal-preset">Quick Preset</label>
            <select id="hf-df-modal-preset">
              ${PRESETS.map(p => `<option value="${p.id}">${p.label}</option>`).join('')}
              <option value="custom">Custom</option>
            </select>
          </div>
          <div class="hf-settings-group">
            <label for="hf-df-modal-min-days">Min Days Ago</label>
            <input id="hf-df-modal-min-days" type="number" min="0" max="3650">
          </div>
          <div class="hf-settings-group">
            <label for="hf-df-modal-max-days">Max Days Ago</label>
            <input id="hf-df-modal-max-days" type="number" min="0" max="3650">
          </div>

          <!-- HEART STYLING SECTION -->
          <div style="font-size: 14px; font-weight: 700; color: #fbbf24; margin: 20px 0 12px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px;">
            Heart Styling & Highlighting
          </div>
          <div class="hf-settings-group hf-switch-container">
            <label for="hf-enabled">Enable heart styling</label>
            <label class="hf-switch">
              <input id="hf-enabled" type="checkbox">
              <span class="hf-slider"></span>
            </label>
          </div>
          <div class="hf-settings-group">
            <label for="hf-color-idle">Idle color</label>
            <input id="hf-color-idle" type="color">
          </div>
          <div class="hf-settings-group">
            <label for="hf-color-hover">Hover color</label>
            <input id="hf-color-hover" type="color">
          </div>
          <div class="hf-settings-group">
            <label for="hf-scale-idle">Idle scale</label>
            <input id="hf-scale-idle" type="number" min="1" max="5" step="0.1">
          </div>
          <div class="hf-settings-group">
            <label for="hf-scale-hover">Hover scale</label>
            <input id="hf-scale-hover" type="number" min="1" max="5" step="0.1">
          </div>
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
    fab.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>';

    const backdrop = document.getElementById('hf-settings-modal-backdrop');
    const enabled = document.getElementById('hf-enabled');
    const colorIdle = document.getElementById('hf-color-idle');
    const colorHover = document.getElementById('hf-color-hover');
    const scaleIdle = document.getElementById('hf-scale-idle');
    const scaleHover = document.getElementById('hf-scale-hover');
    const borderUnlikedEnabled = document.getElementById('hf-border-unliked-enabled');
    const borderUnlikedColor = document.getElementById('hf-border-unliked-color');
    const borderUnlikedGlow = document.getElementById('hf-border-unliked-glow');

    const dfModalEnabled = document.getElementById('hf-df-modal-enabled');
    const dfModalPreset = document.getElementById('hf-df-modal-preset');
    const dfModalMinDays = document.getElementById('hf-df-modal-min-days');
    const dfModalMaxDays = document.getElementById('hf-df-modal-max-days');

    const syncFields = () => {
      enabled.checked = CONFIG.ENABLED;
      colorIdle.value = CONFIG.COLOR_IDLE;
      colorHover.value = CONFIG.COLOR_HOVER;
      scaleIdle.value = CONFIG.SCALE_IDLE;
      scaleHover.value = CONFIG.SCALE_HOVER;
      borderUnlikedEnabled.checked = CONFIG.BORDER_UNLIKED_ENABLED;
      borderUnlikedColor.value = CONFIG.BORDER_UNLIKED_COLOR;
      borderUnlikedGlow.checked = CONFIG.BORDER_UNLIKED_GLOW;

      dfModalEnabled.checked = CONFIG.DATE_FILTER_ENABLED;
      dfModalPreset.value = CONFIG.DATE_PRESET;
      dfModalMinDays.value = CONFIG.DATE_MIN_DAYS;
      dfModalMaxDays.value = CONFIG.DATE_MAX_DAYS;
    };

    dfModalPreset.addEventListener('change', (e) => {
      const p = PRESETS.find(pr => pr.id === e.target.value);
      if (p) {
        dfModalMinDays.value = p.min;
        dfModalMaxDays.value = p.max;
      }
    });

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
      CONFIG.ENABLED = enabled.checked;
      CONFIG.COLOR_IDLE = colorIdle.value;
      CONFIG.COLOR_HOVER = colorHover.value;
      CONFIG.SCALE_IDLE = Math.max(1, Math.min(5, parseFloat(scaleIdle.value) || DEFAULTS.SCALE_IDLE));
      CONFIG.SCALE_HOVER = Math.max(1, Math.min(5, parseFloat(scaleHover.value) || DEFAULTS.SCALE_HOVER));
      CONFIG.BORDER_UNLIKED_ENABLED = borderUnlikedEnabled.checked;
      CONFIG.BORDER_UNLIKED_COLOR = borderUnlikedColor.value;
      CONFIG.BORDER_UNLIKED_GLOW = borderUnlikedGlow.checked;

      CONFIG.DATE_FILTER_ENABLED = dfModalEnabled.checked;
      CONFIG.DATE_PRESET = dfModalPreset.value;
      CONFIG.DATE_MIN_DAYS = Math.max(0, parseInt(dfModalMinDays.value, 10) || 0);
      CONFIG.DATE_MAX_DAYS = Math.max(CONFIG.DATE_MIN_DAYS, parseInt(dfModalMaxDays.value, 10) || 0);

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
