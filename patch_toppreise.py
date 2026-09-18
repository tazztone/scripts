import re

with open("userscripts/toppreise/toppreise.user.js", "r") as f:
    content = f.read()

# Introduce priceToCents helper function
helper_fn = """
  const priceToCents = p => Math.round((parseFloat(p) || 0) * 100);
"""
content = content.replace("  const parsePrice = str => {", helper_fn + "\n  const parsePrice = str => {")

# Replace floating-point comparisons
# 1. 1.01 in analyzePriceTimeSeries
content = re.sub(r'while \(idx > 0 && prices\[idx\] <= curr \* 1\.01\) \{', 'while (idx > 0 && priceToCents(prices[idx]) <= priceToCents(curr)) {', content)

# 2. 1.01 in analyzePriceTimeSeries
content = re.sub(r'const isAtAllTimeLow = curr <= allTimeLow \* 1\.01;', 'const isAtAllTimeLow = priceToCents(curr) <= priceToCents(allTimeLow);', content)

# 3. 0.99 in analyzePriceTimeSeries
content = re.sub(r'const isNewAllTimeLow = previousLow > 0 && curr < previousLow \* 0\.99;', 'const isNewAllTimeLow = previousLow > 0 && priceToCents(curr) < priceToCents(previousLow);', content)

# 4. 1.01 in computeDealScore
content = re.sub(r'const isAtLow = cardPrice <= stats\.tiefstpreis \* 1\.01;', 'const isAtLow = priceToCents(cardPrice) <= priceToCents(stats.tiefstpreis);', content)

# 5. 1.01 in extractCardData
content = re.sub(r'const isVerifiedNonBest = !!\(stats && cardPrice > 0 && stats\.tiefstpreis > 0 && cardPrice > stats\.tiefstpreis \* 1\.01\);', 'const isVerifiedNonBest = !!(stats && cardPrice > 0 && stats.tiefstpreis > 0 && priceToCents(cardPrice) > priceToCents(stats.tiefstpreis));', content)

# 6. 1.01 in renderCardEffects
content = re.sub(r'const isAllTimeLow = cardPrice <= stats\.tiefstpreis \* 1\.01;', 'const isAllTimeLow = priceToCents(cardPrice) <= priceToCents(stats.tiefstpreis);', content)

# 7. 1.01 in renderCardEffects (isNewRecord calculation)
content = re.sub(r'\(isAllTimeLow && stats\.previousLow && stats\.previousLow > cardPrice \* 1\.01\)', '(isAllTimeLow && stats.previousLow && priceToCents(stats.previousLow) > priceToCents(cardPrice))', content)

# 8. 1.01 in processProductDetailPage
content = re.sub(r'const isAllTimeLow = currentPrice <= stats\.tiefstpreis \* 1\.01;', 'const isAllTimeLow = priceToCents(currentPrice) <= priceToCents(stats.tiefstpreis);', content)

with open("userscripts/toppreise/toppreise.user.js", "w") as f:
    f.write(content)
