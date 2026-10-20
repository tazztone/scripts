# Agent Guidelines

## Testing & Verification

- **Fast Python Unit Tests (~90ms):**
  ```bash
  .venv/bin/pytest python/
  ```

- **Shell Toolbox Tests (Legacy):**
  > [!NOTE]
  > `sh/TOOLBOXES` is the legacy Bash/Zenity suite superseded by `python/media_toolbox` (dedicated repository: [`tazztone/media-toolbox`](https://github.com/tazztone/media-toolbox)).
  ```bash
  cd sh/TOOLBOXES
  bash testing/test_cross_version.sh
  bash testing/test_runner.sh
  ```

- **Shell Script Linting & Local Git Hook:**
  Local pre-commit hook runs `bash -n` and `shellcheck` (via PATH or `.venv/bin/shellcheck`):
  ```bash
  git config core.hooksPath .githooks
  .githooks/pre-commit
  ```

---

## Repository Scope

> [!NOTE]
> - **Userscripts:** Browser userscripts have been migrated to their own dedicated repository:
>   [`tazztone/userscripts`](https://github.com/tazztone/userscripts) (local: `/home/tazztone/_coding/userscripts`).
> - **Media Toolbox:** Modern media processing has been published as a dedicated repository:
>   [`tazztone/media-toolbox`](https://github.com/tazztone/media-toolbox) (local: `/home/tazztone/_coding/media-toolbox`), superseding the legacy `sh/TOOLBOXES`.
