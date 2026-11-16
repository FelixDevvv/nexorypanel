@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 exit /b 1
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 exit /b 1
".venv\Scripts\pyinstaller.exe" --noconfirm --clean --distpath . NexoryPanel.spec
if errorlevel 1 exit /b 1
echo Build ready: NexoryPanel.exe
pause
