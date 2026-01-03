@echo off
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