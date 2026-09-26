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

A pack <folder> is required for scan/tag/curate/review/approve/export/preflight/preview/upload/url/wizard.
With no arguments this help is shown (nothing runs implicitly).

Prefer guidance? './stickers wizard <folder>' walks the workflow below step by
step (same gates; upload still confirmed explicitly).

Canonical workflow (in order):
  scan       Inventory images, hard-gate check, group visually similar candidates
  tag        Ranked suggestions for stickers missing them (skips suggested/final; --retage forces all)
  curate     scan + build review page (add --serve for loopback direct-save)
  review     Rebuild the review page only (add --serve for direct-save)
  approve    Human approval gate for the current revision (no threshold bypass)
  export     Strict preflight + write stickers.yaml + build receipt
  preview    Re-verify receipt + render locally with signal-sticker-tool
  upload     Re-verify + confirm + upload (use --yes noninteractively)

Browser approval and CLI approval are alternatives: either Approve Pack + Save
in the review page, or './stickers approve <folder>'. Only one is needed.
If tag/curate inputs change while a review server runs, restart it and reload.

Utilities:
  doctor [--upload] [<folder>]   Core env check; with a folder also runs pack preflight.
                                 --upload also requires the uploader + Signal login.
  login      Authenticate signal-sticker-tool (Signal Desktop credentials).
  logout     Remove saved Signal credentials.
  url <folder>   Reprint the share URL of an uploaded pack.
  wizard <folder>  Guided walkthrough (scan/tag/review/export/preview/upload).
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
  python/signal-stickers/stickers tag ./my_pack
  python/signal-stickers/stickers curate ./my_pack --serve
  python/signal-stickers/stickers approve ./my_pack --title "My Pack" --author "me"
  python/signal-stickers/stickers export ./my_pack
  python/signal-stickers/stickers preview ./my_pack
  python/signal-stickers/stickers doctor --upload ./my_pack
  signal-sticker-tool login   # via: ./stickers login
  python/signal-stickers/stickers upload ./my_pack --yes
EOF
}

# Default Signal credentials location used by signal-sticker-tool
# (XDG config home or ~/.config). Never printed, only checked for presence.
default_cred_file() {
    local base="${XDG_CONFIG_HOME:-}"
    if [ -z "$base" ]; then base="$HOME/.config"; fi
    printf '%s' "$base/signal-sticker-tool/credentials.yaml"
}

# Extract an explicit --cred-file/-c value from runner args, if the user
# overrides the default credentials location.
cred_file_from_args() {
    local skip_next=0
    for a in "$@"; do
        if [ "$skip_next" -eq 1 ]; then printf '%s' "$a"; return 0; fi
        case "$a" in
            --cred-file=*) printf '%s' "${a#--cred-file=}"; return 0 ;;
            --cred-file|-c) skip_next=1 ;;
            *) ;;
        esac
    done
    return 1
}

# Credential-safe login check: reports presence/validity only, never values.
check_signal_login() {
    local cred_file
    if ! cred_file="$(cred_file_from_args "$@")"; then
        cred_file="$(default_cred_file)"
    fi
    if [ ! -f "$cred_file" ]; then
        note "  Signal login  not configured (no credentials file)"
        note "                  run './stickers login' (Signal Desktop credentials)"
        return 1
    fi
    if "$PYTHON" - "$cred_file" <<'PY' >/dev/null 2>&1; then
import sys, yaml
with open(sys.argv[1], encoding="utf-8") as fp:
    creds = yaml.safe_load(fp) or {}
ok = isinstance(creds, dict) and bool(str(creds.get("username") or "").strip()) and bool(str(creds.get("password") or "").strip())
raise SystemExit(0 if ok else 1)
PY
        note "  Signal login  configured (credentials file present)"
        return 0
    fi
    note "  Signal login  BROKEN: credentials file exists but has no usable username/password"
    note "                  re-run './stickers login'"
    return 1
}

# Runner-only flags must never reach signal-sticker-tool (its preview/upload
# subcommands take no extra arguments). Forward credential overrides only.
# Result in global array FILTERED.
filter_tool_args() {
    FILTERED=()
    local skip_next=0
    for a in "$@"; do
        if [ "$skip_next" -eq 1 ]; then skip_next=0; FILTERED+=("$a"); continue; fi
        case "$a" in
            --cred-file|-c) FILTERED+=("$a"); skip_next=1 ;;
            --cred-file=*) FILTERED+=("$a") ;;
            *) ;; # drop runner-only and unknown flags
        esac
    done
}

