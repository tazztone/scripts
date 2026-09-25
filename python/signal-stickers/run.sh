#!/usr/bin/env bash
# Signal Stickers Convenience Runner
#
# Wraps classify_and_build.py / review.py behind a small set of workflow verbs and
# picks the right Python interpreter automatically.
#
# Entry points (all equivalent):
#   ./run.sh <action>   ./stickers <action>   bash run.sh <action>

set -e

# Resolve this script's real directory, following symlinks so that the runner can
# be symlinked onto PATH (e.g. ~/bin/stickers) and still find its siblings.
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

# --- Interpreter discovery ----------------------------------------------------
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

# Put the workspace venv on PATH so signal-sticker-tool resolves.
export PATH="$REPO_ROOT/.venv/bin:$DIR/.venv/bin:$PATH"

die() { echo "Error: $*" >&2; exit 1; }
note() { echo "$*"; }

require_sticker_tool() {
    if ! command -v signal-sticker-tool >/dev/null 2>&1; then
        cat >&2 <<EOF
Error: 'signal-sticker-tool' is not installed, so packs cannot be previewed or uploaded.

It is listed in requirements.txt but is not present in the workspace venv.
Install it with:

    $REPO_ROOT/.venv/bin/pip install signal-sticker-tool

(Or install the full set:  $REPO_ROOT/.venv/bin/pip install -r $DIR/requirements.txt)
EOF
        exit 1
    fi
}

usage() {
    cat <<EOF
Signal Sticker Pack Curation & Build Helper

Usage: ./stickers <action> [folder] [options]

  Most actions accept an optional [folder] argument.
  It defaults to the bundled sample pack: $DIR/webp

Curation Workflow (run in order):
  scan       Inventory images, check Signal constraints, detect visual clusters
             (no API calls, safe to re-run)
  curate     Same as scan, then open the review page to pick the best variations
  tag        Run VLM emoji suggestions on the stickers you marked "keep"
  review     Regenerate the review page and open it (no API calls)
  export     Write stickers.yaml from the approved pack_draft.json
  preview    Render the pack locally with signal-sticker-tool
  upload     Encrypt and upload the pack to Signal, then print the share link

Utilities:
  doctor     Check the environment (Python, deps, API key, pack folder).
             Exits non-zero if anything is missing, so it works in CI/scripts.
  help       Show this message

Options:
  --provider openrouter | gemini | anthropic   VLM provider for 'tag'
  --model    <model slug>                      e.g. gemini-2.5-flash
  --title    <pack title>                      Overrides the title in pack_draft.json
  --author   <author name>                     Overrides the author in pack_draft.json
  --workers  <n>                               Parallel VLM requests (default: 4)

Examples:
  ./stickers scan                          # inspect ./webp
  ./stickers curate ./webp                 # scan + review page, folder given explicitly
  ./stickers tag --provider gemini         # classify kept stickers with Gemini
  ./stickers export                        # build ./webp/stickers.yaml
  ./stickers upload                        # ship it

Any other arguments are passed straight through to classify_and_build.py,
so the full Python CLI remains available:

  ./stickers ./webp --classify-kept --title "My Pack" --author "me"
  python classify_and_build.py --help
EOF
}

doctor() {
    local folder="${1:-$DIR/webp}"
    local problems=0

    printf 'Signal Stickers environment check\n\n'

    note "  Python        $("$PYTHON" --version 2>&1)"
    note "  Interpreter   $PYTHON"

    local mods
    for mod in yaml PIL; do
        if "$PYTHON" -c "import $mod" >/dev/null 2>&1; then
            case "$mod" in
                yaml) note "  PyYAML        ok" ;;
                PIL)  note "  Pillow        ok" ;;
            esac
        else
            case "$mod" in
                yaml) note "  PyYAML        MISSING  -> pip install PyYAML" ;;
                PIL)  note "  Pillow        MISSING  -> pip install Pillow" ;;
            esac
            problems=$((problems + 1))
        fi
    done

    if command -v signal-sticker-tool >/dev/null 2>&1; then
        note "  signal-sticker-tool  $(command -v signal-sticker-tool)"
    else
        note "  signal-sticker-tool  MISSING  -> pip install signal-sticker-tool"
        note "                        (only needed for 'preview' and 'upload')"
        problems=$((problems + 1))
    fi

    local key_found=""
    for var in OPENROUTER_API_KEY GEMINI_API_KEY GOOGLE_API_KEY ANTHROPIC_API_KEY; do
        if [ -n "${!var:-}" ]; then
            key_found="$key_found $var"
        fi
    done
    if [ -n "$key_found" ]; then
        note "  API key        set:$key_found"
    else
        note "  API key        NONE  -> set one before running 'tag'"
        note "                   e.g. export OPENROUTER_API_KEY=sk-or-v1-..."
        problems=$((problems + 1))
    fi

    if [ -d "$folder" ]; then
        local count
        count="$(find "$folder" -maxdepth 1 -type f \
            \( -iname '*.webp' -o -iname '*.png' -o -iname '*.apng' \
               -o -iname '*.jpg' -o -iname '*.jpeg' \) 2>/dev/null | wc -l)"
        note "  Pack folder    $folder ($count image(s))"
    else
        note "  Pack folder    $folder  MISSING  -> pass a folder, e.g. ./stickers scan ./webp"
        problems=$((problems + 1))
    fi

    for f in pack_draft.json stickers.yaml; do
        if [ -f "$folder/$f" ]; then
            note "  $f  present"
        else
            note "  $f  not generated yet"
        fi
    done

    echo
    if [ "$problems" -eq 0 ]; then
        note "All checks passed. Next: ./stickers scan"
        return 0
    fi
    note "$problems check(s) need attention (see MISSING above)."
    return 1
}

