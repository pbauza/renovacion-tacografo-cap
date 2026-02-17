@echo off
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul 2>&1
if errorlevel 1 (
  echo Failed to access project directory: %SCRIPT_DIR%
  exit /b 1
)

where git >nul 2>&1
if errorlevel 1 (
  echo Git not found. Install Git and try again.
  popd
  exit /b 1
)

echo Fetching latest changes from origin...
git fetch origin
if errorlevel 1 (
  echo Failed to fetch from origin.
  popd
  exit /b 1
)

echo Switching to master...
git checkout master >nul 2>&1
if errorlevel 1 (
  echo Local master not found. Creating it from origin/master...
  git checkout -b master origin/master
  if errorlevel 1 (
    echo Could not switch to master. Commit/stash local changes and retry.
    popd
    exit /b 1
  )
)

echo Pulling latest version...
git pull origin master
if errorlevel 1 (
  echo Pull failed. Resolve conflicts or local changes and retry.
  popd
  exit /b 1
)

echo Repository updated to latest origin/master.
popd
