# File Organizer

A robust, configurable Python script that organizes files in a directory into sub-folders named by their extension, and optionally groups those extension folders into broad categories.

```
Step 1 — by extension:         Step 2 — by category:

Downloads/                      Downloads/
├── photo.jpg    →  jpg/         ├── Images/
├── scan.jpg     →  jpg/         │   ├── photo.jpg
├── notes.txt    →  txt/         │   └── scan.jpg
├── report.pdf   →  pdf/         ├── Documents/
├── archive.zip  →  zip/         │   ├── notes.txt
├── script.py    →  py/          │   └── report.pdf
└── noext        →  no_extension/└── Code_and_Scripts/
                                     └── script.py
```

---

## Features

- **CLI Interface & Interactive Wizard** — Pass any target folder, or run without arguments to start a user-friendly configuration wizard.
- **Safety Prompts by Default** — In interactive mode, the script does a preview/dry-run first and asks for confirmation before executing.
- **Automatable** — Standard input detection (TTY check) and the `-y` / `--no-prompt` flags bypass all wizard menus and prompts for automated environments (cron jobs, script integrations).
- **Custom Configuration** — Fine-tune categories, file extension mappings, and skip lists inside `config.json`.
- **Dry-run Mode** — Full end-to-end preview (Phase 1 AND Phase 2) of every planned move without touching any files (`--dry-run`).
- **Conflict-safe** — Name collisions are resolved with numeric suffixes (`file_1.txt`) instead of overwriting.
- **Recursive Mode** — Descends into subfolders (`--recursive`) while intelligently skipping folders that are already organized.
- **Clean Fallback** — Operates out of the box with safe hardcoded defaults if `config.json` is missing or invalid.

---

## Requirements

Python 3.9+. No third-party package dependencies.

---

## Usage

### Interactive Wizard
To select options step-by-step:
```bash
python3 organize.py
```

### Direct CLI Commands
```bash
# Organize a specific folder using defaults and skip confirmation
python3 organize.py /path/to/folder -y

# Preview what would happen (no files moved)
python3 organize.py --dry-run /path/to/folder

# Also organize files inside sub-directories recursively
python3 organize.py --recursive /path/to/folder

# Skip Phase 2 (only sort into extension folders)
python3 organize.py --no-categorize /path/to/folder

# Show verbose logs
python3 organize.py -v /path/to/folder
```

---

## Configuration (`config.json`)

Customize the behavior of the organizer by modifying the `config.json` file in the script's directory:

- `skip_names`: List of file/folder names (case-insensitive) to ignore and never move (e.g. `readme.md`, `.gitignore`).
- `no_extension_folder`: Directory name for files without extensions.
- `categories`: Map category names to a list of extensions (without the leading dot) or directory names to merge.

Example `config.json`:
```json
{
  "skip_names": [
    "organize.py",
    "readme.md",
    ".gitignore",
    ".gitkeep",
    "config.json"
  ],
  "no_extension_folder": "no_extension",
  "categories": {
    "Images": ["png", "jpg", "jpeg", "webp", "gif"],
    "Documents": ["pdf", "doc", "docx", "txt", "rtf", "md"]
  }
}
```

---

## Running Tests

### Unit Tests
The project features a comprehensive unit-test suite checking all organization behaviors:
```bash
python3 -m unittest discover -s tests
```

### Manual Testing Sandbox
A pre-configured organized sandbox exists in `mock_dir/` for reference and manual verification of folder layouts.
