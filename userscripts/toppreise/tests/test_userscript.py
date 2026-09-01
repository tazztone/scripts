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
    page.wait_for_timeout(250)

    price_val = page.locator('#f_NewInfoMailForm_priceFrom').input_value()
    # 60% of CHF 1000.00 = 600.00
    assert price_val == '600.00'
    assert page.locator('#im_nimf_prtrm').is_checked()

    # Pre-submit delay (300ms): after 450ms total, it should have submitted
    page.wait_for_timeout(250)
    assert page.locator('#mock-alarm-dialog').get_attribute('data-submitted') == 'true'

    # Grace period before closing (800ms after submit): wait until 1300ms total
    page.wait_for_timeout(900)
    assert page.locator('#mock-alarm-dialog').get_attribute('data-dialog-closed') == 'true'
    assert not page.locator('#mock-alarm-dialog').is_visible()


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


def test_darkreader_dynamic_mode_compatibility(page: Page):
    # Simulate DarkReader stamping data attributes and check that userscript maintains gradient
    page.wait_for_selector('#card-cheapest.tp-heatmap-active')
    card = page.locator('#card-cheapest')

    # Check that darkreader CSS variables are properly populated with gradient and transparent bg
    dr_bgimage = card.evaluate("el => el.style.getPropertyValue('--darkreader-inline-bgimage')")
    dr_bgcolor = card.evaluate("el => el.style.getPropertyValue('--darkreader-inline-bgcolor')")
    assert 'linear-gradient' in dr_bgimage
    assert dr_bgcolor == 'transparent'

    # Check child element transparent backgrounds
    product_name = page.locator('#card-cheapest .product-name')
    child_bg = product_name.evaluate("el => window.getComputedStyle(el).backgroundColor")
    assert child_bg in ('rgba(0, 0, 0, 0)', 'transparent')


def test_price_alarm_settings_configurable_delays(page: Page):
    # Open settings dialog
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    # Default delay values should be 300 and 800
    submit_delay_input = page.locator('#tp-root >> #tp-alarm-submit-delay-val')
    close_delay_input = page.locator('#tp-root >> #tp-alarm-close-delay-val')
    assert submit_delay_input.input_value() == '300'
    assert close_delay_input.input_value() == '800'

    # Update delay values
    submit_delay_input.fill('500')
    close_delay_input.fill('1200')
    page.click('#tp-root >> #tp-btn-save')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='hidden')

    # Re-open dialog and verify updated delay values persisted
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')
    assert page.locator('#tp-root >> #tp-alarm-submit-delay-val').input_value() == '500'
    assert page.locator('#tp-root >> #tp-alarm-close-delay-val').input_value() == '1200'

    # Toggle off auto-submit and verify delays group hides
    page.click('#tp-root >> #tp-alarm-autosubmit-toggle + .tp-slider')
    assert not page.locator('#tp-root >> #tp-alarm-delays-group').is_visible()
    page.click('#tp-root >> #tp-btn-close')


def test_real_deal_on_demand_check_and_badges(page: Page):
    # Setup mock network route for price chart HTML
    def handle_pricechart(route):
        url = route.request.url
        if 'p_pc_pid=797571' in url:
            # Card 1 (1800.00 CHF) -> Tiefstpreis is 1800.00 CHF (All-time low)
            route.fulfill(
                status=200,
                headers={'access-control-allow-origin': '*'},
                content_type='text/html',
                body='''
                <div class="PriceChartLegend">
                  <div class="col-4"><div class="title">aktueller Toppreis</div><div class="Plugin_Price">1800.00</div></div>
                  <div class="col-4"><div class="title">Tiefstpreis</div><div class="Plugin_Price">1800.00</div></div>
                  <div class="col-4"><div class="title">Höchstpreis</div><div class="Plugin_Price">2400.00</div></div>
                </div>
                '''
            )
        elif 'p_pc_pid=797573' in url:
            # Card 3 (15.00 CHF) -> Tiefstpreis was 10.00 CHF (Non-bestpreis)
            route.fulfill(
                status=200,
                headers={'access-control-allow-origin': '*'},
                content_type='text/html',
                body='''
                <div class="PriceChartLegend">
                  <div class="col-4"><div class="title">aktueller Toppreis</div><div class="Plugin_Price">15.00</div></div>
                  <div class="col-4"><div class="title">Tiefstpreis</div><div class="Plugin_Price">10.00</div></div>
                  <div class="col-4"><div class="title">Höchstpreis</div><div class="Plugin_Price">25.00</div></div>
                </div>
                '''
            )
        else:
            route.fulfill(status=404, headers={'access-control-allow-origin': '*'}, body='Not Found')

    page.route('**/plugins/product/pricechart*', handle_pricechart)

    # 1. On Card 1 (RTX 4090, 1800.00 CHF): click on-demand Differenz badge
    page.wait_for_selector('#card-cheapest .badge-dif.tp-deal-badge-interactive')
    page.click('#card-cheapest .badge-dif')

    # Verify badge transforms into Allzeit-Tiefstpreis with halo and clean percentage
    page.wait_for_selector('#card-cheapest .badge-dif.tp-deal-alltime-low')
    badge1 = page.locator('#card-cheapest .badge-dif.tp-deal-alltime-low')
    assert '-67%' in (badge1.text_content() or '')
    assert 'Allzeit-Tiefstpreis' in (badge1.get_attribute('title') or '')
    assert not page.locator('#card-cheapest .tp-card-historical-price').is_visible()

    # 2. On Card 3 (Silikon Case, 15.00 CHF): click on-demand Differenz badge
    page.wait_for_selector('#card-negative .badge-dif.tp-deal-badge-interactive')
    page.click('#card-negative .badge-dif')

    # Verify badge transforms into amber Non-Bestpreis warning with markup % and struck-through fake discount
    page.wait_for_selector('#card-negative .badge-dif.tp-deal-not-low')
    badge3 = page.locator('#card-negative .badge-dif.tp-deal-not-low')
    assert '+50%' in (badge3.text_content() or '')
    assert '-35%' in (badge3.text_content() or '')

    # Verify separated Tiefstpreis subtitle below current price
    page.wait_for_selector('#card-negative .tp-card-historical-price')
    hist_price3 = page.locator('#card-negative .tp-card-historical-price')
    assert 'Tiefstpreis: CHF 10.00' in (hist_price3.text_content() or '')


def test_real_deal_filter_non_bestpreis_toggle(page: Page):
    # Mock routes
    def handle_pricechart(route):
        url = route.request.url
        if 'p_pc_pid=797571' in url:
            route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, content_type='text/html', body='<div class="PriceChartLegend"><div class="title">Tiefstpreis</div><div class="Plugin_Price">1800.00</div></div>')
        elif 'p_pc_pid=797573' in url:
            route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, content_type='text/html', body='<div class="PriceChartLegend"><div class="title">Tiefstpreis</div><div class="Plugin_Price">10.00</div></div>')
        else:
            route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, content_type='text/html', body='<div class="PriceChartLegend"><div class="title">Tiefstpreis</div><div class="Plugin_Price">999.00</div></div>')

    page.route('**/plugins/product/pricechart*', handle_pricechart)

    # Check both cards
    page.wait_for_selector('#card-cheapest .badge-dif')
    page.click('#card-cheapest .badge-dif')
    page.wait_for_selector('#card-cheapest .badge-dif.tp-deal-alltime-low')

    page.wait_for_selector('#card-negative .badge-dif')
    page.click('#card-negative .badge-dif')
    page.wait_for_selector('#card-negative .badge-dif.tp-deal-not-low')

    # Now click filter bar toggle "🌟 Nur Tiefstpreise"
    real_deal_toggle = page.locator('#tp-bar-real-deal-btn')
    assert real_deal_toggle.is_visible()
    real_deal_toggle.click()

    # Card 3 (non-bestpreis) should be hidden with .tp-non-bestpreis-filtered
    page.wait_for_selector('#card-negative.tp-non-bestpreis-filtered', state='attached')
    assert 'tp-non-bestpreis-filtered' in (page.locator('#card-negative').get_attribute('class') or '')
    assert not page.locator('#card-negative').is_visible()

    # Card 1 (all-time low) should still be visible
    assert page.locator('#card-cheapest').is_visible()

    # Click reveal button (👁️) and verify card-negative is shown with outline
    page.click('#tp-bar-reveal-btn')
    assert page.locator('#card-negative').is_visible()


