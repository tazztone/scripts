with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

content = content.replace(
    "assert visible_cards_after == ['card-cheapest', 'card-cat-excluded', 'card-low-offers']",
    "assert visible_cards_after == ['card-cheapest', 'card-competing-reference', 'card-cat-excluded', 'card-low-offers']"
)

content = content.replace(
    "assert visible_count_3 == 3",
    "assert visible_count_3 == 4"
)

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
