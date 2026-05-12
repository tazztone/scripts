import os
import time
from playwright.sync_api import sync_playwright
import pytest

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_HTML = f"file://{os.path.join(BASE_DIR, 'mock_perplexity.html')}"
SCRIPT_PATH = os.path.join(os.path.dirname(BASE_DIR), 'perplexity-auto-approve.user.js')

@pytest.fixture
def userscript_content():
    with open(SCRIPT_PATH, 'r') as f:
        return f.read()

def test_auto_click_behavior(userscript_content):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(MOCK_HTML)
        
        # Inject the script
        page.evaluate(userscript_content)
        
        # 1. Verify progress bar is injected
        approve_btn = page.locator('#approve-btn')
        page.wait_for_selector('.px-progress-bar', timeout=1000)
        assert approve_btn.locator('.px-progress-bar').is_visible()
        
        # 2. Verify auto-click happens after 3s (CONFIG.CLICK_DELAY_MS is 3000)
        # We wait for the button text to change to 'CLICKED'
        page.wait_for_function("document.getElementById('approve-btn').innerText === 'CLICKED'", timeout=4000)
        assert approve_btn.inner_text() == 'CLICKED'
        
        browser.close()

def test_hover_pause_behavior(userscript_content):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(MOCK_HTML)
        
        # Inject script
        page.evaluate(userscript_content)
        
        # Find button and hover
        approve_btn = page.locator('#approve-btn')
        page.wait_for_selector('.px-progress-bar')
        
        # Hover over the button to pause
        approve_btn.hover()
        
        # Wait a bit and check if it has NOT been clicked yet (should be paused)
        time.sleep(2) 
        assert approve_btn.inner_text() != 'CLICKED'
        assert "px-paused" in approve_btn.get_attribute("class")
        
        # Unhover and wait for click
        page.mouse.move(0, 0)
        page.wait_for_function("document.getElementById('approve-btn').innerText === 'CLICKED'", timeout=4000)
        assert approve_btn.inner_text() == 'CLICKED'
        
        browser.close()

def test_github_auto_enable(userscript_content):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(MOCK_HTML)
        
        # Inject script
        page.evaluate(userscript_content)
        
        # The script should automatically trigger the click sequence:
        # 1. Click '+'
        # 2. Hover 'Connectors and sources'
        # 3. Click 'GitHub'
        
        # Verify GitHub pill appears in active-connectors
        page.wait_for_selector('#active-connectors div:has-text("GitHub")', timeout=5000)
        github_pill = page.locator('#active-connectors div:has-text("GitHub")')
        assert github_pill.is_visible()
        
        browser.close()

if __name__ == "__main__":
    # Manual run if not using pytest
    test_auto_click_behavior(open(SCRIPT_PATH).read())
    test_hover_pause_behavior(open(SCRIPT_PATH).read())
    test_github_auto_enable(open(SCRIPT_PATH).read())
    print("All manual tests passed!")
