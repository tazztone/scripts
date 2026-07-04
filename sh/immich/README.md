# Immich Scripts

This directory contains utility scripts for managing and maintaining an [Immich](https://immich.app/) installation.

## Scripts

### `update.sh`
An interactive bash script to safely update your Immich instance. 

**Features:**
- Automatically checks for the absolute latest version tag from the GitHub releases API to use as the default update target.
- Prompts you to pin or update the `IMMICH_VERSION` inside your `.env` file.
- Contains safety checks to detect breaking changes (such as the v2 to v3 migration and deprecated `pgvecto.rs` / ML environment variables).
- Runs `docker compose pull` and `docker compose up -d --remove-orphans` to apply the update cleanly.
- Optionally prunes unused Docker images after the update completes to save disk space.
- Designed with clear terminal status indicators so interactive prompts don't get swallowed by Docker's output bars.

**Usage:**
```bash
./update.sh
```
*Note: This script assumes it is placed in (or run from) the directory containing your Immich `docker-compose.yml` and `.env` files.*
