@echo off
chcp 65001 >nul
title 上傳 AU Supermarket Specials 到 GitHub
cd /d "C:\Users\rick9\.gemini\antigravity\scratch\au-supermarket-specials"

echo =======================================================
echo   正在上傳 AU Supermarket Specials 到 GitHub...
echo =======================================================
echo.
echo 提示：如果稍後跳出視窗，請點擊「Sign in with your browser」即可登入授權。
echo.

git branch -M main
git push -u origin main

echo.
if %ERRORLEVEL% EQU 0 (
    echo =======================================================
    echo   🎉 恭喜！程式碼與自動排程已成功上傳到 GitHub！
    echo =======================================================
) else (
    echo =======================================================
    echo   上傳未完成，請確認是否已完成瀏覽器登入授權。
    echo =======================================================
)
echo.
pause
