@echo off
REM run_test.bat - Simple batch file to run tests on Windows

echo ===================================
echo IDF Modification Test Suite
echo ===================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Show menu
echo Select an option:
echo 1. Run setup (first time only)
echo 2. Run all tests
echo 3. Run baseline only
echo 4. Run efficient HVAC scenario
echo 5. Run efficient lighting scenario  
echo 6. Run envelope upgrade scenario
echo 7. Run comprehensive retrofit
echo 8. Run custom scenarios
echo 9. Exit
echo.

set /p choice="Enter your choice (1-9): "

if "%choice%"=="1" (
    echo Running setup...
    python setup_test.py
    pause
    goto :eof
)

if "%choice%"=="2" (
    echo Running all tests...
    python main_test.py
    pause
    goto :eof
)

if "%choice%"=="3" (
    echo Running baseline only...
    python main_test.py --scenarios baseline
    pause
    goto :eof
)

if "%choice%"=="4" (
    echo Running efficient HVAC scenario...
    python main_test.py --scenarios baseline efficient_hvac
    pause
    goto :eof
)

if "%choice%"=="5" (
    echo Running efficient lighting scenario...
    python main_test.py --scenarios baseline efficient_lighting
    pause
    goto :eof
)

if "%choice%"=="6" (
    echo Running envelope upgrade scenario...
    python main_test.py --scenarios baseline envelope_upgrade
    pause
    goto :eof
)

if "%choice%"=="7" (
    echo Running comprehensive retrofit...
    python main_test.py --scenarios baseline comprehensive_retrofit
    pause
    goto :eof
)

if "%choice%"=="8" (
    set /p scenarios="Enter scenario names separated by spaces: "
    echo Running scenarios: %scenarios%
    python main_test.py --scenarios %scenarios%
    pause
    goto :eof
)

if "%choice%"=="9" (
    echo Exiting...
    exit /b 0
)

echo Invalid choice!
pause