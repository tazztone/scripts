@echo off
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
