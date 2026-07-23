#!/usr/bin/env python3
"""
Toppreise.ch Suite - Userscript Auto-Installer & Launcher Tool
Triggers your browser (Brave/Chrome/Firefox) with a cache-busted, commit-pinned raw URL
so Violentmonkey/Tampermonkey immediately opens the Update/Install dialog for v2.5.0.
"""

import subprocess
import sys
import webbrowser
from pathlib import Path

def get_git_commit_hash():
    try:
        res = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception:
        return 'main'

def main():
    commit_hash = get_git_commit_hash()
    raw_url = f"https://raw.githubusercontent.com/tazztone/scripts/{commit_hash}/userscripts/toppreise/toppreise.user.js"

    print("=" * 60)
    print("🚀 TOPPREISE USERSCRIPT INSTANT INSTALLER")
    print("=" * 60)
    print(f"📌 Latest Commit Hash: {commit_hash}")
    print(f"🔗 Target Install URL: {raw_url}")
    print("=" * 60)
    print("Opening URL in your default browser to trigger Violentmonkey / Tampermonkey...")
    
    try:
        webbrowser.open(raw_url)
        print("✅ Browser tab opened! Violentmonkey / Tampermonkey will prompt you to update.")
    except Exception as e:
        print(f"❌ Failed to open browser automatically: {e}")
        print(f"👉 Please open this URL manually in your browser:\n{raw_url}")

if __name__ == '__main__':
    main()
