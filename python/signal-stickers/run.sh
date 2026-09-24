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
    review)
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        HTML_PATH="$FOLDER/review.html"
        if [ ! -f "$HTML_PATH" ]; then
            HTML_PATH="$DIR/review.html"
        fi
        echo "Review ready: file://$HTML_PATH"
        if command -v xdg-open >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
            xdg-open "$HTML_PATH" 2>/dev/null &
        fi
        ;;
    dedupe)
        shift 1 || true
        # If second arg is a folder, use it; otherwise default to ./webp
        if [ -n "$1" ] && [ -d "$1" ]; then
            FOLDER="$1"
            shift 1
        fi
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --dedupe "$@"
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        ;;
    classify)
        shift 1 || true
        if [ -n "$1" ] && [ -d "$1" ]; then
            FOLDER="$1"
            shift 1
        fi
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" "$@"
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        ;;
    check)
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --check-only
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
        echo "Signal Sticker Pack Helper"
        echo ""
        echo "Usage: ./run.sh [action] [options]"
        echo ""
        echo "Quick Actions:"
        echo "  ./run.sh review       (default) Generate review.html and open in browser"
        echo "  ./run.sh dedupe       Run VLM comparative deduplication on duplicate groups"
        echo "  ./run.sh classify     Classify any unclassified sticker images in ./webp"
        echo "  ./run.sh check        Check constraints and detect near-duplicate frames"
        echo "  ./run.sh preview      Preview pack with signal-sticker-tool"
        echo "  ./run.sh upload       Upload encrypted pack to Signal"
        ;;
    *)
        # If user passes custom args directly like ./run.sh ./webp --dedupe
        "$PYTHON" "$DIR/classify_and_build.py" "$@"
        ;;
esac
