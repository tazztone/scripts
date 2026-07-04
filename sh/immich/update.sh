#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required" >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose (Compose v2) is required" >&2
  exit 1
fi

echo "Immich update (docs-style)"
echo
echo "Reminder: do your DB backup in the Immich GUI first."
echo "Docs: https://docs.immich.app/administration/backup-and-restore/"
echo

read -r -p "Continue with docker compose pull && up -d? (y/n) [y]: " ok
ok="${ok:-y}"
[[ "${ok,,}" == "y" || "${ok,,}" == "yes" ]] || exit 0

if [[ -f ".env" ]]; then
  current="$(grep -E '^[[:space:]]*IMMICH_VERSION=' .env | tail -n 1 | cut -d= -f2- || true)"
  current="${current:-release}"
  read -r -p "Change IMMICH_VERSION in .env? Current='$current' (y/n) [n]: " ch
  ch="${ch:-n}"
  if [[ "${ch,,}" == "y" || "${ch,,}" == "yes" ]]; then
    echo "Fetching latest version from GitHub..."
    latest="$(curl -s https://api.github.com/repos/immich-app/immich/releases/latest | grep -oE '"tag_name": *"[^"]+"' | head -n1 | cut -d'"' -f4)"
    default_target="${latest:-$current}"
    read -r -p "Enter target IMMICH_VERSION (e.g. v3, v3.1.0) [$default_target]: " target
    target="${target:-$default_target}"
    echo
    echo "WARNING: Immich docs say downgrades are not supported."
    echo "Target: $target"
    read -r -p "Proceed to set IMMICH_VERSION=$target ? (y/n) [y]: " setok
    setok="${setok:-y}"
    [[ "${setok,,}" == "y" || "${setok,,}" == "yes" ]] || exit 0

    if [[ "$target" == v3* ]]; then
      if grep -qE '^(DB_VECTOR_EXTENSION=pgvecto\.rs|IMMICH_MACHINE_LEARNING_PING_TIMEOUT|MACHINE_LEARNING_PRELOAD__CLIP|MACHINE_LEARNING_PRELOAD__FACIAL_RECOGNITION)' .env; then
        echo
        echo "WARNING: Deprecated v2 environment variables detected in .env!"
        echo "Immich v3 has breaking changes. Please review the migration guide:"
        echo "https://immich.app/blog/v3-migration"
        read -r -p "Are you sure you want to proceed? (y/n) [n]: " v3ok
        v3ok="${v3ok:-n}"
        [[ "${v3ok,,}" == "y" || "${v3ok,,}" == "yes" ]] || exit 0
      fi
    fi

    if grep -qE '^[[:space:]]*IMMICH_VERSION=' .env; then
      sed -i "s/^[[:space:]]*IMMICH_VERSION=.*/IMMICH_VERSION=$target/" .env
    else
      printf "\nIMMICH_VERSION=%s\n" "$target" >> .env
    fi
  fi
else
  echo "NOTE: .env not found; skipping IMMICH_VERSION pinning."
fi

echo
echo "Pulling Docker images..."
docker compose pull

echo
echo "Starting containers in the background..."
docker compose up -d --remove-orphans

echo
read -r -p "Prune unused Docker images? (y/n) [n]: " prune
prune="${prune:-n}"
if [[ "${prune,,}" == "y" || "${prune,,}" == "yes" ]]; then
  docker image prune -f
fi

echo "Done."
