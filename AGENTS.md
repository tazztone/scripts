# Agent Guidelines

## Testing & Verification

- Run all test suites (Python + Userscripts) using the workspace virtualenv:
  ```bash
  userscripts/venv/bin/pytest
  ```
- Run only userscript end-to-end tests:
  ```bash
  userscripts/venv/bin/pytest userscripts/
  ```
- Run only Python tests:
  ```bash
  userscripts/venv/bin/pytest python/
  ```
- Verify userscript JavaScript syntax before committing:
  ```bash
  node --check userscripts/<project>/<name>.user.js
  ```

## Versioning & Git Commits

- Do not manually increment userscript patch `@version` headers for routine changes; the `.git/hooks/pre-commit` hook (`userscripts/bump_version_precommit.py`) automatically increments patch numbers on staged `*.user.js` files and synchronizes adjacent `README.md` install links.
- When committing changes touching userscripts, ensure write access is permitted for pre-commit hook execution.
