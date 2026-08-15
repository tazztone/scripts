#!/usr/bin/env bash
# Immich One-Click Desktop Launcher
# Modeled after Unsloth Studio desktop runner architecture
set -euo pipefail

IMMICH_DIR="/home/tazztone/immich-app"
DATA_DIR="$HOME/.local/share/immich"
LOG_FILE="$DATA_DIR/immich-launcher.log"
LOCK_DIR="${XDG_RUNTIME_DIR:-/tmp}/immich-launcher-$(id -u).lock"
IMMICH_PORT=2283
HEALTH_URL="http://127.0.0.1:${IMMICH_PORT}/api/server/ping"
FALLBACK_HEALTH_URL="http://127.0.0.1:${IMMICH_PORT}/api/server-info/ping"
TIMEOUT_SEC=60
POLL_INTERVAL_SEC=0.5

# Hardware / Mount configs
UUID="C2B4194AB41941F9"
MOUNT_POINT="/media/tazztone/WD_14TB"
SOCKET_PATH="/run/user/$(id -u)/podman/podman.sock"
SOCKET_TIMEOUT=15

mkdir -p "$DATA_DIR"

# ── Notifications ──
_notify() {
    local title="$1"
    local msg="$2"
    local urgency="${3:-normal}"
    if command -v notify-send >/dev/null 2>&1; then
        notify-send -u "$urgency" -a "Immich Launcher" "$title" "$msg" 2>/dev/null || true
    fi
}

# ── HTTP GET check ──
_check_health() {
    if command -v curl >/dev/null 2>&1; then
        curl -fsS --max-time 1 "$HEALTH_URL" >/dev/null 2>&1 || curl -fsS --max-time 1 "$FALLBACK_HEALTH_URL" >/dev/null 2>&1 || curl -fsS --max-time 1 "http://127.0.0.1:${IMMICH_PORT}/" >/dev/null 2>&1
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- --timeout=1 "$HEALTH_URL" >/dev/null 2>&1 || wget -qO- --timeout=1 "http://127.0.0.1:${IMMICH_PORT}/" >/dev/null 2>&1
    else
        return 1
    fi
}

# ── Launch Immich PWA / Browser window ──
_open_app() {
    local app_url="http://localhost:${IMMICH_PORT}"
    if [ -f /opt/brave.com/brave/brave-browser ]; then
        /opt/brave.com/brave/brave-browser --profile-directory=Default --app-id=llgjbhgnegoenepjafbbonhhkdocfpck >/dev/null 2>&1 &
    elif command -v brave-browser >/dev/null 2>&1; then
        brave-browser --app="$app_url" >/dev/null 2>&1 &
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$app_url" >/dev/null 2>&1 &
    else
        echo "Open in your browser: $app_url" >&2
    fi
}

# ── Atomic Single-Instance Guard ──
_acquire_lock() {
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        echo "$$" > "$LOCK_DIR/pid"
        return 0
    fi

    # Lock exists: check if owner process is still running
    local old_pid
    old_pid=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
        # Another launcher is active, wait for it to finish starting Immich
        local deadline=$(( $(date +%s) + TIMEOUT_SEC ))
        while [ "$(date +%s)" -lt "$deadline" ]; do
            if _check_health; then
                _open_app
                exit 0
            fi
            sleep "$POLL_INTERVAL_SEC"
        done
        exit 0
    fi

    # Stale lock: clean up and reclaim
    rm -rf "$LOCK_DIR"
    mkdir "$LOCK_DIR" 2>/dev/null || return 1
    echo "$$" > "$LOCK_DIR/pid"
}

_release_lock() {
    [ -d "$LOCK_DIR" ] || return 0
    [ "$(cat "$LOCK_DIR/pid" 2>/dev/null)" = "$$" ] || return 0
    rm -rf "$LOCK_DIR"
}

# ── Pre-flight Checks (Drive Mount & Podman Socket) ──
_ensure_environment() {
    # 1. Check drive mount
    if [ -d "$MOUNT_POINT" ]; then
        if ! mountpoint -q "$MOUNT_POINT"; then
            echo "[$(date)] Attempting to mount WD_14TB drive..." >> "$LOG_FILE"
            if sudo mount -t ntfs -o nosuid,nodev,relatime,uid=1000,gid=1000,fmask=0133,dmask=0022,allow_other UUID="$UUID" "$MOUNT_POINT" 2>>"$LOG_FILE"; then
                echo "[$(date)] Successfully mounted WD_14TB." >> "$LOG_FILE"
            else
                echo "[$(date)] Warning: Could not automatically mount $MOUNT_POINT." >> "$LOG_FILE"
            fi
        fi
    fi

    # 2. Ensure Podman socket is active
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user start podman.socket >> "$LOG_FILE" 2>&1 || true
        local waited=0
        while [ ! -S "$SOCKET_PATH" ] && [ "$waited" -lt "$SOCKET_TIMEOUT" ]; do
            sleep 1
            waited=$(( waited + 1 ))
        done
    fi
}

# ── Main ──

# Fast-path: if already running and healthy, open immediately
if _check_health; then
    _open_app
    exit 0
fi

# Acquire single-instance lock
_acquire_lock
trap '_release_lock' EXIT INT TERM

# Re-check after lock
if _check_health; then
    _open_app
    exit 0
fi

_notify "Starting Immich" "Booting photo services and storage stack..." "low"
echo "=== Immich Launcher Starting: $(date) ===" >> "$LOG_FILE"

# Prepare environment (drive & podman socket)
_ensure_environment

# Launch container stack with podman-compose
if [ -d "$IMMICH_DIR" ]; then
    cd "$IMMICH_DIR"
    if command -v podman-compose >/dev/null 2>&1; then
        echo "[$(date)] Running podman-compose up -d..." >> "$LOG_FILE"
        podman-compose up -d >> "$LOG_FILE" 2>&1 || true
    elif command -v docker-compose >/dev/null 2>&1; then
        docker-compose up -d >> "$LOG_FILE" 2>&1 || true
    else
        echo "[$(date)] ERROR: Neither podman-compose nor docker-compose found." >> "$LOG_FILE"
        _notify "Immich Error" "podman-compose not found." "critical"
        exit 1
    fi
else
    echo "[$(date)] ERROR: $IMMICH_DIR not found." >> "$LOG_FILE"
    _notify "Immich Error" "Directory $IMMICH_DIR does not exist." "critical"
    exit 1
fi

# Poll until healthy
deadline=$(( $(date +%s) + TIMEOUT_SEC ))
while [ "$(date +%s)" -lt "$deadline" ]; do
    if _check_health; then
        echo "[$(date)] Immich became healthy!" >> "$LOG_FILE"
        _release_lock
        _open_app
        exit 0
    fi
    sleep "$POLL_INTERVAL_SEC"
done

echo "[$(date)] Timed out waiting for Immich to become healthy." >> "$LOG_FILE"
_notify "Immich Timeout" "Immich took longer than ${TIMEOUT_SEC}s to start. Check $LOG_FILE" "normal"
exit 1
