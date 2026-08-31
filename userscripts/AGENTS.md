# Userscripts Agent Guidelines

## Testing & Verification

- **Playwright E2E Suite:**
  ```bash
  userscripts/venv/bin/pytest userscripts/
  ```
- **Syntax Validation:**
  ```bash
  node --check userscripts/<project>/<name>.user.js
  ```

## Development & Mock Testing Patterns

- **AJAX Absolute URL Fallback:**
  Always construct userscript `fetch()` URLs with an origin fallback so requests don't fail with `Failed to fetch` on `file://` Playwright test pages:
  ```javascript
  const baseUrl = (location.origin && location.origin.startsWith('http')) ? location.origin : 'https://www.target-domain.com';
  const url = `${baseUrl}/endpoint`;
  ```
- **Playwright Mock Route CORS:**
  Always pass `headers={'access-control-allow-origin': '*'}` in `route.fulfill(...)` when intercepting userscript network calls from `file://` test origins.
- **Styled Switch Assertions:**
  Zero-opacity `<input type="checkbox">` elements inside custom toggle switches fail `is_visible()`. Assert state with `locator('input').is_checked()` and trigger clicks on the visible `.tp-slider` label.
- **Defensive Shadow DOM Binding:**
  Helper functions attaching event listeners to dual/linked inputs (e.g. range + number input) must null-check elements before binding to keep modal initialization resilient against template changes.

## Versioning & Git Commits

- **Automatic Patch Bumping:** `.git/hooks/pre-commit` (`userscripts/bump_version_precommit.py`) automatically increments `@version` patch numbers on staged `*.user.js` files and syncs adjacent `README.md` install links. Do not manually bump patch versions for routine commits.
- **Pre-commit Write Permission:** Commits touching userscripts require write access (`BypassSandbox: true`) so the auto-bump hook can update the staged script and `README.md`.


