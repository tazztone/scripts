# Windows Batch Scripts

This repository contains a collection of Windows batch scripts for file management and organization. The scripts are named according to the main tool they use and the action they perform.

## Scripts

### ExifTool Scripts
These scripts require [ExifTool](https://exiftool.org/) to be installed and available in your system's PATH.

*   **`exiftool_copy_and_organize_by_date.bat`**
    *   **Description**: Copies ARW, JPG, and MP4 files from a source directory (default `F:`) to a destination directory (default `X:`), organizing them into folders by date (`Year/Year-Month-Day/YearMonthDay`). Files are renamed to include the timestamp.
    *   **Note**: You need to edit the `source` and `destination` variables in the script before running it.

*   **`exiftool_rotate_mp4_270deg.bat`**
    *   **Description**: Rotates all MP4 files in the current directory by 270 degrees using ExifTool's `-Rotation` tag.

### Windows (Standard Batch) Scripts
These scripts use standard Windows command-line tools and do not require external dependencies.

*   **`windows_create_txt_for_each_png.bat`**
    *   **Description**: Creates a corresponding `.txt` file for each `.png` file in the current directory. You will be prompted to enter the text content to be written into the files.

*   **`windows_move_each_file_to_own_folder.bat`**
    *   **Description**: Moves each file in the current directory into a new subfolder named after the file itself.

*   **`windows_organize_files_by_extension.bat`**
    *   **Description**: Moves all files in the current directory into subfolders named after their file extension (e.g., all `.jpg` files go into a `jpg` folder).

*   **`windows_organize_images_by_date.bat`**
    *   **Description**: Moves `.jpg` and `.png` files into subfolders based on their last modified date (YYYY-MM-DD).

## Usage

1.  Download the script you want to use.
2.  Place it in the directory where you want to perform the operations (unless otherwise noted).
3.  Double-click the `.bat` file to run it.

**Caution**: Always back up your data before running scripts that move or modify files.
