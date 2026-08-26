import os
import pytest
from playwright.sync_api import Page

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_HTML = f"file://{os.path.join(BASE_DIR, 'mock_toppreise.html')}"
SCRIPT_PATH = os.path.join(os.path.dirname(BASE_DIR), 'toppreise.user.js')


@pytest.fixture(scope='session')
def userscript_content():
    with open(SCRIPT_PATH, encoding='utf-8') as script:
        return script.read()


@pytest.fixture
def page(browser, userscript_content):
    page = browser.new_page()
    page.goto(MOCK_HTML)
    page.evaluate(userscript_content)
    page.wait_for_selector('#tp-root >> #tp-settings-fab')
    yield page
    page.close()


def test_best_price_highlighting_and_dimming(page: Page):
    # Card 1 is cheapest store price -> highlighted
    page.wait_for_selector('#card-cheapest.tp-is-cheapest')
    assert 'tp-is-cheapest' in (page.locator('#card-cheapest').get_attribute('class') or '')
    assert page.locator('#card-cheapest .tp-best-price-badge').is_visible()

    # Card 2 is more expensive -> not cheapest
    assert 'tp-not-cheapest' in (page.locator('#card-expensive').get_attribute('class') or '')


def test_shadow_dom_settings_dialog_open_and_close(page: Page):
    fab = page.locator('#tp-root >> #tp-settings-fab')
    dialog = page.locator('#tp-root >> #tp-settings-dialog')

    assert not dialog.is_visible()

    fab.click()
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')
    assert dialog.is_visible()

    # Close with close button
    page.click('#tp-root >> #tp-btn-close')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='hidden')
    assert not dialog.is_visible()


def test_negative_keywords_filtering(page: Page):
    # Open settings dialog and set negative keyword
    page.click('#tp-root >> #tp-settings-fab')
    page.fill('#tp-root >> #tp-negative-terms-input', 'Case, Hülle')
    page.click('#tp-root >> #tp-btn-save')

    page.wait_for_selector('#card-negative.tp-negative-filtered', state='attached')
    assert 'tp-negative-filtered' in (page.locator('#card-negative').get_attribute('class') or '')
    assert 'tp-negative-filtered' not in (page.locator('#card-cheapest').get_attribute('class') or '')


def test_min_offers_filter(page: Page):
    # Open settings and set min offers to 3
    page.click('#tp-root >> #tp-settings-fab')
    page.fill('#tp-root >> #tp-min-offers-val', '3')
    page.click('#tp-root >> #tp-btn-save')

    page.wait_for_selector('#card-low-offers.tp-min-offers-filtered', state='attached')
    assert 'tp-min-offers-filtered' in (page.locator('#card-low-offers').get_attribute('class') or '')
    assert 'tp-min-offers-filtered' not in (page.locator('#card-cheapest').get_attribute('class') or '')


def test_price_alarm_automation(page: Page):
    page.evaluate("""() => {
      document.querySelector('#mock-alarm-dialog').style.display = 'block';
    }""")
    page.wait_for_timeout(350)

    price_val = page.locator('#f_NewInfoMailForm_priceFrom').input_value()
    # 60% of CHF 1000.00 = 600.00
    assert price_val == '600.00'
    assert page.locator('#im_nimf_prtrm').is_checked()


def test_suite_filter_bar_and_category_pill_styles(page: Page):
    # Verify filter bar is injected and styled
    filter_bar = page.locator('#tp-suite-filter-bar')
    page.wait_for_selector('#tp-suite-filter-bar')
    assert filter_bar.is_visible()

    # Verify inline negative input is present and styled
    neg_input = page.locator('#tp-inline-negative-input')
    assert neg_input.is_visible()
    border_radius = neg_input.evaluate("el => window.getComputedStyle(el).borderRadius")
    assert border_radius == '8px'


