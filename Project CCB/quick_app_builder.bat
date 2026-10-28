@echo off
title CalmCircleBreath Build Script
echo ===============================
echo  Building CalmCircleBreath App
echo ===============================

REM --- Optional: activate venv ---
REM call venv\Scripts\activate

REM --- Clean up old builds ---
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist CalmCircleBreath.spec del CalmCircleBreath.spec

REM --- Ensure PyInstaller is available ---
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM --- Build executable ---
echo.
echo Building EXE...
pyinstaller --noconsole --onefile --windowed --icon=assets\logo.ico --name="CalmCircleBreath" app.py

if %errorlevel% neq 0 (
    echo Build failed. Check for errors above.
    pause
    exit /b
)

REM --- Define install directory ---
set INSTALL_DIR="C:\Program Files\CalmCircleBreath"

REM --- Create folder in Program Files (requires admin rights) ---
echo.
echo Creating install folder at %INSTALL_DIR%
mkdir %INSTALL_DIR% >nul 2>&1

REM --- Copy built exe and assets ---
echo Copying files...
copy /Y "dist\CalmCircleBreath.exe" %INSTALL_DIR% >nul
xcopy assets %INSTALL_DIR%\assets /E /I /Y >nul

REM --- Create a desktop shortcut ---
echo Creating desktop shortcut...
set SHORTCUT="%USERPROFILE%\Desktop\CalmCircleBreath.lnk"
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut(%SHORTCUT%); $s.TargetPath='%INSTALL_DIR%\CalmCircleBreath.exe'; $s.IconLocation='%INSTALL_DIR%\assets\logo.ico'; $s.Save()"

echo.
echo ==============================================
echo CalmCircleBreath built and installed!
echo Location: %INSTALL_DIR%
echo Shortcut on Desktop
echo ==============================================

pause