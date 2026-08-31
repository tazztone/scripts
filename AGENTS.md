# Agent Guidelines

## Testing & Verification

- **Default (Fast Python Unit Tests — ~90ms):**
  ```bash
  userscripts/venv/bin/pytest
  ```
  *(or explicitly: `userscripts/venv/bin/pytest python/`)*

- **Userscripts Playwright E2E Browser Tests (~25s):**
  ```bash
  userscripts/venv/bin/pytest userscripts/
  ```

- **Run Both Suites:**
  ```bash
  userscripts/venv/bin/pytest python/ userscripts/
  ```
