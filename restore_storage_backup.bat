@echo off
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul 2>&1
if errorlevel 1 (
  echo Failed to access project directory: %SCRIPT_DIR%
  exit /b 1
)

set "STORAGE_DIR=%CD%\storage"
set "BACKUP_DIR=%STORAGE_DIR%\backups"
set "SOURCE_BACKUP="

if not exist "%STORAGE_DIR%" (
  echo Storage directory not found: %STORAGE_DIR%
  popd
  exit /b 1
)

if not exist "%BACKUP_DIR%" (
  echo Storage backup directory not found: %BACKUP_DIR%
  echo Start the app at least once so storage backups are created.
  popd
  exit /b 1
)

if "%~1"=="" goto :pick_latest
if /I "%~1"=="latest" goto :pick_latest

if exist "%~1" (
  set "SOURCE_BACKUP=%~1"
  goto :restore
)

if exist "%BACKUP_DIR%\%~1" (
  set "SOURCE_BACKUP=%BACKUP_DIR%\%~1"
  goto :restore
)

echo Storage backup file not found: %~1
popd
exit /b 1

:pick_latest
for /f "delims=" %%F in ('dir /b /a:-d /o:-n "%BACKUP_DIR%\storage_*.zip" 2^>nul') do (
  set "SOURCE_BACKUP=%BACKUP_DIR%\%%F"
  goto :restore
)

echo No storage backups found in: %BACKUP_DIR%
popd
exit /b 1

:restore
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
set "ROLLBACK=%BACKUP_DIR%\storage_before_restore_!STAMP!.zip"

set "PS_STORAGE_DIR=%STORAGE_DIR%"
set "PS_ROLLBACK=%ROLLBACK%"
powershell -NoProfile -Command "$storage = $env:PS_STORAGE_DIR; $rollback = $env:PS_ROLLBACK; $items = Get-ChildItem -LiteralPath $storage -Force | Where-Object { $_.Name -ne 'backups' }; if ($items.Count -gt 0) { Compress-Archive -Path ($items | ForEach-Object { $_.FullName }) -DestinationPath $rollback -Force }"
if errorlevel 1 (
  echo Could not create rollback backup. Close app/processes using storage and retry.
  popd
  exit /b 1
)
echo Rollback backup created: %ROLLBACK%

for /f "delims=" %%F in ('dir /b /a:-d "%STORAGE_DIR%"') do (
  del /f /q "%STORAGE_DIR%\%%F" >nul 2>&1
)
for /f "delims=" %%D in ('dir /b /ad "%STORAGE_DIR%"') do (
  if /I not "%%D"=="backups" rd /s /q "%STORAGE_DIR%\%%D"
)

powershell -NoProfile -Command "Expand-Archive -LiteralPath '%SOURCE_BACKUP%' -DestinationPath '%STORAGE_DIR%' -Force"
if errorlevel 1 (
  echo Restore failed. Ensure app is closed and retry.
  popd
  exit /b 1
)

echo Restored storage from: %SOURCE_BACKUP%
echo Current storage path: %STORAGE_DIR%

popd

