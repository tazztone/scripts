// ==UserScript==
// @name         Fastlog Gebraucht & Geprüft Product Watcher
// @namespace    https://github.com/tazztone/scripts
// @version      1.0.1
// @description  Monitors shop.fastlog.ch for new products in Gebraucht & Geprüft category and sends notifications via Telegram, Discord, or Browser.
// @author       tazztone
// @match        https://shop.fastlog.ch/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_notification
// @grant        GM_registerMenuCommand
// @connect      shop.fastlog.ch
// @connect      api.telegram.org
// @connect      discord.com
// @run-at       document-idle
// @background
// @crontab      */15 * * * *
// ==/UserScript==

/**
 * Configuration & Defaults
 */
const CONFIG = {
  RSS_FEED_URL: 'https://shop.fastlog.ch/product-category/gebraucht-geprueft/feed/',
  FALLBACK_HTML_URL: 'https://shop.fastlog.ch/product-category/gebraucht-geprueft/',
  CHECK_INTERVAL_MS: 15 * 60 * 1000, // 15 minutes
  STORAGE_KEYS: {
    SEEN_PRODUCTS: 'fastlog_seen_products_v1',
    TELEGRAM_TOKEN: 'fastlog_telegram_token',
    TELEGRAM_CHAT_ID: 'fastlog_telegram_chat_id',
    DISCORD_WEBHOOK: 'fastlog_discord_webhook',
  },
};

