# Bitwarden JSON Export Deduplicator

A Python utility to remove duplicate folders and items from Bitwarden JSON export files.

## Overview

If you've been using Bitwarden for a while, you might have accumulated duplicate entries in your vault. This can happen when importing from multiple sources, syncing issues, or manual entry errors. This tool helps clean up your Bitwarden vault by removing duplicates from the JSON export file.

The script identifies duplicates based on:
- For folders: Folder names
- For items: A composite key of name, type, username, password, and TOTP (URIs are ignored to ensure entries with the same credentials are deduplicated even if they point to different URLs)

## Features

- Removes duplicate folders and items from Bitwarden JSON exports
- Aggressively deduplicates by ignoring 'notes' and 'URIs'
- Preserves entries if their Name, Username, Password, or TOTP differ
- Preserves the first occurrence of each unique entry
- Maintains references between items and folders
- Generates detailed summary reports
- Command-line interface with customizable options
- No external dependencies (uses only Python standard library)

## Installation

No installation is required. Simply download the script and run it with Python 3.6 or higher.

```bash
# Clone the repository
git clone https://github.com/biplobice/bitwarden-deduplicator.git

# Navigate to the directory
cd bitwarden-deduplicator

# Make the script executable (Unix/Linux/macOS)
chmod +x deduplicate_bitwarden.py
```

## Usage

### Basic Usage

```bash
python deduplicate_bitwarden.py your_bitwarden_export.json
```

This will create a deduplicated file named `your_bitwarden_export_deduplicated.json` in the same directory.

### Advanced Options

```bash
python deduplicate_bitwarden.py your_bitwarden_export.json -o custom_output.json -s summary.md -q
```

#### Command-line Arguments

- `input_file`: Path to the Bitwarden JSON export file (required)
- `-o, --output`: Path to save the deduplicated JSON file (default: input_file_deduplicated.json)
- `-s, --summary`: Path to save the deduplication summary in Markdown format
- `-q, --quiet`: Suppress progress output

## Example

### Input

A Bitwarden JSON export file with duplicate folders and items.

### Output

1. A deduplicated JSON file that can be imported back into Bitwarden
2. (Optional) A summary report in Markdown format

### Sample Summary Report

```markdown
# Bitwarden JSON Deduplication Summary

## Original File
- Filename: bitwarden_export.json
- Size: 1,379,851 bytes (1.32 MB)
- Folders: 88
- Items: 1,794

## Deduplicated File
- Filename: bitwarden_export_deduplicated.json
- Size: 798,668 bytes (0.76 MB)
- Folders: 46
- Items: 1,015

## Results
- Removed 42 duplicate folders (47.7% reduction)
- Removed 779 duplicate items (43.4% reduction)
- Reduced file size by 581,183 bytes (42.1% reduction)

## Method
The deduplication was performed using a Python script that:
1. Identified duplicate folders based on folder names
2. Identified duplicate items based on a composite key of Name, Type, Username, Password, and TOTP (ignoring URIs and Notes)
3. Preserved the first occurrence of each unique entry
4. Maintained references between items and folders

Generated on: 2025-08-06 13:45:22
```

## How to Export/Import Bitwarden Data

### Exporting from Bitwarden

1. Log in to your Bitwarden vault
2. Go to "Tools" > "Export Vault"
3. Choose "JSON (Unencrypted)" as the file format
4. Enter your master password and click "Export Vault"
5. Save the JSON file to your computer

### Importing back to Bitwarden

1. Log in to your Bitwarden vault
2. Go to "Tools" > "Import Data"
3. Select "Bitwarden (json)" as the file format
4. Choose your deduplicated JSON file
5. Click "Import Data"

## Security Considerations

- The script processes unencrypted Bitwarden JSON exports, which contain sensitive information
- Always handle these files securely and delete them after use
- Run the script on a trusted computer
- Consider using the `-q` (quiet) option to prevent sensitive information from appearing in terminal output

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request