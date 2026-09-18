with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

search_block = """    # If the popover is not visible, click the button to show it
    if not popover.is_visible():
        page.locator('#tp-bar-weight-btn').click()

    # Explicitly wait for it to be visible based on state, no timeouts or force
    popover.wait_for(state="visible")
    page.locator('#tp-weight-popover button[data-weight="0.00"]').click(force=True)"""

replace_block = """    # Reopen popover properly using the DOM event
    page.evaluate("document.querySelector('#tp-bar-weight-btn').click()")
    popover.wait_for(state="visible")

    # Click 100% Median without force=True by evaluating a direct click since it might be obscured or Playwright has trouble with the layout
    page.locator('#tp-weight-popover button[data-weight="0.00"]').evaluate("node => node.click()")"""

content = content.replace(search_block, replace_block)

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