def test_real_deal_settings_modal_controls(page: Page):
    # Open settings dialog
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    # Verify Section 6 controls exist
    real_deal_toggle = page.locator('#tp-root >> #tp-real-deal-filter-toggle')
    min_discount_input = page.locator('#tp-root >> #tp-real-deal-min-val')
    assert not real_deal_toggle.is_checked()
    assert min_discount_input.input_value() == '30'

    # Toggle filter on and set threshold to 40
    page.click('#tp-root >> #tp-real-deal-filter-toggle + .tp-slider')
    min_discount_input.fill('40')
    page.click('#tp-root >> #tp-btn-save')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='hidden')

    # Re-open dialog and verify settings persisted
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')
    assert page.locator('#tp-root >> #tp-real-deal-filter-toggle').is_checked()
    assert page.locator('#tp-root >> #tp-real-deal-min-val').input_value() == '40'
    page.click('#tp-root >> #tp-btn-close')


def test_real_deal_rich_tooltips_with_peak_context(page: Page):
    def handle_pricechart(route):
        url = route.request.url
        if 'p_pc_pid=797571' in url:
            # Card 1 (1800.00 CHF, Tiefstpreis 1800.00 CHF, Höchstpreis 2400.00 CHF -> -25% drop)
            route.fulfill(
                status=200,
                headers={'access-control-allow-origin': '*'},
                content_type='text/html',
                body='''
                <div class="PriceChartLegend">
                  <div class="col-4"><div class="title">aktueller Toppreis</div><div class="Plugin_Price">1800.00</div></div>
                  <div class="col-4"><div class="title">Tiefstpreis</div><div class="Plugin_Price">1800.00</div></div>
                  <div class="col-4"><div class="title">Höchstpreis</div><div class="Plugin_Price">2400.00</div></div>
                </div>
                '''
            )
        elif 'p_pc_pid=797573' in url:
            # Card 3 (15.00 CHF, Tiefstpreis 10.00 CHF, Höchstpreis 25.00 CHF)
            route.fulfill(
                status=200,
                headers={'access-control-allow-origin': '*'},
                content_type='text/html',
                body='''
                <div class="PriceChartLegend">
                  <div class="col-4"><div class="title">aktueller Toppreis</div><div class="Plugin_Price">15.00</div></div>
                  <div class="col-4"><div class="title">Tiefstpreis</div><div class="Plugin_Price">10.00</div></div>
                  <div class="col-4"><div class="title">Höchstpreis</div><div class="Plugin_Price">25.00</div></div>
                </div>
                '''
            )
        else:
            route.fulfill(status=404, headers={'access-control-allow-origin': '*'}, body='Not Found')

    page.route('**/plugins/product/pricechart*', handle_pricechart)

    # Check Card 1
    page.wait_for_selector('#card-cheapest .badge-dif')
    page.click('#card-cheapest .badge-dif')
    page.wait_for_selector('#card-cheapest .badge-dif.tp-deal-alltime-low')

    badge1 = page.locator('#card-cheapest .badge-dif.tp-deal-alltime-low')
    title1 = badge1.get_attribute('title') or ''
    assert 'Allzeit-Tiefstpreis' in title1
    assert '-25% vom Höchstpreis CHF 2400.00' in title1

    # Check Card 3
    page.wait_for_selector('#card-negative .badge-dif')
    page.click('#card-negative .badge-dif')
    page.wait_for_selector('#card-negative .badge-dif.tp-deal-not-low')

    badge3 = page.locator('#card-negative .badge-dif.tp-deal-not-low')
    title3 = badge3.get_attribute('title') or ''
    assert 'Historischer Tiefstpreis lag bei CHF 10.00 (+50% Aufschlag)' in title3
    assert 'Höchstpreis: CHF 25.00' in title3


def test_real_deal_dom_memoization_and_cache_pruning(page: Page):
    # Test cache pruning in localStorage
    page.evaluate('''() => {
        const now = Date.now();
        const staleTime = now - (15 * 24 * 3600 * 1000); // 15 days ago (expired)
        const freshTime = now - (1 * 3600 * 1000);       // 1 hour ago (fresh)
        localStorage.setItem('tp_hist_v1_stale999', JSON.stringify({ tiefstpreis: 50, hoechstpreis: 100, time: staleTime }));
        localStorage.setItem('tp_hist_v1_fresh999', JSON.stringify({ tiefstpreis: 80, hoechstpreis: 120, time: freshTime }));
    }''')

    # Trigger setCachedPriceStats by mocking a route and clicking check badge
    page.route('**/plugins/product/pricechart*', lambda route: route.fulfill(
        status=200,
        headers={'access-control-allow-origin': '*'},
        content_type='text/html',
        body='<div class="PriceChartLegend"><div class="title">Tiefstpreis</div><div class="Plugin_Price">1800.00</div></div>'
    ))

    page.wait_for_selector('#card-cheapest .badge-dif')
    page.click('#card-cheapest .badge-dif')
    page.wait_for_selector('#card-cheapest .badge-dif.tp-deal-alltime-low')

    # Stale item should be pruned, fresh item preserved
    stale_exists = page.evaluate("() => localStorage.getItem('tp_hist_v1_stale999') !== null")
    fresh_exists = page.evaluate("() => localStorage.getItem('tp_hist_v1_fresh999') !== null")
    assert not stale_exists
    assert fresh_exists


def test_real_deal_removes_heatmap_on_non_bestpreis(page: Page):
    # Both card 1 (all-time low) and card 3 (non-bestpreis) initially have heatmap
    card1 = page.locator('#card-cheapest')
    card3 = page.locator('#card-negative')
    assert 'tp-heatmap-active' in (card1.get_attribute('class') or '')
    assert 'tp-heatmap-active' in (card3.get_attribute('class') or '')

    # Mock routes
    def handle_pricechart(route):
        url = route.request.url
        if 'p_pc_pid=797571' in url:
            route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, content_type='text/html', body='<div class="PriceChartLegend"><div class="title">Tiefstpreis</div><div class="Plugin_Price">1800.00</div></div>')
        elif 'p_pc_pid=797573' in url:
            route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, content_type='text/html', body='<div class="PriceChartLegend"><div class="title">Tiefstpreis</div><div class="Plugin_Price">10.00</div></div>')
        else:
            route.fulfill(status=404, headers={'access-control-allow-origin': '*'}, body='Not Found')

    page.route('**/plugins/product/pricechart*', handle_pricechart)

    # Check card 1 (all-time low) -> heatmap stays active
    page.click('#card-cheapest .badge-dif')
    page.wait_for_selector('#card-cheapest .badge-dif.tp-deal-alltime-low')
    assert 'tp-heatmap-active' in (card1.get_attribute('class') or '')

    # Check card 3 (non-bestpreis, 15 CHF vs 10 CHF low) -> heatmap is removed
    page.click('#card-negative .badge-dif')
    page.wait_for_selector('#card-negative .badge-dif.tp-deal-not-low')
    assert 'tp-heatmap-active' not in (card3.get_attribute('class') or '')


