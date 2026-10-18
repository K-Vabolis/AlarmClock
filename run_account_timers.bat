@echo off
cd /d "%~dp0"

where pythonw >nul 2>nul
if errorlevel 1 (
    echo Python is not installed or not on PATH.
    echo Get it from https://www.python.org/downloads/ and tick "Add Python to PATH".
    pause
    exit /b 1
)

start "" pythonw account_timers.py
exit /b 0
