with open("userscripts/toppreise/toppreise.user.js", "r") as f:
    content = f.read()

# Replace extractCardData price extraction
search_block = """  function extractCardData(card) {
    const pid = getCardProductId(card);
    const cardPriceEl = CONFIG.USE_SHIPPING_PRICE
      ? (card.querySelector('.price_information_product .shippingPrice .Plugin_Price') || card.querySelector('.price_information_product .productPrice .Plugin_Price') || card.querySelector('.priceContainer.shippingPrice .Plugin_Price') || card.querySelector('.priceContainer.productPrice .Plugin_Price') || card.querySelector('.Plugin_Price'))
      : (card.querySelector('.price_information_product .productPrice .Plugin_Price') || card.querySelector('.price_information_product .shippingPrice .Plugin_Price') || card.querySelector('.priceContainer.productPrice .Plugin_Price') || card.querySelector('.priceContainer.shippingPrice .Plugin_Price') || card.querySelector('.Plugin_Price'));
    const cardPrice = cardPriceEl ? parsePrice(cardPriceEl.textContent) : 0;"""

replace_block = """  function extractCanonicalPrice(card) {
    if (!card) return { price: 0, el: null };

    // First, try to find the specific layout for "ab CHF XX.XX" inside price_information_product
    // which represents the actual current best price shown to the user on the card.
    // It is typically in .productPrice .Plugin_Price or .shippingPrice .Plugin_Price,
    // BUT we must avoid grabbing reference prices that might be hiding in tooltips or other elements.

    // Select the main price container usually containing the primary displayed price
    const mainPriceInfo = card.querySelector('.Plugin_PriceInformation, .price_information_product');

    let priceEl = null;
    if (mainPriceInfo) {
      priceEl = CONFIG.USE_SHIPPING_PRICE
        ? (mainPriceInfo.querySelector('.shippingPrice .Plugin_Price') || mainPriceInfo.querySelector('.productPrice .Plugin_Price'))
        : (mainPriceInfo.querySelector('.productPrice .Plugin_Price') || mainPriceInfo.querySelector('.shippingPrice .Plugin_Price'));
    }

    // Fallbacks
    if (!priceEl) {
      priceEl = CONFIG.USE_SHIPPING_PRICE
        ? (card.querySelector('.priceContainer.shippingPrice .Plugin_Price') || card.querySelector('.priceContainer.productPrice .Plugin_Price') || card.querySelector('.Plugin_Price'))
        : (card.querySelector('.priceContainer.productPrice .Plugin_Price') || card.querySelector('.priceContainer.shippingPrice .Plugin_Price') || card.querySelector('.Plugin_Price'));
    }

    return {
      price: priceEl ? parsePrice(priceEl.textContent) : 0,
      el: priceEl
    };
  }

  function extractCardData(card) {
    const pid = getCardProductId(card);
    const priceData = extractCanonicalPrice(card);
    const cardPriceEl = priceData.el;
    const cardPrice = priceData.price;"""

content = content.replace(search_block, replace_block)

with open("userscripts/toppreise/toppreise.user.js", "w") as f:
    f.write(content)
