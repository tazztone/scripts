@echo off
:: =================================================================================================
:: Script Name: exiftool_copy_and_organize_by_date.bat
:: Description: Copies ARW, JPG, and MP4 files from a source directory to a destination directory,
::              organizing them into folders by date (Year/Year-Month-Day/YearMonthDay).
::              Files are renamed to include the timestamp.
:: Dependencies: exiftool (must be in PATH)
:: Usage: Edit the "source" and "destination" variables below, then run the script.
:: =================================================================================================

set "source=F:"
set "destination=X:"

echo Starting Transfer...
echo Source: %source%
echo Destination: %destination%
echo.

:: REAL RUN COMMAND (Single Line)
:: -o .    : COPIES files (Safety first). If you want to MOVE (delete from source), remove "-o ."
:: -P      : Preserves original file creation dates.

exiftool -r -o . -progress -P -ext ARW -ext jpg -ext mp4 -d "%destination%/%%Y/%%Y-%%m-%%d/%%Y%%m%%d" "-Filename<${FileModifyDate}-%%f%%-c.%%e" "-Filename<${DateTimeOriginal}-%%f%%-c.%%e" "%source%/"

echo.
echo -----------------------------------------------------------
echo Process complete.
echo -----------------------------------------------------------
pause
