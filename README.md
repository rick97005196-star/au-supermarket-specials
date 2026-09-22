# 🦘 澳洲三大超市每週特價追蹤與採買助手 (Woolworths · Coles · ALDI)

專為在澳洲生活與採買設計的每週特價追蹤軟體。整合澳洲三大超市（Woolworths、Coles、ALDI）的最新每週型錄與半價特價（1/2 Price），提供秒級搜尋、超市比價、智慧分類採買清單與一鍵複製功能。

---

## 🌟 核心特色

1. **三家超市特價一次看**：
   - 🟢 **Woolworths**：每週型錄、半價（1/2 Price）專區、各式折扣。
   - 🔴 **Coles**：每週型錄、半價（1/2 Price）專區、特價食品與日用品。
   - 🔵 **ALDI**：Super Savers 每週特價品項、週三/週六 Special Buys。
2. **中英雙語關鍵字搜尋**：
   - 輸入「牛奶」自動對應 `milk`、「蛋」自動對應 `egg`、「冰淇淋」自動對應 `ice cream` 等常見生活品項。
3. **半價（1/2 Price）專屬篩選**：
   - 快速切換「只要半價」，幫您鎖定 50% OFF 的超值好康。
4. **超市分組採買清單**：
   - 一鍵將商品加入清單，系統自動按 Woolworths、Coles、ALDI 獨立分組。
   - 計算各店小計與全單預計節省金額。
   - 提供實體採買勾選功能，買完直接打勾。
   - 支援「一鍵複製清單」，格式清晰，可直接發送到手機 LINE 或通訊軟體。
5. **本地 SQLite 儲存**：
   - 資料抓取後永久快取於本機 SQLite，搜尋查詢極速響應，離線也能查看。
6. **一鍵更新**：
   - 澳洲超市每週三換檔，點擊網頁右上角的「更新特價型錄」即可自動爬取最新優惠。

---

## 🚀 快速啟動方式

### 方法一：Windows 一鍵啟動 (推薦)
直接雙擊點擊專案目錄下的：
```bat
run.bat
```
程式會自動啟動伺服器並在您的預設瀏覽器開啟 `http://localhost:8000`。

### 方法二：命令列啟動
```powershell
cd C:\Users\rick9\.gemini\antigravity\scratch\au-supermarket-specials
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
開啟瀏覽器前往：`http://localhost:8000`

---

## 📅 澳洲超市採買小撇步

- **特價換檔日**：
  - **Woolworths & Coles**：每週三早上正式更換每週型錄（檔期通常為週三至下週二）。
  - **ALDI**：常態 Super Savers 每週更新；每週三與週六推出限量 Special Buys。
- **手機使用**：
  - 伺服器啟動於 `0.0.0.0:8000`，只要您的手機與電腦處於同一個 Wi-Fi 區域網路，可在手機瀏覽器輸入 `http://<電腦IP>:8000`（如 `http://192.168.1.100:8000`）即可在超市現場邊推車邊看清單！

---

## 📂 專案檔案結構

```
au-supermarket-specials/
├── data/
│   └── specials.db            # SQLite 資料庫 (特價品與採買清單)
├── scrapers/
│   ├── coles_scraper.py       # Coles 特價型錄爬蟲
│   ├── woolies_scraper.py     # Woolworths 特價型錄爬蟲
│   ├── aldi_scraper.py        # ALDI Super Savers / Special Buys 爬蟲
│   └── updater.py             # 統一更新調度器
├── static/
│   ├── index.html             # 現代化 Web 介面 (Tailwind CSS)
│   └── app.js                 # 前端互動邏輯 (搜尋/篩選/清單管理)
├── database.py                # 資料庫 CRUD 操作模組
├── main.py                    # FastAPI 後端 API 伺服器
├── requirements.txt           # Python 相依套件清單
├── run.bat                    # Windows 一鍵啟動腳本
└── README.md                  # 專案說明文件
```
