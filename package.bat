@echo off
REM Get the directory of the batch file itself
set "SCRIPT_DIR=%~dp0"

echo Running PowerShell script: %SCRIPT_DIR%package.ps1

REM Execute the PowerShell script using the powershell.exe interpreter
powershell.exe -ExecutionPolicy Bypass -File "%SCRIPT_DIR%package.ps1"

if %ERRORLEVEL% NEQ 0 (
echo.
echo ERROR: PowerShell script failed.
pause
)
