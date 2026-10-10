@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch-GrooveGoblin.ps1" -CheckOnly
set "GG_RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %GG_RESULT%
