# Coles 一般價：改用 Rick 的電腦讀取

GitHub 的雲端主機讀 Coles 網站時，每次讀到第 5 頁就被 Coles 的機器人檢查擋下來，一週約 390 頁永遠讀不完，所以網站一直沒有 Coles 一般價。
這個工具改在 Rick 自己的 Windows 電腦上讀（同一支讀取程式 `scrapers/coles_regular.py --local`），讀完就自動放上 GitHub，網站幾分鐘後自動更新。

## 一次設定（約 3 分鐘）

在電腦上打開 **PowerShell**（開始選單搜尋 PowerShell），貼上這一行，按 Enter：

```powershell
irm https://raw.githubusercontent.com/rick97005196-star/au-supermarket-specials/main/tools/coles_local_setup.ps1 | iex
```

它會依序：

1. 在 `%USERPROFILE%\coles-reader\au-supermarket-specials` 建一個讀取專用的小資料夾（只下載需要的檔案，約 5 MB；不會動到其他資料夾）
2. 安裝 Python 套件 `curl_cffi`
3. **測試**：這台電腦能不能讀 Coles（10 頁，什麼都不存）。Coles 也擋的話就停在這裡，什麼都不改
4. 測試通過才繼續：確認能上傳 GitHub（可能跳出瀏覽器登入）→ 建立每天 18:00 的排程（電腦當時沒開，下次開機會補跑）→ 馬上開始第一次讀取

需要：Python（已經有）、Git（已經有）。可以重複執行，會自動更新。

## 平常

- 每天 18:00（或之後電腦一開）在背景讀，約 1 小時，看不到視窗；這週讀完之後的每天什麼都不做
- 一週讀完就把 `static/data/regular-coles.json` 推上 GitHub，網站自動上線（快速部署會被觸發）
- 讀取中途電腦關掉也沒關係，下次從停下的地方繼續
- 一樣慢慢讀（每頁間隔幾秒），遇到 Coles 的機器人檢查就停，**不會嘗試繞過**
- 這週由電腦讀的時候，雲端就不讀 Coles（進度檔裡有 `"by": "local"`），兩邊不會互相覆蓋

## 檢查／停止

- 紀錄檔：`%USERPROFILE%\coles-reader\au-supermarket-specials\tools\coles_local.log`
- 只測試：`python tools\coles_local.py --test`（在上面的資料夾裡）
- 手動馬上讀一次：`schtasks /Run /TN "Coles regular prices"`
- 停用：`schtasks /Delete /TN "Coles regular prices" /F`（雲端會恢復每週讀前 5 頁）

## 給 Claude Code / 技術細節

- `tools/coles_local_setup.ps1`：找到真正的 python.exe（排除 Microsoft Store 的假 python），下載並執行 `tools/coles_local_setup.py`
- `tools/coles_local_setup.py`：`git clone --depth 1 --filter=blob:none --sparse`，sparse-checkout 只留 `categories.py`、`scrapers/`、`tools/`、`data/ai_categories.json`、`data/coles_regular_progress.json`、`static/data/regular-coles.json`；`schtasks /Create /XML`（StartWhenAvailable、最長 2 小時、pythonw.exe 不開視窗），失敗時改用 `schtasks /SC DAILY /ST 18:00`
- `tools/coles_local.py`：只在乾淨的 main 上執行；`git pull --rebase` → `coles_regular.py --local` → 只 commit 兩個檔案（只有進度時加 `[skip ci]`）→ `git pull --rebase -X theirs` → `git push`（雲端同時改了進度檔時，以這台電腦讀的為準）
