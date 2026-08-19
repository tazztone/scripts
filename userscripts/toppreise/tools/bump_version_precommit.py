#!/usr/bin/env python3
"""Pre-commit hook: Auto-bump patch version in toppreise.user.js and update README when staged."""

import os
import re
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_FILE = os.path.join(BASE_DIR, 'toppreise.user.js')
README_FILE = os.path.join(BASE_DIR, 'README.md')


def main():
    try:
        staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).splitlines()
    except subprocess.CalledProcessError:
        return 0

    toppreise_rel = os.path.relpath(SCRIPT_FILE)
    if not any(toppreise_rel in path or 'toppreise.user.js' in path for path in staged):
        return 0

    if not os.path.exists(SCRIPT_FILE):
        return 0

    with open(SCRIPT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'//\s*@version\s+(\d+)\.(\d+)\.(\d+)', content)
    if not match:
        return 0

    major, minor, patch = match.group(1), match.group(2), int(match.group(3))
    new_patch = patch + 1
    new_version = f"{major}.{minor}.{new_patch}"

    # Update toppreise.user.js
    new_content = re.sub(
        r'(//\s*@version\s+)\d+\.\d+\.\d+',
        rf'\g<1>{new_version}',
        content
    )
    with open(SCRIPT_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    subprocess.run(['git', 'add', SCRIPT_FILE], check=True)

    # Update README.md installation link if present
    if os.path.exists(README_FILE):
        with open(README_FILE, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        new_readme = re.sub(
            r'\(v\d+\.\d+\.\d+\)',
            f'(v{new_version})',
            readme_content
        )
        if new_readme != readme_content:
            with open(README_FILE, 'w', encoding='utf-8') as f:
                f.write(new_readme)
            subprocess.run(['git', 'add', README_FILE], check=True)

    print(f"🚀 [pre-commit] Auto-bumped Toppreise Suite to v{new_version}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
