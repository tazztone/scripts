# put-files-into-folder-by-extension

A two-script toolkit that first sorts files into extension folders, then groups those into broad categories.

```
Step 1 — by extension:         Step 2 — by category:

Downloads/                      Downloads/
├── photo.jpg    →  jpg/         ├── Images/
├── scan.jpg     →  jpg/         │   ├── photo.jpg
├── notes.txt    →  txt/         │   └── scan.jpg
├── report.pdf   →  pdf/         ├── Documents/
└── archive.zip  →  zip/         │   ├── notes.txt
                                  │   └── report.pdf
                                  └── Software_and_Archives/
                                      └── archive.zip
```

---

## Script 1 — `put_files_into_folder_by_extension.py`

Moves every loose file into a sub-folder named after its extension (`jpg/`, `pdf/`, etc.).

### Features

- **CLI interface** — pass any target folder, or omit it for the current working directory
- **Dry-run mode** — preview every planned move without touching files (`--dry-run`)
- **Recursive mode** — also descend into sub-directories (`--recursive`)
- **Conflict-safe** — name collisions are resolved with numeric suffixes (`file_1.txt`) instead of overwriting
- **Skip-list** — the script itself, `README.md`, `.gitignore`, and `.gitkeep` are never moved
- **No-extension files** — files without an extension go into `no_extension/`
- **Summary** — prints how many files were moved per extension

### Requirements

Python 3.9+. No third-party packages.

### Usage

```bash
# Organize the current working directory
python put_files_into_folder_by_extension.py

# Organize a specific folder
python put_files_into_folder_by_extension.py /path/to/folder

# Preview what would happen (no files moved)
python put_files_into_folder_by_extension.py --dry-run /path/to/folder

# Also organise files inside sub-directories
python put_files_into_folder_by_extension.py --recursive /path/to/folder

# Verbose output
python put_files_into_folder_by_extension.py -v /path/to/folder
```

### Options

| Flag | Description |
|---|---|
| `folder` | Directory to organise (default: CWD) |
| `--dry-run` | Print planned moves without executing them |
| `--recursive` | Also process files in sub-directories |
| `-v` / `--verbose` | Show debug-level output |

---

## Script 2 — `categorize_organized_folders.py`

Merges the extension folders produced by Script 1 into 8 broad category folders, then removes the now-empty extension folders.

### Categories

| Category | Extensions |
|---|---|
| 🖼️ `Images` | `png` `jpg` `jpeg` `webp` `gif` `avif` `heic` `svg` `psd` `cr2` `ico` |
| 📄 `Documents` | `pdf` `doc` `docx` `txt` `rtf` `ppt` `pptx` `xls` `xlsx` `md` `csv` `xps` `epub` `azw3` `opml` |
| 🎬 `Video` | `mp4` `mkv` `avi` `flv` `wmv` `mpg` `m4v` `ogv` `swf` `mov` `drp` `prproj` `pdrproj` |
| 🎵 `Audio` | `mp3` `wav` `flac` `ogg` `m4a` `m4b` `aac` `pls` `m3u` `xm` |
| 📦 `Software_and_Archives` | `zip` `rar` `7z` `gz` `bz2` `deb` `msi` `exe` `iso` `ova` `jar` `apk` `vsix` `nzb` `dlc` |
| 💻 `Code_and_Scripts` | `py` `html` `htm` `js` `css` `sh` `bat` `ps1` `lua` `xml` `xht` `ejs` `c` `cpp` `h` |
| 🤖 `AI_and_Models` | `safetensors` `gguf` `pt` |
| ⚙️ `Data_and_Config` | `json` `yaml` `yml` `ini` `log` `db` `sqlite3` `dat` |

Special "already-named" folders (`_AI`, `_PDF`, `_EBOOKS`, `_AUDIOBOOKS`, `_SOFTWARE`) are also merged into the appropriate category.

### Usage

```bash
# Categorize the current working directory
python categorize_organized_folders.py

# Categorize a specific folder
python categorize_organized_folders.py /path/to/folder

# Preview (no files moved)
python categorize_organized_folders.py --dry-run /path/to/folder

# Verbose output
python categorize_organized_folders.py -v /path/to/folder
```

### Options

| Flag | Description |
|---|---|
| `folder` | Directory to categorise (default: CWD) |
| `--dry-run` | Print planned moves without executing them |
| `-v` / `--verbose` | Show debug-level output |

---

## Recommended workflow

```bash
# 1. Preview step 1
python put_files_into_folder_by_extension.py --dry-run ~/Downloads

# 2. Run step 1
python put_files_into_folder_by_extension.py ~/Downloads

# 3. Preview step 2
python categorize_organized_folders.py --dry-run ~/Downloads

# 4. Run step 2
python categorize_organized_folders.py ~/Downloads
```
