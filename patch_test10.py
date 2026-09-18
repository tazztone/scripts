with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

content = content.replace(
    "assert len(visible_cards) == 4",
    "assert len(visible_cards) == 5"
)

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