# Keep preflight read-only: drop serve/prune/mode flags that either confuse
# the validator or would mutate the draft outside their own commands.
filter_preflight_args() {
    FILTERED=()
    local skip_next=0
    local PREV_FLAG=""
    for a in "$@"; do
        if [ "$skip_next" -eq 1 ]; then
            case "$PREV_FLAG" in
                --title|--author|--cover|--model|--out|--draft|--cache|--workers|--cluster-distance) FILTERED+=("$a") ;;
                *) ;;
            esac
            skip_next=0; continue
        fi
        case "$a" in
            --strict-quality|--yes|--resume|--dedupe) FILTERED+=("$a") ;;
            --title|--author|--cover|--model|--out|--draft|--cache|--workers|--cluster-distance) FILTERED+=("$a"); PREV_FLAG="$a"; skip_next=1 ;;
            --title=*|--author=*|--cover=*|--model=*|--out=*|--draft=*|--cache=*|--workers=*|--cluster-distance=*|--linkage=*) FILTERED+=("$a") ;;
            --linkage) FILTERED+=("$a"); PREV_FLAG="$a"; skip_next=1 ;;
            *) ;; # drop --serve/--port/--prune/mode/unknown flags
        esac
    done
}

doctor() {
    local upload_mode=0
    local raw=()
    for a in "$@"; do
        if [ "$a" = "--upload" ]; then upload_mode=1; else raw+=("$a"); fi
    done
    local folder="${raw[0]:-}"
    case "$folder" in
        -*) folder="" ;;
    esac
    local pre_args=()
    if [ -n "$folder" ]; then
        pre_args=("${raw[@]:1}")
    else
        pre_args=("${raw[@]}")
    fi
    # Unhfiltered remainder for the login check so a --cred-file/-c
    # override is honored there (preflight itself takes no such flag).
    local login_args=("${pre_args[@]}")
    # Drop serve/mode flags so a doctor folder check stays read-only.
    filter_preflight_args "${pre_args[@]}"
    pre_args=("${FILTERED[@]}")

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
        if [ "$upload_mode" -eq 1 ] && ! signal-sticker-tool --help >/dev/null 2>&1; then
            note "  signal-sticker-tool  BROKEN: installed but --help fails; reinstall upload requirements"
            problems=$((problems + 1))
        fi
    else
        note "  signal-sticker-tool  not installed (only needed for preview/upload)"
        note "                        $PYTHON -m pip install -r $DIR/requirements-upload.txt"
        if [ "$upload_mode" -eq 1 ]; then
            problems=$((problems + 1))
        else
            warnings=$((warnings + 1))
        fi
    fi

    if [ "$upload_mode" -eq 1 ]; then
        if ! check_signal_login "${login_args[@]}"; then
            problems=$((problems + 1))
        fi
    fi

    if [ -n "${OPENROUTER_API_KEY:-}" ]; then
        note "  OPENROUTER_API_KEY set (only needed for 'tag')"
    else
        note "  OPENROUTER_API_KEY not set (only needed for 'tag')"
        warnings=$((warnings + 1))
    fi


    if [ -z "$folder" ]; then
        echo
        if [ "$upload_mode" -eq 1 ]; then
            if [ "$problems" -eq 0 ]; then
                note "Upload readiness passed (env only). Pass a folder for pack checks: ./stickers doctor --upload ./my_pack"
                return 0
            fi
            note "$problems upload-readiness check(s) failing."
            return 1
        fi
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
        note "  uploaded.yaml present: signal-sticker-tool wrote it on a prior upload and will refuse to re-upload while it exists"
    fi

    echo
    note "Running pack preflight (schema/hash/manifest freshness)..."
    if "$PYTHON" "$DIR/classify_and_build.py" "$folder" --preflight "${pre_args[@]}"; then
        note "Pack preflight passed."
    else
        note "Pack preflight FAILED (see above)."
        return 1
    fi

    if [ "$problems" -ne 0 ]; then
        if [ "$upload_mode" -eq 1 ]; then note "$problems upload-readiness check(s) failing."; else note "$problems core check(s) failing."; fi
        return 1
    fi
    if [ "$upload_mode" -eq 1 ]; then
        if [ "$warnings" -ne 0 ]; then note "Upload readiness passed with $warnings optional warning(s)."; else note "Upload readiness passed."; fi
        return 0
    fi
    if [ "$warnings" -ne 0 ]; then note "Core ok with $warnings optional warning(s)."; fi
    return 0
}