def test_card_quick_block_button_and_toast_undo(page: Page):
    # Verify quick-block button is injected on cards
    page.wait_for_selector('#card-cheapest .tp-card-quick-block')
    btn = page.locator('#card-cheapest .tp-card-quick-block')
    assert btn.is_visible()
    assert 'Grafikkarten' in (btn.text_content() or '')

    # Click quick-block on cheapest card
    btn.click()

    # Card should be category filtered (display: none -> attached)
    page.wait_for_selector('#card-cheapest.tp-category-filtered', state='attached')
    assert 'tp-category-filtered' in (page.locator('#card-cheapest').get_attribute('class') or '')

    # Blocked chip row should appear on top filter bar
    page.wait_for_selector('#tp-suite-filter-bar .tp-blocked-chip')
    chip = page.locator('#tp-suite-filter-bar .tp-blocked-chip').first
    assert chip.is_visible()
    assert 'Grafikkarten' in (chip.text_content() or '')

    # Toast should appear inside Shadow DOM with undo button
    toast = page.locator('#tp-root >> .tp-toast')
    page.wait_for_selector('#tp-root >> .tp-toast', state='visible')
    assert toast.is_visible()
    assert 'Grafikkarten' in (toast.text_content() or '')

    undo_btn = page.locator('#tp-root >> .tp-toast-undo')
    assert undo_btn.is_visible()

    # Click undo
    undo_btn.click()

    # Card should no longer be filtered (becomes visible again)
    page.wait_for_selector('#card-cheapest:not(.tp-category-filtered)', state='visible')
    assert 'tp-category-filtered' not in (page.locator('#card-cheapest').get_attribute('class') or '')


def test_modal_mode_and_settings_in_shadow_dom(page: Page):
    # Open settings modal
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    # Toggle mode to 'hide' via segmented control
    page.click('#tp-root >> label[for="tp-mode-hide"]')
    page.click('#tp-root >> #tp-btn-save')

    # Dialog should close and body class updated
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='hidden')
    has_mode_hide = page.evaluate("() => document.body.classList.contains('tp-mode-hide')")
    assert has_mode_hide is True


def test_sort_by_offers(page: Page):
    # Open settings and enable sort by offers desc
    page.click('#tp-root >> #tp-settings-fab')
    page.click('#tp-root >> label[for="tp-sort-desc"]')
    page.click('#tp-root >> #tp-btn-save')

    # The card with 20 offers (card-cat-excluded) should now be first
    cards = page.locator('#product-list .Plugin_Product')
    first_card_id = cards.first.get_attribute('id')
    assert first_card_id == 'card-cat-excluded'


def test_reset_all_filters(page: Page):
    # Add negative term and min offers filter
    page.click('#tp-root >> #tp-settings-fab')
    page.fill('#tp-root >> #tp-negative-terms-input', 'Case')
    page.fill('#tp-root >> #tp-min-offers-val', '10')
    page.click('#tp-root >> #tp-btn-save')

    page.wait_for_selector('#card-negative.tp-negative-filtered', state='attached')
    page.wait_for_selector('#card-low-offers.tp-min-offers-filtered', state='attached')

    # Click Reset on top filter bar
    page.click('#tp-bar-reset-btn')

    # Verify all filters are cleared and cards restored to visible
    page.wait_for_selector('#card-negative:not(.tp-negative-filtered)', state='visible')
    page.wait_for_selector('#card-low-offers:not(.tp-min-offers-filtered)', state='visible')
    assert 'tp-negative-filtered' not in (page.locator('#card-negative').get_attribute('class') or '')
    assert 'tp-min-offers-filtered' not in (page.locator('#card-low-offers').get_attribute('class') or '')


def test_quick_block_hidden_on_non_neue_toppreise_pages(page: Page):
    # Simulate navigation to a normal search / category page
    page.evaluate("""() => {
        document.body.classList.remove('Page_ListTopPriceReductionProducts');
        document.body.removeAttribute('data-current_url');
        // Trigger re-process
        window.dispatchEvent(new Event('scroll'));
    }""")
    page.wait_for_timeout(350)

    # Verify quick-block buttons are removed / absent on regular pages
    quick_blocks = page.locator('.tp-card-quick-block')
    assert quick_blocks.count() == 0


def test_filter_bar_mounting_safety_and_interaction(page: Page):
    # Assert filter bar is not mounted inside .f_filter_plugin, .filters, or header
    is_safe_placement = page.evaluate("""() => {
        const bar = document.getElementById('tp-suite-filter-bar');
        if (!bar) return false;
        return !bar.closest('.header, [class*="MainTopHead"], [class*="MainHead"], .f_filter_plugin, .filters, .filterBox');
    }""")
    assert is_safe_placement is True

    # Test negative input interaction
    neg_input = page.locator('#tp-inline-negative-input')
    neg_input.fill('Adapter')
    page.wait_for_timeout(250)
    assert neg_input.input_value() == 'Adapter'


