@echo off
setlocal

cd /d "%~dp0"

echo Installing Python requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install requirements.
  exit /b 1
)

echo Starting application...
python main.py

