@echo off
setlocal enabledelayedexpansion
title SMART GUARDIAN - Digital Oilfield & Reservoir Intelligence Platform

echo ======================================================================
echo           SMART GUARDIAN - PRODUCTION SURVEILLANCE & RESERVOIR
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/4] Running Automated Test Suite (138 Tests - Step 2A + 2B + 2C + Well Management)...
.\.venv\Scripts\python.exe -m pytest backend/tests -q
if %errorlevel% neq 0 (
    echo [ERROR] Test suite encountered failures.
    pause
    exit /b %errorlevel%
)
echo [PASS] All 138 Reservoir, Surveillance & Well Management Tests Passed.
echo.

echo [2/4] Executing End-to-End Architectural Verification...
set PYTHONPATH=backend
.\.venv\Scripts\python.exe backend/verify_e2e.py
if %errorlevel% neq 0 (
    echo [ERROR] E2E Verification failed.
    pause
    exit /b %errorlevel%
)
echo.

echo [3/4] Launching FastAPI Backend Server on port 8000...
start "Smart Guardian - Backend API (Port 8000)" cmd /k "cd /d ""%~dp0"" && set PYTHONPATH=backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Waiting for backend API to initialize...
timeout /t 3 /nobreak >nul

echo [4/4] Launching Next.js Frontend Dashboard on port 3000...
start "Smart Guardian - Frontend (Port 3000)" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo Waiting for frontend dev server...
timeout /t 4 /nobreak >nul

echo.
echo ======================================================================
echo   SMART GUARDIAN IS READY
echo   - Frontend Dashboard : http://localhost:3000
echo   - Backend Swagger API: http://127.0.0.1:8000/docs
echo ======================================================================
echo.

echo Opening Dashboard and Swagger API in your default browser...
start http://localhost:3000
start http://127.0.0.1:8000/docs

echo Services are actively running in their respective command windows.
echo You may close this launcher window at any time.
timeout /t 5 >nul
exit /b 0