(() => {
  'use strict';

  // State
  let isChecking = false;

  /**
   * Safe Storage Helpers
   */
  function getSeenProducts() {
    try {
      const raw = GM_getValue(CONFIG.STORAGE_KEYS.SEEN_PRODUCTS, '[]');
      return new Set(JSON.parse(raw));
    } catch (err) {
      console.error('[Fastlog Watcher] Error reading storage:', err);
      return new Set();
    }
  }

  function saveSeenProducts(seenSet) {
    try {
      const arr = Array.from(seenSet);
      GM_setValue(CONFIG.STORAGE_KEYS.SEEN_PRODUCTS, JSON.stringify(arr));
    } catch (err) {
      console.error('[Fastlog Watcher] Error writing storage:', err);
    }
  }

  /**
   * Notification Dispatchers
   */
  function notifyTelegram(product) {
    const token = GM_getValue(CONFIG.STORAGE_KEYS.TELEGRAM_TOKEN, '');
    const chatId = GM_getValue(CONFIG.STORAGE_KEYS.TELEGRAM_CHAT_ID, '');

    if (!token || !chatId) return;

    const message = `🛍️ *Neues Produkt auf Fastlog (Gebraucht & Geprüft)!*\n\n*${escapeMarkdown(product.title)}*\n\n🔗 ${product.url}`;

    GM_xmlhttpRequest({
      method: 'POST',
      url: `https://api.telegram.org/bot${token}/sendMessage`,
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({
        chat_id: chatId,
        text: message,
        parse_mode: 'Markdown',
      }),
      onload: (res) => console.log('[Fastlog Watcher] Telegram notification sent:', res.status),
      onerror: (err) => console.error('[Fastlog Watcher] Telegram send failed:', err),
    });
  }

  function notifyDiscord(product) {
    const webhookUrl = GM_getValue(CONFIG.STORAGE_KEYS.DISCORD_WEBHOOK, '');
    if (!webhookUrl) return;

    GM_xmlhttpRequest({
      method: 'POST',
      url: webhookUrl,
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({
        embeds: [{
          title: `🛍️ Neues Produkt: ${product.title}`,
          url: product.url,
          color: 3066993, // Green
          description: product.description || 'Neuer Artikel in Gebraucht & Geprüft hinzugefügt!',
          timestamp: new Date().toISOString(),
        }],
      }),
      onload: (res) => console.log('[Fastlog Watcher] Discord notification sent:', res.status),
      onerror: (err) => console.error('[Fastlog Watcher] Discord send failed:', err),
    });
  }

  function notifyBrowser(product) {
    if (typeof GM_notification === 'function') {
      GM_notification({
        title: 'Fastlog Watcher',
        text: `Neues Produkt: ${product.title}`,
        highlight: true,
        onclick: () => window.open(product.url, '_blank'),
      });
    }
  }

  function escapeMarkdown(text) {
    return text.replace(/[_*[\]()~`>#+-=|{}.!]/g, '\\$&');
  }

  function dispatchNotifications(newProducts) {
    for (const product of newProducts) {
      notifyTelegram(product);
      notifyDiscord(product);
      notifyBrowser(product);
    }
  }

  /**
   * Data Extraction: Primary RSS XML Parser
   */
  function parseRssFeed(xmlText) {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
    const items = xmlDoc.querySelectorAll('item');
    const products = [];

    items.forEach((item) => {
      const title = item.querySelector('title')?.textContent?.trim() || '';
      const url = item.querySelector('link')?.textContent?.trim() || item.querySelector('guid')?.textContent?.trim() || '';
      const description = item.querySelector('description')?.textContent?.replace(/<[^>]*>?/gm, '').trim() || '';

      if (title && url) {
        products.push({ id: url, title, url, description });
      }
    });

    return products;
  }

  /**
   * Data Extraction: Fallback HTML DOM Parser
   */
  function parseCategoryHtml(htmlText) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlText, 'text/html');
    const productElements = doc.querySelectorAll('li.product, .product');
    const products = [];

    productElements.forEach((el) => {
      const linkEl = el.querySelector('a.woocommerce-LoopProduct-link, a[href*="/produkt/"]');
      const titleEl = el.querySelector('.woocommerce-loop-product__title, .product-title, h2, h3');
      const priceEl = el.querySelector('.price, .woocommerce-Price-amount');

      const url = linkEl?.getAttribute('href') || '';
      const title = titleEl?.textContent?.trim() || linkEl?.textContent?.trim() || '';
      const price = priceEl?.textContent?.trim() || '';

      if (url && title) {
        products.push({
          id: url,
          title,
          url,
          description: price ? `Preis: ${price}` : '',
        });
      }
    });

    return products;
  }

  /**
   * Core Watcher Execution Loop
   */
  function checkForNewProducts(isManual = false) {
    if (isChecking) return;
    isChecking = true;

    console.log('[Fastlog Watcher] Checking feed for new products...');

    GM_xmlhttpRequest({
      method: 'GET',
      url: CONFIG.RSS_FEED_URL,
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' },
      onload: (response) => {
        let products = [];
        if (response.status === 200 && response.responseText.includes('<rss')) {
          products = parseRssFeed(response.responseText);
        }

        // Fallback to HTML if RSS failed or returned empty
        if (products.length === 0) {
          fetchHtmlFallback(isManual);
        } else {
          processProducts(products, isManual);
        }
      },
      onerror: () => fetchHtmlFallback(isManual),
    });
  }

  function fetchHtmlFallback(isManual) {
    GM_xmlhttpRequest({
      method: 'GET',
      url: CONFIG.FALLBACK_HTML_URL,
      onload: (response) => {
        if (response.status === 200) {
          const products = parseCategoryHtml(response.responseText);
          processProducts(products, isManual);
        } else {
          console.error('[Fastlog Watcher] Failed to fetch category page');
          isChecking = false;
        }
      },
      onerror: (err) => {
        console.error('[Fastlog Watcher] HTTP error on fallback HTML fetch:', err);
        isChecking = false;
      },
    });
  }

  function processProducts(products, isManual) {
    const seenSet = getSeenProducts();
    const isFirstRun = seenSet.size === 0;
    const newProducts = [];

    for (const prod of products) {
      if (!seenSet.has(prod.id)) {
        seenSet.add(prod.id);
        if (!isFirstRun) {
          newProducts.push(prod);
        }
      }
    }

    saveSeenProducts(seenSet);
    isChecking = false;

    if (isFirstRun) {
      console.log(`[Fastlog Watcher] Initialized watcher. Seeded ${products.length} existing products.`);
      if (isManual) {
        alert(`Initialisierung abgeschlossen! ${products.length} bestehende Produkte gespeichert. Ab jetzt wirst du bei neuen Produkten benachrichtigt.`);
      }
    } else if (newProducts.length > 0) {
      console.log(`[Fastlog Watcher] Found ${newProducts.length} new product(s)!`);
      dispatchNotifications(newProducts);
      if (isManual) {
        alert(`${newProducts.length} neue(s) Produkt(e) gefunden! Benachrichtigung verschickt.`);
      }
    } else {
      console.log('[Fastlog Watcher] No new products found.');
      if (isManual) {
        alert('Keine neuen Produkte gefunden.');
      }
    }
  }

  /**
   * User Configuration Commands (GM Register Menu)
   */
  function registerMenuCommands() {
    if (typeof GM_registerMenuCommand !== 'function') return;

    GM_registerMenuCommand('🔍 Jetzt nach neuen Produkten suchen', () => {
      checkForNewProducts(true);
    });

    GM_registerMenuCommand('⚙️ Telegram Bot Token einstellen', () => {
      const current = GM_getValue(CONFIG.STORAGE_KEYS.TELEGRAM_TOKEN, '');
      const input = prompt('Gib deinen Telegram Bot Token ein (z.B. 123456789:ABCdef...):', current);
      if (input !== null) {
        GM_setValue(CONFIG.STORAGE_KEYS.TELEGRAM_TOKEN, input.trim());
        alert('Telegram Bot Token gespeichert.');
      }
    });

    GM_registerMenuCommand('💬 Telegram Chat ID einstellen', () => {
      const current = GM_getValue(CONFIG.STORAGE_KEYS.TELEGRAM_CHAT_ID, '');
      const input = prompt('Gib deine Telegram Chat ID ein (z.B. 987654321):', current);
      if (input !== null) {
        GM_setValue(CONFIG.STORAGE_KEYS.TELEGRAM_CHAT_ID, input.trim());
        alert('Telegram Chat ID gespeichert.');
      }
    });

    GM_registerMenuCommand('📢 Discord Webhook URL einstellen', () => {
      const current = GM_getValue(CONFIG.STORAGE_KEYS.DISCORD_WEBHOOK, '');
      const input = prompt('Gib deine Discord Webhook URL ein:', current);
      if (input !== null) {
        GM_setValue(CONFIG.STORAGE_KEYS.DISCORD_WEBHOOK, input.trim());
        alert('Discord Webhook URL gespeichert.');
      }
    });
  }

  /**
   * Orchestration & Booting
   */
  registerMenuCommands();

  // Initial check on script load
  checkForNewProducts(false);

  // Background interval check for managers without @crontab support
  setInterval(() => {
    checkForNewProducts(false);
  }, CONFIG.CHECK_INTERVAL_MS);

})();
