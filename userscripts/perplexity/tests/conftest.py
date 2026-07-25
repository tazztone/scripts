import os
from pathlib import Path


# Keep the large, machine-specific Playwright browser download local to this
# repository while leaving it ignored by git.
os.environ.setdefault(
    'PLAYWRIGHT_BROWSERS_PATH',
    str(Path(__file__).resolve().parents[2] / '.playwright-browsers'),
)
