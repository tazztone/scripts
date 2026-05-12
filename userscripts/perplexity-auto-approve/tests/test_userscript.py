import os
import pytest
from playwright.sync_api import sync_playwright, Page

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_HTML = f"file://{os.path.join(BASE_DIR, 'mock_perplexity.html')}"
SCRIPT_PATH = os.path.join(os.path.dirname(BASE_DIR), 'perplexity-auto-approve.user.js')


@pytest.fixture(scope='session')
def userscript_content():
    with open(SCRIPT_PATH, 'r') as f:
        return f.read()


@pytest.fixture
def page(userscript_content):
    """Fresh browser page for each test with the userscript injected."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page()
        pg.goto(MOCK_HTML)
        pg.evaluate(userscript_content)
        yield pg
        browser.close()


def test_auto_click_behavior(page: Page):
    # Verify progress bar is injected
    page.wait_for_selector('.px-progress-bar', timeout=1000)
    assert page.locator('#approve-btn .px-progress-bar').is_visible()

    # Verify auto-click happens after delay (CONFIG.CLICK_DELAY_MS = 3000)
    page.wait_for_function("document.getElementById('approve-btn').innerText === 'CLICKED'", timeout=4000)
    assert page.locator('#approve-btn').inner_text() == 'CLICKED'


def test_hover_pause_behavior(page: Page):
    approve_btn = page.locator('#approve-btn')
    page.wait_for_selector('.px-progress-bar')

    # Hover to pause
    approve_btn.hover()

    # Wait 2 s — button should NOT have been clicked yet
    page.wait_for_timeout(2000)
    assert approve_btn.inner_text() != 'CLICKED'
    assert 'px-paused' in (approve_btn.get_attribute('class') or '')

    # Unhover and wait for click
    page.mouse.move(0, 0)
    page.wait_for_function("document.getElementById('approve-btn').innerText === 'CLICKED'", timeout=4000)
    assert approve_btn.inner_text() == 'CLICKED'


def test_github_auto_enable(page: Page):
    # Script should automatically trigger the GitHub connector enable sequence
    page.wait_for_selector('#active-connectors :has-text("GitHub")', timeout=5000)
    assert page.locator('#active-connectors :has-text("GitHub")').is_visible()


if __name__ == '__main__':
    content = open(SCRIPT_PATH).read()
    for test_fn in [test_auto_click_behavior, test_hover_pause_behavior, test_github_auto_enable]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.goto(MOCK_HTML)
            pg.evaluate(content)
            test_fn(pg)
            browser.close()
    print('All manual tests passed!')
