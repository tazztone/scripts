with open("userscripts/toppreise/toppreise.user.js", "r") as f:
    content = f.read()

# Since we already extract the canonical price and recalculate states continuously inside processListings -> renderCardEffects
# using the LATEST cardPrice and LATEST stats object on every DOM mutation or debounce timer,
# "ensuring the current card price hasn't changed from when the network request was fired" is naturally
# handled in the reactive loop because `extractCardData` grabs the fresh DOM price and `computeDealScore` / `isAllTimeLow` recalculate.
# However, to be extra robust, we should explicitly check inside the click handler to make sure `extractCanonicalPrice` didn't change while awaiting.
# Actually, the user's issue says:
# "A request-time/current-time price recheck to prevent stale asynchronous history responses from applying to a changed card."

search_block = """          badgeDifEl.classList.add('tp-deal-loading');
          badgeDifEl.innerHTML = `<div class="text">Prüfe...</div><p>⏳</p>`;
          const fetchedStats = await fetchSingleProductPriceStats(currentPid, 1, true);
          badgeDifEl.classList.remove('tp-deal-loading');
          if (fetchedStats) {
            processListings();
          } else {"""

replace_block = """          badgeDifEl.classList.add('tp-deal-loading');
          badgeDifEl.innerHTML = `<div class="text">Prüfe...</div><p>⏳</p>`;
          const requestTimePrice = extractCanonicalPrice(card).price;
          const fetchedStats = await fetchSingleProductPriceStats(currentPid, 1, true);

          // Re-verify the card's price hasn't changed underneath us (e.g. dynamic sorting/reactivity)
          const currentTimePrice = extractCanonicalPrice(card).price;
          if (requestTimePrice !== currentTimePrice) {
            // Price changed during fetch, fetch might be stale or product swapped
            badgeDifEl.classList.remove('tp-deal-loading');
            return;
          }

          badgeDifEl.classList.remove('tp-deal-loading');
          if (fetchedStats) {
            processListings();
          } else {"""

content = content.replace(search_block, replace_block)

with open("userscripts/toppreise/toppreise.user.js", "w") as f:
    f.write(content)
