with open("userscripts/toppreise/toppreise.user.js", "r") as f:
    content = f.read()

# Make the states explicit in processProductDetailPage and normal badge render
# Wait, let's see how it's handled. It says "Update badge rendering logic to rely on the four states: new-low, at-low, above-low, and unknown, and strictly show 'Aufschlag' only on above-low."
# The user's complaint is: "Since CHF 37.95 equals CHF 37.95, the amber `Aufschlag +26%` state means the comparison code is reading a different, hidden/reference price than the live price rendered on the card. ... The underlying badge logic calculates the warning from cardPrice"
# Actually, we just refactored extractCanonicalPrice to make `cardPrice` correct.
# With cardPrice resolving to 37.95, `cardPrice <= stats.tiefstpreis` is true (3795 <= 3795).
# So it falls into `isAllTimeLow`.
# And `isAllTimeLow` renders:
# `<div class="text">Differenz</div><p>-${rawDiscount}%</p>`
# Wait, the prompt plan asks for:
# "Four explicit states: new-low, at-low, above-low, and unknown."
# "Aufschlag rendering only for a verified above-low state."

search_block = """        if (stats && cardPrice > 0 && stats.tiefstpreis > 0) {
          const isAllTimeLow = priceToCents(cardPrice) <= priceToCents(stats.tiefstpreis);
          const isNonBest = !isAllTimeLow;
          const isNewRecord = !!(stats.isNewAllTimeLow || (isAllTimeLow && stats.previousLow && priceToCents(stats.previousLow) > priceToCents(cardPrice)));
          const prevLow = stats.previousLow;
          const realDropVsPrev = prevLow && prevLow > cardPrice ? Math.round(((prevLow - cardPrice) / prevLow) * 100) : (stats.realDiscountVsPrevLow || 0);

          if (CONFIG.FILTER_BESTPREIS_ENABLED !== false && isNonBest && CONFIG.REAL_DEAL_FILTER_ACTIVE) {
            card.classList.add('tp-non-bestpreis-filtered');
          } else {
            card.classList.remove('tp-non-bestpreis-filtered');
          }

          const hasSignificantPeak = stats.hoechstpreis && stats.hoechstpreis > stats.tiefstpreis * 1.02;

          if (isAllTimeLow) {"""

replace_block = """        if (stats && cardPrice > 0 && stats.tiefstpreis > 0) {
          // Explicit states
          const cPrice = priceToCents(cardPrice);
          const cTiefstpreis = priceToCents(stats.tiefstpreis);

          let state = 'unknown';
          if (cPrice < cTiefstpreis) {
            state = 'new-low';
          } else if (cPrice === cTiefstpreis) {
            state = 'at-low';
          } else {
            state = 'above-low';
          }

          const isAllTimeLow = (state === 'new-low' || state === 'at-low');
          const isNonBest = (state === 'above-low');
          const isNewRecord = (state === 'new-low') || !!(stats.isNewAllTimeLow || (isAllTimeLow && stats.previousLow && priceToCents(stats.previousLow) > cPrice));
          const prevLow = stats.previousLow;
          const realDropVsPrev = prevLow && prevLow > cardPrice ? Math.round(((prevLow - cardPrice) / prevLow) * 100) : (stats.realDiscountVsPrevLow || 0);

          if (CONFIG.FILTER_BESTPREIS_ENABLED !== false && isNonBest && CONFIG.REAL_DEAL_FILTER_ACTIVE) {
            card.classList.add('tp-non-bestpreis-filtered');
          } else {
            card.classList.remove('tp-non-bestpreis-filtered');
          }

          const hasSignificantPeak = stats.hoechstpreis && stats.hoechstpreis > stats.tiefstpreis * 1.02;

          if (isAllTimeLow) {"""

content = content.replace(search_block, replace_block)

with open("userscripts/toppreise/toppreise.user.js", "w") as f:
    f.write(content)
