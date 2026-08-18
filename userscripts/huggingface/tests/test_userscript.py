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


@pytest.fixture
def shared_footer_page(browser, userscript_content):
    page = browser.new_page()
    page.goto(MOCK_HTML)
    page.evaluate("""() => {
      for (const [cardId, likeId] of [['card-unliked', 'unliked-like'], ['card-liked', 'liked-like']]) {
        const card = document.querySelector(`#${cardId}`);
        document.querySelector(`#${likeId}`).prepend(card.querySelector('.task-badge svg'));
      }
    }""")
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
    assert 'hf-is-liked' in (page.locator('#card-liked').get_attribute('class') or '')
    assert 'hf-is-unliked' not in (page.locator('#card-liked').get_attribute('class') or '')

    page.click('#liked-like')
    page.wait_for_function('window.likeRequests.length === 1')

    assert requests(page)[0]['url'] == '/api/models/owner/liked-model/like'
    assert requests(page)[0]['method'] == 'DELETE'
    assert page.locator('#liked-like').inner_text() == '6'

    page.click('#task-icon')
    assert page.evaluate('window.navigationAttempts') == 1
    assert len(requests(page)) == 1


def test_hydrated_liked_card_clears_unliked_border(page: Page):
    assert 'hf-is-unliked' in (page.locator('#card-unliked').get_attribute('class') or '')

    page.locator('#unliked-like svg').evaluate("""svg => {
      svg.classList.add('text-red-500');
      svg.querySelector('path').setAttribute('d', 'M22.5,4c-2,0-3.9,0.8-5.3,2.2L16,7.4');
    }""")
    page.wait_for_timeout(350)

    classes = page.locator('#card-unliked').get_attribute('class') or ''
    assert 'hf-is-liked' in classes
    assert 'hf-is-unliked' not in classes
    assert page.locator('#unliked-like').get_attribute('aria-pressed') == 'true'
    assert page.locator('#card-unliked').evaluate(
        "card => getComputedStyle(card).borderTopColor"
    ) != 'rgb(16, 185, 129)'


def test_shared_footer_rescan_preserves_liked_state(shared_footer_page: Page):
    initial = shared_footer_page.evaluate("""() => [
      document.querySelector('#card-unliked').className,
      document.querySelector('#card-liked').className
    ]""")
    shared_footer_page.evaluate("document.body.append(document.createElement('span'))")
    shared_footer_page.wait_for_timeout(350)
    final = shared_footer_page.evaluate("""() => [
      document.querySelector('#card-unliked').className,
      document.querySelector('#card-liked').className
    ]""")

    assert 'hf-is-unliked' in initial[0]
    assert 'hf-is-liked' in initial[1]
    assert 'hf-is-unliked' in final[0]
    assert 'hf-is-liked' in final[1]


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


def test_negative_text_filter_substring(page: Page):
    page.fill('#hf-exclude-input', 'gguf')
    page.wait_for_function("document.querySelector('#card-gguf').classList.contains('hf-filtered-out')")

    assert 'hf-filtered-out' in (page.locator('#card-gguf').get_attribute('class') or '')
    assert 'hf-filtered-out' not in (page.locator('#card-fp8').get_attribute('class') or '')
    assert 'hf-filtered-out' not in (page.locator('#card-unliked').get_attribute('class') or '')
    assert 'hf-filtered-out' not in (page.locator('#card-liked').get_attribute('class') or '')
    assert 'Showing 3 / 4' in page.locator('#hf-df-badge').inner_text()


def test_negative_text_filter_regex_and_multi_term(page: Page):
    page.fill('#hf-exclude-input', '/(?:gguf|fp8)/i')
    page.wait_for_function("document.querySelector('#card-gguf').classList.contains('hf-filtered-out') && document.querySelector('#card-fp8').classList.contains('hf-filtered-out')")

    assert 'hf-filtered-out' in (page.locator('#card-gguf').get_attribute('class') or '')
    assert 'hf-filtered-out' in (page.locator('#card-fp8').get_attribute('class') or '')
    assert 'hf-filtered-out' not in (page.locator('#card-unliked').get_attribute('class') or '')
    assert 'Showing 2 / 4' in page.locator('#hf-df-badge').inner_text()


def test_negative_text_filter_clear_button(page: Page):
    page.fill('#hf-exclude-input', 'gguf')
    page.wait_for_function("document.querySelector('#card-gguf').classList.contains('hf-filtered-out')")

    page.click('#hf-exclude-clear-btn')
    page.wait_for_function("!document.querySelector('#card-gguf').classList.contains('hf-filtered-out')")

    assert page.locator('#hf-exclude-input').input_value() == ''
    assert 'hf-filtered-out' not in (page.locator('#card-gguf').get_attribute('class') or '')
    assert 'All shown (4)' in page.locator('#hf-df-badge').inner_text()


def test_negative_text_filter_toggle(page: Page):
    page.fill('#hf-exclude-input', 'gguf')
    page.wait_for_function("document.querySelector('#card-gguf').classList.contains('hf-filtered-out')")

    # Disable toggle
    page.click('#hf-exclude-toggle + .hf-slider')
    page.wait_for_function("!document.querySelector('#card-gguf').classList.contains('hf-filtered-out')")

    assert page.locator('#hf-exclude-input').input_value() == 'gguf'
    assert 'hf-filtered-out' not in (page.locator('#card-gguf').get_attribute('class') or '')
    assert 'hf-section-dimmed' in (page.locator('#hf-exclude-section-body').get_attribute('class') or '')

    # Re-enable toggle
    page.click('#hf-exclude-toggle + .hf-slider')
    page.wait_for_function("document.querySelector('#card-gguf').classList.contains('hf-filtered-out')")
    assert 'hf-filtered-out' in (page.locator('#card-gguf').get_attribute('class') or '')
