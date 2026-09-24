# Agent Guidelines

## Testing & Verification

> [!IMPORTANT]
> **Prefer targeted testing!** Do **NOT** run the full `userscripts/venv/bin/pytest python/ userscripts/` command unless strictly necessary (e.g. explicitly requested by the user), as running the entire suite is slow (~35–45s). Always run the most specific/targeted test command for the area you are working on.

- **Default (Fast Python Unit Tests — ~90ms):**
  ```bash
  userscripts/venv/bin/pytest python/
  ```

- **Targeted Userscript Playwright Tests:**
  > [!NOTE]
  > Since system Google Chrome is not installed at `/opt/google/chrome/chrome`, pass `PLAYWRIGHT_BROWSERS_PATH` and override `addopts` to use Playwright's local Chromium:
  ```bash
  PLAYWRIGHT_BROWSERS_PATH=/home/tazztone/_coding/scripts/userscripts/.playwright-browsers userscripts/venv/bin/pytest userscripts/<script_folder>/tests/<test_file>.py -o addopts="--import-mode=importlib"
  ```
  *Examples for Toppreise:*
  ```bash
  # Modal & settings interactions
  PLAYWRIGHT_BROWSERS_PATH=/home/tazztone/_coding/scripts/userscripts/.playwright-browsers userscripts/venv/bin/pytest userscripts/toppreise/tests/test_ui_modal.py -o addopts="--import-mode=importlib"

  # Feed scanner & deal scoring
  PLAYWRIGHT_BROWSERS_PATH=/home/tazztone/_coding/scripts/userscripts/.playwright-browsers userscripts/venv/bin/pytest userscripts/toppreise/tests/test_feed_scanner.py -o addopts="--import-mode=importlib"

  # Fast price logic & unit tests
  PLAYWRIGHT_BROWSERS_PATH=/home/tazztone/_coding/scripts/userscripts/.playwright-browsers userscripts/venv/bin/pytest userscripts/toppreise/tests/test_price_logic.py userscripts/toppreise/tests/unit/ -o addopts="--import-mode=importlib"
  ```

- **All Userscript Playwright Tests (~25s):**
  ```bash
  PLAYWRIGHT_BROWSERS_PATH=/home/tazztone/_coding/scripts/userscripts/.playwright-browsers userscripts/venv/bin/pytest userscripts/ -o addopts="--import-mode=importlib"
  ```

- **Full Suite (Slow — run only when explicitly necessary):**
  ```bash
  userscripts/venv/bin/pytest python/ userscripts/
  ```

---

## Userscript Bundling & Development

- **Building Bundles:**
  When editing modular code in `userscripts/<script>/src/`, compile the bundled artifact before testing or committing:
  ```bash
  node userscripts/<script>/tools/build.js
  ```
- **Verifying Bundles (CI Quality Check):**
  ```bash
  node userscripts/<script>/tools/build.js --check
  ```
- **Pre-commit Quality Gates:**
  The repository pre-commit hooks execute unit test suites and taxonomy verification, and will automatically bump the bundle version patch level upon commit.
  > [!NOTE]
  > When executing `git commit` via agent commands, `BypassSandbox: true` is required to allow write access to `.git/index.lock` and permit the pre-commit script to update bundle versions.

---

## Userscript UI/UX & Architecture Invariants

- **No Redundant Controls:** Avoid duplicating controls that are already directly accessible in the top filter bar (such as negative terms or min-offers steppers) inside the settings modal.
- **Single-Page Visibility over Tabs:** Keep settings modals on a single scrollable page with colored section groupings rather than multi-tab layouts that conceal options.
- **Continuous Scales:** When rendering heatmaps or relative price differences, prefer a continuous scale (e.g., $-100\%$ hot to $+100\%$ cold with neutral parity at $0\%$) over fragmented discrete tiers.
- **Feature Graduation:** When moving a feature out of Beta, sweep across `README.md`, UI strings, comments, and test names (`_beta_`) to keep terminology consistent.
- **Test & Scratch Hygiene:** Never leave empty or untracked placeholder files in test suites (e.g., `tests/unit/`). Place exploratory scripts in `scratch/`.

---

## Violentmonkey & Firefox Testing

- **Branch Testing URLs:**
  When testing changes on a branch other than `main` (e.g. `testing`), ensure `@updateURL` and `@downloadURL` in `src/app.js` point to the raw GitHub branch URL.
- **Dispatching Updates to Firefox:**
  To prompt Violentmonkey to install or update the script in Firefox:
  ```bash
  firefox "https://raw.githubusercontent.com/tazztone/scripts/<branch>/userscripts/<script>/<script>.user.js"
  ```