confirm_upload() {
    local has_yes=0
    for a in "${ARGS[@]}"; do [ "$a" = "--yes" ] && has_yes=1; done
    if [ -f "$FOLDER/uploaded.yaml" ]; then
        echo "Note: $FOLDER/uploaded.yaml exists from a prior upload." >&2
        echo "signal-sticker-tool will NOT create a new pack while it exists;" >&2
        echo "it shows the previous upload instead. Delete or rename uploaded.yaml" >&2
        echo "for an intentional re-upload (packs cannot be edited after upload)." >&2
        if [ "$has_yes" -eq 0 ]; then
            printf 'Type YES to run the uploader anyway (or re-run with --yes): ' >&2
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

# ask "prompt" Y|N → exit 0 on yes. Empty answer takes the default;
# EOF aborts the wizard. Reads stdin so answers can be piped in tests.
ask() {
    local prompt="$1" def="$2" ans=""
    if [ "$def" = "Y" ]; then printf '%s [Y/n] ' "$prompt"
    else printf '%s [y/N] ' "$prompt"; fi
    if ! IFS= read -r ans; then printf '\nAborted.\n' >&2; exit 1; fi
    case "$ans" in
        "") [ "$def" = "Y" ] ;;
        [Yy]|[Yy][Ee][Ss]) return 0 ;;
        *) return 1 ;;
    esac
}

# Space-separated draft census: undecided no-final-emoji tag-errors state.
# Prints "0 0 0 none" when no usable draft exists yet.
draft_counts() {
    "$PYTHON" - "$FOLDER" "$DIR" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
try:
    from classify_and_build import final_emoji_for_entry
    draft = json.loads((Path(sys.argv[1]) / "pack_draft.json").read_text(encoding="utf-8"))
    stickers = draft.get("stickers", {}) or {}
    und = sum(1 for i in stickers.values() if i.get("selection") == "undecided")
    noem = sum(1 for i in stickers.values()
               if i.get("selection") in ("keep", "undecided") and not final_emoji_for_entry(i))
    err = sum(1 for i in stickers.values() if i.get("tag_status") in ("error", "unresolved", "stale"))
    print(f"{und} {noem} {err} {draft.get('pack_state', 'none')}")
except Exception:
    print("0 0 0 none")
PY
}

pack_ready_quiet() {
    "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --preflight >/dev/null 2>&1
}

wizard_review_round() {
    local server_log server_pid url ans
    server_log="$(mktemp)"
    echo "Starting review server (rendering the page first; this takes a few seconds)..."
    # Unbuffered so the startup banner reaches the log even though stdout
    # is redirected (block buffering would hide it until the server exits).
    PYTHONUNBUFFERED=1 "$PYTHON" "$DIR/review.py" "$FOLDER" --serve >"$server_log" 2>&1 &
    server_pid=$!
    url=""
    for _ in $(seq 1 150); do
        sleep 0.2
        url="$(grep -o 'http://127\.0\.0\.1:[0-9]*' "$server_log" 2>/dev/null | head -n 1)"
        [ -n "$url" ] && break
        kill -0 "$server_pid" 2>/dev/null || break
    done
    if [ -z "$url" ]; then
        kill "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
        echo "Review server failed to start; log (last lines):"
        tail -n 15 "$server_log"
        rm -f "$server_log"
        return 1
    fi
    echo "Review page: $url"
    open_url "$url"
    echo "In the browser: resolve Undecided, set exactly one emoji per kept sticker,"
    echo "set title/author/cover, click Approve Pack, then Save."
    echo "Press Enter when done ('q' then Enter quits the wizard)."
    if ! IFS= read -r ans; then ans="q"; fi
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
    rm -f "$server_log"
    [ "$ans" = "q" ] && return 1
    return 0
}

