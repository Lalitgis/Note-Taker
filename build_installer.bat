@echo off
rem Builds a Windows installer: dist\DailySidebarNext-Setup.exe
rem Needs Inno Setup 6 (free): winget install JRSoftware.InnoSetup
cd /d "%~dp0"
set PY=python
if exist "..\.venv\Scripts\python.exe" set PY=..\.venv\Scripts\python.exe
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    echo Inno Setup 6 was not found.
    echo Install it with:   winget install JRSoftware.InnoSetup
    echo or from https://jrsoftware.org/isdl.php  then run this file again.
    pause
    exit /b 1
)

for /f "delims=" %%v in ('%PY% -c "import dailysidebar; print(dailysidebar.__version__)"') do set VERSION=%%v
echo Building Daily Sidebar Next %VERSION% ...

%PY% -m pip install --upgrade pyinstaller || goto :fail
%PY% -m PyInstaller --noconfirm --windowed --name DailySidebarNext --icon assets\icon.ico --add-data "assets;assets" main.py || goto :fail
"%ISCC%" /DMyAppVersion=%VERSION% installer\DailySidebarNext.iss || goto :fail

echo.
echo Done: dist\DailySidebarNext-Setup.exe
echo Double-click it to install. You can delete this source folder afterwards.
pause
exit /b 0

:fail
echo.
echo Build failed, see the messages above.
pause
exit /b 1
