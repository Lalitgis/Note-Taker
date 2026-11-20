@echo off
rem Builds dist\DailySidebarNext\DailySidebarNext.exe with PyInstaller.
cd /d "%~dp0"
set PY=python
if exist "..\.venv\Scripts\python.exe" set PY=..\.venv\Scripts\python.exe
%PY% -m pip install --upgrade pyinstaller
%PY% -m PyInstaller --noconfirm --windowed --name DailySidebarNext --icon assets\icon.ico --add-data "assets;assets" main.py
echo.
echo Done. The app is in dist\DailySidebarNext\
pause
