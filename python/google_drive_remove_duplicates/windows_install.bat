@echo off
REM Create a virtual environment
python -m venv venv
REM Activate the virtual environment
call venv\Scripts\activate.bat
REM Install required packages
pip install -r requirements.txt
echo Virtual environment setup complete. 
pause 