def test_real_deal_batch_check_button_counter_and_run(page: Page):
    batch_btn = page.locator('#tp-bar-batch-check-btn')
    assert batch_btn.is_visible()

    # In mock_toppreise.html, 3 cards have >= 30% discount (-67%, -35%, -50%)
    assert 'Check Deals (3)' in (batch_btn.text_content() or '')

    # Mock routes
    def handle_pricechart(route):
        route.fulfill(
            status=200,
            headers={'access-control-allow-origin': '*'},
            content_type='text/html',
            body='<div class="PriceChartLegend"><div class="title">Tiefstpreis</div><div class="Plugin_Price">500.00</div></div>'
        )

    page.route('**/plugins/product/pricechart*', handle_pricechart)

    # 1. Checking one card individually reduces the batch count from (3) to (2)
    page.click('#card-cheapest .badge-dif')
    page.wait_for_selector('#card-cheapest .badge-dif.tp-deal-not-low')
    assert 'Check Deals (2)' in (batch_btn.text_content() or '')

    # 2. Clicking batch button runs the batch check for remaining cards
    batch_btn.click()
    page.wait_for_selector('#card-negative .badge-dif.tp-deal-alltime-low')
    page.wait_for_selector('#card-cat-excluded .badge-dif.tp-deal-not-low')

    # Wait for batch run to complete (tp-batch-active removed)
    page.wait_for_function("() => !document.querySelector('#tp-bar-batch-check-btn').classList.contains('tp-batch-active')")

    # Once finished, remaining unchecked deals should be 0 or show completion status
    btn_text = batch_btn.text_content() or ''
    assert 'Check Deals (0)' in btn_text or 'geprüft' in btn_text


def test_empty_state_notice_and_actions(page: Page):
    # Initially all 5 cards in mock_toppreise are visible, no empty notice
    assert not page.locator('#tp-empty-state-notice').is_visible()

    # Filter all 5 cards by setting negative terms
    page.fill('#tp-inline-negative-input', 'GeForce, Silikon, iPhone, Dell')
    page.wait_for_selector('#tp-empty-state-notice')

    notice = page.locator('#tp-empty-state-notice')
    assert notice.is_visible()
    assert 'Alle 5 Angebote' in (notice.text_content() or '')

    # Clicking "👁️ Ausgeblendete anzeigen" reveals previews
    page.click('#tp-empty-reveal-btn')
    assert 'tp-reveal-filtered' in (page.locator('body').get_attribute('class') or '')
    assert not page.locator('#tp-empty-state-notice').is_visible()

    # Toggle reveal off again -> notice comes back
    page.click('#tp-bar-reveal-btn')
    page.wait_for_selector('#tp-empty-state-notice')

    # Clicking "🔄 Filter zurücksetzen" clears filters and restores cards
    page.click('#tp-empty-reset-btn')
    assert not page.locator('#tp-empty-state-notice').is_visible()
    assert page.locator('#card-cheapest').is_visible()


def test_real_deal_threshold_quick_selector(page: Page):
    thresh_btn = page.locator('#tp-bar-threshold-btn')
    popover = page.locator('#tp-threshold-popover')
    batch_btn = page.locator('#tp-bar-batch-check-btn')

    assert thresh_btn.is_visible()
    assert '≥30%' in (thresh_btn.text_content() or '')
    # Initially at 30%, 3 cards qualify (-67%, -35%, -50%)
    assert 'Check Deals (3)' in (batch_btn.text_content() or '')

    # Open popover
    thresh_btn.click()
    assert 'tp-show' in (popover.get_attribute('class') or '')

    # Select >= 50%
    page.click('#tp-threshold-popover button[data-val="50"]')
    assert 'tp-show' not in (popover.get_attribute('class') or '')
    assert '≥50%' in (thresh_btn.text_content() or '')

    # At 50%, only 2 cards qualify (-67%, -50%) -> count updates live to (2)
    assert 'Check Deals (2)' in (batch_btn.text_content() or '')


def test_product_detail_page_deal_badge(page: Page):
    # Mock route for product detail chart
    page.route('**/plugins/product/pricechart*840582*', lambda route: route.fulfill(
        status=200,
        headers={'access-control-allow-origin': '*'},
        content_type='text/html',
        body='''
        <div class="PriceChartLegend">
          <div class="col-4"><div class="title">Tiefstpreis</div><div class="Plugin_Price">350.90</div></div>
          <div class="col-4"><div class="title">Höchstpreis</div><div class="Plugin_Price">700.00</div></div>
        </div>
        '''
    ))

    # Setup detail page DOM structure
    page.evaluate('''() => {
        document.body.innerHTML = `
          <div class="Plugin_ProductHeading">
            <h1>SHARP 55HR7265E <a href="/plugins/product/pricechart?p_pc_pid=840582">Preischart</a></h1>
          </div>
          <div class="productPrice"><div class="Plugin_Price">350.90</div></div>
        `;
        window.ToppreiseSuite?.processProductDetailPage?.();
    }''')

    page.wait_for_selector('#tp-detail-deal-badge.tp-is-alltime-low')
    badge = page.locator('#tp-detail-deal-badge')
    assert 'Allzeit-Tiefstpreis' in (badge.text_content() or '')
    title = badge.get_attribute('title') or ''
    assert 'Allzeit-Tiefstpreis' in title
    assert 'CHF 700.00' in title


def test_real_world_toppreise_pricechart_html_parsing(page: Page):
    # Real HTML layout directly from Toppreise.ch pricechart endpoint
    real_toppreise_html = '''
    <div id="Plugin_PriceChart_121918" data-product-id="845299" class="Plugin_PriceChart Plugin_PriceChart_Fullview">
      <div class="PriceChartLegend d-block col-12 text-center">
        <div class="row align-items-center">
          <div class="col-4 col-md-3">
            <div class="row p-2">
              <div class="title col-12">aktueller Toppreis</div>
              <div class="col-12 pt-2">
                <div class="row">
                  <span class="chartProductPrice col-12 col-lg p-0">
                    <div id="Plugin_PriceInformation_216829" class="Plugin_PriceInformation">
                      <div class="priceContainer unrelatedprice">
                        <div class="Plugin_Price "> 79.45 </div>
                      </div>
                    </div>
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div class="col-4 col-md-3">
            <div class="row p-2">
              <div class="title col-12">Tiefstpreis</div>
              <div class="col-12 pt-2">
                <div class="row">
                  <div class="chartProductPrice col-12 col-lg p-0">
                    <div id="Plugin_PriceInformation_216829" class="Plugin_PriceInformation">
                      <div class="priceContainer unrelatedprice">
                        <div class="Plugin_Price "> 79.45 </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="col-4 col-md-3">
            <div class="row p-2">
              <div class="title col-12">Höchstpreis</div>
              <div class="col-12 pt-2">
                <div class="row">
                  <div class="chartProductPrice col-12 col-lg p-0">
                    <div id="Plugin_PriceInformation_216829" class="Plugin_PriceInformation">
                      <div class="priceContainer unrelatedprice">
                        <div class="Plugin_Price "> 172.00 </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    '''
    page.route('**/plugins/product/pricechart*', lambda route: route.fulfill(
        status=200,
        headers={'access-control-allow-origin': '*'},
        content_type='text/html',
        body=real_toppreise_html
    ))

    # Click Differenz badge on card-cheapest (price 1800 CHF vs Tiefstpreis 79.45 CHF -> +2166% markup)
    page.click('#card-cheapest .badge-dif')

    # Expect badge to be created with markup badge, NOT 'Nicht verfügbar'
    page.wait_for_selector('#card-cheapest .badge-dif.tp-deal-not-low', timeout=3000)
    badge = page.locator('#card-cheapest .badge-dif.tp-deal-not-low')
    assert '+2166%' in (badge.text_content() or '')

    # Now verify all-time low case when Tiefstpreis matches card price (1800 CHF)
    real_alltime_low_html = real_toppreise_html.replace('79.45', '1800.00')
    page.route('**/plugins/product/pricechart*456*', lambda route: route.fulfill(
        status=200,
        headers={'access-control-allow-origin': '*'},
        content_type='text/html',
        body=real_alltime_low_html
    ))
    # card-negative has product id 456, price 15 CHF -> let's make mock match 15.00
    real_negative_html = real_toppreise_html.replace('79.45', '15.00')
    page.route('**/plugins/product/pricechart*456*', lambda route: route.fulfill(
        status=200,
        headers={'access-control-allow-origin': '*'},
        content_type='text/html',
        body=real_negative_html
    ))
    page.click('#card-negative .badge-dif')
    page.wait_for_selector('#card-negative .badge-dif.tp-deal-alltime-low', timeout=3000)
    neg_badge = page.locator('#card-negative .badge-dif.tp-deal-alltime-low')
    assert '-35%' in (neg_badge.text_content() or '')


