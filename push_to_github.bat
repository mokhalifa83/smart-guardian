@echo off
title Push Smart Guardian to GitHub
cd /d "%~dp0"
echo ========================================================
echo  Pushing Smart Guardian Repository to GitHub:
echo  https://github.com/mokhalifa83/smart-guardian
echo ========================================================
echo.
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo [SUCCESS] Repository pushed to GitHub successfully!
) else (
    echo [ERROR] Push failed. Please check your GitHub credentials or permissions.
)
pause
