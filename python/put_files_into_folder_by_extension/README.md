# put-files-into-folder-by-extension

A Python script that organises files in a directory into sub-folders named after their file extension.

```
before/                       after/
├── photo.jpg          →      ├── jpg/
├── notes.txt          →      │   └── photo.jpg
├── report.pdf         →      ├── txt/
├── archive.zip        →      │   └── notes.txt
└── data               →      ├── pdf/
                       →      │   └── report.pdf
                       →      ├── zip/
                       →      │   └── archive.zip
                       →      └── no_extension/
                       →          └── data
```

## Features

- **CLI interface** — pass any target folder as an argument, or omit it to use the current working directory
- **Dry-run mode** — preview every planned move without touching files (`--dry-run`)
- **Recursive mode** — also descend into sub-directories (`--recursive`)
- **Conflict-safe** — if a file with the same name already exists in the destination, a numeric suffix is added (`file_1.txt`, `file_2.txt`, …) instead of overwriting
- **Skip-list** — the script itself, `README.md`, `.gitignore`, and `.gitkeep` are never moved
- **No-extension files** — files without an extension go into `no_extension/`
- **Summary** — prints how many files were moved per extension

## Requirements

Python 3.9 or later. No third-party packages needed.

## Usage

### 1. Basic Organization
Organizes files into sub-folders named after their extension (e.g., `.jpg` files go into `jpg/`).

```bash
# Organize the current working directory
python put_files_into_folder_by_extension.py

# Organize a specific folder
python put_files_into_folder_by_extension.py /path/to/folder

# Preview what would happen (no files moved)
python put_files_into_folder_by_extension.py --dry-run /path/to/folder

# Also organise files inside sub-directories
python put_files_into_folder_by_extension.py --recursive /path/to/folder
```

### 2. High-Level Categorization
Once organized by extension, you can group those folders into higher-level categories like `Images/`, `Documents/`, and `Video/` using `categorize_organized_folders.py`.

```bash
# Categorize extension folders in the current directory
python categorize_organized_folders.py

# Categorize a specific folder
python categorize_organized_folders.py /path/to/folder

# Preview categorization
python categorize_organized_folders.py --dry-run /path/to/folder
```

## Options (put_files_into_folder_by_extension.py)

| Flag | Description |
|---|---|
| `folder` | Directory to organise (default: CWD) |
| `--dry-run` | Print planned moves without executing them |
| `--recursive` | Also process files in sub-directories |
| `-v` / `--verbose` | Show debug-level output |

## Categorization Logic
The `categorize_organized_folders.py` script uses the following default mapping:

- **Images**: `png`, `jpg`, `jpeg`, `webp`, `gif`, `avif`, `heic`, `svg`, `psd`, `cr2`, `ico`
- **Documents**: `pdf`, `doc`, `docx`, `txt`, `rtf`, `ppt`, `pptx`, `xls`, `xlsx`, `md`, `csv`, `xps`, `epub`, `azw3`, `opml`, `resolved`
- **Video**: `mp4`, `mkv`, `avi`, `flv`, `wmv`, `mpg`, `m4v`, `ogv`, `swf`, `drp`, `prproj`, `pdrproj`, `mov`
- **Audio**: `mp3`, `wav`, `flac`, `ogg`, `m4a`, `m4b`, `aac`, `pls`, `m3u`, `xm`
- **Software_and_Archives**: `zip`, `rar`, `7z`, `gz`, `bz2`, `deb`, `msi`, `exe`, `iso`, `ova`, `jar`, `apk`, `vsix`, `nzb`, `dlc`, `btsearch`
- **Code_and_Scripts**: `py`, `html`, `htm`, `js`, `css`, `sh`, `bat`, `ps1`, `lua`, `xml`, `xht`, `ejs`, `c`, `cpp`, `h`
- **AI_and_Models**: `safetensors`, `gguf`, `pt`, `_AI`
- **Data_and_Config**: `json`, `yaml`, `yml`, `ini`, `log`, `db`, `sqlite3`, `dat`, `tpx`, `synapse4`, `ica`, `jnlp`, `crdownload`, `pp3`, `mcf`, `abs`, `aspx`

## Example output

```
INFO: photo.jpg  →  jpg/photo.jpg
INFO: notes.txt  →  txt/notes.txt
INFO: report.pdf →  pdf/report.pdf

INFO: Summary:
INFO:   .jpg                 1 file(s)
INFO:   .pdf                 1 file(s)
INFO:   .txt                 1 file(s)
INFO: Moved 3 file(s) in total.
```

