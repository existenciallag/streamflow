@echo off
REM ============================================================
REM build_installer.bat — StreamFlow Windows Installer Builder
REM ============================================================
REM Run this once on a Windows PC that has Python installed.
REM It will produce:  output\StreamFlow_Setup_v1.0.exe
REM
REM Requirements:
REM   Python 3.10 or 3.11 (add to PATH during Python installation)
REM   Inno Setup 6  — https://jrsoftware.org/isinfo.php (default install path)
REM ============================================================

setlocal

echo.
echo ============================================================
echo  StreamFlow — Windows Installer Builder
echo ============================================================
echo.

REM ── 1. Check Python ──────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11 and add it to PATH.
    pause & exit /b 1
)
echo [OK] Python found.

REM ── 2. Install / upgrade build tools ─────────────────────────
echo.
echo [1/5] Installing build requirements...
pip install --upgrade pip pyinstaller >nul
pip install -r requirements.txt >nul
echo [OK] Dependencies installed.

REM ── 3. Clean previous build ───────────────────────────────────
echo.
echo [2/5] Cleaning previous build artifacts...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist
if exist output  rmdir /s /q output
echo [OK] Clean.

REM ── 4. PyInstaller — create the application bundle ───────────
echo.
echo [3/5] Building application bundle (this takes 3-5 minutes)...
pyinstaller streamflow.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller failed. Check the output above for details.
    pause & exit /b 1
)
echo [OK] Bundle created at dist\StreamFlow\

REM ── 5. Create placeholder so Inno Setup can create db\ dir ───
mkdir db_placeholder 2>nul
echo . > db_placeholder\keep

REM ── 6. Inno Setup — create the installer .exe ─────────────────
echo.
echo [4/5] Building installer...

REM Try the default Inno Setup 6 installation paths
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if "%ISCC%"=="" (
    echo [WARN] Inno Setup not found at default path.
    echo        Download from https://jrsoftware.org/isinfo.php and install, then re-run.
    echo.
    echo        The application bundle is ready at dist\StreamFlow\
    echo        You can zip that folder and distribute it manually.
    pause & exit /b 0
)

mkdir output 2>nul
%ISCC% installer.iss
if errorlevel 1 (
    echo [ERROR] Inno Setup compilation failed.
    pause & exit /b 1
)

echo.
echo ============================================================
echo  [5/5] DONE!
echo  Installer:  output\StreamFlow_Setup_v1.0.exe
echo  Size:       ~300-400 MB (includes Python + all libraries)
echo ============================================================
echo.
echo  Distribute that single .exe file. Users just run it and
echo  click Next - Next - Finish.
echo.
pause
