// ==UserScript==
// @name         Hugging Face Yellow Hearts & Unliked Model Highlighter
// @namespace    https://github.com/tazztone/scripts
// @version      1.2.0
// @description  Make heart icons larger/yellow, highlight unliked models with a green border, and like models directly from list cards.
// @author       tazztone
// @match        https://huggingface.co/models*
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
  BORDER_UNLIKED_GLOW: true
};

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
    max-width: 480px;
    max-height: 80vh;
    overflow-y: auto;
    padding: 24px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    background: rgba(30, 41, 59, 0.92);
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
  .hf-settings-group input[type="number"] {
    box-sizing: border-box;
    width: 100%;
    min-height: 34px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    background: rgba(15, 23, 42, 0.6);
    color: #fff;
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
    set BORDER_UNLIKED_GLOW(value) { setValue('BORDER_UNLIKED_GLOW', value); }
  };

  let currentUser = null;
  const likedModelIds = new Set();
  let isFetchingLikes = false;

  const buildHeartStyle = () => CONFIG.ENABLED ? `
    svg.hf-heart-icon,
    svg[data-hf-heart="true"],
    svg.hf-is-liked-heart {
      color: ${CONFIG.COLOR_IDLE} !important;
      fill: ${CONFIG.COLOR_IDLE} !important;
      transform: scale(${CONFIG.SCALE_IDLE}) !important;
      transform-origin: center !important;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), color 0.2s ease, filter 0.2s ease !important;
    }
    svg.hf-heart-icon path,
    svg[data-hf-heart="true"] path,
    svg.hf-is-liked-heart path {
      fill: currentColor !important;
    }
    svg.hf-heart-icon:hover,
    svg[data-hf-heart="true"]:hover,
    svg.hf-is-liked-heart:hover {
      transform: scale(${CONFIG.SCALE_HOVER}) !important;
      color: ${CONFIG.COLOR_HOVER} !important;
      fill: ${CONFIG.COLOR_HOVER} !important;
      filter: drop-shadow(0 0 6px rgba(251, 191, 36, 0.65)) !important;
      cursor: pointer;
    }
    .hf-inline-like-btn,
    div:has(> svg.hf-heart-icon),
    button:has(> svg.hf-heart-icon),
    div:has(> svg:has(path[d^="M22.45"])),
    div:has(> svg:has(path[d^="M22.5,4"])),
    button:has(> svg:has(path[d^="M22.45"])),
    button:has(> svg:has(path[d^="M22.5,4"])) {
      overflow: visible !important;
    }
    article.overview-card-wrapper.hf-is-unliked {
      border: 2px solid ${CONFIG.BORDER_UNLIKED_COLOR} !important;
      border-radius: 12px !important;
      ${CONFIG.BORDER_UNLIKED_GLOW ? `box-shadow: 0 4px 20px rgba(16, 185, 129, 0.15) !important;` : ''}
      transition: border 0.3s ease, box-shadow 0.3s ease !important;
    }
    article.overview-card-wrapper.hf-is-liked {
      border: 1px solid rgba(255, 255, 255, 0.05) !important;
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

  async function initUserLikes() {
    try {
      let username = null;
      const propsElements = document.querySelectorAll('[data-props]');
      for (const el of propsElements) {
        try {
          const parsed = JSON.parse(el.getAttribute('data-props'));
          if (parsed && (parsed.user || parsed.authLight?.u?.username)) {
            username = parsed.user || parsed.authLight?.u?.username;
            break;
          }
        } catch (e) {}
      }

      if (!username) {
        const settingsLink = document.querySelector('a[href^="/settings/"]');
        if (settingsLink) {
          const href = settingsLink.getAttribute('href');
          const parts = href.split('/').filter(Boolean);
          if (parts.length >= 2) username = parts[1];
        }
      }

      if (!username) {
        const res = await fetch('/api/whoami');
        if (res.ok) {
          const data = await res.json();
          username = data.name || data.username;
        }
      }

      if (username) {
        currentUser = username;
        await refreshLikesList();
      }
    } catch (e) {
      console.warn('[HF Yellow Hearts] Could not detect user session:', e);
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
      console.warn('[HF Yellow Hearts] Error fetching likes:', e);
    } finally {
      isFetchingLikes = false;
    }
  }

  const RESERVED_PREFIXES = new Set([
    'models', 'datasets', 'spaces', 'docs', 'posts', 'papers', 'settings', 'login', 'logout', 'join', 'pricing', 'notifications', 'search'
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
      if (d.includes('22.5') || d.includes('22.45') || (d.startsWith('M22.') && d.includes('29')) || (d.includes('M16') && d.includes('29'))) {
        svg.dataset.hfHeart = 'true';
        svg.classList.add('hf-heart-icon');
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
        heartSvg.dataset.hfHeart = 'true';
        heartSvg.classList.add('hf-heart-icon', 'hf-is-liked-heart');
        heartSvg.classList.remove('hf-is-unliked-heart');

        heartSvg.style.setProperty('color', CONFIG.COLOR_IDLE || '#fbbf24', 'important');
        heartSvg.style.setProperty('fill', CONFIG.COLOR_IDLE || '#fbbf24', 'important');

        if (path) {
          path.style.setProperty('fill', 'currentColor', 'important');
          path.style.setProperty('color', CONFIG.COLOR_IDLE || '#fbbf24', 'important');
        }
      } else {
        delete heartSvg.dataset.hfHeart;
        heartSvg.classList.remove('hf-heart-icon', 'hf-is-liked-heart');
        heartSvg.classList.add('hf-is-unliked-heart');

        heartSvg.style.removeProperty('color');
        heartSvg.style.removeProperty('fill');

        if (path) {
          path.style.removeProperty('fill');
          path.style.removeProperty('color');
        }
      }
    }
  }

  function processModelCards() {
    const cards = document.querySelectorAll('article.overview-card-wrapper');
    cards.forEach(card => {
      const modelId = getModelIdFromCard(card);
      if (!modelId) return;

      updateCardVisual(card, modelId);
      setupHeartButton(card, modelId);
    });
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

    // Prevent parent <a> link drag/selection without calling preventDefault on mousedown
    // (calling preventDefault on mousedown cancels browser click generation)
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

      // Optimistic UI update
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
        processModelCards();
      }, 200);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function setupUI() {
    if (document.getElementById('hf-settings-fab')) return;

    const container = document.createElement('div');
    container.innerHTML = `
      <button id="hf-settings-fab" type="button" title="Configure Hugging Face hearts" aria-label="Configure Hugging Face hearts">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>
      <div id="hf-settings-modal-backdrop">
        <div id="hf-settings-modal" role="dialog" aria-modal="true" aria-labelledby="hf-settings-title">
          <h3 id="hf-settings-title">Hugging Face Hearts</h3>
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
          <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 16px 0;">
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

    const syncFields = () => {
      enabled.checked = CONFIG.ENABLED;
      colorIdle.value = CONFIG.COLOR_IDLE;
      colorHover.value = CONFIG.COLOR_HOVER;
      scaleIdle.value = CONFIG.SCALE_IDLE;
      scaleHover.value = CONFIG.SCALE_HOVER;
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
      CONFIG.ENABLED = enabled.checked;
      CONFIG.COLOR_IDLE = colorIdle.value;
      CONFIG.COLOR_HOVER = colorHover.value;
      CONFIG.SCALE_IDLE = Math.max(1, Math.min(5, parseFloat(scaleIdle.value) || DEFAULTS.SCALE_IDLE));
      CONFIG.SCALE_HOVER = Math.max(1, Math.min(5, parseFloat(scaleHover.value) || DEFAULTS.SCALE_HOVER));
      CONFIG.BORDER_UNLIKED_ENABLED = borderUnlikedEnabled.checked;
      CONFIG.BORDER_UNLIKED_COLOR = borderUnlikedColor.value;
      CONFIG.BORDER_UNLIKED_GLOW = borderUnlikedGlow.checked;
      injectStyles();
      processModelCards();
      close();
    });
  }

  injectStyles();

  const init = async () => {
    setupUI();
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
