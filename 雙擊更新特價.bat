@echo off
chcp 65001 >nul
title 澳洲三大超市特價情報 - 一鍵更新腳本
echo ==================================================
echo 🦘 正在爬取最新超市特價 (Coles / Woolworths / ALDI)...
echo ==================================================
echo.

python -c "from scrapers.updater import update_all_stores; update_all_stores(max_catalogue_pages=10)"
if %errorlevel% neq 0 (
    echo [警告] 爬蟲更新遇到部分連線問題，嘗試直接匯出既有資料...
)

echo.
echo 📊 正在匯出最新靜態資料庫 (specials.json & stats.json)...
python export_static_data.py

echo.
echo 📦 正在重新打包 Cloudflare Pages 上傳壓縮檔 (au-supermarket-specials-static.zip)...
powershell -Command "Compress-Archive -Path 'static\*' -DestinationPath 'au-supermarket-specials-static.zip' -Force"

echo.
echo ==================================================
echo ✅ 更新完成！
echo 1. 本地伺服器特價資料已是最新。
echo 2. 靜態上傳檔 au-supermarket-specials-static.zip 已打包好。
echo    若使用 Cloudflare Pages，只需將 static 目錄拖曳上傳即可！
echo ==================================================
echo.
pause
