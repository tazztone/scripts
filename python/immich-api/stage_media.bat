@echo off
setlocal

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%stage_media.py"

:: Check if Python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found in PATH. Please install Python 3.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py"
    )
) else (
    set "PY_CMD=python"
)

:: If no arguments passed, run standard clean and open staging folders
if "%~1"=="" (
    echo [INFO] Running standard media staging with --clean and --open...
    %PY_CMD% "%PYTHON_SCRIPT%" --clean --open
) else (
    %PY_CMD% "%PYTHON_SCRIPT%" %*
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Staging script exited with an error.
    pause
)

endlocal
