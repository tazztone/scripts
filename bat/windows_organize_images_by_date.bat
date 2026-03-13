@echo off
:: =================================================================================================
:: Script Name: windows_organize_images_by_date.bat
:: Description: Moves JPG and PNG files into subfolders based on their last modified date (YYYY-MM-DD).
:: Dependencies: None (standard Windows batch commands)
:: Usage: Run this script in the directory containing the images you want to organize.
:: =================================================================================================

setlocal enabledelayedexpansion

for %%F in (*.jpg *.png) do (
    for /f "tokens=1-3 delims=/ " %%A in ("%%~tF") do (
        set "day=%%A"
        set "month=%%B"
        set "year=%%C"
    )

    set "folder=!year!-!month!-!day!"

    if not exist "!folder!" mkdir "!folder!"

    move "%%F" "!folder!\"
)

echo Image organization complete.
pause
