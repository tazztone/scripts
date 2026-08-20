# THE FINALS & OBS Automation

Launcher script for [THE FINALS](https://store.steampowered.com/app/2073850/THE_FINALS/) with automated OBS Studio Replay Buffer management.

## Features

- **Sequential Startup:** Launches Steam and the game first, then waits for the game process (`Discovery.exe` / `Discovery-Win64-Shipping.exe`) and Wayland compositor mapping before starting OBS.
- **Automatic Window Capture:** Prevents premature PipeWire screencast permission popups by ensuring the game window already exists when OBS initializes.
- **Session-Aware:** Detects if OBS was already running before the game launched; leaves your existing session untouched if so.
- **Auto-Cleanup on Exit:** If OBS was launched specifically for this session, a background watcher waits for the game to terminate, grants a 15-second grace period (to save last-second clips), and gracefully closes OBS to free GPU VRAM and video encoders.
- **Failure Notification:** Sends a desktop notification if the game fails to initialize within the 90-second timeout.

## Usage

Run directly or bind to a desktop shortcut:
```bash
./FINALS_OBS.sh
```
