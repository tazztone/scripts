@echo off
:: =================================================================================================
:: Script Name: exiftool_rotate_mp4_270deg.bat
:: Description: Rotates all MP4 files in the current directory by 270 degrees using ExifTool.
:: Dependencies: exiftool (must be in PATH)
:: Usage: Run this script in the directory containing the MP4 files you want to rotate.
:: =================================================================================================

echo Rotating all MP4 files in this folder by 270 degrees...
exiftool -Rotation=270 *.MP4

echo.
echo Process complete.
pause