def test_discount_heatmap_rendering(page: Page):
    # Card 1 has -67% discount -> hot thermal styling
    page.wait_for_selector('#card-cheapest.tp-heatmap-active')
    card_hot = page.locator('#card-cheapest')
    assert 'tp-heatmap-active' in (card_hot.get_attribute('class') or '')

    # Card 2 has -10% discount -> cold thermal styling
    card_cold = page.locator('#card-expensive')
    assert 'tp-heatmap-active' in (card_cold.get_attribute('class') or '')

    # Check CSS variable values on cards
    hot_bg = card_hot.evaluate("el => el.style.getPropertyValue('--tp-heat-bg')")
    cold_bg = card_cold.evaluate("el => el.style.getPropertyValue('--tp-heat-bg')")
    assert 'linear-gradient' in hot_bg
    assert 'linear-gradient' in cold_bg
    assert hot_bg != cold_bg


def test_discount_heatmap_toolbar_toggle(page: Page):
    heat_btn = page.locator('#tp-bar-heat-btn')
    page.wait_for_selector('#tp-bar-heat-btn')
    assert heat_btn.is_visible()
    assert 'tp-active' in (heat_btn.get_attribute('class') or '')

    # Click to toggle heatmap OFF
    heat_btn.click()
    page.wait_for_timeout(200)

    assert 'tp-active' not in (heat_btn.get_attribute('class') or '')
    assert 'tp-heatmap-active' not in (page.locator('#card-cheapest').get_attribute('class') or '')

    # Click to toggle heatmap back ON
    heat_btn.click()
    page.wait_for_timeout(200)

    assert 'tp-active' in (heat_btn.get_attribute('class') or '')
    assert 'tp-heatmap-active' in (page.locator('#card-cheapest').get_attribute('class') or '')


def test_discount_heatmap_settings_modal_controls(page: Page):
    # Open settings modal
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    # Toggle heatmap switch off inside modal via slider
    slider = page.locator('#tp-root >> #tp-heatmap-enabled-toggle + .tp-slider')
    slider.click()
    page.click('#tp-root >> #tp-btn-save')

    page.wait_for_timeout(200)
    assert 'tp-heatmap-active' not in (page.locator('#card-cheapest').get_attribute('class') or '')

    # Re-enable in settings
    page.click('#tp-root >> #tp-settings-fab')
    slider.click()
    page.click('#tp-root >> #tp-btn-save')

    page.wait_for_timeout(200)
    assert 'tp-heatmap-active' in (page.locator('#card-cheapest').get_attribute('class') or '')


def test_sort_by_discount(page: Page):
    # Open settings and enable sort by discount descending
    page.click('#tp-root >> #tp-settings-fab')
    page.click('#tp-root >> label[for="tp-sort-discount"]')
    page.click('#tp-root >> #tp-btn-save')

    # Card 1 has 67% discount, Card 4 has 50% discount
    cards = page.locator('#product-list .Plugin_Product')
    first_id = cards.nth(0).get_attribute('id')
    second_id = cards.nth(1).get_attribute('id')
    assert first_id == 'card-cheapest'  # 67%
    assert second_id == 'card-cat-excluded'  # 50%


def test_blocked_categories_collapse_and_expand(page: Page):
    # Quick block cheapest card to add category
    page.wait_for_selector('#card-cheapest .tp-card-quick-block')
    page.click('#card-cheapest .tp-card-quick-block')

    # Drawer should be visible (auto-expanded on block action)
    drawer = page.locator('#tp-blocked-cats-container')
    page.wait_for_selector('#tp-blocked-cats-container', state='visible')
    assert drawer.is_visible()

    # Click toggle button in top bar to collapse
    toggle_btn = page.locator('#tp-bar-cats-toggle')
    assert toggle_btn.is_visible()
    toggle_btn.click()

    # Drawer should now be hidden
    page.wait_for_selector('#tp-blocked-cats-container', state='hidden')
    assert not drawer.is_visible()

    # Click toggle button again to expand
    toggle_btn.click()
    page.wait_for_selector('#tp-blocked-cats-container', state='visible')
    assert drawer.is_visible()

