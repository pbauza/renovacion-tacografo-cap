@echo off
setlocal EnableDelayedExpansion

set "DB_DIR=%LOCALAPPDATA%\RenovacionesTacografoCap"
set "DB_FILE=%DB_DIR%\renovaciones.db"
set "BACKUP_DIR=%DB_DIR%\backups"
set "SOURCE_BACKUP="

if not exist "%BACKUP_DIR%" (
  echo Backup directory not found: %BACKUP_DIR%
  echo Start the app at least once so backups are created.
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

echo Backup file not found: %~1
exit /b 1

:pick_latest
for /f "delims=" %%F in ('dir /b /a:-d /o:-n "%BACKUP_DIR%\renovaciones_*.db" 2^>nul') do (
  set "SOURCE_BACKUP=%BACKUP_DIR%\%%F"
  goto :restore
)

echo No DB backups found in: %BACKUP_DIR%
exit /b 1

:restore
if not exist "%DB_DIR%" mkdir "%DB_DIR%"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
if exist "%DB_FILE%" (
  set "ROLLBACK=%BACKUP_DIR%\renovaciones_before_restore_!STAMP!.db"
  copy /Y "%DB_FILE%" "!ROLLBACK!" >nul
  if errorlevel 1 (
    echo Could not create rollback backup. Close the app and retry.
    exit /b 1
  )
  echo Rollback copy created: !ROLLBACK!
)

copy /Y "%SOURCE_BACKUP%" "%DB_FILE%" >nul
if errorlevel 1 (
  echo Restore failed. Ensure the app is closed and retry.
  exit /b 1
)

echo Restored DB from: %SOURCE_BACKUP%
echo Current DB: %DB_FILE%

