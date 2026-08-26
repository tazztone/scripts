# Userscripts Agent Guidelines

## Testing & Verification

- Run userscript end-to-end browser tests using the shared virtualenv:
  ```bash
  userscripts/venv/bin/pytest userscripts/
  ```
- Verify JavaScript syntax before committing:
  ```bash
  node --check userscripts/<project>/<name>.user.js
  ```

## Versioning & Git Commits

- Do not manually increment userscript patch `@version` headers for routine changes; the `.git/hooks/pre-commit` hook (`userscripts/bump_version_precommit.py`) automatically increments patch numbers on staged `*.user.js` files and synchronizes adjacent `README.md` install links.
- When committing changes touching userscripts, ensure write access is permitted for pre-commit hook execution.
