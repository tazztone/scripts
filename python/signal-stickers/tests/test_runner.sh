#!/usr/bin/env bash
# Behavioral checks for python/signal-stickers runner (no network, no API calls).
set -u

DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"
RUNNER="$DIR/run.sh"

if [ -f "$REPO_ROOT/.venv/bin/python" ]; then
    PY="$REPO_ROOT/.venv/bin/python"
else
    PY="$(command -v python3)"
fi

pass=0
fail=0
ok() { pass=$((pass + 1)); echo "ok: $1"; }
bad() { fail=$((fail + 1)); echo "FAIL: $1"; }

# 1. No arguments shows help and runs nothing implicitly.
out="$(bash "$RUNNER" 2>&1)"; code=$?
[ "$code" -eq 0 ] && echo "$out" | grep -q "pack <folder> is required" && ok "no-arg help" || bad "no-arg help (code=$code)"

# 2. scan without a folder is a clear error, not an implicit default.
out="$(bash "$RUNNER" scan 2>&1)"; code=$?
[ "$code" -ne 0 ] && echo "$out" | grep -q "pack folder is required" && ok "scan requires folder" || bad "scan requires folder (code=$code)"

# 3. A nonexistent folder argument is reported clearly (treated as folder, not flag).
out="$(bash "$RUNNER" scan /no/such/pack-xyz 2>&1)"; code=$?
[ "$code" -ne 0 ] && echo "$out" | grep -qi "does not exist" && ok "missing folder error" || bad "missing folder error (code=$code)"

# 4. doctor without a folder is a capability check (core deps present here).
out="$(bash "$RUNNER" doctor 2>&1)"; code=$?
[ "$code" -eq 0 ] && ok "doctor env-only" || bad "doctor env-only (code=$code)"

# 5. Fixture: scan + preflight blocked before approval; export blocked too.
FIX="$(mktemp -d)"
"$PY" -c "from PIL import Image; Image.new('RGBA',(512,512),(0,0,0,0)).save('$FIX/a.webp','WEBP')"
out="$(bash "$RUNNER" scan "$FIX" 2>&1)"; code=$?
[ "$code" -eq 0 ] && [ -f "$FIX/pack_draft.json" ] && ok "scan writes draft" || bad "scan writes draft (code=$code)"
out="$(bash "$RUNNER" preflight "$FIX" 2>&1)"; code=$?
[ "$code" -ne 0 ] && echo "$out" | grep -qi "approve" && ok "preflight blocks unapproved" || bad "preflight blocks unapproved (code=$code)"
out="$(bash "$RUNNER" export "$FIX" 2>&1)"; code=$?
[ "$code" -ne 0 ] && [ ! -f "$FIX/stickers.yaml" ] && ok "export blocked, no YAML" || bad "export blocked, no YAML (code=$code)"

# 6. Stray file types fail preflight.
printf 'junk' > "$FIX/stray.tiff"
out="$(bash "$RUNNER" preflight "$FIX" 2>&1)"; code=$?
[ "$code" -ne 0 ] && echo "$out" | grep -q "stray.tiff" && ok "stray file flagged" || bad "stray file flagged (code=$code)"
rm -f "$FIX/stray.tiff"

# 7. curate --serve does not leak --serve to the scanner (no misleading fallback).
out="$(bash "$RUNNER" help 2>&1)"; code=$?
echo "$out" | grep -q "\-\-serve" && ok "help documents --serve" || bad "help documents --serve"

