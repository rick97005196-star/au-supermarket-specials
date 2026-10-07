# 🇦🇺 澳洲超市每週特價比價站 (AU Supermarket Specials) - 專案交接與 AI 上下文提示詞

> **使用說明**：若要讓其他 AI（如 Claude、ChatGPT、Cursor、Copilot 等）接手本專案，您可以直接將本文件整篇複製貼給該 AI 作為 **System Prompt / 專案上下文說明**。

---

## 📌 1. 專案概述 (Project Overview)
- **專案名稱**：澳洲超市每週特價比價站 (AU Supermarket Specials)
- **主要用戶**：澳洲華人、留學生、打工度假 (WHV) 族群。
- **核心功能**：
  1. **每週特價同步**：自動抓取澳洲三大超市（Woolworths、Coles、ALDI）每週三更替的半價與精選特價。
  2. **下週型錄預告 (Next Week Preview)**：提前公佈下週即將生效的特價。
  3. **購物清單與即時計算**：勾選商品、累計省下金額與總價、支援離線本地儲存。
  4. **四語系即時切換**：繁體中文（台灣習慣用詞）、英文、日文、韓文。
  5. **13 大部門智能分類**：生鮮蔬果、肉品、海鮮、蛋奶、烘焙、冷凍、糧油調味、休閒零食、飲料、酒類、美妝保健、日用清潔、寵物用品。
  6. **雙模式運行**：支援本地 Python FastAPI 伺服器動態查詢，亦支援一鍵靜態化部署至 Cloudflare Pages。
- **線上網址**：`https://au-supermarket-specials.pages.dev`
- **GitHub 倉庫**：`https://github.com/rick97005196-star/au-supermarket-specials`

---

## 🛠️ 2. 技術棧 (Tech Stack)
- **前端**：純原生 HTML5 + Vanilla JavaScript + CSS（Tailwind 實用類別風格設計、深色/淺色模式、完美支援手機與桌面 RWD）。零 npm 繁重構建依賴，靜態載入速度極快。
- **後端 API**：Python 3.10+ / FastAPI / Uvicorn。
- **資料庫**：SQLite3 (`data/specials.db`)。
- **爬蟲工具**：`requests` + `beautifulsoup4`（高效純 HTTP 爬蟲）+ 備用 `selenium`。
- **AI 翻譯引擎**：Google Gemini API (`gemini-2.5-flash`) + 本地澳洲超市專業名詞字典修復庫。
- **CI/CD 自動化**：GitHub Actions 爬取與部署 (`.github/workflows/auto_update.yml`)。準時啟動靠 Cloudflare 定時器 (`cloudflare/update-timer`，週一至週三每 30 分鐘、週三 00:01 換週、週四至週日每天兩次)，GitHub 自己的排程常被略過，只當備援；定時器停擺時會寄信通知 (`scripts/check_timer.py`)。
- **託管平台**：Cloudflare Pages (Direct Upload / Wrangler)。

---

## 📂 3. 專案目錄結構 (Repository Structure)

```text
au-supermarket-specials/
├── .github/
│   └── workflows/
│       ├── auto_update.yml       # 爬取、翻譯、檢查與自動發布（由定時器啟動）
│       └── deploy_timer.yml      # 部署 Cloudflare 定時器
├── cloudflare/
│   └── update-timer/             # Cloudflare 定時器：準時啟動 auto_update.yml（沒有公開網址）
├── data/
│   └── specials.db               # SQLite 資料庫 (特價品、購物清單、更新時間元數據)
├── scrapers/
│   ├── aldi_scraper.py           # ALDI 動態日期/主題爬蟲 (Super Savers + Special Buys)
│   ├── coles_scraper.py          # Coles 每週型錄爬蟲 (本週半價 + 下週預告)
│   ├── woolies_scraper.py        # Woolworths 每週型錄爬蟲 (本週半價 + 下週預告)
│   └── updater.py                # 統一排程執行器 (協調整合三大超市爬蟲與入庫)
├── scripts/
│   └── auto_translate.py         # AI 多語系翻譯引擎 (Gemini API 批次處理 + 防呆字典)
├── static/                       # Cloudflare Pages 靜態網站發布目錄
│   ├── index.html                # 前端主頁面
│   ├── css/
│   │   └── style.css             # 完整樣式表 (包含卡片佈局、標籤置頂排版、RWD)
│   ├── js/
│   │   ├── app.js                # 前端核心邏輯 (篩選、搜尋、多語切換、購物清單)
│   │   └── i18n.js               # UI 介面多語系文本字典
│   └── data/
│       ├── specials.json         # 匯出的全站特價商品快照 (供靜態網站讀取)
│       ├── stats.json            # 統計數據 (各超市數量、半價數量、檔期)
│       └── translations.json     # 全商品翻譯快取字典 (超過 4,000 筆)
├── categories.py                 # 13 大分類器 (正則規則) 與人氣熱門商品評分演算法
├── database.py                   # SQLite 操作層 (增刪查改、防清空保護機制)
├── deploy_cloudflare.bat         # 本地一鍵部署至 Cloudflare 批次檔
├── export_static_data.py         # 將 SQLite 資料導出為 static/data/*.json
├── main.py                       # FastAPI 後端主程式
└── requirements.txt              # Python 套件依賴清單
```

---

## 🧠 4. 關鍵業務邏輯與架構細節 (Key Logic & Rules)

### ① 澳洲超市週期機制 (Wednesday Cycle)
- 澳洲超市特價以**每週三**為基準日（週期：週三～隔週二）。
- `period` 欄位區分：
  - `'current'`：當期特價（本週三生效）。
  - `'next'`：下週預告（下週三即將生效，通常於週一或週二釋出型錄）。

### ② ALDI 爬蟲特殊處理
- ALDI 網址採動態日期（如 `/special-buys/2026-09-23`）及主題分頁（如 `?theme=Kids+Toys`）。
- **避坑重點**：ALDI 的 HTML 結構中，單位比較價格（如 `($2.20 per 100 g)`）先於售價（`$0.99`）出現。爬蟲必須精確選取 `[data-test="product-tile__price"]` 避免抓錯價格。

### ③ 防清空保護機制 (Anti-wipeout Guard)
- 在 `database.py` 的 `save_specials()` 中設有防護門檻：若既有資料筆數大於 400，但新爬取的資料筆數異常偏低時，會自動阻止 `DELETE` 清空操作，避免網路或反爬問題導致線上頁面反白。

### ④ 商品卡片設計排版規範
- **頂部標籤列**：超市標籤（Coles / Woolworths / ALDI）與人氣/新品標籤獨立放置於圖片上方專屬空間，不遮擋商品圖片。
- **半價圓形標籤**：黃底紅字的 `1/2` 標誌懸浮於圖片右上角。
- **標題與翻譯高度**：英文主標題限制 3 行，多語翻譯副標題限制 2 行，過長文字自帶滑鼠懸停 (hover) 提示，不會跑版或被截斷。

---

## 🚀 5. 常見維護指令 (Quick Reference Commands)

| 任務 | 執行指令 |
| :--- | :--- |
| **啟動本地開發伺服器** | `python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload` |
| **執行全超市爬蟲更新** | `python -c "from scrapers.updater import update_all_stores; update_all_stores()"` |
| **僅更新 ALDI 爬蟲** | `python scrapers/aldi_scraper.py` |
| **執行 AI 批次翻譯** | `python scripts/auto_translate.py` |
| **導出靜態 JSON 檔案** | `python export_static_data.py` |
| **手動發布至 Cloudflare** | `npx wrangler pages deploy static --project-name=au-supermarket-specials` |
