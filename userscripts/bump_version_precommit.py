#!/usr/bin/env python3
"""Universal pre-commit hook: Auto-bumps patch versions for any staged userscripts (*.user.js) and syncs their adjacent README.md files."""

import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bump_version_string(match):
    prefix = match.group(1)
    major = match.group(2)
    minor = match.group(3)
    patch = int(match.group(4)) + 1
    new_ver = f"{major}.{minor}.{patch}"
    return f"{prefix}{new_ver}", new_ver


def process_script(script_relpath):
    script_abspath = os.path.join(REPO_ROOT, script_relpath)
    if not os.path.exists(script_abspath):
        return

    # Skip reference or template example scripts
    if 'references' in script_relpath.split(os.sep) or 'example' in os.path.basename(script_relpath):
        return

    with open(script_abspath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match standard userscript @version (e.g. // @version 1.2.3)
    pattern = r'(//\s*@version\s+)(\d+)\.(\d+)\.(\d+)'
    match = re.search(pattern, content)
    if not match:
        return

    new_content, new_version = re.subn(
        pattern,
        lambda m: f"{m.group(1)}{m.group(2)}.{m.group(3)}.{int(m.group(4)) + 1}",
        content,
        count=1
    )
    extracted_version = f"{match.group(2)}.{match.group(3)}.{int(match.group(4)) + 1}"

    with open(script_abspath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    subprocess.run(['git', 'add', script_abspath], check=True)

    # Sync adjacent README.md in the same directory if it exists
    script_dir = os.path.dirname(script_abspath)
    readme_path = os.path.join(script_dir, 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        new_readme = re.sub(
            r'\(v\d+\.\d+\.\d+\)',
            f'(v{extracted_version})',
            readme_content
        )
        if new_readme != readme_content:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(new_readme)
            subprocess.run(['git', 'add', readme_path], check=True)

    script_name = os.path.basename(script_relpath)
    print(f"🚀 [pre-commit] Auto-bumped {script_name} to v{extracted_version}")


def main():
    try:
        staged_files = subprocess.check_output(
            ['git', 'diff', '--cached', '--name-only'],
            text=True
        ).splitlines()
    except subprocess.CalledProcessError:
        return 0

    staged_userscripts = [
        path for path in staged_files
        if path.endswith('.user.js') and path.startswith('userscripts/')
    ]

    for script_path in staged_userscripts:
        process_script(script_path)

    return 0


if __name__ == '__main__':
    sys.exit(main())
