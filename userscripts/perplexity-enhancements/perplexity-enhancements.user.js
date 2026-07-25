// ==UserScript==
// @name         Perplexity Enhancements
// @namespace    https://github.com/tazztone/scripts
// @version      1.0.1
// @description  Keeps a preferred Perplexity model active and safely automates agent approvals and GitHub connector enablement.
// @author       tazztone
// @match        https://www.perplexity.ai/*
// @match        https://perplexity.ai/*
// @run-at       document-idle
// @grant        GM_getValue
// @grant        GM_setValue
// @noframes
// ==/UserScript==

const DEFAULTS = {
  MODEL_LOCK_ENABLED: true,
  TARGET_MODEL: 'Claude Sonnet 4.6',
  ENABLE_THINKING: true,
  AUTO_APPROVE: true,
  AUTO_ENABLE_GITHUB: true,
  CLICK_DELAY_MS: 3000,
  APPROVE_TEXTS: ['approve', 'confirm', 'allow'],
  OBSERVER_DEBOUNCE_MS: 150,
  MODEL_COOLDOWN_MS: 900,
  DEBUG: true
};

const STORAGE_PREFIX = 'px_enhancements_';
const LEGACY_PREFIXES = ['px_model_lock_', 'px_auto_approve_'];

const FEATURE_STYLES = `
  .px-model-lock-indicator { width: 6px; height: 6px; border-radius: 50%; display: inline-block; margin-left: 8px; vertical-align: middle; transition: all .3s ease; }
  .px-auto-approve-btn { position: relative !important; overflow: hidden !important; }
  .px-progress-bar { position: absolute; top: 0; left: 0; height: 4px; width: 100%; background: #00cc66; transform-origin: left; z-index: 10; pointer-events: none; }
  .px-paused .px-progress-bar { background: #ffa500 !important; }
`;

const MODAL_STYLES = `
  #px-settings-fab { position: fixed; right: 16px; bottom: 16px; width: 50px; height: 50px; border: 1px solid rgba(255,255,255,.14); border-radius: 50%; background: rgba(30,41,59,.9); color: #f1f5f9; box-shadow: 0 4px 12px rgba(0,0,0,.3); cursor: pointer; z-index: 99999; display: flex; align-items: center; justify-content: center; transition: all .2s ease; }
  #px-settings-fab:hover { background: rgba(59,130,246,.95); transform: scale(1.08); }
  #px-settings-fab svg { width: 24px; height: 24px; }
  #px-settings-modal-backdrop { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; background: rgba(15,23,42,.55); backdrop-filter: blur(6px); z-index: 99998; opacity: 0; pointer-events: none; transition: opacity .2s ease; }
  #px-settings-modal-backdrop.open { opacity: 1; pointer-events: auto; }
  #px-settings-modal { box-sizing: border-box; width: min(90%, 480px); max-height: 85vh; overflow-y: auto; padding: 24px; border: 1px solid rgba(255,255,255,.12); border-radius: 16px; background: rgba(30,41,59,.96); color: #f8fafc; box-shadow: 0 20px 25px -5px rgba(0,0,0,.5); font: 14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; transform: translateY(8px) scale(.97); transition: transform .2s ease; }
  #px-settings-modal-backdrop.open #px-settings-modal { transform: translateY(0) scale(1); }
  #px-settings-modal h3 { margin: 0 0 20px; color: #60a5fa; font-size: 18px; }
  .px-settings-section { padding-bottom: 8px; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,.08); }
  .px-settings-section h4 { margin: 0 0 16px; color: #60a5fa; font-size: 13px; letter-spacing: .5px; text-transform: uppercase; }
  .px-settings-group { display: flex; flex-direction: column; gap: 8px; margin-bottom: 18px; }
  .px-settings-group label { color: #cbd5e1; font-size: 13px; font-weight: 600; }
  .px-settings-group input[type="text"], .px-settings-group input[type="number"] { box-sizing: border-box; width: 100%; min-height: 34px; padding: 6px 8px; border: 1px solid rgba(255,255,255,.12); border-radius: 6px; background: rgba(15,23,42,.7); color: #fff; }
  .px-settings-group input[type="range"] { width: 100%; accent-color: #3b82f6; }
  .px-switch-container { display: flex; flex-direction: row; align-items: center; justify-content: space-between; }
  .px-switch { position: relative; width: 44px; height: 24px; flex: 0 0 auto; }
  .px-switch input { position: absolute; opacity: 0; width: 1px; height: 1px; }
  .px-slider { position: absolute; inset: 0; border: 1px solid rgba(255,255,255,.12); border-radius: 24px; background: rgba(15,23,42,.7); cursor: pointer; }
  .px-slider::before { content: ""; position: absolute; left: 3px; bottom: 3px; width: 16px; height: 16px; border-radius: 50%; background: #94a3b8; transition: transform .2s ease; }
  .px-switch input:checked + .px-slider { background: #3b82f6; }
  .px-switch input:checked + .px-slider::before { transform: translateX(20px); background: #fff; }
  .px-modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }
  .px-btn { padding: 10px 18px; border-radius: 8px; border: 0; font-size: 13px; font-weight: 600; cursor: pointer; }
  .px-btn-secondary { border: 1px solid rgba(255,255,255,.12); background: transparent; color: #cbd5e1; }
  .px-btn-primary { background: linear-gradient(135deg,#60a5fa,#2563eb); color: #fff; }
`;

