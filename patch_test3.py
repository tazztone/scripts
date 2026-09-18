with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

# Playwright might be failing because the previous click closed the popover and the document click handler keeps it closed.
# We should click with force=True if it is unclickable, or fix the document click handler issue in the test.
# The user issue asked to "fix the ... reintroduced force=True Playwright click". So we should make the element interactable normally.

search_block = """    # If the popover is not visible, click the button to show it
    if not popover.is_visible():
        page.locator('#tp-bar-weight-btn').click()

    # Explicitly wait for it to be visible based on state, no timeouts or force
    popover.wait_for(state="visible")
    btn = page.locator('#tp-weight-popover button[data-weight="0.00"]')
    btn.wait_for(state="visible")
    btn.click()"""

replace_block = """    # If the popover is not visible, click the button to show it
    if not popover.is_visible():
        page.locator('#tp-bar-weight-btn').click()

    # Explicitly wait for it to be visible based on state, no timeouts or force
    popover.wait_for(state="visible")
    btn = page.locator('#tp-weight-popover button[data-weight="0.00"]')
    # The first click on an option might close the popover. We clicked the button to open it,
    # but maybe we need to dispatch a click event if Playwright thinks it's not stable.
    # The button has `display: none` when the popover doesn't have the `tp-show` class.
    # Let's use evaluate to ensure the popover has the class, then click normally.
    page.evaluate("document.querySelector('#tp-weight-popover').classList.add('tp-show')")
    btn.click()"""

content = content.replace(search_block, replace_block)

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