# 8. Bounded curate --serve smoke: scanner never sees --serve, loopback server
# starts (bind+render proven by the banner), and the process stops cleanly.
# No cross-process HTTP fetch here: sandboxes may block child-process loopback
# while in-process serving is already covered by the pytest CAS test.
serve_log="$(mktemp)"
if PYTHONUNBUFFERED=1 "$PY" - "$RUNNER" "$FIX" "$serve_log" <<'PYEOF' >/dev/null 2>&1; then
import os, re, subprocess, sys, time
runner, fix, serve_log = sys.argv[1], sys.argv[2], sys.argv[3]
env = dict(os.environ, PYTHONUNBUFFERED="1")
with open(serve_log, "w") as f:
    proc = subprocess.Popen(["bash", runner, "curate", fix, "--serve"],
                            stdout=f, stderr=subprocess.STDOUT, env=env)
    url = None
    for _ in range(100):
        time.sleep(0.2)
        text = open(serve_log, errors="replace").read()
        if "Review server (loopback only)" in text:
            m = re.search(r"http://127\.0\.0\.1:\d+", text)
            url = m.group(0) if m else None
            break
        if proc.poll() is not None:
            break
    ok = bool(url) and proc.poll() is None
    ok = ok and "unrecognized arguments" not in open(serve_log, errors="replace").read()
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
        proc.wait(timeout=10)
    sys.exit(0 if ok else 1)
PYEOF
    ok "curate --serve smoke (loopback starts, --serve filtered, clean stop)"
else
    bad "curate --serve smoke (see $serve_log)"
fi
if grep -q "unrecognized arguments.*--serve" "$serve_log" 2>/dev/null; then
    bad "curate --serve leaked to scanner"
else
    ok "curate --serve keeps --serve from scanner"
fi
if grep -q "another terminal" "$serve_log" 2>/dev/null; then
    ok "curate --serve hints at second terminal"
else
    bad "curate --serve hints at second terminal"
fi
rm -f "$serve_log"

# 9. Finalize the fixture into an approved, exported pack (no API calls).
"$PY" - "$FIX" <<'PYEOF'
import json, sys
from pathlib import Path
folder = Path(sys.argv[1])
dp = folder / "pack_draft.json"
draft = json.loads(dp.read_text(encoding="utf-8"))
draft.setdefault("meta", {})["title"] = "Runner Test Pack"
draft["meta"]["author"] = "runner-test"
for item in draft.get("stickers", {}).values():
    item["selection"] = "keep"
    item["emojis"] = ["\U0001F600"]
    if item.get("tag_status") in ("error", "unresolved", "stale"):
        item["tag_status"] = "suggested"
dp.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
PYEOF
out="$(bash "$RUNNER" approve "$FIX" 2>&1)"; code=$?
[ "$code" -eq 0 ] && ok "approve finalized fixture" || bad "approve finalized fixture (code=$code)"
out="$(bash "$RUNNER" export "$FIX" 2>&1)"; code=$?
[ "$code" -eq 0 ] && [ -f "$FIX/stickers.yaml" ] && ok "export finalized fixture" || bad "export finalized fixture (code=$code)"

# 10. Fake signal-sticker-tool: records argv, mirrors upstream ownership of
# uploaded.yaml (writes it on upload, refuses while it exists) and --help.
FAKEBIN="$(mktemp -d)"
FAKELOG="$(mktemp)"
export FAKE_TOOL_LOG="$FAKELOG"
cat > "$FAKEBIN/signal-sticker-tool" <<'FAKEEOF'
#!/usr/bin/env bash
echo "$*" >> "$FAKE_TOOL_LOG"
cmd="${1:-}"
case "$cmd" in
    --help) echo "fake signal-sticker-tool"; exit 0 ;;
    preview) touch preview.html; echo "preview ok"; exit 0 ;;
    upload)
        if [ -f uploaded.yaml ]; then
            echo 'File "uploaded.yaml" found: already uploaded!'
            echo "https://signal.art/addstickers/#pack_id=OLD&pack_key=OLD"
            exit 0
        fi
        printf 'id: FAKEID\nkey: FAKEKEY\n' > uploaded.yaml
        echo "This pack is available in URL:"
        echo "  https://signal.art/addstickers/#pack_id=FAKEID&pack_key=FAKEKEY"
        exit 0 ;;
    login) echo "logged in (fake)"; exit 0 ;;
    logout) echo "logged out (fake)"; exit 0 ;;
    url)
        [ -f uploaded.yaml ] || { echo "not uploaded yet" >&2; exit 1; }
        echo "https://signal.art/addstickers/#pack_id=FAKEID&pack_key=FAKEKEY"
        exit 0 ;;
    *) echo "unknown command: $cmd" >&2; exit 1 ;;
