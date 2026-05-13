import os
import time
import json
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navigating to perplexity.ai...")
        page.goto("https://www.perplexity.ai/")
        page.wait_for_timeout(2000)
        
        # Type "github" to trigger suggestions
        print("Typing 'github' into textarea...")
        try:
            textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="anything"]')
            textarea.first.fill("github")
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Could not type in textarea: {e}")
            # Try another selector
            page.locator('textarea').first.fill("github")
            page.wait_for_timeout(2000)
        
        page.screenshot(path="perplexity_screenshot.png")
        print("Screenshot saved to perplexity_screenshot.png")
        
        # Dump all buttons and their attributes
        print("Analyzing buttons...")
        buttons_data = page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                return buttons.map((b, i) => {
                    const rect = b.getBoundingClientRect();
                    const style = window.getComputedStyle(b);
                    const svgs = Array.from(b.querySelectorAll('svg')).map(s => s.outerHTML);
                    const uses = Array.from(b.querySelectorAll('use')).map(u => u.outerHTML);
                    const paths = Array.from(b.querySelectorAll('svg path')).map(p => p.getAttribute('d'));
                    
                    return {
                        index: i,
                        text: b.textContent,
                        outerHTML: b.outerHTML.substring(0, 300) + '...',
                        role: b.getAttribute('role'),
                        ariaHasPopup: b.getAttribute('aria-haspopup'),
                        width: rect.width,
                        height: rect.height,
                        classes: b.className,
                        borderStyle: style.borderStyle,
                        borderWidth: style.borderWidth,
                        borderColor: style.borderColor,
                        hasPlusChar: b.textContent.includes('+'),
                        svgCount: svgs.length,
                        paths: paths.slice(0, 3),
                        useRefs: uses
                    };
                });
            }
        """)
        
        # Filter to interesting buttons
        relevant_buttons = [b for b in buttons_data if 'github' in b['text'].lower() or b['ariaHasPopup'] == 'menu']
        
        print(f"Found {len(buttons_data)} total buttons, showing {len(relevant_buttons)} related to GitHub/Menu.")
        print(json.dumps(relevant_buttons, indent=2))
        
        browser.close()

if __name__ == "__main__":
    main()
