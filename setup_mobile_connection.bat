@echo off
title SafeRide AI - Mobile Connection Setup
echo ========================================================
echo  SafeRide AI - Android Mobile Connection Setup
echo ========================================================
echo.

set ADB="%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
if not exist %ADB% (
    set ADB=adb
)

echo [1/3] Checking connected Android devices...
%ADB% devices
echo.

echo [2/3] Setting up USB port forwarding (adb reverse tcp:8000 tcp:8000)...
%ADB% reverse tcp:8000 tcp:8000
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Port 8000 forwarded! Physical phone can reach http://127.0.0.1:8000 over USB.
) else (
    echo [WARNING] adb reverse failed. Ensure phone has USB Debugging enabled.
)
echo.

echo [3/3] Testing API connectivity from device...
%ADB% shell "curl -s http://127.0.0.1:8000/health"
echo.
echo.
echo ========================================================
echo Tips for Android Testing:
echo - USB Cable: URL is http://127.0.0.1:8000 (after running this script)
echo - Emulator: URL is http://10.0.2.2:8000
echo - Wi-Fi (No USB): URL is http://10.88.216.148:8000
echo ========================================================
pause
