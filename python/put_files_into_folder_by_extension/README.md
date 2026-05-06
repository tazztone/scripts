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

```bash
# Organize the current working directory
python put_files_into_folder_by_extension.py

# Organize a specific folder
python put_files_into_folder_by_extension.py /path/to/folder

# Preview what would happen (no files moved)
python put_files_into_folder_by_extension.py --dry-run /path/to/folder

# Also organise files inside sub-directories
python put_files_into_folder_by_extension.py --recursive /path/to/folder

# Combine flags
python put_files_into_folder_by_extension.py --dry-run --recursive /path/to/folder

# Verbose output
python put_files_into_folder_by_extension.py -v /path/to/folder
```

## Options

| Flag | Description |
|---|---|
| `folder` | Directory to organise (default: CWD) |
| `--dry-run` | Print planned moves without executing them |
| `--recursive` | Also process files in sub-directories |
| `-v` / `--verbose` | Show debug-level output |

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
