@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
:: EXIFTOOL COPY AND ORGANIZE BY DATE
:: Copies photos/videos from source to destination, organizing by date.
:: ============================================================================

:: ---------------- CONFIGURATION ----------------
:: Hardcoded drives (comment out to enable prompts)
set "source=F:"
set "destination=X:"

:: File extensions to process (space-separated)
set "extensions=ARW jpg mp4 XML HIF"

:: Log file location (in destination root)
set "logfile=%destination%\exiftool_transfer.log"

:: Set to 1 for dry-run (test without copying), 0 for actual copy
set "dryrun=1"
:: ------------------------------------------------

:: ---------------- INTERACTIVE MODE (uncomment to enable) ----------------
:: set /p "source=Enter Source Drive (e.g. F:): "
:: set /p "destination=Enter Destination Drive (e.g. X:): "
:: set /p "dryrun=Dry-run mode? (1=yes, 0=no): "
:: ------------------------------------------------------------------------

:: Get timestamp for logging
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set "timestamp=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%:%datetime:~12,2%"

:: ============================================================================
:: VALIDATION
:: ============================================================================

echo.
echo ============================================================
echo   EXIFTOOL COPY AND ORGANIZE BY DATE
echo ============================================================
echo.

:: Check if source exists
if not exist "%source%\" (
    echo [ERROR] Source drive "%source%" does not exist or is not accessible.
    echo Please check the drive letter and try again.
    pause
    exit /b 1
)

:: Check if destination exists
if not exist "%destination%\" (
    echo [ERROR] Destination drive "%destination%" does not exist or is not accessible.
    echo Please check the drive letter and try again.
    pause
    exit /b 1
)

:: Check if exiftool is available
where exiftool >nul 2>&1
if errorlevel 1 (
    echo [ERROR] exiftool not found in PATH.
    echo Please install exiftool and ensure it's in your PATH.
    pause
    exit /b 1
)

:: ============================================================================
:: BUILD EXTENSION FLAGS
:: ============================================================================

set "extflags="
for %%E in (%extensions%) do (
    set "extflags=!extflags! -ext %%E"
)

:: ============================================================================
:: DISPLAY SETTINGS
:: ============================================================================

echo   Source:       %source%
echo   Destination:  %destination%
echo   Extensions:   %extensions%
echo   Log file:     %logfile%
if "%dryrun%"=="1" (
    echo   Mode:         DRY-RUN (no files will be copied^)
) else (
    echo   Mode:         COPY
)
echo.
echo ------------------------------------------------------------

:: ============================================================================
:: LOGGING HEADER
:: ============================================================================

echo. >> "%logfile%"
echo ============================================================ >> "%logfile%"
echo [%timestamp%] Transfer started >> "%logfile%"
echo Source: %source% >> "%logfile%"
echo Destination: %destination% >> "%logfile%"
echo Extensions: %extensions% >> "%logfile%"
if "%dryrun%"=="1" (
    echo Mode: DRY-RUN >> "%logfile%"
) else (
    echo Mode: COPY >> "%logfile%"
)
echo ============================================================ >> "%logfile%"

:: ============================================================================
:: EXECUTE EXIFTOOL
:: ============================================================================

:: FLAG EXPLANATIONS:
:: -r          : Recursive (searches subfolders)
:: -o .        : Copy mode (does not delete source files)
:: -wm cg      : Skip existing files (create only, gracefully skip if exists)
:: -m          : Ignores minor warnings (cleaner log)
:: -progress   : Shows progress bar
:: -P          : Preserves file modification date/time
:: -ext        : Specific file extensions to include

:: Date tag priority (last one wins, so list from lowest to highest priority):
:: 1. FileModifyDate     - Fallback: file system modification date
:: 2. FileCreateDate     - Windows file creation date  
:: 3. CreateDate         - Common in MP4/video files
:: 4. MediaCreateDate    - Specific to video container formats
:: 5. DateTimeOriginal   - Best: actual capture date from camera

if "%dryrun%"=="1" (
    echo [DRY-RUN] Simulating transfer...
    echo [DRY-RUN] Files would be copied to: %destination%
    echo.
    :: Note: -testname cannot be used with -o, so we show the path preview
    exiftool -r -m -progress -P %extflags% -d "%destination%/%%Y/%%Y-%%m-%%d/%%Y%%m%%d" "-testname<${FileModifyDate}-%%f%%-c.%%e" "-testname<${FileCreateDate}-%%f%%-c.%%e" "-testname<${CreateDate}-%%f%%-c.%%e" "-testname<${MediaCreateDate}-%%f%%-c.%%e" "-testname<${DateTimeOriginal}-%%f%%-c.%%e" "%source%/" 2>&1 | find /v "File not found"
    set "exitcode=!errorlevel!"
    echo.
    echo [DRY-RUN] The above shows what WOULD be copied.
    echo [DRY-RUN] No files were actually transferred.
) else (
    echo Starting transfer...
    echo Logging details to: %logfile%
    echo.
    
    :: Logic:
    :: -o . tells exiftool to COPY (not move). The "." is a dummy source-preservation target.
    :: We provide FULL ABSOLUTE PATHS in the Filename/date-string, so they land in %destination%.
    
    (
        exiftool -r -o . -wm cg -m -progress -P %extflags% -d "%destination%/%%Y/%%Y-%%m-%%d/%%Y%%m%%d" "-Filename<${FileModifyDate}-%%f%%-c.%%e" "-Filename<${FileCreateDate}-%%f%%-c.%%e" "-Filename<${CreateDate}-%%f%%-c.%%e" "-Filename<${MediaCreateDate}-%%f%%-c.%%e" "-Filename<${DateTimeOriginal}-%%f%%-c.%%e" "%source%/"
    ) >> "%logfile%" 2>&1
    
    set "exitcode=!errorlevel!"
    
    :: Show tail of log or success message
    echo Transfer finished. Output saved to log.
)

:: ============================================================================
:: ERROR HANDLING & LOGGING
:: ============================================================================

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set "endtimestamp=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%:%datetime:~12,2%"

echo.
echo ============================================================

if !exitcode! equ 0 (
    echo [SUCCESS] Transfer completed successfully.
    echo [%endtimestamp%] Transfer completed successfully >> "%logfile%"
) else if !exitcode! equ 1 (
    echo [WARNING] Transfer completed with minor warnings.
    echo [%endtimestamp%] Transfer completed with warnings (exit code: 1^) >> "%logfile%"
) else (
    echo [ERROR] Transfer encountered errors. Exit code: !exitcode!
    echo [%endtimestamp%] Transfer failed with exit code: !exitcode! >> "%logfile%"
)

echo ============================================================
echo.
echo Log saved to: %logfile%
echo.

pause
endlocal
exit /b !exitcode!
