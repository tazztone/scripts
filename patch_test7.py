with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

# Fix the test where 5 cards is hardcoded but we added a 6th card (the regression fixture)
content = content.replace("assert len(card_visibilities) == 5", "assert len(card_visibilities) == 6")
content = content.replace("assert visible_count_1 == 5", "assert visible_count_1 == 6")

# Also the empty state test says "Filter all 5 cards by setting negative terms"
# and searches for 'GeForce, Silikon, iPhone, Dell'.
# We need to add 'ENDGAME' to the negative terms so the new 6th card is filtered too.
content = content.replace("page.fill('#tp-inline-negative-input', 'GeForce, Silikon, iPhone, Dell')", "page.fill('#tp-inline-negative-input', 'GeForce, Silikon, iPhone, Dell, ENDGAME')")

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
