import os

import pytest
from playwright.sync_api import Page


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_HTML = f"file://{os.path.join(BASE_DIR, 'mock_huggingface.html')}"
SCRIPT_PATH = os.path.join(os.path.dirname(BASE_DIR), 'huggingface-heart.user.js')


@pytest.fixture(scope='session')
def userscript_content():
    with open(SCRIPT_PATH, encoding='utf-8') as script:
        return script.read()


@pytest.fixture
def page(browser, userscript_content):
    page = browser.new_page()
    page.goto(MOCK_HTML)
    page.evaluate(userscript_content)
    page.wait_for_selector('#unliked-like[data-hf-inline-bound]')
    yield page
    page.close()


def requests(page: Page):
    return page.evaluate('window.likeRequests')


def test_inline_like_and_unlike_stay_on_the_card(page: Page):
    page.click('#unliked-like')
    page.wait_for_function('window.likeRequests.length === 1')

    assert page.url == MOCK_HTML
    assert requests(page)[0]['url'] == '/api/models/owner/model/like'
    assert requests(page)[0]['method'] == 'POST'
    assert page.locator('#card-unliked').get_attribute('class').find('hf-is-liked') >= 0
    assert page.locator('#card-unliked').get_attribute('class').find('hf-is-unliked') == -1
    assert page.locator('#unliked-like').inner_text() == '34'
    assert 'text-red-500' in (page.locator('#unliked-like svg').get_attribute('class') or '')

    page.click('#unliked-like')
    page.wait_for_function('window.likeRequests.length === 2')

    assert requests(page)[1]['method'] == 'DELETE'
    assert page.locator('#card-unliked').get_attribute('class').find('hf-is-unliked') >= 0
    assert page.locator('#unliked-like').inner_text() == '33'


def test_liked_card_uses_delete_and_task_icon_does_not_bind(page: Page):
    page.click('#liked-like')
    page.wait_for_function('window.likeRequests.length === 1')

    assert requests(page)[0]['url'] == '/api/models/owner/liked-model/like'
    assert requests(page)[0]['method'] == 'DELETE'
    assert page.locator('#liked-like').inner_text() == '6'

    page.click('#task-icon')
    assert page.evaluate('window.navigationAttempts') == 1
    assert len(requests(page)) == 1


@pytest.mark.parametrize('fetch_mode,expected_alert', [
    ('unauthorized', True),
    ('reject', False),
])
def test_failed_request_restores_optimistic_state(page: Page, fetch_mode, expected_alert):
    page.evaluate(f"window.fetchMode = '{fetch_mode}'")
    page.click('#unliked-like')
    page.wait_for_function('window.likeRequests.length === 1')
    page.wait_for_function("document.querySelector('#unliked-like').getAttribute('aria-pressed') === 'false'")

    assert page.locator('#card-unliked').get_attribute('class').find('hf-is-unliked') >= 0
    assert page.locator('#unliked-like').inner_text() == '33'
    assert bool(page.evaluate('window.alertMessages.length')) is expected_alert


def test_keyboard_activation(page: Page):
    page.locator('#unliked-like').focus()
    page.keyboard.press('Space')
    page.wait_for_function('window.likeRequests.length === 1')

    assert requests(page)[0]['method'] == 'POST'
    assert page.locator('#unliked-like').get_attribute('aria-pressed') == 'true'


def test_dynamic_cards_are_bound_once(page: Page):
    page.evaluate("""
      const card = document.querySelector('#card-unliked').cloneNode(true);
      card.id = 'card-dynamic';
      card.querySelector('.model-link').href = '/owner/dynamic-model';
      card.querySelector('.title').textContent = 'owner/dynamic-model';
      const like = card.querySelector('#unliked-like');
      like.id = 'dynamic-like';
      like.removeAttribute('data-hf-inline-bound');
      like.removeAttribute('aria-label');
      like.removeAttribute('aria-pressed');
      like.removeAttribute('role');
      like.removeAttribute('tabindex');
      like.classList.remove('hf-inline-like-btn');
      like.style.cursor = '';
      document.querySelector('#model-grid').appendChild(card);
    """)
    page.wait_for_selector('#dynamic-like[data-hf-inline-bound]')
    page.click('#dynamic-like')
    page.wait_for_function('window.likeRequests.length === 1')

    assert requests(page)[0]['url'] == '/api/models/owner/dynamic-model/like'
    assert requests(page)[0]['method'] == 'POST'
