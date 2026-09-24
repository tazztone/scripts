#!/usr/bin/env bash
# Signal Stickers Convenience Runner
# Automatically locates .venv and runs classification, deduplication, or review.

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"

# Locate Python in workspace .venv or fall back to python3
if [ -f "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
elif [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON="$(command -v python)"
else
    echo "Error: Python 3 not found." >&2
    exit 1
fi

ACTION="${1:-review}"
FOLDER="${2:-$DIR/webp}"

case "$ACTION" in
    curate|review)
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --scan >/dev/null 2>&1 || true
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        HTML_PATH="$FOLDER/review.html"
        if [ ! -f "$HTML_PATH" ]; then
            HTML_PATH="$DIR/review.html"
        fi
        echo "Curation/Review ready: file://$HTML_PATH"
        if command -v xdg-open >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
            xdg-open "$HTML_PATH" 2>/dev/null &
        fi
        ;;
    scan|check)
        shift 1 || true
        if [ -n "$1" ] && [ -d "$1" ]; then
            FOLDER="$1"
            shift 1
        fi
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --scan "$@"
        ;;
    tag|classify)
        shift 1 || true
        if [ -n "$1" ] && [ -d "$1" ]; then
            FOLDER="$1"
            shift 1
        fi
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --classify-kept "$@"
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        ;;
    export)
        shift 1 || true
        if [ -n "$1" ] && [ -d "$1" ]; then
            FOLDER="$1"
            shift 1
        fi
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --build-yaml "$@"
        ;;
    dedupe)
        shift 1 || true
        if [ -n "$1" ] && [ -d "$1" ]; then
            FOLDER="$1"
            shift 1
        fi
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --scan "$@"
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        ;;
    upload)
        shift 1 || true
        export PATH="$REPO_ROOT/.venv/bin:$PATH"
        cd "$FOLDER" && signal-sticker-tool upload "$@"
        ;;
    preview)
        shift 1 || true
        export PATH="$REPO_ROOT/.venv/bin:$PATH"
        cd "$FOLDER" && signal-sticker-tool preview "$@"
        ;;
    help|--help|-h)
        echo "Signal Sticker Pack Curation & Build Helper"
        echo ""
        echo "Usage: ./stickers [action] [options]"
        echo ""
        echo "Curation Workflow:"
        echo "  ./stickers scan       Inventory images, check constraints & detect visual clusters"
        echo "  ./stickers curate     (default) Open visual cluster review to pick best variations"
        echo "  ./stickers tag        Run VLM emoji suggestions ONLY on kept stickers"
        echo "  ./stickers review     Review tags, verify contrast & edit emojis"
        echo "  ./stickers export     Compile stickers.yaml from approved kept stickers"
        echo "  ./stickers preview    Preview sticker pack with signal-sticker-tool"
        echo "  ./stickers upload     Upload encrypted pack to Signal"
        ;;
    *)
        # If user passes custom args directly like ./run.sh ./webp --dedupe
        "$PYTHON" "$DIR/classify_and_build.py" "$@"
        ;;
esac
