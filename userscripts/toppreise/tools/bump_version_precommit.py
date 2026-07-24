#!/usr/bin/env python3
"""
Pre-commit hook tool to automatically increment the patch version (@version X.Y.Z)
for any staged .user.js files before a commit completes.
"""

import subprocess
import re
import sys
from pathlib import Path

def get_staged_userscripts():
    try:
        res = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True,
            text=True,
            check=True
        )
        files = res.stdout.strip().splitlines()
        return [f for f in files if f.endswith('.user.js') and not f.endswith('example.user.js')]
    except Exception as e:
        print(f"⚠️ Error checking staged files: {e}")
        return []

def bump_version_in_file(filepath):
    path = Path(filepath)
    if not path.exists():
        return False

    content = path.read_text(encoding='utf-8')
    match = re.search(r'^(//\s*@version\s+)(\d+\.\d+\.)(\d+)', content, re.MULTILINE)
    
    if not match:
        # Try two-part version (e.g. 1.0 -> 1.0.1)
        match_two = re.search(r'^(//\s*@version\s+)(\d+\.\d+)(\s*)$', content, re.MULTILINE)
        if match_two:
            new_version = f"{match_two.group(2)}.1"
            new_content = content[:match_two.start(2)] + new_version + content[match_two.end(2):]
            path.write_text(new_content, encoding='utf-8')
            subprocess.run(['git', 'add', filepath], check=True)
            print(f"🚀 Auto-bumped {filepath} @version to {new_version}")
            return True
        return False

    prefix = match.group(1)
    major_minor = match.group(2)
    patch = int(match.group(3)) + 1
    new_version_str = f"{prefix}{major_minor}{patch}"
    
    new_content = content[:match.start()] + new_version_str + content[match.end():]
    path.write_text(new_content, encoding='utf-8')
    
    # Re-stage the modified userscript
    subprocess.run(['git', 'add', filepath], check=True)
    print(f"🚀 Auto-bumped {filepath} @version to {major_minor}{patch}")
    return True

def main():
    staged_scripts = get_staged_userscripts()
    if not staged_scripts:
        sys.exit(0)

    for script in staged_scripts:
        bump_version_in_file(script)

    sys.exit(0)

if __name__ == '__main__':
    main()