esac
FAKEEOF
chmod +x "$FAKEBIN/signal-sticker-tool"
export PATH="$FAKEBIN:$PATH"

# 11. login passthrough reaches the tool and points at credential help.
out="$(bash "$RUNNER" login 2>&1)"; code=$?
[ "$code" -eq 0 ] && tail -n 1 "$FAKELOG" | grep -q "^login$" && echo "$out" | grep -qi "isolated context" && ok "login passthrough + hint" || bad "login passthrough + hint (code=$code)"

# 12. preview works and forwards no runner flags.
out="$(bash "$RUNNER" preview "$FIX" 2>&1)"; code=$?
[ "$code" -eq 0 ] && [ -f "$FIX/preview.html" ] && tail -n 1 "$FAKELOG" | grep -q "^preview$" && ok "preview forwards clean argv" || bad "preview forwards clean argv (code=$code)"

# 13. upload --yes succeeds; --yes never reaches the external tool.
out="$(bash "$RUNNER" upload "$FIX" --yes 2>&1)"; code=$?
[ "$code" -eq 0 ] && [ -f "$FIX/uploaded.yaml" ] && tail -n 1 "$FAKELOG" | grep -q "^upload$" && ok "upload filters --yes" || bad "upload filters --yes (code=$code)"
grep -q -- "--yes" "$FAKELOG" && bad "runner flag leaked to tool" || ok "no runner flag leaked to tool"

# 14. stray mode flags are dropped from preflight and the tool call too.
out="$(bash "$RUNNER" upload "$FIX" --yes --serve 2>&1)"; code=$?
[ "$code" -eq 0 ] && tail -n 1 "$FAKELOG" | grep -q "^upload$" && ok "upload drops --serve" || bad "upload drops --serve (code=$code)"

# 15. url reprints the share link.
out="$(bash "$RUNNER" url "$FIX" 2>&1)"; code=$?
[ "$code" -eq 0 ] && echo "$out" | grep -q "signal.art/addstickers" && ok "url reprints link" || bad "url reprints link (code=$code)"

# 16. doctor --upload fails with no Signal login, passes once configured.
XDG_EMPTY="$(mktemp -d)"
out="$(XDG_CONFIG_HOME="$XDG_EMPTY" bash "$RUNNER" doctor --upload "$FIX" 2>&1)"; code=$?
[ "$code" -ne 0 ] && echo "$out" | grep -qi "login" && ok "doctor --upload gates on login" || bad "doctor --upload gates on login (code=$code)"
XDG_FULL="$(mktemp -d)"
mkdir -p "$XDG_FULL/signal-sticker-tool"
printf 'username: fake-user\npassword: fake-pass\n' > "$XDG_FULL/signal-sticker-tool/credentials.yaml"
out="$(XDG_CONFIG_HOME="$XDG_FULL" bash "$RUNNER" doctor --upload "$FIX" 2>&1)"; code=$?
[ "$code" -eq 0 ] && echo "$out" | grep -q "Upload readiness passed" && ok "doctor --upload passes when ready" || bad "doctor --upload passes when ready (code=$code)"

# 17. doctor --upload drops serve flags and stays read-only (draft untouched).
# Note: the backup lives outside the pack so preflight never sees it.
DRAFT_BAK="$(mktemp)"
cp "$FIX/pack_draft.json" "$DRAFT_BAK"
out="$(XDG_CONFIG_HOME="$XDG_FULL" bash "$RUNNER" doctor --upload "$FIX" --serve 2>&1)"; code=$?
if [ "$code" -eq 0 ] && cmp -s "$FIX/pack_draft.json" "$DRAFT_BAK"; then
    ok "doctor --upload drops --serve, draft untouched"
else
    bad "doctor --upload drops --serve, draft untouched (code=$code)"
fi
rm -f "$DRAFT_BAK"

rm -rf "$FAKEBIN" "$FAKELOG" "$XDG_EMPTY" "$XDG_FULL" "$DRAFT_BAK"
rm -rf "$FIX"

echo "---"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
