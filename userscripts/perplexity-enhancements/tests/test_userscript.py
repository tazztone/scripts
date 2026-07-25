import os

import pytest
from playwright.sync_api import Page


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_HTML = f"file://{os.path.join(BASE_DIR, 'mock_perplexity.html')}"
SCRIPT_PATH = os.path.join(os.path.dirname(BASE_DIR), 'perplexity-enhancements.user.js')


@pytest.fixture(scope='session')
def userscript_content():
    with open(SCRIPT_PATH, encoding='utf-8') as script:
        return script.read()


@pytest.fixture
def page(browser, userscript_content):
    page = browser.new_page()
    page.goto(MOCK_HTML)
    page.evaluate("localStorage.setItem('px_enhancements_CLICK_DELAY_MS', '300')")
    page.evaluate(userscript_content)
    yield page
    page.close()


@pytest.fixture
def settings_page(browser, userscript_content):
    page = browser.new_page()
    page.goto(MOCK_HTML)
    page.evaluate("localStorage.setItem('px_enhancements_CLICK_DELAY_MS', '3000')")
    page.evaluate(userscript_content)
    yield page
    page.close()


def test_model_lock_and_thinking(page: Page):
    page.wait_for_function("document.querySelector('#model-select-btn').textContent.includes('Claude Sonnet 4.6 Thinking')")
    page.wait_for_selector('#model-select-btn .px-model-lock-indicator')
    assert page.locator('#model-select-btn .px-model-lock-indicator').is_visible()
    assert page.evaluate("getComputedStyle(document.querySelector('.px-model-lock-indicator')).backgroundColor") == 'rgb(0, 204, 102)'


def test_manual_model_deviation_recovers(page: Page):
    page.wait_for_function("document.querySelector('#model-select-btn').textContent.includes('Claude Sonnet 4.6 Thinking')")
    page.click('#model-select-btn')
    page.locator('[data-model="Sonar 2"]').click()
    page.wait_for_function("document.querySelector('#model-select-btn').textContent.includes('Claude Sonnet 4.6 Thinking')", timeout=5000)


def test_approval_countdown_and_duplicate_mutations(page: Page):
    page.wait_for_selector('#approve-btn .px-progress-bar')
    page.wait_for_selector('#confirm-btn .px-progress-bar')
    page.evaluate("document.body.appendChild(document.createElement('div'))")
    page.wait_for_function("document.querySelector('#approve-btn').textContent === 'CLICKED'", timeout=3000)
    assert page.locator('#approve-btn').inner_text() == 'CLICKED'
    assert page.locator('#approve-btn .px-progress-bar').count() == 0


def test_hover_pauses_approval(page: Page):
    button = page.locator('#approve-btn')
    page.wait_for_selector('#approve-btn .px-progress-bar')
    button.hover()
    page.wait_for_timeout(450)
    assert button.inner_text() != 'CLICKED'
    assert 'px-paused' in (button.get_attribute('class') or '')
    page.mouse.move(0, 0)
    page.wait_for_function("document.querySelector('#approve-btn').textContent === 'CLICKED'", timeout=3000)


def test_github_suggestion_is_enabled_but_followup_is_ignored(page: Page):
    page.wait_for_selector('#active-connectors button[aria-haspopup="menu"]')
    assert page.locator('#active-connectors button').inner_text() == 'GitHub'
    assert page.locator('.follow-up').inner_text().startswith('Your complete github')


def test_settings_save_and_disable_cancels_pending_approval(settings_page: Page):
    page = settings_page
    page.wait_for_selector('#approve-btn .px-progress-bar')
    page.click('#px-settings-fab')
    assert page.locator('#px-settings-modal-backdrop.open').is_visible()
    page.locator('#px-auto-approve-enabled').evaluate('(el) => { el.click(); }')
    page.locator('#px-model-lock-enabled').evaluate('(el) => { el.click(); }')
    page.click('#px-btn-save')
    page.wait_for_timeout(450)
    assert page.locator('#approve-btn').inner_text() != 'CLICKED'
    assert page.locator('.px-model-lock-indicator').count() == 0
    assert page.evaluate("localStorage.getItem('px_enhancements_AUTO_APPROVE')") == 'false'


def test_settings_escape_and_legacy_migration(browser, userscript_content):
    page = browser.new_page()
    page.goto(MOCK_HTML)
    page.evaluate("localStorage.setItem('px_model_lock_TARGET_MODEL', JSON.stringify('Sonar 2'))")
    page.evaluate("localStorage.setItem('px_model_lock_ENABLE_THINKING', 'false')")
    page.evaluate(userscript_content)
    page.click('#px-settings-fab')
    page.keyboard.press('Escape')
    assert page.locator('#px-settings-modal-backdrop.open').count() == 0
    page.click('#px-settings-fab')
    assert page.locator('#px-model-lock-target').input_value() == 'Sonar 2'
    assert page.evaluate("localStorage.getItem('px_enhancements_TARGET_MODEL')") == '"Sonar 2"'
    page.close()
