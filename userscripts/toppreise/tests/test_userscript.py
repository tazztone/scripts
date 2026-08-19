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

    # Expand category drawer if collapsed
    toggle_btn = page.locator('#tp-toggle-cats-btn')
    if toggle_btn.is_visible():
        toggle_btn.click()

    # Verify group pills have proper CSS styling (not unstyled raw text)
    pill = page.locator('.tp-group-pill').first
    page.wait_for_selector('.tp-group-pill')
    assert pill.is_visible()

    # Check computed styles: border-radius, background, display
    display_val = pill.evaluate("el => window.getComputedStyle(el).display")
    border_radius = pill.evaluate("el => window.getComputedStyle(el).borderRadius")
    assert 'inline-flex' in display_val or 'flex' in display_val
    assert border_radius == '12px'


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


def test_modal_popover_in_shadow_dom(page: Page):
    # Open settings modal
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    # Click group chevron inside modal
    chevron = page.locator('#tp-root >> #tp-settings-dialog .tp-group-chevron').first
    page.wait_for_selector('#tp-root >> #tp-settings-dialog .tp-group-chevron', state='visible')
    chevron.click()

    # Verify popover is rendered inside Shadow DOM / dialog
    popover = page.locator('#tp-root >> .tp-group-popover')
    page.wait_for_selector('#tp-root >> .tp-group-popover', state='visible')
    assert popover.is_visible()

    # Close modal
    page.click('#tp-root >> #tp-btn-close')


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

    # Click Reset on toolbar
    page.click('#tp-tb-reset')

    # Verify all filters are cleared and cards restored to visible
    page.wait_for_selector('#card-negative:not(.tp-negative-filtered)', state='visible')
    page.wait_for_selector('#card-low-offers:not(.tp-min-offers-filtered)', state='visible')
    assert 'tp-negative-filtered' not in (page.locator('#card-negative').get_attribute('class') or '')
    assert 'tp-min-offers-filtered' not in (page.locator('#card-low-offers').get_attribute('class') or '')

