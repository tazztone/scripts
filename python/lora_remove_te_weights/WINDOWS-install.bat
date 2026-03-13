@echo off
REM Create venv if it doesn't exist
if not exist venv (
    python -m venv venv
)

REM Activate venv and install requirements
call venv\Scripts\activate
pip install --upgrade pip
pip install safetensors torch

echo Installation complete. You can now run WINDOWS-start.bat to use the script.
pause