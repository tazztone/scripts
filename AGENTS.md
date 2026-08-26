# Agent Guidelines

## Testing & Verification

- Run all test suites (Python + Userscripts) using the workspace virtualenv:
  ```bash
  userscripts/venv/bin/pytest
  ```
- Run only Python tests:
  ```bash
  userscripts/venv/bin/pytest python/
  ```
- Run only Userscript tests:
  ```bash
  userscripts/venv/bin/pytest userscripts/
  ```