def test_filter_bar_hidden_on_product_detail_page(page: Page):
    # Simulate product detail page
    page.evaluate('''() => {
        document.body.className = 'color_bg Page_Product';
        document.body.setAttribute('data-current_url', '/preisvergleich/TV-Geraete/SHARP-55HR7265E-p840582');
        window.ToppreiseSuite?.processListings?.();
    }''')
    page.wait_for_timeout(200)

    # Filter bar must be completely absent on product detail page
    filter_bar = page.locator('#tp-suite-filter-bar')
    assert filter_bar.count() == 0

    # Settings FAB is still available
    fab = page.locator('#tp-root >> #tp-settings-fab')
    assert fab.is_visible()


def test_deal_only_buttons_hidden_on_category_page(page: Page):
    # Simulate standard category/search listing page
    page.evaluate('''() => {
        document.body.className = 'color_bg Page_Browsing';
        document.body.setAttribute('data-current_url', '/produktsuche/TV-Video/TV-Geraete-Zubehoer/TV-Geraete-c986');
        window.ToppreiseSuite?.processListings?.();
    }''')
    page.wait_for_timeout(200)

    # Filter bar itself is visible on category listings
    filter_bar = page.locator('#tp-suite-filter-bar')
    assert filter_bar.is_visible()

    # Listing features are visible
    assert page.locator('#tp-inline-negative-input').is_visible()
    assert page.locator('#tp-bar-reveal-btn').is_visible()
    assert page.locator('#tp-bar-reset-btn').is_visible()

    # Deal-feed-only features are hidden
    assert not page.locator('#tp-bar-heat-btn').is_visible()
    assert not page.locator('#tp-bar-real-deal-btn').is_visible()
    assert not page.locator('#tp-bar-threshold-wrapper').is_visible()


def test_check_deal_button_not_injected_on_category_page(page: Page):
    # Simulate category page where cards have no difference badge
    page.evaluate('''() => {
        document.body.className = 'color_bg Page_Browsing';
        document.body.setAttribute('data-current_url', '/produktsuche/TV-Video/TV-Geraete-Zubehoer/TV-Geraete-c986');
        // Remove badge-dif elements from cards to simulate real category catalog
        document.querySelectorAll('.badge-dif').forEach(b => b.remove());
        window.ToppreiseSuite?.processListings?.();
    }''')
    page.wait_for_timeout(200)

    # Verify no interactive deal badges exist on standard catalog listings
    assert page.locator('.badge-dif.tp-deal-badge-interactive').count() == 0


def test_slash_key_focuses_negative_filter(page: Page):
    filter_bar = page.locator('#tp-suite-filter-bar')
    assert filter_bar.is_visible()

    # Make sure focus is on body
    page.evaluate("() => document.body.focus()")
    page.keyboard.press('/')

    is_focused = page.evaluate("() => document.activeElement?.id === 'tp-inline-negative-input'")
    assert is_focused


def test_escape_blurs_negative_filter(page: Page):
    input_el = page.locator('#tp-inline-negative-input')
    input_el.focus()
    assert page.evaluate("() => document.activeElement?.id === 'tp-inline-negative-input'")

    page.keyboard.press('Escape')
    assert not page.evaluate("() => document.activeElement?.id === 'tp-inline-negative-input'")


def test_slash_key_noop_when_typing_in_input(page: Page):
    page.evaluate("""() => {
        const inp = document.createElement('input');
        inp.id = 'native-test-input';
        document.body.appendChild(inp);
        inp.focus();
    }""")
    assert page.evaluate("() => document.activeElement?.id === 'native-test-input'")

    page.keyboard.press('/')
    assert page.evaluate("() => document.activeElement?.id === 'native-test-input'")


def test_sparkline_renders_with_cached_timeseries(page: Page):
    # Enable sparklines for testing
    page.evaluate("""() => {
        window.ToppreiseSuite.CONFIG.ENABLE_SPARKLINES = true;
    }""")
    # Inject cached price stats with timeSeries into localStorage
    page.evaluate("""() => {
        const stats = {
            tiefstpreis: 1800.0,
            hoechstpreis: 2200.0,
            aktuellerToppreis: 1800.0,
            timeSeries: [[1672531199, 2200.0], [1675209599, 2000.0], [1677628799, 1800.0]],
            time: Date.now()
        };
        localStorage.setItem('tp_hist_v1_797571', JSON.stringify(stats));
        window.ToppreiseSuite?.processListings?.();
    }""")

    # Verify sparkline SVG is rendered on card-cheapest
    sparkline = page.locator('#card-cheapest .tp-sparkline')
    assert sparkline.is_visible()

    polyline = page.locator('#card-cheapest .tp-sparkline polyline')
    assert polyline.count() == 1
    # Down-trending price => stroke is green (#10b981)
    stroke = polyline.get_attribute('stroke')
    assert stroke == '#10b981'


def test_sparkline_not_rendered_without_timeseries(page: Page):
    page.evaluate("""() => {
        localStorage.removeItem('tp_hist_v1_797572');
        window.ToppreiseSuite?.processListings?.();
    }""")
    assert page.locator('#card-expensive .tp-sparkline').count() == 0


def test_sparkline_trending_up_renders_red(page: Page):
    page.evaluate("""() => {
        window.ToppreiseSuite.CONFIG.ENABLE_SPARKLINES = true;
        const stats = {
            tiefstpreis: 900.0,
            hoechstpreis: 1200.0,
            aktuellerToppreis: 1100.0,
            timeSeries: [[1672531199, 900.0], [1675209599, 1000.0], [1677628799, 1100.0]],
            time: Date.now()
        };
        localStorage.setItem('tp_hist_v1_797572', JSON.stringify(stats));
        window.ToppreiseSuite?.processListings?.();
    }""")

    sparkline = page.locator('#card-expensive .tp-sparkline')
    assert sparkline.is_visible()

    polyline = page.locator('#card-expensive .tp-sparkline polyline')
    stroke = polyline.get_attribute('stroke')
    # Up-trending price => stroke is red (#ef4444)
    assert stroke == '#ef4444'


def test_config_export_produces_valid_json(page: Page):
    # Open settings dialog
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    # Setup export interception
    exported_data = page.evaluate("""() => {
        return new Promise(resolve => {
            const originalCreateObjectURL = URL.createObjectURL;
            URL.createObjectURL = blob => {
                const reader = new FileReader();
                reader.onload = () => {
                    const captured = JSON.parse(reader.result);
                    URL.createObjectURL = originalCreateObjectURL;
                    resolve(captured);
                };
                reader.readAsText(blob);
                return 'blob:mock-url';
            };
            const shadow = document.getElementById('tp-root').shadowRoot;
            shadow.getElementById('tp-export-config-btn').click();
        });
    }""")

    assert exported_data is not None
    assert '_meta' in exported_data
    assert 'config' in exported_data
    assert 'MODE' in exported_data['config']
    assert 'MARGIN_PERCENT' in exported_data['config']
    assert 'NEGATIVE_TERMS' in exported_data['config']


def test_config_import_applies_settings(page: Page):
    # Open settings dialog
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    # Trigger file import via DataTransfer / File
    page.evaluate("""() => {
        const shadow = document.getElementById('tp-root').shadowRoot;
        const fileInput = shadow.getElementById('tp-import-config-file');
        const testPayload = {
            _meta: { version: '2.13.0' },
            config: {
                MARGIN_PERCENT: 7.5,
                NEGATIVE_TERMS: 'ImportedNegativeTerm',
                REAL_DEAL_MIN_DISCOUNT: 45,
                MODE: 'hide'
            }
        };
        const blob = new Blob([JSON.stringify(testPayload)], { type: 'application/json' });
        const file = new File([blob], 'config.json', { type: 'application/json' });
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    }""")

    # Give FileReader a tick
    page.wait_for_timeout(200)

    # Check updated CONFIG and UI fields
    config_state = page.evaluate("""() => ({
        margin: window.ToppreiseSuite?.CONFIG?.MARGIN_PERCENT,
        neg: window.ToppreiseSuite?.CONFIG?.NEGATIVE_TERMS,
        minDiscount: window.ToppreiseSuite?.CONFIG?.REAL_DEAL_MIN_DISCOUNT,
        mode: window.ToppreiseSuite?.CONFIG?.MODE,
        inlineNegInput: document.getElementById('tp-inline-negative-input')?.value
    })""")

    assert config_state['margin'] == 7.5
    assert config_state['neg'] == 'ImportedNegativeTerm'
    assert config_state['minDiscount'] == 45
    assert config_state['mode'] == 'hide'
    assert config_state['inlineNegInput'] == 'ImportedNegativeTerm'


