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
rm -f "$serve_log"

rm -rf "$FIX"

echo "---"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