(() => {
  'use strict';

  const log = (...args) => { if (readConfig('DEBUG', DEFAULTS.DEBUG)) console.log('[Perplexity Enhancements]', ...args); };
  const error = (...args) => console.error('[Perplexity Enhancements]', ...args);
  const normalize = value => String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();

  function parseStored(value) {
    if (value === null || value === undefined) return { found: false, value: undefined };
    if (typeof value !== 'string') return { found: true, value };
    try { return { found: true, value: JSON.parse(value) }; } catch (_) { return { found: true, value }; }
  }

  function readLocal(key) {
    try { return parseStored(localStorage.getItem(key)); } catch (_) { return { found: false, value: undefined }; }
  }

  function readGM(key) {
    try {
      if (typeof GM_getValue === 'function') return parseStored(GM_getValue(key, undefined));
    } catch (_) { /* fall through to localStorage */ }
    return { found: false, value: undefined };
  }

  function writeValue(key, value) {
    try { if (typeof GM_setValue === 'function') GM_setValue(STORAGE_PREFIX + key, value); } catch (_) { /* localStorage remains available */ }
    try { localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value)); } catch (_) { /* storage may be blocked */ }
  }

  function readConfig(key, fallback) {
    const canonicalKey = STORAGE_PREFIX + key;
    const gm = readGM(canonicalKey);
    if (gm.found) return gm.value;

    const canonicalLocal = readLocal(canonicalKey);
    if (canonicalLocal.found) {
      try { if (typeof GM_setValue === 'function') GM_setValue(canonicalKey, canonicalLocal.value); } catch (_) {}
      return canonicalLocal.value;
    }

    for (const prefix of LEGACY_PREFIXES) {
      const legacy = readLocal(prefix + key);
      if (legacy.found) {
        writeValue(key, legacy.value);
        log('Migrated legacy setting', prefix + key, 'to', canonicalKey);
        return legacy.value;
      }
    }
    return fallback;
  }

  function intConfig(key, fallback, min, max) {
    const value = Number.parseInt(readConfig(key, fallback), 10);
    if (!Number.isFinite(value)) return fallback;
    return Math.max(min, Math.min(max, value));
  }

  const CONFIG = {
    get MODEL_LOCK_ENABLED() {
      const canonical = readConfig('MODEL_LOCK_ENABLED', undefined);
      if (canonical !== undefined) return Boolean(canonical);
      const legacy = readConfig('ENABLED', undefined);
      if (legacy !== undefined) { writeValue('MODEL_LOCK_ENABLED', Boolean(legacy)); return Boolean(legacy); }
      return DEFAULTS.MODEL_LOCK_ENABLED;
    },
    set MODEL_LOCK_ENABLED(value) { writeValue('MODEL_LOCK_ENABLED', Boolean(value)); },
    get TARGET_MODEL() { return String(readConfig('TARGET_MODEL', DEFAULTS.TARGET_MODEL)); },
    set TARGET_MODEL(value) { writeValue('TARGET_MODEL', String(value)); },
    get ENABLE_THINKING() { return Boolean(readConfig('ENABLE_THINKING', DEFAULTS.ENABLE_THINKING)); },
    set ENABLE_THINKING(value) { writeValue('ENABLE_THINKING', Boolean(value)); },
    get AUTO_APPROVE() { return Boolean(readConfig('AUTO_APPROVE', DEFAULTS.AUTO_APPROVE)); },
    set AUTO_APPROVE(value) { writeValue('AUTO_APPROVE', Boolean(value)); },
    get AUTO_ENABLE_GITHUB() { return Boolean(readConfig('AUTO_ENABLE_GITHUB', DEFAULTS.AUTO_ENABLE_GITHUB)); },
    set AUTO_ENABLE_GITHUB(value) { writeValue('AUTO_ENABLE_GITHUB', Boolean(value)); },
    get CLICK_DELAY_MS() { return intConfig('CLICK_DELAY_MS', DEFAULTS.CLICK_DELAY_MS, 100, 30000); },
    set CLICK_DELAY_MS(value) {
      const parsed = Number.parseInt(value, 10);
      writeValue('CLICK_DELAY_MS', Math.max(100, Math.min(30000, Number.isFinite(parsed) ? parsed : DEFAULTS.CLICK_DELAY_MS)));
    },
    get APPROVE_TEXTS() { return readConfig('APPROVE_TEXTS', DEFAULTS.APPROVE_TEXTS); },
    get OBSERVER_DEBOUNCE_MS() { return intConfig('OBSERVER_DEBOUNCE_MS', DEFAULTS.OBSERVER_DEBOUNCE_MS, 50, 1000); },
    get MODEL_COOLDOWN_MS() { return intConfig('MODEL_COOLDOWN_MS', DEFAULTS.MODEL_COOLDOWN_MS, 100, 5000); },
    get DEBUG() { return Boolean(readConfig('DEBUG', DEFAULTS.DEBUG)); }
  };

  function injectStyle(id, text) {
    if (document.getElementById(id)) return;
    const style = document.createElement('style');
    style.id = id;
    style.textContent = text;
    (document.head || document.documentElement).appendChild(style);
  }

  function isVisible(el) {
    if (!el || !document.contains(el)) return false;
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0;
  }

  function dispatchClickEvents(el) {
    if (!el) return;
    const events = [
      typeof PointerEvent === 'function' ? new PointerEvent('pointerdown', { bubbles: true, cancelable: true }) : null,
      typeof PointerEvent === 'function' ? new PointerEvent('pointerup', { bubbles: true, cancelable: true }) : null,
      new MouseEvent('mousedown', { bubbles: true, cancelable: true }),
      new MouseEvent('mouseup', { bubbles: true, cancelable: true }),
      new MouseEvent('click', { bubbles: true, cancelable: true })
    ];
    events.filter(Boolean).forEach(event => el.dispatchEvent(event));
  }

  // --- Model lock ---
  function findModelButton() {
    const textarea = document.querySelector('textarea[placeholder*="Ask" i], textarea[placeholder*="anything" i], textarea');
    const promptBox = textarea && (textarea.closest('form') || textarea.parentElement?.closest('div'));
    const candidates = promptBox ? [...promptBox.querySelectorAll('button')] : [...document.querySelectorAll('button')];
    const keywords = ['model', 'best', 'sonar', 'gpt-', 'gemini', 'claude'];

    return candidates.find(btn => {
      if (!isVisible(btn)) return false;
      const text = normalize(btn.textContent);
      const label = normalize(btn.getAttribute('aria-label'));
      if (text.includes('github') || text.includes('attach') || text.includes('focus') || text.includes('search') || label.includes('voice') || label.includes('dictate')) return false;
      const rect = btn.getBoundingClientRect();
      if (Math.abs(rect.width - rect.height) < 4 && rect.width < 50) return false;
      const hasMenu = ['menu', 'listbox', 'dialog'].includes(btn.getAttribute('aria-haspopup')) || btn.hasAttribute('aria-expanded');
      const hasChevron = Boolean(btn.querySelector('svg')) || /[⌵▼]/.test(text);
      return hasMenu || hasChevron || keywords.some(keyword => text.includes(keyword));
    });
  }

  function isTargetStateActive(button) {
    if (!button) return false;
    const text = normalize(button.textContent);
    const modelMatches = text.includes(normalize(CONFIG.TARGET_MODEL));
    const thinkingMatches = text.includes('thinking');
    return CONFIG.ENABLE_THINKING ? modelMatches && thinkingMatches : modelMatches && !thinkingMatches;
  }

  function isDisabledOption(el) {
    const text = normalize(el.textContent);
    return el.disabled || el.getAttribute('aria-disabled') === 'true' || el.getAttribute('data-disabled') !== null || text.includes('locked') || (text.includes('max') && text.includes('claude')) || window.getComputedStyle(el).opacity === '0.5';
  }

  function findDropdownModelItem() {
    const target = normalize(CONFIG.TARGET_MODEL);
    const trigger = findModelButton();
    const candidates = [...document.querySelectorAll('[role="menuitem"], [role="option"], [role="menuitemcheckbox"], button, .dropdown-item')];
    return candidates.find(el => isVisible(el) && !el.closest('#px-settings-modal') && el !== trigger && !trigger?.contains(el) && !isDisabledOption(el) && normalize(el.textContent).includes(target));
  }

  function findThinkingRow() {
    const trigger = findModelButton();
    const candidates = [...document.querySelectorAll('[role="menuitem"], [role="option"], [role="menuitemcheckbox"], button, .dropdown-item, div')];
    return candidates.find(el => {
      if (!isVisible(el) || el.closest('#px-settings-modal') || el === trigger || trigger?.contains(el)) return false;
      const text = normalize(el.textContent);
      return text.includes('thinking') && !/(claude|gpt|sonar|gemini)/.test(text) && el.querySelector('button[role="switch"], input[type="checkbox"], [aria-checked]');
    });
  }

  function switchState(row) {
    const el = row?.querySelector('button[role="switch"], input[type="checkbox"], [aria-checked]');
    if (!el) return null;
    return el.type === 'checkbox' ? el.checked : el.getAttribute('aria-checked') === 'true';
  }

  function ensureSwitchState(row, desired) {
    const current = switchState(row);
    if (current === null || current === desired) return false;
    const control = row.querySelector('button[role="switch"], input[type="checkbox"], [aria-checked]');
    dispatchClickEvents(control);
    return true;
  }

  function updateModelIndicator(active, status) {
    const button = findModelButton();
    if (!button) return;
    let indicator = button.querySelector('.px-model-lock-indicator');
    if (!indicator) { indicator = document.createElement('span'); indicator.className = 'px-model-lock-indicator'; button.appendChild(indicator); }
    indicator.style.backgroundColor = active ? '#00cc66' : '#ffa500';
    indicator.style.boxShadow = `0 0 6px ${active ? '#00cc66' : '#ffa500'}`;
    indicator.title = active ? `Model lock active: ${CONFIG.TARGET_MODEL}` : `Model lock: ${status}`;
  }

  function removeModelIndicators() { document.querySelectorAll('.px-model-lock-indicator').forEach(el => el.remove()); }

  let modelInteraction = false;
  let modelCooldownUntil = 0;

  function runModelLock() {
    if (!CONFIG.MODEL_LOCK_ENABLED) { removeModelIndicators(); return; }
    if (modelInteraction || Date.now() < modelCooldownUntil) return;
    const button = findModelButton();
    if (!button) return;
    if (isTargetStateActive(button)) { updateModelIndicator(true, 'active'); return; }
    updateModelIndicator(false, 'syncing');

    const modelItem = findDropdownModelItem();
    const thinkingRow = findThinkingRow();
    if (!modelItem && !thinkingRow) {
      modelInteraction = true;
      dispatchClickEvents(button);
      setTimeout(() => { modelInteraction = false; runModelLock(); }, 250);
      return;
    }

    modelInteraction = true;
    let changed = false;
    if (thinkingRow) changed = ensureSwitchState(thinkingRow, CONFIG.ENABLE_THINKING) || changed;
    if (modelItem) { dispatchClickEvents(modelItem); changed = true; }
    modelCooldownUntil = Date.now() + CONFIG.MODEL_COOLDOWN_MS;
    setTimeout(() => { modelCooldownUntil = 0; modelInteraction = false; runModelLock(); }, changed ? CONFIG.MODEL_COOLDOWN_MS + 50 : 250);
  }

  // --- Approval automation ---
  const activeTimers = new Map();

  function findApproveButtons() {
    const texts = Array.isArray(CONFIG.APPROVE_TEXTS) ? CONFIG.APPROVE_TEXTS : DEFAULTS.APPROVE_TEXTS;
    return [...document.querySelectorAll('button, [role="button"]')].filter(el => {
      const text = normalize(el.textContent);
      return isVisible(el) && !activeTimers.has(el) && !el.dataset.pxClicked && !el.disabled && el.getAttribute('aria-disabled') !== 'true' && texts.some(value => text.startsWith(normalize(value)));
    });
  }

  function removeApprovalDecoration(button) {
    button.classList.remove('px-auto-approve-btn', 'px-paused');
    button.querySelector('.px-progress-bar')?.remove();
  }

  function scheduleApproval(button) {
    if (activeTimers.has(button)) return;
    const delay = CONFIG.CLICK_DELAY_MS;
    button.classList.add('px-auto-approve-btn');
    const progress = document.createElement('div');
    progress.className = 'px-progress-bar';
    progress.style.transform = 'scaleX(1)';
    button.appendChild(progress);
    let remaining = delay;
    let paused = false;
    let timer;
    const update = () => { progress.style.transform = `scaleX(${Math.max(0, remaining / delay)})`; };
    const cleanup = () => { clearInterval(timer); activeTimers.delete(button); removeApprovalDecoration(button); };
    const tick = () => {
      if (!document.contains(button) || !isVisible(button) || button.dataset.pxClicked) { cleanup(); return; }
      if (paused) return;
      remaining -= 100;
      update();
      if (remaining <= 0) {
        cleanup();
        button.dataset.pxClicked = '1';
        button.click();
        log('Approved action card button.');
      }
    };
    timer = setInterval(tick, 100);
    activeTimers.set(button, timer);
    button.addEventListener('mouseenter', () => { paused = true; button.classList.add('px-paused'); }, { passive: true });
    button.addEventListener('mouseleave', () => { paused = false; button.classList.remove('px-paused'); }, { passive: true });
  }

  function cancelApprovalTimers() {
    activeTimers.forEach((timer, button) => { clearInterval(timer); removeApprovalDecoration(button); });
    activeTimers.clear();
  }

  // --- GitHub connector ---
  function isGithubEnabled() {
    const active = [...document.querySelectorAll('button[aria-haspopup="menu"], button[aria-expanded], [data-testid="message-input-active-connectors"] img[alt*="GitHub" i]')];
    return active.some(el => normalize(el.textContent || el.getAttribute('alt')).includes('github')) || Boolean(document.querySelector('svg path[d*="M12 2C6.477 2 2 6.477 2 12c0 4.419 2.865 8.166 6.839 9.489"]'));
  }

  function tryClickSuggestionPill() {
    if (!CONFIG.AUTO_ENABLE_GITHUB || isGithubEnabled()) return false;
    const matches = ['github', '+ github', 'github +', 'add github', 'enable github'];
    const pill = [...document.querySelectorAll('button')].find(el => {
      const text = normalize(el.textContent);
      if (!matches.includes(text) || !isVisible(el) || el.getAttribute('aria-haspopup') === 'menu' || el.getBoundingClientRect().width > 500) return false;
      const style = window.getComputedStyle(el);
      const dashed = el.classList.contains('border-dashed') || style.borderStyle === 'dashed';
      const plus = Boolean(el.querySelector('use[xlink\\:href*="plus"], svg path[d*="M12 5l0 14"], svg path[d*="M19 13h-6"]'));
      return dashed || plus;
    });
    if (pill) { pill.click(); log('Enabled GitHub via suggestion pill.'); return true; }
    return false;
  }

  let connectorLock = false;
  let connectorRoute = location.href;

  function runGithub() {
    if (!CONFIG.AUTO_ENABLE_GITHUB || isGithubEnabled() || connectorLock) return;
    connectorLock = true;
    tryClickSuggestionPill();
    setTimeout(() => { connectorLock = false; }, 2000);
  }

  // --- Settings UI ---
  function setupSettingsUI() {
    if (document.getElementById('px-settings-fab')) return;
    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
      <button id="px-settings-fab" type="button" title="Configure Perplexity enhancements" aria-label="Configure Perplexity enhancements">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2a2 2 0 0 1 2 2v.2a7.7 7.7 0 0 1 2.1.9l.15-.1a2 2 0 1 1 2.8 2.8l-.1.15a7.7 7.7 0 0 1 .9 2.1H20a2 2 0 1 1 0 4h-.2a7.7 7.7 0 0 1-.9 2.1l.1.15a2 2 0 1 1-2.8 2.8l-.15-.1a7.7 7.7 0 0 1-2.1.9V20a2 2 0 1 1-4 0v-.2a7.7 7.7 0 0 1-2.1-.9l-.15.1a2 2 0 1 1-2.8-2.8l.1-.15a7.7 7.7 0 0 1-.9-2.1H4a2 2 0 1 1 0-4h.2a7.7 7.7 0 0 1 .9-2.1l-.1-.15a2 2 0 1 1 2.8-2.8l.15.1a7.7 7.7 0 0 1 2.1-.9V4a2 2 0 0 1 2-2z"/><circle cx="12" cy="12" r="3"/></svg>
      </button>
      <div id="px-settings-modal-backdrop"><div id="px-settings-modal" role="dialog" aria-modal="true" aria-labelledby="px-settings-title" tabindex="-1">
        <h3 id="px-settings-title">Perplexity Enhancements</h3>
        <section class="px-settings-section"><h4>Model Lock</h4>
          <div class="px-settings-group px-switch-container"><label for="px-model-lock-enabled">Enable model lock</label><label class="px-switch"><input id="px-model-lock-enabled" type="checkbox"><span class="px-slider"></span></label></div>
          <div class="px-settings-group"><label for="px-model-lock-target">Target model</label><input id="px-model-lock-target" type="text" autocomplete="off"></div>
          <div class="px-settings-group px-switch-container"><label for="px-model-lock-thinking">Enable Thinking mode</label><label class="px-switch"><input id="px-model-lock-thinking" type="checkbox"><span class="px-slider"></span></label></div>
        </section>
        <section class="px-settings-section"><h4>Auto Approve</h4>
          <div class="px-settings-group px-switch-container"><label for="px-auto-approve-enabled">Auto-approve actions</label><label class="px-switch"><input id="px-auto-approve-enabled" type="checkbox"><span class="px-slider"></span></label></div>
          <div class="px-settings-group px-switch-container"><label for="px-auto-approve-github">Auto-enable GitHub</label><label class="px-switch"><input id="px-auto-approve-github" type="checkbox"><span class="px-slider"></span></label></div>
          <div class="px-settings-group" id="px-auto-approve-delay-group"><label for="px-auto-approve-delay-range">Approval countdown (seconds)</label><input id="px-auto-approve-delay-range" type="range" min="1" max="30" step="1"><input id="px-auto-approve-delay-value" type="number" min="1" max="30" step="1"></div>
        </section>
        <div class="px-modal-actions"><button type="button" class="px-btn px-btn-secondary" id="px-btn-close">Cancel</button><button type="button" class="px-btn px-btn-primary" id="px-btn-save">Save Settings</button></div>
      </div></div>`;
    document.body.appendChild(wrapper);

    const backdrop = document.getElementById('px-settings-modal-backdrop');
    const modal = document.getElementById('px-settings-modal');
    const enabled = document.getElementById('px-model-lock-enabled');
    const target = document.getElementById('px-model-lock-target');
    const thinking = document.getElementById('px-model-lock-thinking');
    const autoApprove = document.getElementById('px-auto-approve-enabled');
    const autoGithub = document.getElementById('px-auto-approve-github');
    const delayRange = document.getElementById('px-auto-approve-delay-range');
    const delayValue = document.getElementById('px-auto-approve-delay-value');
    const delayGroup = document.getElementById('px-auto-approve-delay-group');
    const sync = () => {
      enabled.checked = CONFIG.MODEL_LOCK_ENABLED; target.value = CONFIG.TARGET_MODEL; thinking.checked = CONFIG.ENABLE_THINKING;
      autoApprove.checked = CONFIG.AUTO_APPROVE; autoGithub.checked = CONFIG.AUTO_ENABLE_GITHUB;
      const seconds = Math.max(1, Math.min(30, Math.round(CONFIG.CLICK_DELAY_MS / 1000))); delayRange.value = seconds; delayValue.value = seconds;
      delayGroup.style.opacity = CONFIG.AUTO_APPROVE ? '1' : '.4'; delayGroup.querySelectorAll('input').forEach(input => { input.disabled = !CONFIG.AUTO_APPROVE; });
    };
    const close = () => backdrop.classList.remove('open');
    document.getElementById('px-settings-fab').addEventListener('click', () => { sync(); backdrop.classList.add('open'); modal.focus(); });
    document.getElementById('px-btn-close').addEventListener('click', close);
    backdrop.addEventListener('click', event => { if (event.target === backdrop) close(); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && backdrop.classList.contains('open')) close(); });
    autoApprove.addEventListener('change', event => { delayGroup.style.opacity = event.target.checked ? '1' : '.4'; delayGroup.querySelectorAll('input').forEach(input => { input.disabled = !event.target.checked; }); });
    delayRange.addEventListener('input', event => { delayValue.value = event.target.value; });
    delayValue.addEventListener('input', event => { delayRange.value = event.target.value; });
    document.getElementById('px-btn-save').addEventListener('click', () => {
      const model = target.value.trim();
      if (!model) { target.focus(); return; }
      const seconds = Math.max(1, Math.min(30, Number.parseInt(delayValue.value, 10) || 3));
      CONFIG.MODEL_LOCK_ENABLED = enabled.checked; CONFIG.TARGET_MODEL = model; CONFIG.ENABLE_THINKING = thinking.checked;
      CONFIG.AUTO_APPROVE = autoApprove.checked; CONFIG.AUTO_ENABLE_GITHUB = autoGithub.checked; CONFIG.CLICK_DELAY_MS = seconds * 1000;
      modelInteraction = false; modelCooldownUntil = 0;
      if (!CONFIG.AUTO_APPROVE) cancelApprovalTimers();
      if (!CONFIG.MODEL_LOCK_ENABLED) removeModelIndicators();
      close(); run();
    });
    sync();
  }

  // --- Shared orchestration ---
  function run() {
    try {
      if (CONFIG.MODEL_LOCK_ENABLED) runModelLock(); else removeModelIndicators();
      if (CONFIG.AUTO_APPROVE) findApproveButtons().forEach(scheduleApproval); else cancelApprovalTimers();
      if (CONFIG.AUTO_ENABLE_GITHUB) runGithub();
    } catch (e) { error('Run failed:', e); modelInteraction = false; }
  }

  let debounceTimer = null;
  let lastUrl = location.href;
  const observer = new MutationObserver(() => {
    try {
      if (location.href !== lastUrl) { lastUrl = location.href; modelInteraction = false; modelCooldownUntil = 0; connectorLock = false; connectorRoute = lastUrl; }
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(run, CONFIG.OBSERVER_DEBOUNCE_MS);
    } catch (e) { error('Observer failed:', e); }
  });

  const handleNavigation = () => { lastUrl = location.href; modelInteraction = false; modelCooldownUntil = 0; connectorLock = false; connectorRoute = lastUrl; run(); };
  if (self.navigation && typeof self.navigation.addEventListener === 'function') self.navigation.addEventListener('navigatesuccess', handleNavigation);

  injectStyle('px-enhancements-feature-style', FEATURE_STYLES);
  injectStyle('px-enhancements-modal-style', MODAL_STYLES);
  setupSettingsUI();
  observer.observe(document.documentElement, { childList: true, subtree: true });
  run();
  setInterval(run, 5000);
})();