def test_config_import_invalid_json_shows_error_toast(page: Page):
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    page.evaluate("""() => {
        const shadow = document.getElementById('tp-root').shadowRoot;
        const fileInput = shadow.getElementById('tp-import-config-file');
        const blob = new Blob(['{ this is not valid json...'], { type: 'application/json' });
        const file = new File([blob], 'corrupt.json', { type: 'application/json' });
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    }""")

    page.wait_for_timeout(200)
    toast = page.locator('#tp-root >> .tp-toast')
    assert toast.is_visible()
    assert 'Import fehlgeschlagen' in (toast.text_content() or '')


def test_config_import_ignores_unknown_and_debug_keys(page: Page):
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    page.evaluate("""() => {
        const shadow = document.getElementById('tp-root').shadowRoot;
        const fileInput = shadow.getElementById('tp-import-config-file');
        const payload = {
            config: {
                UNRECOGNIZED_SECURITY_KEY: 'exploit',
                DEBUG: false,
                MARGIN_PERCENT: 4.2
            }
        };
        const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
        const file = new File([blob], 'safe_config.json', { type: 'application/json' });
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    }""")

    page.wait_for_timeout(200)
    res = page.evaluate("""() => ({
        margin: window.ToppreiseSuite?.CONFIG?.MARGIN_PERCENT,
        unknown: window.ToppreiseSuite?.CONFIG?.UNRECOGNIZED_SECURITY_KEY,
        debug: window.ToppreiseSuite?.CONFIG?.DEBUG
    })""")

    assert res['margin'] == 4.2
    assert res['unknown'] is None
    # DEBUG is preserved and not overwritten
    assert res['debug'] is True


def test_filter_bar_stepper_buttons(page: Page):
    # Reset min offers
    page.evaluate("""() => {
        window.ToppreiseSuite.CONFIG.MIN_OFFERS = 0;
        window.ToppreiseSuite.processListings();
    }""")

    val_span = page.locator('#tp-bar-min-val')
    plus_btn = page.locator('#tp-bar-min-plus')
    minus_btn = page.locator('#tp-bar-min-minus')

    assert val_span.text_content() == '0'

    plus_btn.click()
    assert val_span.text_content() == '1'
    assert page.evaluate("() => window.ToppreiseSuite?.CONFIG?.MIN_OFFERS") == 1

    plus_btn.click()
    assert val_span.text_content() == '2'
    assert page.evaluate("() => window.ToppreiseSuite?.CONFIG?.MIN_OFFERS") == 2

    minus_btn.click()
    assert val_span.text_content() == '1'
    assert page.evaluate("() => window.ToppreiseSuite?.CONFIG?.MIN_OFFERS") == 1


def test_inline_negative_input_clear_button(page: Page):
    inp = page.locator('#tp-inline-negative-input')
    clear_btn = page.locator('#tp-clear-neg-btn')

    inp.fill('QuickClearTest')
    inp.dispatch_event('input')
    assert clear_btn.is_visible()
    assert page.evaluate("() => window.ToppreiseSuite?.CONFIG?.NEGATIVE_TERMS") == 'QuickClearTest'

    clear_btn.click()
    assert inp.input_value() == ''
    assert not clear_btn.is_visible()
    assert page.evaluate("() => window.ToppreiseSuite?.CONFIG?.NEGATIVE_TERMS") == ''


def test_negative_terms_multi_delimiter_support(page: Page):
    # Test combination of newline, semicolon, and comma delimiters
    page.evaluate("""() => {
        window.ToppreiseSuite.CONFIG.NEGATIVE_TERMS = "GeForce;\\n4080, NonExistentTerm";
        window.ToppreiseSuite.processListings();
    }""")

    # Both card 1 (contains GeForce) and card 2 (contains 4080) should be filtered
    page.wait_for_selector('#card-cheapest.tp-negative-filtered', state='attached')
    page.wait_for_selector('#card-expensive.tp-negative-filtered', state='attached')

    assert 'tp-negative-filtered' in (page.locator('#card-cheapest').get_attribute('class') or '')
    assert 'tp-negative-filtered' in (page.locator('#card-expensive').get_attribute('class') or '')


def test_sparkline_handles_edge_cases(page: Page):
    # Enable sparklines for testing
    page.evaluate("""() => {
        window.ToppreiseSuite.CONFIG.ENABLE_SPARKLINES = true;
    }""")

    # 1 data point only -> not enough for a trend line, no sparkline rendered
    page.evaluate("""() => {
        const stats = {
            tiefstpreis: 1800.0,
            hoechstpreis: 2200.0,
            timeSeries: [[1672531199, 1800.0]],
            time: Date.now()
        };
        localStorage.setItem('tp_hist_v1_797571', JSON.stringify(stats));
        window.ToppreiseSuite?.processListings?.();
    }""")
    assert page.locator('#card-cheapest .tp-sparkline').count() == 0

    # Flat price trend (equal start and end) -> renders green (price did not go up)
    page.evaluate("""() => {
        const stats = {
            tiefstpreis: 1800.0,
            hoechstpreis: 1800.0,
            timeSeries: [[1672531199, 1800.0], [1675209599, 1800.0]],
            time: Date.now()
        };
        localStorage.setItem('tp_hist_v1_797571', JSON.stringify(stats));
        window.ToppreiseSuite?.processListings?.();
    }""")
    sparkline = page.locator('#card-cheapest .tp-sparkline')
    assert sparkline.is_visible()
    polyline = page.locator('#card-cheapest .tp-sparkline polyline')
    assert polyline.get_attribute('stroke') == '#10b981'

    # Disabled by default -> sparklines not rendered even if data exists
    page.evaluate("""() => {
        window.ToppreiseSuite.CONFIG.ENABLE_SPARKLINES = false;
        window.ToppreiseSuite?.processListings?.();
    }""")
    assert page.locator('#card-cheapest .tp-sparkline').count() == 0


def test_negative_caching_and_manual_click_override(page: Page):
    # Set negative cache for card-cheapest (product 797571)
    page.evaluate("""() => {
        localStorage.setItem('tp_hist_v1_797571', JSON.stringify({ unavailable: true, time: Date.now() }));
    }""")

    # Batch check ignores negatively cached card
    cached = page.evaluate("() => window.ToppreiseSuite?.CONFIG ? localStorage.getItem('tp_hist_v1_797571') : null")
    assert 'unavailable' in (cached or '')

    # Manual click bypasses negative cache and fetches fresh stats
    page.route('**/plugins/product/pricechart*797571*', lambda route: route.fulfill(
        status=200,
        headers={'access-control-allow-origin': '*'},
        content_type='text/html',
        body='<div class="PriceChartLegend"><div class="title">Tiefstpreis</div><div class="Plugin_Price">1800.00</div></div>'
    ))

    page.click('#card-cheapest .badge-dif')
    page.wait_for_selector('#card-cheapest .badge-dif.tp-deal-alltime-low')
    badge = page.locator('#card-cheapest .badge-dif.tp-deal-alltime-low')
    assert '-67%' in (badge.text_content() or '')
    assert 'Allzeit-Tiefstpreis' in (badge.get_attribute('title') or '')


def test_sparklines_beta_settings_toggle(page: Page):
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    toggle = page.locator('#tp-root >> #tp-sparklines-toggle')
    assert not toggle.is_checked()

    # Toggle sparklines on via slider click
    page.click('#tp-root >> #tp-sparklines-toggle + .tp-slider')
    assert toggle.is_checked()

    # Save
    page.click('#tp-root >> #tp-btn-save')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='hidden')

    assert page.evaluate("() => window.ToppreiseSuite?.CONFIG?.ENABLE_SPARKLINES") is True


