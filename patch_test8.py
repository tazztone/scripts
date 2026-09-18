with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

content = content.replace("assert 'Alle 5 Angebote' in (notice.text_content() or '')", "assert 'Alle 6 Angebote' in (notice.text_content() or '')")
content = content.replace("assert visible_count_2 == 5", "assert visible_count_2 == 6")
content = content.replace("assert visible_count_3 == 4", "assert visible_count_3 == 5")

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
