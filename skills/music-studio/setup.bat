@echo off
rem One-time setup: ffmpeg, ACE-Step 1.5, models.  Double-click me.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows.ps1" %*
pause
