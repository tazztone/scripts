# scripts-sh

A collection of "Right-Click" productivity tools for Ubuntu users. These scripts integrate directly into the Nautilus file manager (Files), allowing you to convert, compress, and manipulate video/audio files without opening a heavy GUI application.

![alt text](image.png)

Powered by `ffmpeg`, `zenity`, and `bc`.

## 🚀 Features

- **Smart Compression:** Fit videos to exact sizes (e.g., 9MB for Email, 25MB for Discord) with auto-downscaling logic.
- **Instant Conversions:** One-click presets for MP4, WebM, ProRes, and DNxHD.
- **Workflow Automation:** Trim, scale, and extract audio instantly.
- **GUI Feedback:** Uses Zenity to provide progress bars, confirmation dialogs, and user input fields.

## 🛠️ Prerequisites

You need a few standard tools installed on your system. Open a terminal and run:

```bash
sudo apt update
sudo apt install ffmpeg zenity bc
```
*   `ffmpeg`: The core media engine.
*   `zenity`: Creates the popup windows and progress bars.
*   `bc`: Performs math calculations for bitrate scripts.

## 📥 Installation

1.  **Clone this repository** (or download the scripts):
    ```bash
    git clone https://github.com/YOUR_USERNAME/nautilus-ffmpeg-scripts.git
    ```

2.  **Move scripts to the Nautilus folder:**
    Depending on your Ubuntu version, the folder is in one of two places:
    *   **Ubuntu 22.04 / 24.04+ (Modern):** `~/.local/share/nautilus/scripts/`
    *   *Older Ubuntu:* `~/.gnome2/nautilus-scripts/`

    ```bash
    # Create the directory if it doesn't exist
    mkdir -p ~/.local/share/nautilus/scripts/
    
    # Copy all scripts into it
    cp *.sh ~/.local/share/nautilus/scripts/
    ```

3.  **Make them executable:**
    Linux requires scripts to have permission to run.
    ```bash
    chmod +x ~/.local/share/nautilus/scripts/*.sh
    ```

## 🖱️ How to Use

1.  Open your file manager (**Files / Nautilus**).
2.  Select one or more video/audio files.
3.  **Right-Click** the selection.
4.  Navigate to **Scripts** in the context menu.
5.  Choose the tool you want to run (e.g., `Smart_Compress_9MB.sh`).

*A popup window will appear showing the progress, and the new file will be created in the same folder as the original.*

## 📂 Included Scripts

Quick command-line tools for common video and audio tasks.

| Script | Description | Usage |
| :--- | :--- | :--- |
| `001-AAC-PCM-remux.sh` | Remux AAC/PCM | (Original script) |
| `002-filesize-9.sh` | Filesize utility | (Original script) |
| `003-scale-video.sh` | Resize video | `./003-scale-video.sh <input> <width> [output]` |
| `004-convert-format.sh` | Change container | `./004-convert-format.sh <input> <ext> [output]` |
| `005-extract-audio.sh` | Extract audio track | `./005-extract-audio.sh <input> [format]` |
| `006-trim-video.sh` | Fast video trimming | `./006-trim-video.sh <input> <start> <duration>` |
| `007-compress-video.sh` | CRF compression | `./007-compress-video.sh <input> <crf> [preset]` |
| `008-concat-videos.sh` | Join videos | `./008-concat-videos.sh <output> <in1> <in2> ...` |
| `009-make-gif.sh` | High-quality GIF | `./009-make-gif.sh <input> <start> <dur> <width>` |
| `010-add-watermark.sh` | Add watermark | `./010-add-watermark.sh <video> <img> <pos>` |
| `011-generate-thumbnails.sh` | Frame extraction | `./011-generate-thumbnails.sh <input> <interval>` |

## Testing (`/testing`)

- `run_ffmpeg_tests.sh`: Automated test suite for all FFmpeg utilities.


## 🤝 Contributing

Feel free to submit Pull Requests with your own useful FFmpeg one-liners!

1.  Fork the Project
2.  Create your Feature Branch
3.  Commit your Changes
4.  Push to the Branch
5.  Open a Pull Request