wizard_flow() {
    note "=== Sticker pack wizard: $FOLDER ==="
    note "Quit anytime (Ctrl-C or 'q'); completed steps are kept, re-run to resume."
    echo
    note "Step 0: environment"
    if ! doctor; then
        echo "Fix the environment above, then re-run the wizard."
        exit 1
    fi
    echo
    if ask "Step 1: run scan (inventory + similar-image groups)?" Y; then
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --scan || note "Scan reported issues; continuing with the existing draft."
    fi
    read -r und noem err state <<< "$(draft_counts)"
    echo
    note "Draft: $und undecided, $noem without final emoji, $err provider errors (state: $state)."
    if [ "$noem" -gt 0 ] || [ "$err" -gt 0 ]; then
        if [ -n "${OPENROUTER_API_KEY:-}" ]; then
            if ask "Step 2: run tag (OpenRouter suggestions)?" Y; then
                "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --classify-kept || note "Tagging left entries unresolved; they stay for manual review."
                "$PYTHON" "$DIR/review.py" "$FOLDER" >/dev/null
            fi
        else
            note "Step 2: OPENROUTER_API_KEY not set, skipping tag — assign emojis by hand in review."
        fi
    else
        note "Step 2: tagging not needed (every kept sticker has a final emoji)."
    fi
    echo
    while ! pack_ready_quiet; do
        note "Step 3: the pack is not export-ready yet:"
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --preflight 2>&1 | tail -n 12
        if ! ask "Open the review page (loopback server) to resolve this?" Y; then
            echo "Stopped before approval. Re-run the wizard to resume."
            exit 1
        fi
        wizard_review_round || { echo "Stopped. Re-run the wizard to resume."; exit 1; }
        echo
    done
    note "Step 3: pack is approved and preflight-clean."
    echo
    if ask "Step 4: export stickers.yaml + receipt?" Y; then
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --build-yaml || { echo "Export failed (see above)."; exit 1; }
    else
        echo "Stopped before export. Re-run the wizard to resume."
        exit 1
    fi
    echo
    if command -v signal-sticker-tool >/dev/null 2>&1; then
        if ask "Step 5: preview locally?" Y; then
            ( cd "$FOLDER" && signal-sticker-tool preview ) || { echo "Preview failed (see above)."; exit 1; }
        fi
        echo
        if check_signal_login; then
            print_pack_summary
            if ask "Step 6: UPLOAD to Signal? Irreversible (packs cannot be edited)." N; then
                ( cd "$FOLDER" && signal-sticker-tool upload ) || { echo "Upload failed (see above)."; exit 1; }
                echo
                echo "Upload finished. Reprint the link later with: ./stickers url $FOLDER"
            else
                echo "Skipped upload. Run './stickers upload $FOLDER' when ready."
            fi
        else
            echo "Skipped upload: no Signal login. Run './stickers login', then './stickers upload $FOLDER'."
        fi
    else
        echo "Skipped preview/upload: signal-sticker-tool not installed."
        echo "Install it, run './stickers login', then './stickers preview $FOLDER' and './stickers upload $FOLDER'."
    fi
    echo
    note "Wizard done."
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
        if [ -n "${FOLDER:-}" ]; then
            doctor "$FOLDER" "${ARGS[@]}" || exit 1
        elif [ "${#ARGS[@]}" -gt 0 ]; then
            doctor "${ARGS[@]}" || exit 1
        else
            doctor || exit 1
        fi
        ;;

    login|logout)
        require_sticker_tool
        if [ "$ACTION" = "login" ]; then
            echo "Have your Signal Desktop credentials ready (see README 'Uploading':" >&2
            echo "Desktop --enable-dev-tools, DevTools console in 'Electron Isolated Context')." >&2
        fi
        filter_tool_args "${ARGS[@]}"
        # shellcheck disable=SC2128
        signal-sticker-tool "$ACTION" "${FILTERED[@]}"
        ;;

    url)
        shift_folder
        require_folder
        require_sticker_tool
        filter_tool_args "${ARGS[@]}"
        # shellcheck disable=SC2128
        ( cd "$FOLDER" && signal-sticker-tool url "${FILTERED[@]}" )
        ;;

    wizard)
        shift_folder
        require_folder
        wizard_flow
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
            echo "Review server starting (loopback only). Leave this terminal running and"
            echo "use another terminal for tag/approve/export. If you tag while serving,"
            echo "restart this server and reload the page before approving."
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
        # The classifier falls through to the strict export gate, so a pack
        # with remaining errors exits non-zero. Regenerate the review page
        # regardless so new suggestions are never hidden behind a stale page.
        classify_ok=1
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --classify-kept "${ARGS[@]}" || classify_ok=0
        "$PYTHON" "$DIR/review.py" "$FOLDER"
        echo
        echo "Review page: file://$FOLDER/review.html"
        if [ "$classify_ok" -eq 0 ]; then
            echo "Note: tagging left unresolved/error entries (see above); resolve them"
            echo "in review or re-run tag, then Approve, Save, and export."
            exit 1
        fi
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
        filter_preflight_args "${ARGS[@]}"
        PRE_ARGS=("${FILTERED[@]}")
        filter_tool_args "${ARGS[@]}"
        TOOL_ARGS=("${FILTERED[@]}")
        [ -f "$FOLDER/stickers.yaml" ] || die "No stickers.yaml in $FOLDER. Run './stickers export $FOLDER' first."
        [ -f "$FOLDER/stickers.yaml.receipt.json" ] || die "No build receipt in $FOLDER. Re-run './stickers export $FOLDER' (stale YAML is never trusted)."
        # shellcheck disable=SC2128
        "$PYTHON" "$DIR/classify_and_build.py" "$FOLDER" --preflight "${PRE_ARGS[@]}"
        print_pack_summary
        if [ "$ACTION" = "preview" ]; then
            # shellcheck disable=SC2128
            ( cd "$FOLDER" && signal-sticker-tool preview "${TOOL_ARGS[@]}" )
        else
            confirm_upload || exit 1
            # shellcheck disable=SC2128
            ( cd "$FOLDER" && signal-sticker-tool upload "${TOOL_ARGS[@]}" )
            echo
            echo "Upload finished. The tool printed the share URL above and saved it in $FOLDER/uploaded.yaml."
            echo "Reprint later with: ./stickers url $FOLDER"
        fi
        ;;

    *)
        "$PYTHON" "$DIR/classify_and_build.py" "$ACTION" "$@"
        ;;
esac
