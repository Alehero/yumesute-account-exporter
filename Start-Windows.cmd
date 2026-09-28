@echo off
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo Install uv first: winget install --id=astral-sh.uv -e
  echo Then open a new terminal and try again.
  pause
  exit /b 1
)
uv run --locked --python 3.12 python launcher.py %*
pause
