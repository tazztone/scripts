# Agent Guidelines

## Testing & Verification

- **Fast Python Unit Tests (~90ms):**
  ```bash
  .venv/bin/pytest python/
  ```

- **Shell Toolbox Tests:**
  ```bash
  cd sh/TOOLBOXES
  bash testing/test_cross_version.sh
  bash testing/test_runner.sh
  ```

---

## Repository Scope

> [!NOTE]
> Browser userscripts have been migrated to their own dedicated repository:
> [`tazztone/userscripts`](https://github.com/tazztone/userscripts) (local: `/home/tazztone/_coding/userscripts`).
> For all userscript development, bundling, and testing, please refer to the `AGENTS.md` in that repository.
