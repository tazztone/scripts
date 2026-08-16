#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/stage_media.py"

# If no arguments are passed, stage with --clean and --open
if [ $# -eq 0 ]; then
    python3 "${PYTHON_SCRIPT}" --clean --open
else
    python3 "${PYTHON_SCRIPT}" "$@"
fi
