@echo off
title Cloudflare Pages Deployment
echo ===================================================
echo   Deploying AU Supermarket Specials to Cloudflare
echo ===================================================
echo.
echo Exporting latest specials data to static/data...
set PYTHON_EXE=C:\Users\rick9\AppData\Local\Python\pythoncore-3.14-64\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)
"%PYTHON_EXE%" export_static_data.py
echo.
echo Deploying to Cloudflare Pages...
if "%CLOUDFLARE_API_TOKEN%"=="" (
    echo Please set CLOUDFLARE_API_TOKEN environment variable.
)
npx wrangler pages deploy static --project-name=au-supermarket-specials
echo.
echo ===================================================
echo   Deployment finished! Live at:
echo   https://au-supermarket-specials.pages.dev
echo ===================================================
pause
