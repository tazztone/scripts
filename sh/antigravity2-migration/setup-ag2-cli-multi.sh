#!/usr/bin/env bash
#
# Antigravity 2.0 CLI (agy) Multi-Account Setup Script
# Configures isolated environments for Tazz (default) and Natalie (agy2).
#

set -euo pipefail

BIN_DIR="$HOME/bin"
CONFIG_CLI_NATALIE="$HOME/.antigravity-cli-account2"

# Ensure directories exist
mkdir -p "$BIN_DIR" "$CONFIG_CLI_NATALIE"

echo "=================================================================="
echo "          ANTIGRAVITY 2.0 CLI MULTI-ACCOUNT SETUP"
echo "=================================================================="
echo

# Helper function to safely backup existing files
safe_write() {
  local target="$1"
  local content="$2"
  if [ -f "$target" ]; then
    echo "    [Backup] Backing up existing $(basename "$target") to ${target}.bak"
    cp -f "$target" "${target}.bak"
  fi
  echo "$content" > "$target"
}

# 1. Locate real agy binary
REAL_AGY="/home/tazztone/.local/bin/agy"
if [ ! -f "$REAL_AGY" ]; then
  # Try finding it in PATH
  if command -v agy >/dev/null; then
    REAL_AGY=$(which agy)
  else
    echo "    [!] Warning: Real 'agy' executable not found at ~/.local/bin/agy."
    echo "        The wrapper scripts will still be created pointing to ~/.local/bin/agy."
  fi
fi

echo "    Target real agy executable: $REAL_AGY"
echo

# 2. Write Natalie wrapper (agy2)
echo "[1/2] Creating Natalie's wrapper script (agy2)..."
NATALIE_WRAPPER_CONTENT=$(cat << EOF
#!/usr/bin/env sh
set -eu
REAL_AGY="$REAL_AGY"
if [ ! -f "\$REAL_AGY" ]; then
  echo "Real agy executable not found at \$REAL_AGY" >&2
  exit 1
fi
export HOME="\$HOME/.antigravity-cli-account2"
# Force keyring connection failure by providing a non-existent DBus socket path
export DBUS_SESSION_BUS_ADDRESS="unix:path=/dev/null/nonexistent"
# Clear parent Antigravity session/IDE environment variables to prevent hijacking Tazz's active server
for var in \$(env | grep -o '^ANTIGRAVITY_[A-Z0-9_]*'); do
  unset "\$var"
done
exec "\$REAL_AGY" "\$@"
EOF
)

safe_write "$BIN_DIR/agy2" "$NATALIE_WRAPPER_CONTENT"
chmod +x "$BIN_DIR/agy2"
echo "    [+] Wrapper 'agy2' deployed successfully."
echo

# 3. Write Tazz wrapper (agy-tazz)
echo "[2/2] Creating Tazz's explicit wrapper script (agy-tazz)..."
TAZZ_WRAPPER_CONTENT=$(cat << EOF
#!/usr/bin/env sh
set -eu
REAL_AGY="$REAL_AGY"
if [ ! -f "\$REAL_AGY" ]; then
  echo "Real agy executable not found at \$REAL_AGY" >&2
  exit 1
fi
exec "\$REAL_AGY" "\$@"
EOF
)

safe_write "$BIN_DIR/agy-tazz" "$TAZZ_WRAPPER_CONTENT"
chmod +x "$BIN_DIR/agy-tazz"
echo "    [+] Wrapper 'agy-tazz' deployed successfully."
echo

echo "=================================================================="
echo "          CLI DEPLOYMENT INITIALIZED!"
echo "=================================================================="
echo "    - Tazz uses: normal 'agy' command (or explicit 'agy-tazz')"
echo "    - Natalie uses: 'agy2' command"
echo "    - Natalie's isolated directory: ~/.antigravity-cli-account2"
echo "=================================================================="
