#!/usr/bin/env bash
# ==============================================================================
# Media Toolbox — Nautilus User Scripts Launcher
# Installed to: ~/.local/share/nautilus/scripts/Media-Toolbox
# ==============================================================================
set -euo pipefail

# 1. Parse selected files from Nautilus environment or positional arguments
declare -a FILES=()

if [[ -n "${NAUTILUS_SCRIPT_SELECTED_FILE_PATHS:-}" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" ]] && continue
        FILES+=("$line")
    done <<< "$NAUTILUS_SCRIPT_SELECTED_FILE_PATHS"
elif [[ $# -gt 0 ]]; then
    FILES=("$@")
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "Error: No files selected or provided to Media Toolbox." >&2
    if command -v notify-send >/dev/null 2>&1; then
        notify-send --urgency=low "Media Toolbox" "No files selected or provided."
    fi
    exit 1
fi

# 2. Locate Python 3 interpreter
PYTHON=""

# (a) Explicit override
if [[ -n "${MEDIA_TOOLBOX_PYTHON:-}" && -x "$MEDIA_TOOLBOX_PYTHON" ]]; then
    PYTHON="$MEDIA_TOOLBOX_PYTHON"
fi

# (b) Resolve relative to script location
if [[ -z "$PYTHON" ]]; then
    SCRIPT_PATH="$(readlink -f -- "$0" 2>/dev/null || realpath -- "$0" 2>/dev/null || echo "$0")"
    SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_PATH")" >/dev/null 2>&1 && pwd)"
    REPO_ROOT="$(cd -- "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd)"
    if [[ -x "$REPO_ROOT/.venv/bin/python3" ]]; then
        PYTHON="$REPO_ROOT/.venv/bin/python3"
    fi
fi

# (c) Active virtualenv
if [[ -z "$PYTHON" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python3" ]]; then
    PYTHON="$VIRTUAL_ENV/bin/python3"
fi

# (d) Well-known virtualenv paths
if [[ -z "$PYTHON" ]]; then
    for candidate in \
        "/home/tazztone/_coding/scripts/.venv/bin/python3" \
        "$HOME/.local/share/media_toolbox/venv/bin/python3" \
        "$HOME/.venv/bin/python3"; do
        if [[ -x "$candidate" ]]; then
            PYTHON="$candidate"
            break
        fi
    done
fi

# (e) System fallback
if [[ -z "$PYTHON" ]]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
        PYTHON="$(command -v python)"
    fi
fi

if [[ -z "$PYTHON" ]]; then
    echo "Error: Python 3 interpreter could not be found." >&2
    if command -v notify-send >/dev/null 2>&1; then
        notify-send --urgency=critical "Media Toolbox" "Python 3 interpreter could not be found."
    fi
    exit 1
fi

# 3. Ensure media_toolbox module is in PYTHONPATH
SCRIPT_PATH="$(readlink -f -- "$0" 2>/dev/null || realpath -- "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_PATH")" >/dev/null 2>&1 && pwd)"
REPO_PYTHON="$(cd -- "$SCRIPT_DIR/../.." >/dev/null 2>&1 && pwd)"
if [[ -f "$REPO_PYTHON/media_toolbox/__init__.py" ]]; then
    export PYTHONPATH="$REPO_PYTHON${PYTHONPATH:+:$PYTHONPATH}"
else
    WELL_KNOWN_PYTHON="/home/tazztone/_coding/scripts/python"
    if [[ -f "$WELL_KNOWN_PYTHON/media_toolbox/__init__.py" ]]; then
        export PYTHONPATH="$WELL_KNOWN_PYTHON${PYTHONPATH:+:$PYTHONPATH}"
    fi
fi

# 4. Dispatch execution
if [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
    # Graphical environment: launch GUI detached
    nohup "$PYTHON" -m media_toolbox.ui.app "${FILES[@]}" >/dev/null 2>&1 &
    exit 0
else
    # Terminal / headless fallback: run CLI
    exec "$PYTHON" -m media_toolbox.cli "${FILES[@]}"
fi
