#!/usr/bin/env bash

# Track whether OBS was already running before this script
OBS_WAS_RUNNING=0
if pgrep -x "obs|obs-studio" >/dev/null 2>&1; then
  OBS_WAS_RUNNING=1
fi

# Wait for Steam to be ready
if ! pgrep -x steam >/dev/null 2>&1; then
  steam -silent >/dev/null 2>&1 &
  
  # Wait dynamically for steamwebhelper to start (up to 45 seconds)
  # which indicates that Steam has finished updating and logging in.
  timeout=45
  while ! pgrep -x steamwebhelper >/dev/null 2>&1 && [ $timeout -gt 0 ]; do
    sleep 1
    ((timeout--))
  done
  # A short extra buffer to ensure Steam is fully responsive
  sleep 2
fi

# Launch the game via Steam
steam -applaunch 2073850 >/dev/null 2>&1 &

# Wait for THE FINALS process (Discovery.exe / Discovery-Win64-Shipping.exe) to initialize
GAME_PATTERN="(Discovery\.exe|Discovery-Win64-Shipping\.exe)"
timeout=90
while ! pgrep -i -f "$GAME_PATTERN" >/dev/null 2>&1 && [ $timeout -gt 0 ]; do
  sleep 1
  ((timeout--))
done

# If the game failed to start within the timeout, notify and exit
if ! pgrep -i -f "$GAME_PATTERN" >/dev/null 2>&1; then
  if command -v notify-send >/dev/null 2>&1; then
    notify-send -u low "THE FINALS Launcher" "Game did not launch within 90s. OBS start aborted."
  fi
  exit 1
fi

# Brief buffer to let the game window map to the Wayland compositor
sleep 4

# Start OBS with Replay Buffer if it wasn't running already
if [ "$OBS_WAS_RUNNING" -eq 0 ]; then
  if command -v obs >/dev/null 2>&1; then
    obs --startreplaybuffer --minimize-to-tray >/dev/null 2>&1 &
  elif flatpak info com.obsproject.Studio >/dev/null 2>&1; then
    flatpak run com.obsproject.Studio --startreplaybuffer --minimize-to-tray >/dev/null 2>&1 &
  fi

  # Background watcher: monitors game process and closes OBS when game exits
  (
    # Wait until all instances of the game process exit
    while pgrep -i -f "$GAME_PATTERN" >/dev/null 2>&1; do
      sleep 3
    done

    # Grace period (15s) after game close so user can save a final clip
    sleep 15

    # Gracefully shut down OBS to release GPU/VRAM encode sessions
    mapfile -t obs_pids < <(pgrep -x "obs|obs-studio" 2>/dev/null)
    if [ "${#obs_pids[@]}" -gt 0 ]; then
      kill -TERM "${obs_pids[@]}" >/dev/null 2>&1
    fi
  ) >/dev/null 2>&1 &
fi

sleep 2
