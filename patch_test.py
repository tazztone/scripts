with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

# Replace force=True if it still exists
content = content.replace("page.locator('#tp-weight-popover button[data-weight=\"0.00\"]').click(force=True)", "page.locator('#tp-weight-popover button[data-weight=\"0.00\"]').click()")

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