# Resolve an optional leading folder argument.
#
# Bash `set --` inside a function only re-indexes the function's own parameters,
# so the remaining flags are tracked in a global array instead: shift_folder
# sets FOLDER and rewrites ARGS with the folder removed, leaving everything else
# for pass-through to the Python CLI.
FOLDER=""

shift_folder() {
    FOLDER=""
    if [ "${ARGS[0]:-}" != "--" ] && [ -n "${ARGS[0]:-}" ] && [ -d "${ARGS[0]}" ]; then
        FOLDER="${ARGS[0]}"
        ARGS=("${ARGS[@]:1}")
    fi
    return 0
}

ACTION="${1:-curate}"
[ "$#" -gt 0 ] && shift || true
# Everything after the action verb; shift_folder may strip a leading folder.
ARGS=("$@")

case "$ACTION" in
    doctor)
        shift_folder
        [ -n "$FOLDER" ] || FOLDER="$DIR/webp"
        # Keep a broken environment from being masked by `set -e`: report every
        # problem, then exit non-zero so scripts can branch on the status.
        doctor "$FOLDER" || exit 1
        ;;

    help|--help|-h)
        usage
        ;;

    scan|check)
        shift_folder
        [ -n "$FOLDER" ] || FOLDER="$DIR/webp"
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --scan "${ARGS[@]}"
        ;;

    curate|review)
        shift_folder
        [ -n "$FOLDER" ] || FOLDER="$DIR/webp"
        if ! "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --scan "${ARGS[@]}"; then
            note "Scan failed; building the review page from the existing draft instead."
        fi
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        HTML_PATH="$FOLDER/review.html"
        if [ ! -f "$HTML_PATH" ]; then
            HTML_PATH="$DIR/review.html"
        fi
        echo
        echo "Review page ready: file://$HTML_PATH"
        echo "Next: pick the best variation per cluster, then run './stickers export'."
        if command -v xdg-open >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
            xdg-open "$HTML_PATH" >/dev/null 2>&1 &
        fi
        ;;

    tag|classify)
        shift_folder
        [ -n "$FOLDER" ] || FOLDER="$DIR/webp"
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --classify-kept "${ARGS[@]}"
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        echo
        echo "Review page: file://$FOLDER/review.html"
        echo "Next: correct the suggested emojis in the browser, save the draft,"
        echo "      copy it to $FOLDER/pack_draft.json, then run './stickers export'."
        ;;

    export)
        shift_folder
        [ -n "$FOLDER" ] || FOLDER="$DIR/webp"
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --build-yaml "${ARGS[@]}"
        ;;

    preview|upload)
        shift_folder
        [ -n "$FOLDER" ] || FOLDER="$DIR/webp"
        require_sticker_tool
        if [ ! -f "$FOLDER/stickers.yaml" ]; then
            die "No stickers.yaml in $FOLDER. Run './stickers export' first."
        fi
        cd "$FOLDER"
        if [ "$ACTION" = "preview" ]; then
            signal-sticker-tool preview "${ARGS[@]}"
        else
            signal-sticker-tool upload "${ARGS[@]}"
        fi
        ;;

    *)
        # Pass anything else straight through to the Python CLI.
        "$PYTHON" "$DIR/classify_and_build.py" "$ACTION" "$@"
        ;;
esac