def test_real_deal_record_low_with_previous_low_subline(page: Page):
    # Enable sparklines
    page.evaluate("""() => {
        window.ToppreiseSuite.CONFIG.ENABLE_SPARKLINES = true;
    }""")

    # Product 797571 (current price 1800.00 CHF) had a previous low of 2200.00 CHF before dropping to 1800.00 CHF
    def handle_pricechart_post(route):
        if route.request.method == 'POST':
            # Return 2-series JSON with historical points: 2500 -> 2200 -> 1800 (current)
            series_data = [
                [[1672531199000, 2500.0], [1675209599000, 2200.0], [1677628799000, 1800.0]],
                [[1672531199000, 2500.0], [1675209599000, 2200.0], [1677628799000, 1800.0]]
            ]
            route.fulfill(
                status=200,
                headers={'access-control-allow-origin': '*'},
                content_type='application/json',
                body=json.dumps(series_data)
            )
        else:
            route.fallback()

    import json
    page.route('**/plugins/product/pricechart*', handle_pricechart_post)

    # Click Differenz badge on card-cheapest (1800.00 CHF)
    page.click('#card-cheapest .badge-dif')

    # Wait for all-time low badge
    page.wait_for_selector('#card-cheapest .badge-dif.tp-deal-alltime-low')
    badge = page.locator('#card-cheapest .badge-dif.tp-deal-alltime-low')
    title = badge.get_attribute('title') or ''
    assert 'Neuer Allzeit-Tiefstpreis' in title
    assert 'Bisheriger Rekord: CHF 2200.00 (-18%)' in title

    # Verify record-low subline is displayed
    page.wait_for_selector('#card-cheapest .tp-card-historical-price.tp-is-record-low')
    subline = page.locator('#card-cheapest .tp-card-historical-price.tp-is-record-low')
    assert 'Bisher: CHF 2200.00 (-18%)' in (subline.text_content() or '')

    # Verify sparkline is rendered immediately from POST response
    sparkline = page.locator('#card-cheapest .tp-sparkline')
    assert sparkline.is_visible()


def test_deal_score_computation_and_weights(page: Page):
    # Test 1: New Record Low (50/50 default weight)
    # dMedian = 40%, dRecord = 20% -> Score = 0.5*40 + 0.5*20 = 30%
    score_res = page.evaluate("""() => {
        const stats = {
            tiefstpreis: 1500,
            hoechstpreis: 2500,
            medianPrice: 2500,
            previousLow: 1875,
            isNewAllTimeLow: true,
            realDiscountVsPrevLow: 20,
            dataPointCount: 10
        };
        window.ToppreiseSuite.CONFIG.BESTPREISE_WEIGHT_RECORD = 0.50;
        return window.ToppreiseSuite.computeDealScore(stats, 1500);
    }""")
    assert score_res['score'] == 30
    assert score_res['dMedian'] == 40
    assert score_res['dRecord'] == 20
    assert score_res['isNewRecord'] is True

    # Test 2: Matching All-Time Low (dRecord = 0%)
    # dMedian = 30%, dRecord = 0% -> Score = 0.5*30 + 0 = 15%
    match_res = page.evaluate("""() => {
        const stats = {
            tiefstpreis: 1000,
            hoechstpreis: 1600,
            medianPrice: 1428,
            isNewAllTimeLow: false,
            dataPointCount: 8
        };
        window.ToppreiseSuite.CONFIG.BESTPREISE_WEIGHT_RECORD = 0.50;
        return window.ToppreiseSuite.computeDealScore(stats, 1000);
    }""")
    assert match_res['score'] == 15
    assert match_res['dMedian'] == 30
    assert match_res['dRecord'] == 0
    assert match_res['isNewRecord'] is False

    # Test 3: Weight Slider Effect (100% Record Weight vs 100% Median Weight)
    weight_res = page.evaluate("""() => {
        const stats = {
            tiefstpreis: 1000,
            hoechstpreis: 2000,
            medianPrice: 2000,
            previousLow: 1250,
            isNewAllTimeLow: true,
            dataPointCount: 10
        };
        // dMedian = 50%, dRecord = 20%
        window.ToppreiseSuite.CONFIG.BESTPREISE_WEIGHT_RECORD = 1.0;
        const pureRecord = window.ToppreiseSuite.computeDealScore(stats, 1000).score;

        window.ToppreiseSuite.CONFIG.BESTPREISE_WEIGHT_RECORD = 0.0;
        const pureMedian = window.ToppreiseSuite.computeDealScore(stats, 1000).score;

        return { pureRecord, pureMedian };
    }""")
    assert weight_res['pureRecord'] == 20
    assert weight_res['pureMedian'] == 50

    # Test 4: Exclusion: Non-bestpreis
    tier3_nonbest = page.evaluate("""() => {
        const stats = {
            tiefstpreis: 1000,
            hoechstpreis: 1600,
            medianPrice: 1400,
            isNewAllTimeLow: false,
            dataPointCount: 8
        };
        return window.ToppreiseSuite.computeDealScore(stats, 1200); // 1200 > 1000 * 1.01
    }""")
    assert tier3_nonbest is None

    # Test 5: Exclusion: Flat price (< 2% variance)
    tier3_flat = page.evaluate("""() => {
        const stats = {
            tiefstpreis: 1000,
            hoechstpreis: 1010,
            isNewAllTimeLow: false,
            dataPointCount: 12
        };
        return window.ToppreiseSuite.computeDealScore(stats, 1000);
    }""")
    assert tier3_flat is None

    # Test 6: Exclusion: 0% Real Deal Score (price matches low and median, zero savings)
    zero_score = page.evaluate("""() => {
        const stats = {
            tiefstpreis: 1000,
            hoechstpreis: 1500,
            medianPrice: 1000,
            isNewAllTimeLow: false,
            dataPointCount: 10
        };
        return window.ToppreiseSuite.computeDealScore(stats, 1000);
    }""")
    assert zero_score is None


def test_bestpreise_filter_bar_toggle_and_state(page: Page):
    # Verify button exists in filter bar
    btn = page.locator('#tp-suite-filter-bar #tp-bar-bestpreise-btn')
    assert btn.is_visible()
    assert '💎 Neue Bestpreise' in (btn.text_content() or '')

    # Toggle Bestpreise mode ON
    btn.click()

    # Verify bar accent class and active button state
    assert 'tp-bestpreise-bar' in (page.locator('#tp-suite-filter-bar').get_attribute('class') or '')
    assert 'tp-bestpreise-active' in (btn.get_attribute('class') or '')
    assert page.evaluate("() => window.ToppreiseSuite.CONFIG.BESTPREISE_MODE_ACTIVE") is True

    # Redundant controls: Real Deal filter toggle is disabled because Bestpreise mode already filters deals
    real_deal_btn = page.locator('#tp-bar-real-deal-btn')
    assert 'tp-disabled' in (real_deal_btn.get_attribute('class') or '')
    assert 'Inaktiv' in (real_deal_btn.get_attribute('title') or '')

    # On-demand Check Deals button remains enabled and clickable
    batch_btn = page.locator('#tp-bar-batch-check-btn')
    assert 'tp-disabled' not in (batch_btn.get_attribute('class') or '')

    # Toggle Bestpreise mode OFF
    btn.click()
    assert 'tp-bestpreise-bar' not in (page.locator('#tp-suite-filter-bar').get_attribute('class') or '')
    assert 'tp-bestpreise-active' not in (btn.get_attribute('class') or '')
    assert page.evaluate("() => window.ToppreiseSuite.CONFIG.BESTPREISE_MODE_ACTIVE") is False


