# Research Log: Fastlog Gebraucht & Geprüft Product Watcher

## Target URL
`https://shop.fastlog.ch/product-category/gebraucht-geprueft/`

## Data Sources

### 1. Primary: Category RSS Feed
- **URL**: `https://shop.fastlog.ch/product-category/gebraucht-geprueft/feed/`
- **Type**: `application/rss+xml`
- **Format**: Standard RSS 2.0 XML schema.
- **Key Elements**:
  - `item`: Each product entry.
  - `title`: Product title string.
  - `link`: Direct product URL.
  - `pubDate`: Timestamp when product was posted/updated.
  - `guid`: Unique identifier / permalink.
- **Advantages**: Lightweight, structured XML, fast to parse with standard `DOMParser`.

### 2. Fallback: Category HTML Page
- **URL**: `https://shop.fastlog.ch/product-category/gebraucht-geprueft/`
- **DOM Selectors**:
  - Product Container: `li.product` or `div.product`
  - Title Anchor: `a.woocommerce-LoopProduct-link`, `h2.woocommerce-loop-product__title`
  - Price: `span.woocommerce-Price-amount`
  - Product URL: `href` attribute of `a.woocommerce-LoopProduct-link`

## Notification Targets

### 1. Telegram Bot API
- **Endpoint**: `https://api.telegram.org/bot<TOKEN>/sendMessage`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "chat_id": "<CHAT_ID>",
    "text": "🛍️ *Neues Produkt auf Fastlog!*\n\n*Betty Bossi Hand- und Bodendampfreiniger Set*\n🔗 https://shop.fastlog.ch/produkt/...",
    "parse_mode": "Markdown"
  }
  ```

### 2. Discord Webhook
- **Endpoint**: `https://discord.com/api/webhooks/<WEBHOOK_ID>/<TOKEN>`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "embeds": [
      {
        "title": "🛍️ Neues Produkt: Betty Bossi Hand- und Bodendampfreiniger Set",
        "url": "https://shop.fastlog.ch/produkt/...",
        "color": 3066993
      }
    ]
  }
  ```

### 3. Browser Notification
- **API**: `GM_notification`
- **Fallback**: Native Web Notification API.

## Storage Schema
- `fastlog_seen_products`: `string[]` (Array of product URLs or GUIDs).
- `fastlog_config`: `object` (User credentials for Telegram/Discord).
