---
description: How to setup, execute data pipeline, run Streamlit dashboard, and deploy Taiwan Weather Map
---

# Taiwan Weather Map Project Workflow

This workflow guides you through setting up the environment, acquiring CWA weather data, initializing the SQLite database, running the Streamlit interactive weather web app, and committing updates to GitHub.

## Step 1: Environment Setup

1. Ensure Python 3.10+ is installed on your system.
2. Clone the repository and navigate into the project directory:
   ```bash
   git clone https://github.com/ChengxuanWu/TW_weather_map.git
   cd TW_weather_map
   ```
3. Install required Python packages:
   // turbo
   ```bash
   pip install -r requirements.txt
   ```

## Step 2: CWA API Configuration

1. Register for an account on the [CWA Open Data Platform](https://opendata.cwa.gov.tw/).
2. Obtain your **Authorization Key (API Key)** from the member center.
3. Create an environment variable or set your key in `config.py` / `.env`:
   ```bash
   CWA_API_KEY="YOUR_AUTHORIZATION_KEY"
   ```

### CWA Temperature Forecast Datasets Reference

Select the appropriate dataset / table based on the required granularity and time horizon:

| Coverage / Granularity | Dataset ID (Table ID) | Dataset Name (資料集名稱) | Temperature Elements Included |
| :--- | :--- | :--- | :--- |
| **All Taiwan (22 Counties/Cities - 36 Hours)** | `F-C0032-001` | 一般天氣預報-今明相當天氣預報 | `MinT` (最低溫), `MaxT` (最高溫) |
| **All Taiwan (368 Townships - Future 2 Days / 3-Hourly)** | `F-D0047-091` | 鄉鎮天氣預報-台灣未來2天逐3小時天氣預報 | `T` (氣溫), `AT` (體感溫度), `MinT`, `MaxT` |
| **All Taiwan (368 Townships - Future 1 Week)** | `F-D0047-089` | 鄉鎮天氣預報-台灣未來1週天氣預報 | `T` (氣溫), `AT` (體感溫度), `MinT`, `MaxT` |

## Step 3: Fetch Data & Initialize Database

1. Execute the data ingestion script to fetch weather forecast JSON data from CWA API:
   // turbo
   ```bash
   python fetch_weather.py
   ```
2. The script parses MinT/MaxT temperature data and populates the SQLite database (`data.db`) under the `TemperatureForecasts` table.

## Step 4: Launch Interactive Streamlit Web App

1. Start the Streamlit application server:
   // turbo
   ```bash
   streamlit run app.py
   ```
2. Open your browser at `http://localhost:8501`.
3. Interact with the application:
   - Select regions (北部地區, 中部地區, 南部地區, etc.) to view 7-day temperature trends.
   - Pick dates to view the Folium interactive map with temperature color scales.

## Step 5: Version Control & GitHub Sync

1. After making code or documentation updates, verify git status:
   ```bash
   git status
   ```
2. Commit and push your changes:
   ```bash
   git add .
   git commit -m "feat: enhance weather dashboard features"
   git push origin main
   ```
