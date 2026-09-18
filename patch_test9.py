with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

content = content.replace(
    "assert visible_cards == ['card-cheapest', 'card-negative', 'card-cat-excluded', 'card-low-offers']",
    "assert visible_cards == ['card-cheapest', 'card-competing-reference', 'card-negative', 'card-cat-excluded', 'card-low-offers']"
)

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
