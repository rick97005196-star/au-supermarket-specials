@echo off
chcp 65001 > nul
echo ===================================================
echo   🦘 澳洲三大超市每週特價追蹤助手 (Woolworths / Coles / ALDI)
echo ===================================================
echo.
echo 正在檢查與啟動服務...

REM 優先使用本機 Python
set PYTHON_EXE=C:\Users\rick9\AppData\Local\Python\pythoncore-3.14-64\python.exe

if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

REM 自動開啟預設瀏覽器
start "" http://localhost:8000

REM 啟動 FastAPI 伺服器
"%PYTHON_EXE%" -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
