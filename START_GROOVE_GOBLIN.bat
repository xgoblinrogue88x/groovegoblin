@echo off
setlocal
cd /d "%~dp0"
title Groove Goblin - Launcher
if "%~1"=="" (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch-GrooveGoblin.ps1"
) else (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch-GrooveGoblin.ps1" -PythonPath "%~1"
)
if errorlevel 1 (
    echo.
    echo Launch failed. Copy the error above for support.
    pause
    exit /b 1
)
endlocal
