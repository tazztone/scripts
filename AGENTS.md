# Agent Guidelines

## Testing & Verification

> [!IMPORTANT]
> **Prefer targeted testing!** Do **NOT** run the full `userscripts/venv/bin/pytest python/ userscripts/` command unless strictly necessary (e.g. explicitly requested by the user), as running the entire suite is slow (~35–45s). Always run the most specific/targeted test command for the area you are working on.

- **Default (Fast Python Unit Tests — ~90ms):**
  ```bash
  userscripts/venv/bin/pytest python/
  ```

- **Targeted Userscript Playwright Tests (Fast & Specific):**
  ```bash
  userscripts/venv/bin/pytest userscripts/<script_folder>/tests/test_userscript.py
  ```
  *Example for Toppreise:*
  ```bash
  userscripts/venv/bin/pytest userscripts/toppreise/tests/test_userscript.py
  ```

- **All Userscript Playwright Tests (~25s):**
  ```bash
  userscripts/venv/bin/pytest userscripts/
  ```

- **Full Suite (Slow — run only when explicitly necessary):**
  ```bash
  userscripts/venv/bin/pytest python/ userscripts/
  ```
