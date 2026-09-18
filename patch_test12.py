with open("userscripts/toppreise/tests/test_userscript.py", "r") as f:
    content = f.read()

# Replace the synchronous assert with a wait_for or expect
import re
content = re.sub(r'assert "tp-deal-alltime-low" in badge.get_attribute\("class"\)', r'page.wait_for_selector("#card-competing-reference .tp-deal-alltime-low")', content)
content = re.sub(r'assert "tp-deal-not-low" not in badge.get_attribute\("class"\)', r'assert "tp-deal-not-low" not in badge.get_attribute("class")', content)

with open("userscripts/toppreise/tests/test_userscript.py", "w") as f:
    f.write(content)