def test_bestpreise_card_heatmap_and_badge(page: Page):
    # Card 1 (797571, price 1800): New record (median 2400 -> dMed 25%, prevLow 2200 -> dRec 18%) -> Score = 22%
    # Card 2 (797572, price 1100): Matching low (median 1500 -> dMed 27%, dRec 0%) -> Score = 14%
    # Card 3 (797573, price 15): Non-Bestpreis (tiefstpreis 10) -> Excluded
    page.evaluate("""() => {
        localStorage.setItem('tp_hist_v1_797571', JSON.stringify({
            tiefstpreis: 1800,
            hoechstpreis: 2600,
            medianPrice: 2400,
            previousLow: 2200,
            isNewAllTimeLow: true,
            realDiscountVsPrevLow: 18,
            dataPointCount: 10,
            time: Date.now()
        }));
        localStorage.setItem('tp_hist_v1_797572', JSON.stringify({
            tiefstpreis: 1100,
            hoechstpreis: 1800,
            medianPrice: 1500,
            isNewAllTimeLow: false,
            realDiscountVsMedian: 27,
            dataPointCount: 15,
            time: Date.now()
        }));
        localStorage.setItem('tp_hist_v1_797573', JSON.stringify({
            tiefstpreis: 10,
            hoechstpreis: 25,
            isNewAllTimeLow: false,
            dataPointCount: 10,
            time: Date.now()
        }));
        window.ToppreiseSuite.CONFIG.BESTPREISE_WEIGHT_RECORD = 0.50;
        window.ToppreiseSuite.CONFIG.BESTPREISE_MODE_ACTIVE = true;
        window.ToppreiseSuite.processListings();
    }""")

    # Card 1: New Record -> Gold halo, "Real Deal -22%", and subline
    card1_badge = page.locator('#card-cheapest .badge-dif')
    assert 'tp-deal-new-record' in (card1_badge.get_attribute('class') or '')
    assert 'Real Deal' in (card1_badge.text_content() or '')
    assert '-22%' in (card1_badge.text_content() or '')

    card1_subline = page.locator('#card-cheapest .tp-card-historical-price.tp-is-record-low')
    assert 'Bisher: CHF 2200.00 (-18%)' in (card1_subline.text_content() or '')

    # Card 2: Matching Low -> Emerald halo, "Real Deal -14%", and median subline
    card2_badge = page.locator('#card-expensive .badge-dif')
    assert 'tp-deal-alltime-low' in (card2_badge.get_attribute('class') or '')
    assert 'Real Deal' in (card2_badge.text_content() or '')
    assert '-14%' in (card2_badge.text_content() or '')

    card2_subline = page.locator('#card-expensive .tp-card-historical-price.tp-is-at-low')
    assert 'CHF 1500.00 (-27%)' in (card2_subline.text_content() or '')

    # Card 3: Scanned Non-Bestpreis -> Hidden in Bestpreise mode
    assert 'tp-bestpreise-hidden' in (page.locator('#card-negative').get_attribute('class') or '')

    # Unscanned card: Hidden by default in Bestpreise mode, not stuck in loading
    assert 'tp-bestpreise-hidden' in (page.locator('#card-low-offers').get_attribute('class') or '')
    uncached_badge = page.locator('#card-low-offers .badge-dif')
    assert 'tp-deal-loading' not in (uncached_badge.get_attribute('class') or '')

    # Toggle Bestpreise mode OFF -> Restores original badges and removes hidden classes
    page.evaluate("""() => {
        window.ToppreiseSuite.CONFIG.BESTPREISE_MODE_ACTIVE = false;
        window.ToppreiseSuite.processListings();
    }""")
    assert 'tp-bestpreise-hidden' not in (page.locator('#card-negative').get_attribute('class') or '')
    assert 'tp-deal-new-record' not in (page.locator('#card-cheapest .badge-dif').get_attribute('class') or '')
    assert '-67%' in (page.locator('#card-cheapest .badge-dif').text_content() or '')


def test_bestpreise_sorting_by_continuous_score(page: Page):
    # Setup 3 products with continuous Deal Scores:
    # Card 1 (797571): Score = 22%
    # Card 2 (797572): Score = 35% (huge median discount)
    # Card 3 (797573): Score = 28%
    # In Bestpreise mode, sort order must be: Card 2 (35%) -> Card 3 (28%) -> Card 1 (22%)
    page.evaluate("""() => {
        localStorage.setItem('tp_hist_v1_797571', JSON.stringify({
            tiefstpreis: 1800,
            hoechstpreis: 2600,
            medianPrice: 2400,
            previousLow: 2200,
            isNewAllTimeLow: true,
            realDiscountVsPrevLow: 18,
            dataPointCount: 10,
            time: Date.now()
        }));
        localStorage.setItem('tp_hist_v1_797572', JSON.stringify({
            tiefstpreis: 1100,
            hoechstpreis: 3500,
            medianPrice: 3437, // dMedian = 68% -> 0.5*68 + 0 = 34% or ~35%
            isNewAllTimeLow: false,
            dataPointCount: 15,
            time: Date.now()
        }));
        localStorage.setItem('tp_hist_v1_797573', JSON.stringify({
            tiefstpreis: 15,
            hoechstpreis: 40,
            medianPrice: 30,
            previousLow: 20,
            isNewAllTimeLow: true,
            realDiscountVsPrevLow: 25, // dMed 50%, dRec 25% -> Score = 38%
            dataPointCount: 12,
            time: Date.now()
        }));
        window.ToppreiseSuite.CONFIG.BESTPREISE_WEIGHT_RECORD = 0.50;
        window.ToppreiseSuite.CONFIG.BESTPREISE_MODE_ACTIVE = true;
        window.ToppreiseSuite.processListings();
    }""")

    card_ids = page.evaluate("""() => {
        const cards = Array.from(document.querySelectorAll('#product-list .Plugin_Product'));
        return cards.map(c => c.id);
    }""")
    # Scores: Card 3 (38%) -> Card 2 (34%) -> Card 1 (22%)
    assert card_ids[0] == 'card-negative'   # Score 38%
    assert card_ids[1] == 'card-expensive'  # Score 34%
    assert card_ids[2] == 'card-cheapest'   # Score 22%


def test_bestpreise_settings_weight_slider(page: Page):
    # Open settings modal in Shadow DOM
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    toggle = page.locator('#tp-root >> #tp-bestpreise-mode-toggle')
    assert not toggle.is_checked()

    # Toggle on -> Weight slider group should become visible
    page.click('#tp-root >> #tp-bestpreise-mode-toggle + .tp-slider')
    assert toggle.is_checked()

    weight_group = page.locator('#tp-root >> #tp-bestpreise-weight-group')
    assert weight_group.is_visible()

    # Set slider to 70% Record / 30% Median
    page.fill('#tp-root >> #tp-bestpreise-weight-val', '70')
    page.dispatch_event('#tp-root >> #tp-bestpreise-weight-val', 'input')

    desc = page.locator('#tp-root >> #tp-bestpreise-weight-desc')
    assert '30% Median / 70% Neuer Rekord' in (desc.text_content() or '')

    # Save
    page.click('#tp-root >> #tp-btn-save')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='hidden')

    assert page.evaluate("() => window.ToppreiseSuite.CONFIG.BESTPREISE_MODE_ACTIVE") is True
    assert page.evaluate("() => window.ToppreiseSuite.CONFIG.BESTPREISE_WEIGHT_RECORD") == 0.70


def test_outlier_spike_rejection(page: Page):
    # Product: Smartphone normal price ~CHF 1200
    # Vendor glitch: 1-day CHF 15 spike on Day 3
    # Genuine new all-time low drop: CHF 999 on Day 10
    analysis = page.evaluate("""() => {
        const now = Date.now();
        const dayMs = 86400 * 1000;
        const series = [
            [now - 10 * dayMs, 1300],
            [now - 9 * dayMs, 1250],
            [now - 7 * dayMs, 1200],
            [now - 6 * dayMs, 15],   // 1-day glitch anomaly
            [now - 5 * dayMs, 1200],
            [now - 4 * dayMs, 1180],
            [now - 3 * dayMs, 1150],
            [now - 2 * dayMs, 1100],
            [now - 1 * dayMs, 1050],
            [now, 999]              // Current authentic record low
        ];
        return window.ToppreiseSuite.analyzePriceTimeSeries(series, 999);
    }""")

    # Outlier CHF 15 should have been sanitized
    assert analysis is not None
    assert len(analysis['filteredOutliers']) == 1
    assert analysis['filteredOutliers'][0]['price'] == 15
    assert analysis['tiefstpreis'] == 999
    assert analysis['previousLow'] == 1050
    assert analysis['isNewAllTimeLow'] is True


