@echo off
setlocal

:: Build NightCoop Manager as a single EXE
:: Requires: pyinstaller, PyQt6

echo ========================================
echo  NightCoop Manager - Build Script
echo ========================================
echo.

:: Check if pyinstaller is available
where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo ERROR: pyinstaller not found. Run: pip install pyinstaller
    pause
    exit /b 1
)

:: Clean previous build
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo Building single EXE...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "NightCoopManager" ^
    --icon "icon.ico" ^
    --add-data "assets/flags;assets/flags" ^
    --add-data "readme;readme" ^
    --add-data "logo.png;." ^
    --add-data "icon.ico;." ^
    --hidden-import "winreg" ^
    --hidden-import "PyQt6" ^
    main.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build complete!
echo  EXE is in: dist\NightCoopManager.exe
echo ========================================
pause
