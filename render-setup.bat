@echo off
REM Render.com Deployment Setup Script (Windows)
REM Prepares the project for deployment on Render

setlocal enabledelayedexpansion
cls

echo.
echo ==========================================
echo Resume Verification - Render Setup
echo ==========================================
echo.

REM Check for Git
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Git not found. Please install Git first.
    pause
    exit /b 1
)
echo [OK] Git found

REM Check for npm
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] npm not found. Please install Node.js first.
    pause
    exit /b 1
)
echo [OK] npm found

REM Check for Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    pause
    exit /b 1
)
echo [OK] Python found

echo.
echo Step 1: Validating project structure...
if exist "render.yaml" (
    echo [OK] render.yaml exists
) else (
    echo [WARNING] render.yaml not found
)

if exist "backend\requirements.txt" (
    echo [OK] backend\requirements.txt exists
) else (
    echo [WARNING] backend\requirements.txt not found
)

if exist "frontend\package.json" (
    echo [OK] frontend\package.json exists
) else (
    echo [WARNING] frontend\package.json not found
)

echo.
echo Step 2: Checking environment configuration...
if exist ".env.render.production" (
    echo [OK] .env.render.production exists
) else (
    echo [WARNING] .env.render.production not found
)

if exist ".env" (
    echo [OK] .env exists (for local development)
) else (
    echo [WARNING] .env not found (optional)
)

echo.
echo Step 3: Validating render.yaml...
findstr /M "resume-verify-backend" render.yaml >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] render.yaml has backend service
) else (
    echo [ERROR] render.yaml missing backend service
    pause
    exit /b 1
)

findstr /M "resume-verify-frontend" render.yaml >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] render.yaml has frontend service
) else (
    echo [ERROR] render.yaml missing frontend service
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Setup validation complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Create a Render account: https://render.com
echo 2. Push your code to GitHub:
echo    git add .
echo    git commit -m "Prepare for Render deployment"
echo    git push origin main
echo 3. Deploy using Blueprint:
echo    https://dashboard.render.com/blueprints
echo 4. Set environment variables in Render dashboard
echo 5. View logs at dashboard.render.com
echo.
echo For detailed instructions, see: RENDER_DEPLOYMENT_GUIDE.md
echo.
pause
