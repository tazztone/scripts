@echo off
:: ---------------- CONFIGURATION ----------------
:: If you want to be asked for the drive letter every time, use:
:: set /p "source=Enter Source Drive (e.g. F:): "
:: set /p "destination=Enter Destination Drive (e.g. X:): "
set "source=F:"
set "destination=X:"
:: -----------------------------------------------

echo Starting Transfer...
echo Source: %source%
echo Destination: %destination%
echo.

:: EXPLANATION OF FLAGS:
:: -r        : Recursive (searches subfolders)
:: -o .      : Copy mode (does not delete source files)
:: -m        : Ignores minor warnings (cleaner log)
:: -progress : Shows progress bar
:: -P        : Preserves file modification date/time
:: -ext      : Specific file extensions to include (Added XML)

exiftool -r -o . -m -progress -P -ext ARW -ext jpg -ext mp4 -ext XML -d "%destination%/%%Y/%%Y-%%m-%%d/%%Y%%m%%d" "-Filename<${FileModifyDate}-%%f%%-c.%%e" "-Filename<${DateTimeOriginal}-%%f%%-c.%%e" "%source%/"

echo.
echo -----------------------------------------------------------
echo Process complete.
echo -----------------------------------------------------------
pause
