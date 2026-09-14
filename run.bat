@echo off
setlocal

:menu
cls
echo ========================================
echo        Select a Python Script
echo ========================================
echo [1] Receive
echo [2] Transmit
echo [3] Exit
echo ========================================
set /p choice="Enter your choice (1, 2, or 3): "

if "%choice%"=="1" goto run_first
if "%choice%"=="2" goto run_second
if "%choice%"=="3" goto end

echo.
echo Invalid selection. Please enter 1, 2, or 3.
timeout /t 2 >nul
goto menu

:run_first
cls
echo Running Receive.py . . .
python ./script/Receive.py
goto finished

:run_second
cls
echo Running Transmit.py . . .
python ./script/Transmit.py
goto finished

:finished
echo.
echo ========================================
pause
goto menu

:end
echo Exit...
pause