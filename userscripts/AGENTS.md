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

## Development & Mock Testing Patterns

- **Relative AJAX URLs & `file://` Test Fallbacks:**
  When executing background AJAX `fetch()` calls in userscripts, avoid relative paths like `/endpoint` directly because tests loading `file:///.../mock.html` will fail with `Failed to fetch`. Always construct URLs using a base URL fallback:
  ```javascript
  const baseUrl = (location.origin && location.origin.startsWith('http')) ? location.origin : 'https://www.target-domain.com';
  const url = `${baseUrl}/path/to/endpoint`;
  ```
- **Playwright Network Route Interception & CORS:**
  When mocking network requests in Playwright via `page.route()`, requests from `file://` origins fail CORS unless explicit headers are provided:
  ```python
  route.fulfill(status=200, headers={'access-control-allow-origin': '*'}, body=...)
  ```
- **Custom Switches & Hidden Checkbox Assertions:**
  Custom styled toggles (e.g. `<label class="tp-switch"><input type="checkbox">...`) style `<input>` with `opacity: 0` or 0px width. In Playwright, `locator('input').is_visible()` will return `False`. Use `locator('input').is_checked()` for state verification and click the visible slider label (`.tp-slider`) to trigger toggle actions.
- **Defensive Element Binding in Shadow DOM Modals:**
  Ensure helper functions that bind dual controls (e.g. range + number input) check for null elements before attaching listeners so partial DOM updates or missing nodes do not break modal initialization.

## Versioning & Git Commits

- Do not manually increment userscript patch `@version` headers for routine changes; the `.git/hooks/pre-commit` hook (`userscripts/bump_version_precommit.py`) automatically increments patch numbers on staged `*.user.js` files and synchronizes adjacent `README.md` install links.
- When committing changes touching userscripts, ensure write access is permitted for pre-commit hook execution.

