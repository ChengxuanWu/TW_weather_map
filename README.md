# 🌤️ Taiwan Weather Forecast 台灣天氣預報 Web App

> **AI 創新微課程：從氣象資料到互動式天氣預報應用**  
> *Code Smarter, Build a Better Tomorrow! 用程式探索天氣．用資料看見台灣．用 AI 實現更多可能*

[![Tech Stack](https://img.shields.io/badge/Tech%20Stack-CWA%20API%20%7C%20JSON%20%7C%20Python%20%7C%20SQLite%20%7C%20Streamlit-blue.svg)](#-技術棧-tech-stack)
[![Instructor](https://img.shields.io/badge/Instructor-%E7%85%A5%E5%93%A5%20(Huan%20Brother)-orange.svg)](#-致謝--導師-acknowledgments)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 專案簡介 (Project Overview)

本專案為 **AI 創新微課程：Taiwan Weather Forecast** 實作成果。課程引導開發者從中央氣象署（CWA）Open Data 平台獲取台灣即時與預報氣象資料，透過 **Python** 解析 JSON、儲存至 **SQLite** 資料庫，並利用 **Streamlit** 與 **Folium** 打造具備互動式折線圖、氣溫資料表與台灣地圖視覺化的全功能天氣預報 Web App Dashboard。

---

## 🛠️ 技術棧 (Tech Stack)

* **數據來源**: 中央氣象署 CWA Open Data API (交通部中央氣象署)
* **資料格式**: JSON / GeoJSON
* **開發語言**: Python 3.10+
* **數據處理**: Pandas, Requests
* **資料庫**: SQLite 3
* **Web 框架**: Streamlit
* **地圖視覺化**: Folium / Streamlit-Folium
* **版本控制**: Git / GitHub

---

## 🗺️ 24 步驟學習與開發地圖 (24-Step Roadmap)

本專案遵循以下 24 個標準實作步驟，從零構建完整的天氣 Dashboard：

```
+-----------------------------------------------------------------------------------+
|                        Taiwan Weather Forecast 24-Step Roadmap                    |
+-----------------------------------------------------------------------------------+
|  [01-04] CWA API & 資料取得  -->  [05-07] JSON 解析與 Pandas 資料處理               |
|                                                                                   |
|  [08-10] SQLite 資料庫設計   -->  [11-16] Streamlit 互動 Web App 開發               |
|                                                                                   |
|  [17-20] Folium 地圖視覺化   -->  [21-24] GitHub 部署、延伸應用與 AI 探索          |
+-----------------------------------------------------------------------------------+
```

---

### 📚 階段一：API 資料取得與基礎介紹 (Steps 1–4)

#### Step 1: 課程介紹 (AI × 資料 × 天氣 × 實作)
* **課程目標**：掌握 API 資料串接、資料庫設計與 Web App 部署。
* **學習地圖**：從 API 請求到前端視覺化的全棧實作流程。
* **專案成果展示**：展示包含氣溫折線圖、數據表格與動態地圖的終端作品。

#### Step 2: 台灣的天氣與生活 (氣象的重要性)
* **天氣影響生活**：溫度、降雨、颱風對日常與產業的直接影響。
* **資料驅動決策**：利用歷史與預報數據優化出行、農業與商業規劃。
* **智慧應用案例**：結合 AI 進行微氣候預測與自動化提醒。

#### Step 3: 中央氣象署 CWA (Open Data 平台)
* **註冊帳號**：至 [交通部中央氣象署開放資料平臺](https://opendata.cwa.gov.tw/) 註冊。
* **取得 API Key**：於會員中心申請授權碼 (Authorization Key)。
* **選擇資料集**：選用「一般天氣預報-今明相當天氣預報」或「鄉鎮天氣預報」資料集。

#### Step 4: API 資料取得 (使用 Requests 取得 JSON)
使用 Python `requests` 模組對 CWA API 發送 GET 請求：

```python
import requests

url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
headers = {"Authorization": "YOUR_CWA_API_KEY"}
resp = requests.get(url, headers=headers)
data = resp.json()
```

---

### 🔍 階段二：JSON 解析與數據處理 (Steps 5–7)

#### Step 5: JSON 資料結構解析 (找到氣溫資料的位置)
深入剖析 CWA JSON 回傳結構，定位各區域與氣溫元素：

```json
{
  "records": {
    "location": [
      {
        "locationName": "中部地區",
        "weatherElement": [
          { "elementName": "MinT", "time": [...] },
          { "elementName": "MaxT", "time": [...] }
        ]
      }
    ]
  }
}
```

#### Step 6: 提取最高與最低氣溫 (資料分析與處理)
* **解析 JSON**：迴圈走訪 `location` 與 `weatherElement` 陣列。
* **提取 MinT / MaxT**：抽取對應時間區段之最低溫 (MinT) 與最高溫 (MaxT)。
* **轉換成結構化資料**：整理為扁平化的字典串列 (List of Dicts)。

#### Step 7: 資料整理與預覽 (使用 Pandas 觀察資料)
使用 `pandas` 轉置為 DataFrame 並進行預覽與型態轉換：

| regionName | dataDate | minT | maxT |
| :--- | :--- | :--- | :--- |
| 北部地區 | 2026-04-14 | 18.0 | 26.0 |
| 中部地區 | 2026-04-14 | 20.0 | 30.0 |
| 南部地區 | 2026-04-14 | 22.0 | 31.0 |

---

### 💾 階段三：SQLite 資料庫設計與查詢 (Steps 8–10)

#### Step 8: 建立 SQLite 資料庫 (儲存氣溫資料)
* **建立資料庫**：創建本地 `data.db` 檔案。
* **創建資料表**：建立 `TemperatureForecasts` 表。
* **插入氣溫資料**：將清整後的數據批次寫入資料庫。

#### Step 9: 資料庫 Schema 設計 (`TemperatureForecasts`)
設計結構化關聯式表 schema：

```sql
CREATE TABLE IF NOT EXISTS TemperatureForecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regionName TEXT NOT NULL,
    dataDate TEXT NOT NULL,
    minT REAL NOT NULL,
    maxT REAL NOT NULL,
    UNIQUE(regionName, dataDate) ON CONFLICT REPLACE
);
```

#### Step 10: 查詢資料驗證 (使用 SQL 檢查資料)
執行標準 SQL 語法驗證資料完整度：

```sql
-- 查詢所有地區清單
SELECT DISTINCT regionName FROM TemperatureForecasts;

-- 查詢指定地區（如：中部地區）之氣溫預報
SELECT * FROM TemperatureForecasts WHERE regionName = '中部地區';
```

---

### 🖥️ 階段四：Streamlit 互動 Web App 開發 (Steps 11–16)

#### Step 11: Streamlit 入門 (快速建立 Web App)
* **安裝環境**：`pip install streamlit pandas folium streamlit-folium`
* **基本結構**：建立 `app.py` 主程式。
* **Hello World**：執行 `streamlit run app.py` 啟動前端開發伺服器。

#### Step 12: 從資料庫讀取資料 (使用 SQL 查詢)
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("data.db")
df = pd.read_sql_query("SELECT * FROM TemperatureForecasts", conn)
conn.close()
```

#### Step 13: 下拉選單選擇地區 (互動式操作)
提供使用者動態選擇觀測區域（北部地區、中部地區、南部地區、東北部地區、東部地區、東南部地區）：

```python
import streamlit as st

region = st.selectbox(
    "Select Region",
    ["北部地區", "中部地區", "南部地區", "東北部地區", "東部地區", "東南部地區"]
)
```

#### Step 14: 繪製折線圖 (一週最高與最低氣溫)
利用 Streamlit 內建圖表或 Plotly / Matplotlib 繪製氣溫變化趨勢圖：
* 🔴 **MaxT (最高氣溫)**
* 🔵 **MinT (最低氣溫)**

#### Step 15: 顯示資料表格 (清楚呈現一週資料)
利用 `st.dataframe()` 或 `st.table()` 清晰展示日期、最低溫與最高溫資訊。

#### Step 16: 整合 Web App 介面 (選地區看氣溫預報)
打造整潔的 **Taiwan Weather Forecast Dashboard**，將地區選單、折線圖與數據明細卡片一體化呈現在單頁儀表板上。

---

### 🗺️ 階段五：進階台灣地圖視覺化與品質優化 (Steps 17–20)

#### Step 17: 進階：台灣地圖視覺化 (使用 Folium + Streamlit)
使用 `folium` 在地圖上標示台灣各分區並套用氣溫色階（Color Scale）：

* 🔵 **< 20°C**：藍色 (寒冷/舒適)
* 🟢 **20 - 25°C**：綠色 (宜人)
* 🟡 **25 - 30°C**：黃色 (偏熱)
* 🔴 **> 30°C**：紅色 (高溫)

#### Step 18: 選擇日期顯示地圖 (互動式天氣地圖)
* 提供日期選擇器 `st.date_input("Select Date")`。
* 地圖點擊彈窗 (Popup) 顯示詳細氣溫：例如 `中部地區 Min: 20°C | Max: 30°C`。

#### Step 19: 完整成果展示 (Taiwan Weather Dashboard)
將 Folium 互動地圖 (`st_folium`) 與 SQL 氣溫統計表無縫整合，提供雙欄位 (Two-column Layout) 高階響應式面板。

#### Step 20: 程式碼品質與優化 (更好的程式設計)
* **程式結構清晰**：採用模組化設計（拆分 API 抓取、DB 操作、UI 渲染）。
* **錯誤處理機制**：加入 `try-except` 捕抓 API 逾時與 DB 鎖定例外。
* **重複執行不重複插入**：使用 `UPSERT` 或 `INSERT OR REPLACE` 保持資料幂等性。
* **良好的註解**：完整 Python docstrings 與行內說明。

---

### 🚀 階段六：Git 上傳、延伸應用與總結 (Steps 21–24)

#### Step 21: 專案上傳至 GitHub (版本管理與備份)
```bash
git init
git add .
git commit -m "feat: complete Taiwan Weather Forecast Streamlit app"
git remote add origin https://github.com/ChengxuanWu/TW_weather_map.git
git branch -M main
git push -u origin main
```

#### Step 22: 延伸應用與想法 (從天氣氣象到更多可能)
* 💬 **天氣提醒 Line Bot**：每日定時推播當日高低溫與攜帶雨具提醒。
* 🧳 **旅遊行程建議**：結合氣象預報推薦適合室內或戶外景點。
* 🌾 **農業 / 防災應用**：針對寒害、豪大雨提供預警。
* 🤖 **結合 AI 做分析**：使用 LLM 產生自然語言天氣短評與穿搭建議。

#### Step 23: 回顧與重點整理 (你學到了什麼？)
1. ✅ **API 資料取得** (Requests + Authentication)
2. ✅ **JSON 資料分析** (Data extraction & transformation)
3. ✅ **SQLite 資料庫** (Schema, Queries & Persistence)
4. ✅ **Streamlit Web App** (UI Layout, Charts & Folium Maps)
5. ✅ **AI × Coding 實作流程** (Problem solving & Clean code)

#### Step 24: 下一步：繼續探索 (AI × Data × Real World)
* 🌐 探索更多 Open Data API (如：AQI 空氣品質、水資源、交通數據)
* 📊 強化資訊視覺化與 WebGL 渲染
* 🤖 使用 AI 輔助開發 (AI-assisted coding with Cursor/Copilot/Gemini)
* 💡 打造專屬於你的個人作品集！

---

## 🚀 快速開始 (Quick Start)

### 1. 複製專案 (Clone Repository)
```bash
git clone https://github.com/ChengxuanWu/TW_weather_map.git
cd TW_weather_map
```

### 2. 安裝依賴套件 (Install Dependencies)
```bash
pip install -r requirements.txt
```

> **`requirements.txt` 內容範例：**
> ```text
> requests>=2.31.0
> pandas>=2.0.0
> streamlit>=1.30.0
> folium>=0.15.0
> streamlit-folium>=0.18.0
> ```

### 3. 執行氣象資料抓取指令 (Fetch Weather Data)
```bash
python fetch_weather.py
```

### 4. 啟動 Streamlit Web Dashboard
```bash
streamlit run app.py
```

瀏覽器自動開啟 `http://localhost:8501` 即可開始使用！

---

## 📂 專案檔案結構 (Project Structure)

```text
TW_weather_map/
├── README.md              # 專案說明文件 (本檔案)
├── design.md              # 系統架構與設計規格書
├── requirements.txt       # Python 套件依賴清單
├── fetch_weather.py       # CWA API 抓取與 SQLite 寫入腳本
├── app.py                 # Streamlit Web App 主程式
├── data.db                # SQLite 氣溫資料庫 (自動產生)
└── utils/
    ├── cwa_api.py         # CWA API 請求與 JSON 解析模組
    ├── db_manager.py      # SQLite CRUD 操作模組
    └── map_visualizer.py  # Folium 地圖繪製模組
```

---

## 🙏 致謝 & 導師 (Acknowledgments)

* **數據來源**: [交通部中央氣象署 CWA Open Data 平台](https://opendata.cwa.gov.tw/)
* **課程導師**: **煥哥 (Huan Brother)**  
  * *“技術可以解決問題，但更重要的是用技術創造更好的未來！”*  
  * **Learn Today, Build Tomorrow — AI for Learning, AI for a Better Taiwan**

---

© 2026 ChengxuanWu & 煥哥 AI 創新微課程. Released under the [MIT License](LICENSE).
