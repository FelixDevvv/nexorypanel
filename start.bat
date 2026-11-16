@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python 3.11+ is required. Creating the NexoryPanel environment...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Could not create the virtual environment. Install Python 3.11+ and try again.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
  )
)
echo NexoryPanel local server: http://127.0.0.1:5000
echo Press Ctrl+C to stop. Application logs are shown in this terminal.
set NEXORY_OPEN_BROWSER=true
".venv\Scripts\python.exe" app.py
if errorlevel 1 pause
