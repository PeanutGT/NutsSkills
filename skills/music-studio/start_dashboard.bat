@echo off
rem Opens the Music Studio dashboard (http://127.0.0.1:8765). Close this window to stop it.
cd /d "%~dp0scripts"
python server.py
if errorlevel 1 (
  echo.
  echo Could not start. Is Python installed?  Try: python scripts\engine.py check
  pause
)
