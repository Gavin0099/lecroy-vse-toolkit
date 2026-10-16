@echo off
if exist "%~dp0USBTraceTriage.exe" (
    start "" /wait "%~dp0USBTraceTriage.exe"
) else (
    powershell.exe -NoProfile -STA -File "%~dp0tools\start-usb-control-tool.ps1"
    if errorlevel 1 pause
)