def test_rolling_median_time_horizon(page: Page):
    # Product: GPU launched 2 years ago at CHF 2000, sold for ~CHF 800 in last 6 months
    res = page.evaluate("""() => {
        const now = Date.now();
        const dayMs = 86400 * 1000;
        const series = [
            [now - 700 * dayMs, 2200],
            [now - 650 * dayMs, 2100],
            [now - 600 * dayMs, 2000],
            [now - 550 * dayMs, 1900],
            [now - 500 * dayMs, 1800],
            [now - 450 * dayMs, 1700],
            [now - 400 * dayMs, 1600],
            [now - 350 * dayMs, 1500],
            [now - 120 * dayMs, 850],
            [now - 90 * dayMs, 800],
            [now - 60 * dayMs, 780],
            [now - 30 * dayMs, 750],
            [now, 699]
        ];

        const stats180d = window.ToppreiseSuite.analyzePriceTimeSeries(series, 699, 180);
        const statsLifetime = window.ToppreiseSuite.analyzePriceTimeSeries(series, 699, 0);

        return { stats180d, statsLifetime };
    }""")

    # 180d window should only consider points in the last 180 days (around ~780 median)
    assert res['stats180d']['medianPrice'] <= 850
    # Lifetime window includes early launch prices (median = 1700)
    assert res['statsLifetime']['medianPrice'] >= 1500


def test_bestpreise_settings_horizon_selection_persistence(page: Page):
    # Open settings dialog in Shadow DOM
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    # Toggle Bestpreise on if not active
    toggle = page.locator('#tp-root >> #tp-bestpreise-mode-toggle')
    if not toggle.is_checked():
        page.click('#tp-root >> #tp-bestpreise-mode-toggle + .tp-slider')

    horizon_group = page.locator('#tp-root >> #tp-bestpreise-horizon-group')
    assert horizon_group.is_visible()

    # Change horizon select to 180 days (6 months)
    page.select_option('#tp-root >> #tp-bestpreise-horizon-select', '180')

    # Save
    page.click('#tp-root >> #tp-btn-save')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='hidden')

    assert page.evaluate("() => window.ToppreiseSuite.CONFIG.BESTPREISE_MEDIAN_HORIZON_DAYS") == 180


def test_cache_settings_and_clear_button(page: Page):
    # Seed local storage with 2 fake cache items
    page.evaluate("""() => {
        localStorage.setItem('tp_hist_v1_item1', JSON.stringify({ tiefstpreis: 100, time: Date.now() }));
        localStorage.setItem('tp_hist_v1_item2', JSON.stringify({ tiefstpreis: 200, time: Date.now() }));
    }""")

    # Open settings modal
    page.click('#tp-root >> #tp-settings-fab')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='visible')

    # Verify cache count label displays 2 items
    stats_label = page.locator('#tp-root >> #tp-cache-stats-label')
    assert '2 Einträge' in (stats_label.text_content() or '')

    # Change Cache TTL to 72 hours and Neg TTL to 6 hours
    page.select_option('#tp-root >> #tp-cache-ttl-select', '72')
    page.select_option('#tp-root >> #tp-cache-neg-ttl-select', '6')

    # Click Clear Cache button
    page.click('#tp-root >> #tp-cache-clear-btn')
    assert '0 Einträge' in (stats_label.text_content() or '')

    # Verify localStorage items were removed
    remaining_keys = page.evaluate("""() => {
        const keys = [];
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i);
            if (k && k.startsWith('tp_hist_v1_')) keys.push(k);
        }
        return keys;
    }""")
    assert len(remaining_keys) == 0

    # Save
    page.click('#tp-root >> #tp-btn-save')
    page.wait_for_selector('#tp-root >> #tp-settings-dialog', state='hidden')

    assert page.evaluate("() => window.ToppreiseSuite.CONFIG.REAL_DEAL_CACHE_HOURS") == 72
    assert page.evaluate("() => window.ToppreiseSuite.CONFIG.NEGATIVE_CACHE_HOURS") == 6


def test_check_deals_active_in_bestpreise_mode(page: Page):
    # Activate Bestpreise mode
    page.evaluate("""() => {
        window.ToppreiseSuite.CONFIG.BESTPREISE_MODE_ACTIVE = true;
        window.ToppreiseSuite.processListings();
    }""")

    # Check Deals button should NOT be disabled
    batch_btn = page.locator('#tp-suite-filter-bar #tp-bar-batch-check-btn')
    assert batch_btn.is_visible()
    assert 'tp-disabled' not in (batch_btn.get_attribute('class') or '')

    # Threshold button should be visible and interactive
    thresh_btn = page.locator('#tp-suite-filter-bar #tp-bar-threshold-btn')
    assert thresh_btn.is_visible()


def test_unscanned_cards_no_stuck_loading_badge(page: Page):
    # In Bestpreise mode, reveal filtered cards
    page.evaluate("""() => {
        window.ToppreiseSuite.CONFIG.BESTPREISE_MODE_ACTIVE = true;
        document.body.classList.add('tp-reveal-filtered');
        window.ToppreiseSuite.processListings();
    }""")

    # Unscanned card badge must NOT have tp-deal-loading and should show original discount with loupe
    uncached_badge = page.locator('#card-low-offers .badge-dif')
    assert 'tp-deal-loading' not in (uncached_badge.get_attribute('class') or '')
    assert '🔍' in (uncached_badge.text_content() or '')


def test_bestpreise_sorting_nested_wrappers(page: Page):
    # Dynamically wrap each product card in a nested column/cell hierarchy to simulate real site layout:
    # <div id="product-list"><div class="row"><div class="col-md-3 cell-1"><card1>...
    page.evaluate("""() => {
        const list = document.getElementById('product-list');
        const cards = Array.from(list.querySelectorAll('.Plugin_Product'));
        cards.forEach((c, idx) => {
            const col = document.createElement('div');
            col.className = 'col-md-3 custom-col-wrapper';
            col.id = 'col-wrapper-' + idx;
            list.appendChild(col);
            col.appendChild(c);
        });

        // Set deal stats: Card 1 -> Score 15%, Card 2 -> Score 40%, Card 3 -> Score 25%
        localStorage.setItem('tp_hist_v1_797571', JSON.stringify({
            tiefstpreis: 1800,
            hoechstpreis: 2400,
            medianPrice: 2200,
            isNewAllTimeLow: false,
            dataPointCount: 10,
            time: Date.now()
        }));
        localStorage.setItem('tp_hist_v1_797572', JSON.stringify({
            tiefstpreis: 1100,
            hoechstpreis: 3000,
            medianPrice: 2750, // dMed 60% -> Score 30%
            isNewAllTimeLow: false,
            dataPointCount: 10,
            time: Date.now()
        }));
        localStorage.setItem('tp_hist_v1_797573', JSON.stringify({
            tiefstpreis: 15,
            hoechstpreis: 50,
            medianPrice: 40,
            previousLow: 25,
            isNewAllTimeLow: true,
            realDiscountVsPrevLow: 40, // Score 50%
            dataPointCount: 10,
            time: Date.now()
        }));

        window.ToppreiseSuite.CONFIG.BESTPREISE_MODE_ACTIVE = true;
        window.ToppreiseSuite.processListings();
    }""")

    # Verify column wrappers were reordered descending by score:
    # Card 3 (Score 50%) -> Card 2 (Score 30%) -> Card 1 (Score 15%)
    wrapper_ids = page.evaluate("""() => {
        const wrappers = Array.from(document.querySelectorAll('#product-list .custom-col-wrapper'));
        return wrappers.map(w => w.querySelector('.Plugin_Product')?.id);
    }""")
    assert wrapper_ids[0] == 'card-negative'   # Card 3 (50%)
    assert wrapper_ids[1] == 'card-expensive'  # Card 2 (30%)
    assert wrapper_ids[2] == 'card-cheapest'   # Card 1 (15%)


















