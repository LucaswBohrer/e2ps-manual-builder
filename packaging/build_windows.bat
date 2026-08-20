@echo off
setlocal EnableExtensions

REM Build the Windows distribution from the repository root.
REM Requirements: Python 3.10+ (64-bit) and Inno Setup 6.

cd /d "%~dp0.."

python -m pip install --upgrade pip
python -m pip install -r requirements.txt "pyinstaller>=6.0,<7.0"

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q release 2>nul

python packaging\create_application_icon.py
python -m PyInstaller --noconfirm --clean packaging\E2PSManualBuilder.spec
if errorlevel 1 goto :error

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" goto :missing_inno

"%ISCC%" packaging\E2PSManualBuilder.iss
if errorlevel 1 goto :error

echo.
echo V2 build completed successfully.
echo Executable: dist\E2PS Manual Builder\E2PSManualBuilder.exe
echo Installer: release\E2PS-Manual-Builder-V2-Setup-2.0.0.exe
exit /b 0

:missing_inno
echo.
echo Inno Setup 6 was not found.
echo Install it from https://jrsoftware.org/isdl.php and run this file again.
exit /b 2

:error
echo.
echo Distribution build failed. Read the messages above.
exit /b 1
