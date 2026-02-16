@echo off
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul 2>&1
if errorlevel 1 (
  echo Failed to access project directory: %SCRIPT_DIR%
  exit /b 1
)

set "PY_CMD="
where py >nul 2>&1
if not errorlevel 1 set "PY_CMD=py -3.11"
if not defined PY_CMD (
  where python >nul 2>&1
  if not errorlevel 1 set "PY_CMD=python"
)
if not defined PY_CMD (
  echo Python not found. Install Python 3.11+ and try again.
  popd
  exit /b 1
)

if not exist requirements.txt (
  echo requirements.txt not found in: %CD%
  popd
  exit /b 1
)

if not defined DATABASE_URL (
  set "WIN_DB_DIR=%LOCALAPPDATA%\RenovacionesTacografoCap"
  if not exist "!WIN_DB_DIR!" mkdir "!WIN_DB_DIR!"
  set "WIN_DB_PATH=!WIN_DB_DIR!\renovaciones.db"
  set "WIN_DB_URL=sqlite+aiosqlite:///!WIN_DB_PATH:\=/!"
  set "DATABASE_URL=!WIN_DB_URL!"
  echo Using local Windows SQLite DB: !WIN_DB_PATH!
)

echo Installing Python requirements...
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install requirements.
  popd
  exit /b 1
)

echo Starting application...
%PY_CMD% main.py

popd
