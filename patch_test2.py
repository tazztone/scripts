with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

# Replace the problematic popover wait to wait for the button itself to be visible/clickable
search_block = """    # If the popover is not visible, click the button to show it
    if not popover.is_visible():
        page.locator('#tp-bar-weight-btn').click()

    # Explicitly wait for it to be visible based on state, no timeouts or force
    popover.wait_for(state="visible")
    page.locator('#tp-weight-popover button[data-weight="0.00"]').click()"""

replace_block = """    # If the popover is not visible, click the button to show it
    if not popover.is_visible():
        page.locator('#tp-bar-weight-btn').click()

    # Explicitly wait for it to be visible based on state, no timeouts or force
    popover.wait_for(state="visible")
    btn = page.locator('#tp-weight-popover button[data-weight="0.00"]')
    btn.wait_for(state="visible")
    btn.click()"""

content = content.replace(search_block, replace_block)

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
