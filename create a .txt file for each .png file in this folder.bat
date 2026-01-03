@echo off
setlocal enabledelayedexpansion

echo This script will create a .txt file for each .png file in this folder.
echo.

:: Prompt user for the text content
set /p "textContent=Enter the text content for all .txt files: "

echo.
echo Creating .txt files...
echo.

:: Counter for created files
set count=0

:: Loop through all .png files in the current directory
for %%f in (*.png) do (
    :: Get filename without extension
    set "filename=%%~nf"
    
    :: Create .txt file with the same name (without newline)
    <nul set /p "=!textContent!" > "!filename!.txt"
    
    :: Show progress
    echo Created: !filename!.txt
    
    :: Increment counter
    set /a count+=1
)

echo.
if !count! equ 0 (
    echo No .png files found in this directory.
) else (
    echo Successfully created !count! .txt file(s).
)

echo.
pause
