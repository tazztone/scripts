#!/usr/bin/env bash
# Signal Stickers Convenience Runner (OpenRouter-only, explicit folder)
#
# Canonical invocations:
#   python/signal-stickers/stickers <action> <folder> [options]   # from repo root
#   cd python/signal-stickers && ./stickers <action> <folder>     # inside the module
#
# ./run.sh is identical; both work (stickers is a symlink to run.sh).

set -e

_src="${BASH_SOURCE[0]}"
while [ -L "$_src" ]; do
    _dir="$(cd -P "$(dirname "$_src")" >/dev/null 2>&1 && pwd)"
    _src="$(readlink "$_src")"
    case "$_src" in
        /*) ;;
        *) _src="$_dir/$_src" ;;
    esac
done
DIR="$(cd -P "$(dirname "$_src")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"

PYTHON=""
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

export PATH="$REPO_ROOT/.venv/bin:$DIR/.venv/bin:$PATH"

die() { echo "Error: $*" >&2; exit 1; }
note() { echo "$*"; }

require_folder() {
    [ -n "${FOLDER:-}" ] || die "A pack folder is required. Example: ./stickers scan ./my_pack"
    [ -d "$FOLDER" ] || die "Pack folder '$FOLDER' does not exist. Pass an explicit existing folder."
}

require_sticker_tool() {
    if ! command -v signal-sticker-tool >/dev/null 2>&1; then
        cat >&2 <<EOF
Error: 'signal-sticker-tool' is not installed, so packs cannot be previewed or uploaded.

Install the upload tooling with:

    $PYTHON -m pip install -r $DIR/requirements-upload.txt

(Core scan/curate/tag/export only needs: $PYTHON -m pip install -r $DIR/requirements.txt)
EOF
        exit 1
    fi
}

open_url() {
    local target="$1"
    echo "Manual open: $target"
    if command -v xdg-open >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
        xdg-open "$target" >/dev/null 2>&1 &
    elif command -v open >/dev/null 2>&1; then
        open "$target" >/dev/null 2>&1 &
    elif command -v powershell.exe >/dev/null 2>&1; then
        powershell.exe -NoProfile -Command Start-Process "$target" >/dev/null 2>&1 &
    fi
    return 0
}

usage() {
    cat <<EOF
Signal Sticker Pack Curation & Build Helper (OpenRouter-only)

Canonical use:
  python/signal-stickers/stickers <action> <folder> [options]   # from repo root
  cd python/signal-stickers && ./stickers <action> <folder>

A pack <folder> is required for scan/curate/tag/review/export/preview/upload/approve.
With no arguments this help is shown (nothing runs implicitly).

Workflow (in order):
  scan       Inventory images, hard-gate check, group visually similar candidates
  curate     scan + build review page (add --serve for loopback direct-save)
  tag        OpenRouter suggestions for kept stickers lacking a final emoji
  review     Rebuild the review page only (add --serve for direct-save)
  approve    Human approval gate for the current revision (no threshold bypass)
  export     Strict preflight + write stickers.yaml + build receipt
  preview    Re-verify receipt + render locally with signal-sticker-tool
  upload     Re-verify + confirm + upload (use --yes noninteractively)

Utilities:
  doctor [<folder>]   Core env check; with a folder also runs pack preflight.
  preflight <folder>  Strict export/upload preflight only.
  help       Show this message.

Options:
  --model    <slug>   OpenRouter model (default inclusionai/ling-3.0-flash-vl)
  --title    <text>   Explicit pack title (required before approve)
  --author   <text>   Explicit pack author (required before approve)
  --cover    <file>   Cover filename (defaults to first kept sticker)
  --workers  <n>      Parallel suggestions (default 4)
  --serve             curate/review: loopback save server (127.0.0.1 + token)
  --yes               upload: skip interactive confirmation
  --prune             scan: explicitly drop draft entries for missing files
  --cluster-distance <n>  dHash edge threshold (default 6)
  --linkage single|complete (default single)
  --strict-quality    Promote quality recommendations to errors

Examples:
  python/signal-stickers/stickers scan ./my_pack
  python/signal-stickers/stickers curate ./my_pack --serve
  python/signal-stickers/stickers tag ./my_pack
  python/signal-stickers/stickers approve ./my_pack --title "My Pack" --author "me"
  python/signal-stickers/stickers export ./my_pack
  python/signal-stickers/stickers upload ./my_pack --yes
EOF
}

doctor() {
    local folder="${1:-}"
    local problems=0
    local warnings=0

    printf 'Signal Stickers environment check\n\n'
    note "  Python        $("$PYTHON" --version 2>&1)"
    note "  Interpreter   $PYTHON"
    if ! "$PYTHON" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1; then
        note "  Python        MISSING: need >= 3.9"
        problems=$((problems + 1))
    fi

    for mod in yaml PIL; do
        if "$PYTHON" -c "import $mod" >/dev/null 2>&1; then
            case "$mod" in
                yaml) note "  PyYAML        ok (required)" ;;
                PIL)  note "  Pillow        ok (required)" ;;
            esac
        else
            case "$mod" in
                yaml) note "  PyYAML        MISSING (required) -> $PYTHON -m pip install -r $DIR/requirements.txt" ;;
                PIL)  note "  Pillow        MISSING (required) -> $PYTHON -m pip install -r $DIR/requirements.txt" ;;
            esac
            problems=$((problems + 1))
        fi
    done

    if command -v signal-sticker-tool >/dev/null 2>&1; then
        note "  signal-sticker-tool  $(command -v signal-sticker-tool) (preview/upload only)"
    else
        note "  signal-sticker-tool  not installed (only needed for preview/upload)"
        note "                        $PYTHON -m pip install -r $DIR/requirements-upload.txt"
        warnings=$((warnings + 1))
    fi

    if [ -n "${OPENROUTER_API_KEY:-}" ]; then
        note "  OPENROUTER_API_KEY set (only needed for 'tag')"
    else
        note "  OPENROUTER_API_KEY not set (only needed for 'tag')"
        warnings=$((warnings + 1))
    fi


    if [ -z "$folder" ]; then
        echo
        if [ "$problems" -eq 0 ]; then
            note "Core checks passed. Pass a folder for pack checks: ./stickers doctor ./my_pack"
            return 0
        fi
        note "$problems core check(s) failing."
        return 1
    fi

    if [ ! -d "$folder" ]; then
        note "  Pack folder    $folder MISSING -> pass an explicit existing folder"
        return 1
    fi
    local count
    count="$(find "$folder" -maxdepth 1 -type f \( -iname '*.webp' -o -iname '*.png' -o -iname '*.apng' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.gif' -o -iname '*.bmp' \) 2>/dev/null | wc -l)"
    note "  Pack folder    $folder ($count image-like file(s))"
    for f in pack_draft.json stickers.yaml stickers.yaml.receipt.json; do
        if [ -f "$folder/$f" ]; then note "  $f present"; else note "  $f not generated yet"; fi
    done
    if [ -f "$folder/uploaded.yaml" ]; then
        note "  uploaded.yaml present (prior upload marker; verify before re-uploading)"
    fi

    echo
    note "Running pack preflight (schema/hash/manifest freshness)..."
    shift
    if "$PYTHON" "$DIR/classify_and_build.py" "$folder" --preflight "$@"; then
        note "Pack preflight passed."
    else
        note "Pack preflight FAILED (see above)."
        return 1
    fi

    if [ "$problems" -ne 0 ]; then return 1; fi
    if [ "$warnings" -ne 0 ]; then note "Core ok with $warnings optional warning(s)."; fi
    return 0
}

confirm_upload() {
    local has_yes=0
    for a in "${ARGS[@]}"; do [ "$a" = "--yes" ] && has_yes=1; done
    if [ -f "$FOLDER/uploaded.yaml" ]; then
        echo "Note: $FOLDER/uploaded.yaml exists from a prior upload. Re-uploading creates a NEW pack link." >&2
        if [ "$has_yes" -eq 0 ]; then
            printf 'Type YES to upload anyway (or re-run with --yes): ' >&2
            read -r ans || return 1
            [ "$ans" = "YES" ] || { echo "Aborted." >&2; return 1; }
        fi
        return 0
    fi
    if [ "$has_yes" -eq 1 ]; then return 0; fi
    printf 'Upload is irreversible on Signal. Type YES to continue: ' >&2
    read -r ans || return 1
    [ "$ans" = "YES" ] || { echo "Aborted." >&2; return 1; }
}

print_pack_summary() {
    "$PYTHON" - "$FOLDER" <<'PY'
import json, sys
from pathlib import Path
folder = Path(sys.argv[1])
try:
    import yaml
    doc = yaml.safe_load((folder / "stickers.yaml").read_text()) or {}
    meta = doc.get("meta", {}) or {}
    stickers = doc.get("stickers", []) or []
    print(f"Final pack: {meta.get('title')} by {meta.get('author')} — {len(stickers)} stickers, cover {meta.get('cover')}")
    try:
        receipt = json.loads((folder / "stickers.yaml.receipt.json").read_text())
        print(f"Manifest digest: {receipt.get('manifest_digest','')[:16]}  draft r{receipt.get('draft_revision')} {str(receipt.get('draft_digest',''))[:12]}")
    except Exception:
        pass
except Exception as e:
    print(f"(summary unavailable: {e})")
PY
}

FOLDER=""

shift_folder() {
    FOLDER=""
    if [ "${ARGS[0]:-}" != "--" ] && [ -n "${ARGS[0]:-}" ]; then
        case "${ARGS[0]}" in
            -*) ;;
            *)
                FOLDER="${ARGS[0]}"
                ARGS=("${ARGS[@]:1}")
                ;;
        esac
    fi
    return 0
}

if [ "$#" -eq 0 ]; then
    usage
    exit 0
fi

ACTION="${1:-help}"
shift || true
ARGS=("$@")

case "$ACTION" in
    doctor)
        shift_folder
        # shellcheck disable=SC2128
        doctor "${FOLDER:-}" "${ARGS[@]}" || exit 1
        ;;

    help|--help|-h)
        usage
        ;;

    scan|check)
        shift_folder
        require_folder
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --scan "${ARGS[@]}"
        ;;

    curate|review)
        shift_folder
        require_folder
        serve_flag=0
        scan_args=()
        skip_next=0
        for a in "${ARGS[@]}"; do
            if [ "$skip_next" -eq 1 ]; then skip_next=0; continue; fi
            case "$a" in
                --serve) serve_flag=1 ;;
                --port) serve_flag=1; skip_next=1 ;;
                --port=*) serve_flag=1 ;;
                *) scan_args+=("$a") ;;
            esac
        done
        if ! "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --scan "${scan_args[@]}"; then
            note "Scan reported issues; building the review page from the existing draft instead."
        fi
        if [ "$serve_flag" -eq 1 ]; then
            filtered=()
            for a in "${ARGS[@]}"; do [ "$a" = "--serve" ] || filtered+=("$a"); done
            exec "$PYTHON" "$DIR/review.py" "$FOLDER" --serve "${filtered[@]}"
        fi
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        HTML_PATH="$FOLDER/review.html"
        echo
        echo "Review page ready: file://$HTML_PATH"
        echo "Manual open: file://$HTML_PATH"
        echo "Next: resolve Undecided, set title/author/cover, Approve, Save, then './stickers export $FOLDER'."
        open_url "file://$HTML_PATH"
        ;;

    tag|classify)
        shift_folder
        require_folder
        [ -n "${OPENROUTER_API_KEY:-}" ] || die "OPENROUTER_API_KEY is not set. Export it before 'tag'."
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --classify-kept "${ARGS[@]}"
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        echo
        echo "Review page: file://$FOLDER/review.html"
        echo "Next: promote each suggestion to one final emoji, Approve, Save,"
        echo "      then run './stickers export $FOLDER'."
        ;;

    approve)
        shift_folder
        require_folder
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --approve "${ARGS[@]}"
        ;;

    preflight)
        shift_folder
        require_folder
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --preflight "${ARGS[@]}"
        ;;

    export)
        shift_folder
        require_folder
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --build-yaml "${ARGS[@]}"
        ;;

    preview|upload)
        shift_folder
        require_folder
        require_sticker_tool
        [ -f "$FOLDER/stickers.yaml" ] || die "No stickers.yaml in $FOLDER. Run './stickers export $FOLDER' first."
        [ -f "$FOLDER/stickers.yaml.receipt.json" ] || die "No build receipt in $FOLDER. Re-run './stickers export $FOLDER' (stale YAML is never trusted)."
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --preflight "${ARGS[@]}"
        print_pack_summary
        if [ "$ACTION" = "preview" ]; then
            ( cd "$FOLDER" && signal-sticker-tool preview "${ARGS[@]}" )
        else
            confirm_upload || exit 1
            ( cd "$FOLDER" && signal-sticker-tool upload "${ARGS[@]}" )
        fi
        ;;

    *)
        "$PYTHON" "$DIR/classify_and_build.py" "$ACTION" "$@"
        ;;
esac
