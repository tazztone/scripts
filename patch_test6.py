with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

# Add a test for the regression fixture
test_code = """
def test_competing_reference_price_resolves_to_green_low(page: Page):
    \"\"\"
    Validates that the userscript extracts the canonical price (CHF 37.95) correctly
    and ignores competing reference prices (CHF 47.82), resolving to a green
    'Allzeit-Tiefstpreis' state instead of an amber 'Aufschlag' state.
    \"\"\"
    # Wait for initial render
    page.wait_for_selector('.badge-dif')

    card = page.locator('#card-competing-reference')
    badge = card.locator('.badge-dif')

    # Enable Real Deal Filter if necessary
    page.evaluate("() => { window.ToppreiseSuite.CONFIG.REAL_DEAL_FILTER_ACTIVE = true; }")

    # It starts as unchecked
    assert badge.is_visible()

    # Mock the time series endpoint for it
    page.route("**/plugins/product/pricechart", lambda route: route.fulfill(
        status=200,
        headers={'access-control-allow-origin': '*'},
        content_type='application/json',
        body='[[[100000, 47.82], [200000, 37.95]]]'
    ) if '1003795' in route.request.post_data else route.continue_())

    # Click to verify
    badge.click()

    # Wait for the emerald halo to be applied
    expect(badge).to_have_class(re.compile(r'tp-deal-alltime-low'))

    # Should not have the not-low class
    expect(badge).not_to_have_class(re.compile(r'tp-deal-not-low'))

    # Title should indicate Allzeit-Tiefstpreis
    assert 'Allzeit-Tiefstpreis (CHF 37.95)' in badge.get_attribute('title')
"""

# Insert it before the first test function
import re
content = re.sub(r'def test_best_price_highlighting_and_dimming\(page: Page\):', test_code + '\n\ndef test_best_price_highlighting_and_dimming(page: Page):', content)

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
