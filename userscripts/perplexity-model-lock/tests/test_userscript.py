import os
from playwright.sync_api import sync_playwright, Page

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_HTML = f"file://{os.path.join(BASE_DIR, 'mock_perplexity.html')}"
SCRIPT_PATH = os.path.join(os.path.dirname(BASE_DIR), 'perplexity-model-lock.user.js')

def get_userscript_content():
    with open(SCRIPT_PATH, 'r') as f:
        return f.read()

def test_model_lock_behavior(page: Page):
    # 1. Verify that the model button is successfully updated to Claude Sonnet 4.6 Thinking
    page.wait_for_function(
        "document.getElementById('model-select-btn').textContent.includes('Claude Sonnet 4.6 Thinking')",
        timeout=5000
    )
    
    btn_text = page.locator('#model-select-btn').inner_text()
    assert 'Claude Sonnet 4.6 Thinking' in btn_text
    
    # 2. Verify that the green indicator dot is created inside the button
    indicator = page.locator('#model-select-btn .px-model-lock-indicator')
    page.wait_for_selector('#model-select-btn .px-model-lock-indicator', timeout=2000)
    assert indicator.is_visible()
    
    # Check that it has a green background style
    bg_color = page.evaluate("window.getComputedStyle(document.querySelector('.px-model-lock-indicator')).backgroundColor")
    assert bg_color == 'rgb(0, 204, 102)'  # matches #00cc66

def test_manual_deviation_recovery(page: Page):
    # Verify model is locked initially
    page.wait_for_selector('#model-select-btn .px-model-lock-indicator')
    assert 'Claude Sonnet 4.6 Thinking' in page.locator('#model-select-btn').inner_text()
    
    # Manually switch the model to something else
    page.click('#model-select-btn')
    page.wait_for_selector('.dropdown-portal.open')
    
    # Click Sonar 2 (which should close dropdown and change selection to "Sonar 2")
    page.click('.dropdown-item[data-model="Sonar 2"]')
    
    # The script should detect the deviation and force it back to Claude Sonnet 4.6 Thinking
    page.wait_for_function(
        "document.getElementById('model-select-btn').textContent.includes('Claude Sonnet 4.6 Thinking')",
        timeout=6000
    )
    
    btn_text = page.locator('#model-select-btn').inner_text()
    assert 'Claude Sonnet 4.6 Thinking' in btn_text

if __name__ == '__main__':
    content = get_userscript_content()
    
    print("Initializing Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Test 1: Model locking on load
        print("\n--- Running Test 1: Model Lock Behavior ---")
        page = browser.new_page()
        page.goto(MOCK_HTML)
        # Inject and evaluate the userscript
        page.evaluate(content)
        test_model_lock_behavior(page)
        print("Test 1 PASSED!")
        page.close()
        
        # Test 2: Deviation recovery when changed
        print("\n--- Running Test 2: Manual Deviation Recovery ---")
        page = browser.new_page()
        page.goto(MOCK_HTML)
        # Inject and evaluate the userscript
        page.evaluate(content)
        test_manual_deviation_recovery(page)
        print("Test 2 PASSED!")
        page.close()
        
        browser.close()
        
    print('\nAll browser validation tests passed successfully! Perfect grounding achieved.')
