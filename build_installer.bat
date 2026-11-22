@echo off
rem Builds a Windows installer: dist\DailySidebarNext-Setup.exe
rem Needs Python 3.10+ and Inno Setup 6 (this script offers to install Inno Setup with winget).
cd /d "%~dp0"
set PY=python
if exist "..\.venv\Scripts\python.exe" set PY=..\.venv\Scripts\python.exe
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

call :find_iscc
if not defined ISCC (
    echo Inno Setup 6 was not found. Trying to install it with winget...
    winget install --id JRSoftware.InnoSetup -e --accept-source-agreements --accept-package-agreements
    call :find_iscc
)
if not defined ISCC (
    echo.
    echo Inno Setup 6 is still missing. Install it from https://jrsoftware.org/isdl.php
    echo then run this file again.
    pause
    exit /b 1
)

echo Installing build tools...
%PY% -m pip install --upgrade pip >nul
%PY% -m pip install -r requirements.txt pyinstaller || goto :fail

for /f "delims=" %%v in ('%PY% -c "import dailysidebar; print(dailysidebar.__version__)"') do set VERSION=%%v
echo Building Daily Sidebar Next %VERSION% ...

%PY% -m PyInstaller --noconfirm --clean --windowed --name DailySidebarNext --icon assets\icon.ico --add-data "assets;assets" main.py || goto :fail
"%ISCC%" /DMyAppVersion=%VERSION% installer\DailySidebarNext.iss || goto :fail

echo.
echo Done: dist\DailySidebarNext-Setup.exe
echo Double-click it to install. You can delete this source folder afterwards.
explorer dist
pause
exit /b 0

:find_iscc
set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
exit /b 0

:fail
echo.
echo Build failed, see the messages above.
pause
exit /b 1
