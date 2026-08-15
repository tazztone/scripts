# Immich One-Click Desktop Runner

A robust, single-click desktop runner and lifecycle manager for **Immich**, modeled after the **Unsloth Studio** launcher architecture.

---

## 🚀 How It Works

Instead of opening a broken browser tab when containers are down, the launcher acts as an intelligent supervisor:

```
[Click Immich Shortcut]
         │
         ▼
┌───────────────────────────────────────────────┐
│ Fast-Path Check:                              │
│ HTTP GET http://localhost:2283/api/server/ping│
└───────────────────────┬───────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
    [Healthy]                     [Down / Cold]
         │                             │
         │                ┌────────────┴────────────┐
         │                │ Acquire Single-Instance │
         │                │ Lock (/tmp/...lock)     │
         │                └────────────┬────────────┘
         │                             │
         │                ┌────────────┴────────────┐
         │                │ 1. Verify/Mount Drive   │
         │                │ 2. Start Podman Socket  │
         │                │ 3. podman-compose up -d │
         │                └────────────┬────────────┘
         │                             │
         │                ┌────────────┴────────────┐
         │                │ Poll health endpoint    │
         │                │ until status == 200     │
         │                └────────────┬────────────┘
         │                             │
         ▼                             ▼
┌───────────────────────────────────────────────┐
│ Launch Standalone Brave PWA / App Window      │
└───────────────────────────────────────────────┘
```

1. **Instant Fast-Path**: If Immich is already running, clicking the launcher opens the App window immediately (< 100ms) with zero container overhead.
2. **Atomic Single-Instance Mutex**: Prevents race conditions or multiple compose processes if double-clicked rapidly.
3. **Environment & Storage Auto-Mount**: Ensures the external WD 14TB photo library drive (`UUID=C2B4194AB41941F9`) is mounted and the user-level Podman socket (`podman.socket`) is running.
4. **Health Check Polling**: Streams desktop notifications while bringing up the stack and waits for the API to confirm readiness.
5. **Standalone PWA Launch**: Opens Immich in a distraction-free Brave application window.

---

## 📁 Repository Structure

```
immich-launcher/
├── launch-immich.sh   # Core launcher script
├── immich.desktop     # Freedesktop .desktop entry file
├── install.sh         # One-step installer script
└── README.md          # Documentation
```

---

## 🛠️ Installation & Setup

To install or reinstall the launcher onto your system:

```bash
cd /home/tazztone/_coding/scripts/python/immich-launcher
./install.sh
```

This installs:
- Runner script: `~/.local/share/immich/launch-immich.sh`
- Desktop shortcut: `~/Desktop/Immich.desktop`
- App menu entry: `~/.local/share/applications/immich.desktop`

---

## ⚙️ Configuration

Key settings can be modified inside `launch-immich.sh`:

| Variable | Default Value | Description |
|---|---|---|
| `IMMICH_DIR` | `/home/tazztone/immich-app` | Path to docker-compose / podman-compose project |
| `IMMICH_PORT` | `2283` | Web UI and API port |
| `MOUNT_POINT` | `/media/tazztone/WD_14TB` | Mount point for external storage drive |
| `UUID` | `C2B4194AB41941F9` | UUID of the external storage drive |
| `TIMEOUT_SEC`| `60` | Max seconds to wait for backend health check |

---

## 🔍 Logs & Diagnostics

Launcher activity and container boot logs are recorded at:
```bash
cat ~/.local/share/immich/immich-launcher.log
```
