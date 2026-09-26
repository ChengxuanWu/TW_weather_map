"""
Taiwan Weather Forecast Web App (app.py)
Interactive weather dashboard visualizing CWA temperature forecasts and real-time station observations across Taiwan.
Built with Streamlit, Folium, Pandas, and SQLite.
"""

import os
import sqlite3
from typing import Tuple
import pandas as pd
import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium

from utils.cwa_api import CWAApiClient
from utils.moenv_api import MOENVApiClient
from utils.db_manager import DBManager, DEFAULT_DB_PATH

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom CSS (Glassmorphism & Modern Theme)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="台灣氣象與即時觀測儀表板 | Taiwan Weather Map",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Handle pending states from map clicks before widgets render
if "pending_macro" in st.session_state:
    st.session_state["macro_sel"] = st.session_state.pop("pending_macro")
if "pending_county" in st.session_state:
    st.session_state["county_sel"] = st.session_state.pop("pending_county")

# Custom Glassmorphic CSS Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700;800&family=Inter:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans TC', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Concept 2 & 3: Constrain max width for readability, RWD native in Streamlit */
    .main .block-container {
        padding: 0 !important;
        max-width: 1400px !important;
        margin: 0 auto;
        padding-top: 3rem !important;
    }
    
    /* Keep header visible for Sidebar toggle */
    
    /* Concept 1: Hero Banner full width breakout */
    .hero-banner {
        width: 100vw;
        position: relative;
        left: 50%;
        right: 50%;
        margin-left: -50vw;
        margin-right: -50vw;
        margin-top: -3rem; 
        height: 60vh;
        background-image: linear-gradient(rgba(15, 23, 42, 0.5), rgba(15, 23, 42, 0.8)), url('https://images.unsplash.com/photo-1516912481808-3406841bd33c?q=80&w=2070&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        color: white;
        margin-bottom: 4rem; /* Concept 4: Whitespace */
        padding: 0 2rem;
    }
    
    .hero-title {
        font-size: 12rem;
        font-weight: 800;
        text-shadow: 0 4px 20px rgba(0,0,0,0.5);
        margin-bottom: 1rem;
        letter-spacing: 2px;
        color: white;
    }
    
    .hero-subtitle {
        font-size: 5rem;
        font-weight: 400;
        max-width: 800px;
        text-shadow: 0 2px 10px rgba(0,0,0,0.5);
        line-height: 1.6;
        color: rgba(255,255,255,0.9);
    }
    
    /* Concept 4: Whitespace and Visual Hierarchy */
    /* Map Container */
    .stFoliumContainer {
        border-radius: 16px;
        height: 85vh !important;
        width: 100% !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        margin-bottom: 4rem;
        border: 1px solid rgba(128,128,128,0.2);
    }
    
    /* KPI Panel container */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#left-panel-marker) {
        border: none !important;
        background: transparent !important;
        margin-bottom: 2rem;
        box-shadow: none !important;
        padding: 0 !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#left-panel-marker) h3 {
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: 1.5rem;
    }
    
    /* Metric Card Styling (Adapts to Light/Dark) */
    .metric-card {
        background: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.1);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
    }
    .metric-title {
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        opacity: 0.7;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        margin-top: 0.5rem;
    }
    .metric-sub {
        font-size: 0.85rem;
        margin-top: 0.2rem;
        opacity: 0.6;
    }
    
    /* Notification Toggle (Glassmorphism) */
    .hero-notify-toggle {
        margin-top: 1.5rem;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 0.5rem 1rem;
        width: 80%;
        max-width: 700px;
        margin-left: auto;
        margin-right: auto;
        color: white;
        text-align: left;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .hero-notify-toggle summary {
        font-weight: 600;
        font-size: 1.2rem;
        cursor: pointer;
        padding: 0.5rem;
        list-style: none;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .hero-notify-toggle summary::-webkit-details-marker {
        display: none;
    }
    .hero-notify-toggle summary::before {
        content: '▼';
        font-size: 0.9rem;
        margin-right: 0.8rem;
        transition: transform 0.3s ease;
    }
    .hero-notify-toggle[open] summary::before {
        transform: rotate(180deg);
    }
    .hero-notify-toggle ul {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-size: 1rem;
        line-height: 1.6;
        padding-left: 2rem;
        padding-right: 1rem;
        color: rgba(255, 255, 255, 0.95);
    }
    .hero-notify-toggle ul li {
        margin-bottom: 0.8rem;
    }
    .hero-notify-toggle ul li strong {
        color: #FCD34D; /* Light amber for highlights */
    }
    
    /* Expander Data Tables */
    div[data-testid="stExpander"] {
        border-radius: 16px;
        border: 1px solid rgba(128,128,128,0.1) !important;
        margin-bottom: 4rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        background: rgba(128,128,128,0.02) !important;
    }
    
    /* Make the outer map container relative so the switcher anchors to it */
    div[data-testid="stVerticalBlock"]:has(> div > div > div > #legend-marker) {
        position: relative !important;
    }

    /* Layer Switcher (Floating over map) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#legend-marker) {
        position: absolute !important;
        top: 1rem !important;
        right: 1rem !important;
        z-index: 9999 !important;
        margin-top: 0 !important;
        padding: 1rem 1.5rem !important;
        border-radius: 12px !important;
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2) !important;
        width: auto !important;
        text-align: left;
    }
    
    /* Fix text color for light switcher background */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#legend-marker) label p,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(#legend-marker) b {
        color: #1E293B !important;
    }
    
    /* Sidebar text enlargement */
    [data-testid="stSidebar"] h3 { font-size: 1.5rem !important; }
    [data-testid="stSidebar"] p { font-size: 1.1rem !important; }
    .stRadio label p { font-size: 1.15rem !important; font-weight: 600 !important; }
    .stRadio div[role="radiogroup"] label { padding: 0.5rem 1rem !important; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Taiwan Geographic Coordinates & Regional Groupings
# -----------------------------------------------------------------------------
TAIWAN_LOCATIONS = {
    # Northern Taiwan (北部地區)
    "基隆市": {"lat": 25.1276, "lng": 121.7392, "region": "北部地區"},
    "臺北市": {"lat": 25.0375, "lng": 121.5637, "region": "北部地區"},
    "新北市": {"lat": 24.9157, "lng": 121.6739, "region": "北部地區"},
    "桃園市": {"lat": 24.9936, "lng": 121.3010, "region": "北部地區"},
    "新竹市": {"lat": 24.8138, "lng": 120.9675, "region": "北部地區"},
    "新竹縣": {"lat": 24.8387, "lng": 121.0177, "region": "北部地區"},
    "宜蘭縣": {"lat": 24.7021, "lng": 121.7377, "region": "北部地區"},
    # Central Taiwan (中部地區)
    "苗栗縣": {"lat": 24.5602, "lng": 120.8214, "region": "中部地區"},
    "臺中市": {"lat": 24.1477, "lng": 120.6736, "region": "中部地區"},
    "彰化縣": {"lat": 24.0518, "lng": 120.5161, "region": "中部地區"},
    "南投縣": {"lat": 23.9609, "lng": 120.9719, "region": "中部地區"},
    "雲林縣": {"lat": 23.7092, "lng": 120.4313, "region": "中部地區"},
    # Southern Taiwan (南部地區)
    "嘉義市": {"lat": 23.4800, "lng": 120.4491, "region": "南部地區"},
    "嘉義縣": {"lat": 23.4518, "lng": 120.2555, "region": "南部地區"},
    "臺南市": {"lat": 22.9997, "lng": 120.2270, "region": "南部地區"},
    "高雄市": {"lat": 22.6273, "lng": 120.3014, "region": "南部地區"},
    "屏東縣": {"lat": 22.5519, "lng": 120.5487, "region": "南部地區"},
    # Eastern Taiwan (東部地區)
    "花蓮縣": {"lat": 23.9871, "lng": 121.6015, "region": "東部地區"},
    "臺東縣": {"lat": 22.7583, "lng": 121.1444, "region": "東部地區"},
    # Outlying Islands (外島地區)
    "澎湖縣": {"lat": 23.5711, "lng": 119.5793, "region": "外島地區"},
    "金門縣": {"lat": 24.4493, "lng": 118.3766, "region": "外島地區"},
    "連江縣": {"lat": 26.1505, "lng": 119.9499, "region": "外島地區"},
}

REGION_GROUPS = {
    "全台灣 (All)": list(TAIWAN_LOCATIONS.keys()),
    "北部地區": [k for k, v in TAIWAN_LOCATIONS.items() if v["region"] == "北部地區"],
    "中部地區": [k for k, v in TAIWAN_LOCATIONS.items() if v["region"] == "中部地區"],
    "南部地區": [k for k, v in TAIWAN_LOCATIONS.items() if v["region"] == "南部地區"],
    "東部地區": [k for k, v in TAIWAN_LOCATIONS.items() if v["region"] == "東部地區"],
    "外島地區": [k for k, v in TAIWAN_LOCATIONS.items() if v["region"] == "外島地區"],
}


def get_temperature_color(temp: float) -> str:
    if temp is None or pd.isna(temp): return "#94A3B8"
    if temp < 0: return "#004e98"
    elif temp < 5: return "#3a86ff"
    elif temp < 10: return "#00b4d8"
    elif temp < 15: return "#06d6a0"
    elif temp < 20: return "#90be6d"
    elif temp < 25: return "#f9c74f"
    elif temp < 30: return "#f8961e"
    elif temp < 35: return "#f3722c"
    elif temp < 40: return "#d90429"
    else: return "#9d0208"

def get_weather_info(wx: str):
    wx_s = str(wx or "")
    if any(k in wx_s for k in ["雷", "雹"]): return "⛈️", "#8B5CF6"
    elif any(k in wx_s for k in ["雨", "陣雨", "短暫雨", "毛毛雨"]): return "🌧️", "#3B82F6"
    elif any(k in wx_s for k in ["陰"]): return "☁️", "#34D399"
    elif any(k in wx_s for k in ["多雲"]): return "⛅", "#60A5FA"
    elif any(k in wx_s for k in ["晴"]): return "☀️", "#FBBF24"
    else: return "🌤️", "#34D399"

def get_rain_color(pop: float) -> str:
    if pop is None or pd.isna(pop): return "#94A3B8"
    if pop < 20.0: return "#10B981"
    elif pop < 50.0: return "#FBBF24"
    elif pop < 80.0: return "#3B82F6"
    else: return "#8B5CF6"

def get_precipitation_color(precip: float) -> str:
    if precip is None or pd.isna(precip) or precip <= 0.0: return "#10B981"
    elif precip < 5.0: return "#FBBF24"
    elif precip < 15.0: return "#3B82F6"
    else: return "#8B5CF6"

def get_aqi_color(aqi_val: float) -> str:
    if pd.isna(aqi_val) or aqi_val is None: return "#94A3B8"
    if aqi_val <= 50: return "#10B981"
    elif aqi_val <= 100: return "#FBBF24"
    elif aqi_val <= 150: return "#F97316"
    elif aqi_val <= 200: return "#EF4444"
    else: return "#8B5CF6"


# -----------------------------------------------------------------------------
# 3. Data Ingestion & Caching Functions
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_weather_data() -> pd.DataFrame:
    """Load temperature forecast records (F-C0032-001) from SQLite database."""
    db = DBManager(db_path=DEFAULT_DB_PATH)
    df = db.get_all_temperature_forecasts()
    if not df.empty:
        df["minT"] = pd.to_numeric(df["minT"], errors="coerce")
        df["maxT"] = pd.to_numeric(df["maxT"], errors="coerce")
        df["avgT"] = ((df["minT"] + df["maxT"]) / 2.0).round(1)
        df["pop_num"] = pd.to_numeric(df["pop"], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=300)
def load_station_data() -> pd.DataFrame:
    """Load real-time station observation records (O-A0003-001) from SQLite database."""
    db = DBManager(db_path=DEFAULT_DB_PATH)
    df = db.get_latest_station_observations()
    if not df.empty:
        df["temp"] = pd.to_numeric(df["temp"], errors="coerce")
        df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")
        df["precipitation"] = pd.to_numeric(df["precipitation"], errors="coerce").fillna(0.0)
        df["windSpeed"] = pd.to_numeric(df["windSpeed"], errors="coerce")
        df["pressure"] = pd.to_numeric(df["pressure"], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_aqi_data() -> pd.DataFrame:
    """Load real-time AQI observation records from SQLite database."""
    db = DBManager(db_path=DEFAULT_DB_PATH)
    df = db.get_latest_aqi_observations()
    if not df.empty:
        df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
        df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")
    return df


def trigger_api_sync() -> bool:
    """Trigger real-time fetch from CWA API for both F-C0032-001 and O-A0003-001."""
    try:
        client = CWAApiClient()
        db = DBManager(db_path=DEFAULT_DB_PATH)

        # 1. Fetch 36h Regional Forecast (F-C0032-001)
        raw_forecast = client.fetch_dataset("F-C0032-001")
        forecast_records = client.parse_temperature_forecast_36h(raw_forecast)
        if forecast_records:
            db.save_temperature_forecasts(forecast_records)

        # 2. Fetch Real-time Station Observations (O-A0003-001)
        raw_stations = client.fetch_dataset("O-A0003-001")
        station_records = client.parse_station_observations(raw_stations)
        if station_records:
            db.save_station_observations(station_records)

        # 3. Fetch Real-time AQI Observations (AQX_P_432)
        moenv_client = MOENVApiClient()
        raw_aqi = moenv_client.fetch_dataset("aqx_p_432")
        aqi_records = moenv_client.parse_aqi_observations(raw_aqi)
        if aqi_records:
            db.save_aqi_observations(aqi_records)

        st.cache_data.clear()
        st.session_state.get("map_html_cache", {}).clear()
        return True
    except Exception as err:
        st.error(f"同步資料失敗: {err}")
        return False


# -----------------------------------------------------------------------------
# 4. Main Application Layout & Header
# -----------------------------------------------------------------------------
st.markdown("""
<div class="hero-banner">
    <h1 class="hero-title">探索台灣氣象</h1>
    <p class="hero-subtitle">精準觀測 · 即時預警 · 智慧數據</p>
    <p style="font-size: 2rem; color: rgba(255,255,255,0.7); margin-top: 2rem; margin-bottom: 0.5rem;">中央氣象署 (CWA) 開放資料 ✕ 360+ 測站即時觀測</p>
    
<details class="hero-notify-toggle">
<summary>🔔 最新即時氣象與環境通報 (點擊展開)</summary>
<ul>
<li><strong>【環境部空品網】</strong>環境部空氣品質監測網目前公告系統維護中 (預計 12:00-14:00 進行調整)，期間可能暫停部分服務。</li>
<li><strong>【高溫資訊】</strong>臺南市發布橙色燈號，恐連續出現 36 度高溫；南投縣、屏東縣為黃色燈號，請注意防曬與補充水分。</li>
<li><strong>【天氣概況】</strong>輕度颱風「舒力基」於鵝鑾鼻東方海面向北移動。今明兩天全台大多為多雲到晴，東半部需防長浪發生。</li>
</ul>
</details>
</div>
""", unsafe_allow_html=True)

# Ensure Database & Load Data
if not os.path.exists(DEFAULT_DB_PATH):
    st.info("💡 尚未偵測到本地資料庫，正在為您從中央氣象署 (CWA) 獲取最新氣象資料...")
    trigger_api_sync()

df_weather = load_weather_data()
df_stations = load_station_data()
df_aqi = load_aqi_data()

if df_weather.empty and df_stations.empty and df_aqi.empty:
    st.warning("⚠️ 目前資料庫中無氣象資料，請點擊下方按鈕以連線中央氣象署獲取最新預報。")
    if st.button("🔄 立即同步中央氣象署資料", type="primary"):
        with st.spinner("連線 CWA API 下載中..."):
            if trigger_api_sync():
                st.success("氣象資料下載成功！")
                st.rerun()
    st.stop()

# -----------------------------------------------------------------------------
# 5. Sidebar Controls
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 🎛️ 資料與地圖控制")

# View Mode: County Forecast vs. Live Station Observations vs AQI
data_view_mode = st.sidebar.radio(
    "📊 地圖資料來源 (Data Source Layer)",
    options=["縣市 36h 天氣預報 (F-C0032-001)", "全台 360+ 測站即時觀測 (O-A0003-001)", "全台空氣品質即時觀測 (AQX_P_432)"],
    index=1
)

# Macro Region Selector
selected_macro = st.sidebar.selectbox(
    "📍 選擇分區 (Region Group)",
    options=list(REGION_GROUPS.keys()),
    key="macro_sel"
)

# County Focus Filter
available_counties = REGION_GROUPS[selected_macro]
selected_county = st.sidebar.selectbox(
    "🏙️ 聚焦縣市 (Focus County/City)",
    options=["全部顯示"] + available_counties,
    key="county_sel"
)

# Date / Time Period Selector (Only for Forecast Mode)
distinct_dates = sorted(df_weather["dataDate"].dropna().unique().tolist()) if not df_weather.empty else []

def format_date_label(date_str: str) -> str:
    try:
        dt = pd.to_datetime(date_str)
        time_tag = "上午" if dt.hour < 12 else ("下午" if dt.hour < 18 else "晚上")
        return f"{dt.strftime('%m/%d %H:%M')} ({time_tag})"
    except Exception:
        return str(date_str)

if data_view_mode.startswith("縣市") and distinct_dates:
    selected_date = st.sidebar.selectbox(
        "⏱️ 預報時段 (Forecast Slot)",
        options=distinct_dates,
        index=0,
        format_func=format_date_label
    )
else:
    selected_date = distinct_dates[0] if distinct_dates else ""
    if not df_stations.empty:
        latest_obs = df_stations["obsTime"].dropna().iloc[0] if "obsTime" in df_stations.columns else "即時"
        st.sidebar.info(f"📡 測站觀測時間: {latest_obs[:16].replace('T', ' ')}")

st.sidebar.markdown("---")
# Manual Sync Button in Sidebar
if st.sidebar.button("🔄 同步氣象署最新資料 (全部)", use_container_width=True):
    with st.spinner("向中央氣象署更新資料中 (F-C0032 & O-A0003)..."):
        if trigger_api_sync():
            st.sidebar.success("更新完畢！")
            st.rerun()

# -----------------------------------------------------------------------------
# 6. KPI Metric Cards
# -----------------------------------------------------------------------------
with st.container(border=True):
    st.markdown('<div id="left-panel-marker"></div>', unsafe_allow_html=True)
    st.markdown("### 🇹🇼 台灣即時氣象")
    
    col1, col2, col3, col4 = st.columns(4)


if data_view_mode.startswith("縣市"):
    df_slot = df_weather[df_weather["dataDate"] == selected_date] if selected_date else df_weather
    if not df_slot.empty:
        max_row = df_slot.loc[df_slot["maxT"].idxmax()]
        min_row = df_slot.loc[df_slot["minT"].idxmin()]
        avg_max_temp = df_slot["maxT"].mean()
        avg_pop = df_slot["pop_num"].mean()

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🔥 全台預報最高溫</div>
                <div class="metric-value">{max_row['maxT']}°C</div>
                <div class="metric-sub">{max_row['regionName']} ({max_row.get('wx', '')})</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">❄️ 全台預報最低溫</div>
                <div class="metric-value">{min_row['minT']}°C</div>
                <div class="metric-sub">{min_row['regionName']} ({min_row.get('wx', '')})</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🌡️ 縣市平均最高溫</div>
                <div class="metric-value">{avg_max_temp:.1f}°C</div>
                <div class="metric-sub">預報時段 22 縣市均溫</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">💧 全島平均降雨機率</div>
                <div class="metric-value">{avg_pop:.0f}%</div>
                <div class="metric-sub">綜合預報平均降雨率</div>
            </div>
            """, unsafe_allow_html=True)
elif data_view_mode.startswith("全台 360+"):
    # KPI from live station observations (O-A0003-001)
    if not df_stations.empty:
        valid_temp = df_stations.dropna(subset=["temp"])
        max_st = valid_temp.loc[valid_temp["temp"].idxmax()] if not valid_temp.empty else None
        min_st = valid_temp.loc[valid_temp["temp"].idxmin()] if not valid_temp.empty else None
        avg_temp = valid_temp["temp"].mean() if not valid_temp.empty else 0.0
        wettest_st = df_stations.loc[df_stations["precipitation"].idxmax()] if not df_stations.empty else None

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🔥 測站即時最高溫</div>
                <div class="metric-value">{max_st['temp'] if max_st is not None else '--'}°C</div>
                <div class="metric-sub">{max_st['stationName'] if max_st is not None else ''} ({max_st['countyName'] if max_st is not None else ''})</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">❄️ 測站即時最低溫</div>
                <div class="metric-value">{min_st['temp'] if min_st is not None else '--'}°C</div>
                <div class="metric-sub">{min_st['stationName'] if min_st is not None else ''} ({min_st['countyName'] if min_st is not None else ''})</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🌡️ 全台即時均溫</div>
                <div class="metric-value">{avg_temp:.1f}°C</div>
                <div class="metric-sub">{len(valid_temp)} 個有效氣象觀測站</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🌧️ 當前最大降水量</div>
                <div class="metric-value">{wettest_st['precipitation'] if wettest_st is not None else 0.0} mm</div>
                <div class="metric-sub">{wettest_st['stationName'] if wettest_st is not None else ''} ({wettest_st['countyName'] if wettest_st is not None else ''})</div>
            </div>
            """, unsafe_allow_html=True)
elif data_view_mode.startswith("全台空氣品質"):
    if not df_aqi.empty:
        valid_aqi = df_aqi.dropna(subset=["aqi"])
        worst_aqi_st = valid_aqi.loc[valid_aqi["aqi"].idxmax()] if not valid_aqi.empty else None
        avg_aqi = valid_aqi["aqi"].mean() if not valid_aqi.empty else 0.0
        good_aqi_count = (valid_aqi["aqi"] <= 50).sum() if not valid_aqi.empty else 0

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">😷 全台最高 AQI</div>
                <div class="metric-value">{worst_aqi_st['aqi'] if worst_aqi_st is not None else '--'}</div>
                <div class="metric-sub">{worst_aqi_st['sitename'] if worst_aqi_st is not None else ''} ({worst_aqi_st['county'] if worst_aqi_st is not None else ''})</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">指標污染物</div>
                <div class="metric-value">{worst_aqi_st['pollutant'] if worst_aqi_st is not None and worst_aqi_st['pollutant'] else '無'}</div>
                <div class="metric-sub">{worst_aqi_st['sitename'] if worst_aqi_st is not None else ''} 最高污染</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🌿 全台平均 AQI</div>
                <div class="metric-value">{avg_aqi:.1f}</div>
                <div class="metric-sub">{len(valid_aqi)} 個有效空品測站</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🍃 良好測站比例</div>
                <div class="metric-value">{good_aqi_count}/{len(valid_aqi)}</div>
                <div class="metric-sub">AQI ≤ 50 測站數量</div>
            </div>
            """, unsafe_allow_html=True)



# -----------------------------------------------------------------------------
# 7. Interactive Layout: Folium Map (Left) + Temperature Analytics (Right)
# -----------------------------------------------------------------------------
# Full width map container

with st.container():
    with st.container(border=True):
        st.markdown('<div id="legend-marker"></div>', unsafe_allow_html=True)
        # -------------------------------------------------------------------------
        # Display Mode Switcher (Buttons for Temperature, Forecast Weather, Rainy)
        # -------------------------------------------------------------------------
        if data_view_mode.startswith("全台空氣品質"):
            display_mode = st.radio(
                "🎯 地圖指標切換 (Switch Map Indicator)：",
                options=["🍃 空氣品質 (AQI)"],
                horizontal=True,
                index=0
            )
        else:
            display_mode = st.radio(
                "🎯 地圖指標切換 (Switch Map Indicator)：",
                options=["🌡️ 氣溫 (Temperature)", "☁️ 天氣現象 (Weather)", "💧 降雨指標 (Rain / PoP)"],
                horizontal=True,
                index=0
            )
    
        # Dynamic Legend Banner matching display mode
        if display_mode.startswith("🌡️ 氣溫"):
            st.markdown("""
            <div style="margin-top: 1rem; width: 100%;">
                <div style="font-weight: 700; margin-bottom: 0.5rem; font-size: 0.85rem; color: #1E293B;">氣溫色階 (Temperature)</div>
                <div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 0.4rem; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="flex: 1; background: #3B82F6;"></div>
                    <div style="flex: 1; background: #10B981;"></div>
                    <div style="flex: 1; background: #F59E0B;"></div>
                    <div style="flex: 1; background: #EF4444;"></div>
                </div>
                <div style="display: flex; font-size: 0.7rem; color: #475569; text-align: center; font-weight: 500;">
                    <div style="flex: 1;">&lt;20°C<br>涼爽</div>
                    <div style="flex: 1;">20-25°C<br>舒適</div>
                    <div style="flex: 1;">25-30°C<br>微熱</div>
                    <div style="flex: 1;">&gt;30°C<br>炎熱</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif display_mode.startswith("☁️ 天氣"):
            st.markdown("""
            <div style="margin-top: 1rem; width: 100%;">
                <div style="font-weight: 700; margin-bottom: 0.5rem; font-size: 0.85rem; color: #1E293B;">天氣現象 (Weather)</div>
                <div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 0.4rem; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="flex: 1; background: #FBBF24;"></div>
                    <div style="flex: 1; background: #60A5FA;"></div>
                    <div style="flex: 1; background: #34D399;"></div>
                    <div style="flex: 1; background: #3B82F6;"></div>
                    <div style="flex: 1; background: #8B5CF6;"></div>
                </div>
                <div style="display: flex; font-size: 0.7rem; color: #475569; text-align: center; font-weight: 500;">
                    <div style="flex: 1;">☀️晴朗</div>
                    <div style="flex: 1;">⛅多雲</div>
                    <div style="flex: 1;">☁️陰天</div>
                    <div style="flex: 1;">🌧️降雨</div>
                    <div style="flex: 1;">⛈️雷雨</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif display_mode.startswith("🍃 空氣品質"):
            st.markdown("""
            <div style="margin-top: 1rem; width: 100%;">
                <div style="font-weight: 700; margin-bottom: 0.5rem; font-size: 0.85rem; color: #1E293B;">空氣品質 AQI (Air Quality)</div>
                <div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 0.4rem; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="flex: 1; background: #10B981;"></div>
                    <div style="flex: 1; background: #FBBF24;"></div>
                    <div style="flex: 1; background: #F97316;"></div>
                    <div style="flex: 1; background: #EF4444;"></div>
                    <div style="flex: 1; background: #8B5CF6;"></div>
                </div>
                <div style="display: flex; font-size: 0.7rem; color: #475569; text-align: center; font-weight: 500;">
                    <div style="flex: 1;">≤50<br>良好</div>
                    <div style="flex: 1;">51-100<br>普通</div>
                    <div style="flex: 1;">101-150<br>敏感族群</div>
                    <div style="flex: 1;">151-200<br>不良</div>
                    <div style="flex: 1;">&gt;200<br>危害</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="margin-top: 1rem; width: 100%;">
                <div style="font-weight: 700; margin-bottom: 0.5rem; font-size: 0.85rem; color: #1E293B;">降雨指標 (Rain / PoP)</div>
                <div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 0.4rem; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="flex: 1; background: #10B981;"></div>
                    <div style="flex: 1; background: #FBBF24;"></div>
                    <div style="flex: 1; background: #3B82F6;"></div>
                    <div style="flex: 1; background: #8B5CF6;"></div>
                </div>
                <div style="display: flex; font-size: 0.7rem; color: #475569; text-align: center; font-weight: 500;">
                    <div style="flex: 1;">&lt;20%<br>乾爽</div>
                    <div style="flex: 1;">20-50%<br>局部雨</div>
                    <div style="flex: 1;">50-80%<br>顯著</div>
                    <div style="flex: 1;">&gt;80%<br>大雨</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Center map on Taiwan or focused county
    if selected_county != "全部顯示" and selected_county in TAIWAN_LOCATIONS:
        map_center = [TAIWAN_LOCATIONS[selected_county]["lat"], TAIWAN_LOCATIONS[selected_county]["lng"]]
        zoom_level = 10
    elif selected_macro != "全台灣 (All)":
        macro_coords = [TAIWAN_LOCATIONS[c] for c in available_counties if c in TAIWAN_LOCATIONS]
        map_center = [
            sum(c["lat"] for c in macro_coords) / len(macro_coords),
            sum(c["lng"] for c in macro_coords) / len(macro_coords)
        ]
        zoom_level = 8
    else:
        map_center = [23.7, 120.9]
        zoom_level = 7

    _sd = selected_date if "selected_date" in locals() else ""
    map_cache_key = f"{data_view_mode}_{display_mode}_{selected_county}_{selected_macro}_{_sd}"
    if "map_html_cache" not in st.session_state:
        st.session_state["map_html_cache"] = {}

    if map_cache_key in st.session_state["map_html_cache"]:
        map_html = st.session_state["map_html_cache"][map_cache_key]
    else:
        tw_map = folium.Map(
            location=map_center,
            zoom_start=zoom_level,
            min_zoom=7,
            max_bounds=True,
            min_lat=20.5,
            max_lat=26.5,
            min_lon=117.5,
            max_lon=123.5,
            tiles="OpenStreetMap",
            control_scale=True,
            prefer_canvas=True,
        )
        plugins.Fullscreen(position='topleft', title='全螢幕', titleCancel='退出全螢幕').add_to(tw_map)

        # -------------------------------------------------------------------------
        # Render Markers: County Forecast vs Live Station Observation
        # -------------------------------------------------------------------------
        if data_view_mode.startswith("縣市"):
            # Plot County Level Forecasts
            for _, row in df_slot.iterrows():
                county = row["regionName"]
                if county not in TAIWAN_LOCATIONS:
                    continue

                coords = TAIWAN_LOCATIONS[county]
                max_t = row["maxT"]
                min_t = row["minT"]
                wx_desc = row.get("wx", "無資料")
                pop_desc = row.get("pop", "0")
                pop_val = row.get("pop_num", 0)

                # Determine marker presentation based on display_mode
                if display_mode.startswith("🌡️ 氣溫"):
                    marker_color = get_temperature_color(max_t)
                    icon_text = f"{int(round(max_t))}°"
                    icon_font_size = "10px"
                elif display_mode.startswith("☁️ 天氣"):
                    emoji, wx_color = get_weather_info(wx_desc)
                    marker_color = wx_color
                    icon_text = emoji
                    icon_font_size = "13px"
                else:  # Rainy Probability
                    marker_color = get_rain_color(pop_val)
                    icon_text = f"{int(pop_val)}%"
                    icon_font_size = "9px"

                popup_html = f"""
                <div style="font-family: 'Noto Sans TC', sans-serif; min-width: 175px; padding: 4px;">
                    <h4 style="margin: 0 0 6px 0; color: #1E293B; border-bottom: 2px solid {marker_color}; padding-bottom: 4px;">
                        {county}
                    </h4>
                    <div style="font-size: 13px; color: #475569; line-height: 1.6;">
                        <div><b>預報天氣：</b> {wx_desc}</div>
                        <div><b>氣溫範圍：</b> <span style="color:#2563EB; font-weight:bold;">{min_t}°C</span> ~ <span style="color:#DC2626; font-weight:bold;">{max_t}°C</span></div>
                        <div><b>降雨機率：</b> 💧 <b>{pop_desc}%</b></div>
                        <div style="font-size: 11px; color: #94A3B8; margin-top: 4px;">時段: {format_date_label(selected_date)}</div>
                    </div>
                </div>
                """

                html_bubble = f"""
                <div style="background-color: {marker_color}; width: 44px; height: 44px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: white; font-weight: 800; font-size: 16px; box-shadow: 0 4px 8px rgba(0,0,0,0.4); opacity: 0.95;">
                    {icon_text}
                </div>
                """
                folium.Marker(
                    location=[coords["lat"], coords["lng"]],
                    icon=folium.DivIcon(html=html_bubble, icon_size=(44,44), icon_anchor=(22,22)),
                    tooltip=f"{county}: {wx_desc} ｜ {min_t}~{max_t}°C ｜ 💧{pop_desc}%",
                    popup=folium.Popup(popup_html, max_width=280)
                ).add_to(tw_map)

        elif data_view_mode.startswith("全台 360+"):
            # Plot 360+ Real-Time Stations (O-A0003-001)
            st_view = df_stations.dropna(subset=["lat", "lng"]).copy()
            marker_cluster = plugins.MarkerCluster(name="測站叢集").add_to(tw_map)

            for _, row in st_view.iterrows():
                st_name = row["stationName"]
                st_county = row.get("countyName", "")
                st_town = row.get("townName", "")
                st_temp = row.get("temp")
                st_precip = row.get("precipitation", 0.0)
                st_wx = row.get("weather", "無資料")
                st_hum = row.get("humidity", "--")
                st_wind = row.get("windSpeed", "--")

                if display_mode.startswith("🌡️ 氣溫"):
                    marker_color = get_temperature_color(st_temp)
                    icon_text = f"{int(round(st_temp))}°" if pd.notna(st_temp) else "--"
                    icon_font_size = "9px"
                elif display_mode.startswith("☁️ 天氣"):
                    emoji, wx_color = get_weather_info(st_wx)
                    marker_color = wx_color
                    icon_text = emoji
                    icon_font_size = "11px"
                else:  # Rain
                    marker_color = get_precipitation_color(st_precip)
                    icon_text = f"{st_precip:.0f}m" if pd.notna(st_precip) else "0m"
                    icon_font_size = "8px"

                popup_html = f"""
                <div style="font-family: 'Noto Sans TC', sans-serif; min-width: 180px; padding: 4px;">
                    <h4 style="margin: 0 0 4px 0; color: #1E293B; border-bottom: 2px solid {marker_color};">
                        {st_name} 測站 ({st_county}{st_town})
                    </h4>
                    <div style="font-size: 12px; color: #475569; line-height: 1.6;">
                        <div><b>當前天氣：</b> {st_wx}</div>
                        <div><b>即時氣溫：</b> <span style="font-weight:bold; color:#DC2626;">{st_temp}°C</span></div>
                        <div><b>即時降水：</b> 💧 <b>{st_precip} mm</b></div>
                        <div><b>相對濕度：</b> {st_hum}% ｜ <b>風速：</b> {st_wind} m/s</div>
                    </div>
                </div>
                """

                html_bubble = f"""
                <div style="background-color: {marker_color}; width: 40px; height: 40px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: white; font-weight: 800; font-size: 15px; text-shadow: 0 1px 2px rgba(0,0,0,0.3); box-shadow: 0 4px 8px rgba(0,0,0,0.4); opacity: 0.95;">
                    {icon_text}
                </div>
                """
                folium.Marker(
                    location=[row["lat"], row["lng"]],
                    icon=folium.DivIcon(html=html_bubble, icon_size=(40,40), icon_anchor=(20,20)),
                    tooltip=f"{st_name} ({st_county}): {st_temp}°C ｜ {st_wx} ｜ 💧{st_precip}mm",
                    popup=folium.Popup(popup_html, max_width=280)
                ).add_to(marker_cluster)

        elif data_view_mode.startswith("全台空氣品質"):
            # Plot Real-Time AQI Observations (AQX_P_432)
            aqi_view = df_aqi.dropna(subset=["latitude", "longitude"]).copy()
            marker_cluster = plugins.MarkerCluster(name="空品測站叢集").add_to(tw_map)

            for _, row in aqi_view.iterrows():
                marker_color = get_aqi_color(row["aqi"])
                icon_text = f"{int(row['aqi'])}" if pd.notna(row['aqi']) else "--"

                popup_html = f"""
                <div style="font-family: 'Noto Sans TC', sans-serif; min-width: 180px; padding: 4px;">
                    <h4 style="margin: 0 0 4px 0; color: #1E293B; border-bottom: 2px solid {marker_color};">
                        {row['sitename']} ({row['county']})
                    </h4>
                    <div style="font-size: 12px; color: #475569; line-height: 1.6;">
                        <div><b>空氣品質 (AQI)：</b> <span style="font-weight:bold; color:{marker_color};">{row['aqi']}</span> ({row['status']})</div>
                        <div><b>主要污染物：</b> {row['pollutant'] if row['pollutant'] else '無'}</div>
                        <div><b>PM2.5：</b> {row['pm25']} μg/m3</div>
                        <div><b>PM10：</b> {row['pm10']} μg/m3</div>
                    </div>
                </div>
                """

                html_bubble = f"""
                <div style="background-color: {marker_color}; width: 40px; height: 40px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: white; font-weight: 800; font-size: 15px; text-shadow: 0 1px 2px rgba(0,0,0,0.3); box-shadow: 0 4px 8px rgba(0,0,0,0.4); opacity: 0.95;">
                    {icon_text}
                </div>
                """
                folium.Marker(
                    location=[row["latitude"], row["longitude"]],
                    icon=folium.DivIcon(html=html_bubble, icon_size=(40,40), icon_anchor=(20,20)),
                    tooltip=f"{row['sitename']}: AQI {row['aqi']} ({row['status']})",
                    popup=folium.Popup(popup_html, max_width=280)
                ).add_to(marker_cluster)

                folium.Marker(
                    location=[row["latitude"], row["longitude"]],
                    icon=folium.DivIcon(
                        icon_size=(40, 18),
                        icon_anchor=(20, 9),
                        html=f"""
                        <div style="font-size: 9px; font-weight: 700; color: #ffffff; text-align: center; text-shadow: 0px 1px 3px rgba(0,0,0,0.9); pointer-events: none;">
                            {icon_text}
                        </div>
                        """
                    )
                ).add_to(marker_cluster)

        import json
        @st.cache_data
        def load_geojson():
            with open("taiwan_counties.json", "r", encoding="utf-8") as f:
                return json.load(f)
        try:
            geojson_data = load_geojson()

            # Build county color map for choropleth rendering
            county_color_map = {}
            if data_view_mode.startswith("縣市"):
                for _, row in df_slot.iterrows():
                    c = row["regionName"]
                    if display_mode.startswith("🌡️ 氣溫"):
                        county_color_map[c] = get_temperature_color(row["maxT"])
                    elif display_mode.startswith("☁️ 天氣"):
                        _, color = get_weather_info(row.get("wx", ""))
                        county_color_map[c] = color
                    else:
                        county_color_map[c] = get_rain_color(row.get("pop_num", 0))
            elif data_view_mode.startswith("全台 360+"):
                if display_mode.startswith("🌡️ 氣溫"):
                    grp = st_view.groupby("countyName")["temp"].mean()
                    for c, val in grp.items(): county_color_map[c] = get_temperature_color(val)
                elif display_mode.startswith("💧 降雨"):
                    grp = st_view.groupby("countyName")["precipitation"].mean()
                    for c, val in grp.items(): county_color_map[c] = get_precipitation_color(val)
                elif display_mode.startswith("☁️ 天氣"):
                    grp = st_view.groupby("countyName")["weather"].agg(lambda x: x.mode()[0] if not x.empty else "")
                    for c, val in grp.items(): 
                        _, color = get_weather_info(val)
                        county_color_map[c] = color
            elif data_view_mode.startswith("全台空氣品質"):
                grp = aqi_view.groupby("county")["aqi"].mean()
                for c, val in grp.items(): county_color_map[c] = get_aqi_color(val)

            def get_county_style(feature):
                c_name = feature['properties']['COUNTYNAME']
                # Try to match the exact name
                color = county_color_map.get(c_name)

                # Alias handling for Taiwan naming conventions and historical county updates
                if not color: color = county_color_map.get(c_name.replace("臺", "台"))
                if not color: color = county_color_map.get(c_name.replace("台", "臺"))
                if not color: color = county_color_map.get(c_name.replace("桃園縣", "桃園市"))

                return {
                    'fillColor': color if color else '#ffffff',
                    'color': '#333333',
                    'weight': 1,
                    'fillOpacity': 0.6 if color else 0.05
                }

            folium.GeoJson(
                geojson_data,
                name="台灣縣市邊界",
                style_function=get_county_style,
                highlight_function=lambda feature: {
                    'fillColor': '#3b82f6',
                    'color': '#3b82f6',
                    'weight': 2,
                    'fillOpacity': 0.4
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['COUNTYNAME'],
                    aliases=[''],
                    labels=False,
                    style="background-color: white !important; color: #333333 !important; font-family: arial; font-size: 14px; padding: 6px 10px; border: none !important; border-radius: 4px; box-shadow: 0 4px 6px rgba(0,0,0,0.15) !important;"
                )
            ).add_to(tw_map)
        except Exception as e:
            pass

        folium.LayerControl(position="topright").add_to(tw_map)
        map_html = tw_map._repr_html_()
        if len(st.session_state["map_html_cache"]) > 20:
            st.session_state["map_html_cache"].clear()
        st.session_state["map_html_cache"][map_cache_key] = map_html

    import streamlit.components.v1 as components
    # Instant rendering via cached HTML string
    components.html(map_html, height=900)

with st.expander("📊 顯示詳細數據分析與資料表 (View Analytics & Data Tables)", expanded=False):
    st.markdown("### 📈 數據分析與趨勢視覺化 (Trend Analytics)")

    if data_view_mode.startswith("縣市"):
        chart_county = selected_county if selected_county != "全部顯示" else (available_counties[0] if available_counties else "臺北市")
        selected_trend_county = st.selectbox(
            "選擇趨勢分析縣市：",
            options=available_counties,
            index=available_counties.index(chart_county) if chart_county in available_counties else 0
        )

        df_county = df_weather[df_weather["regionName"] == selected_trend_county].sort_values("dataDate")
        if not df_county.empty:
            chart_df = df_county.copy()
            chart_df["時段標籤"] = chart_df["dataDate"].apply(format_date_label)
            chart_df = chart_df.rename(columns={"maxT": "最高氣溫 (°C)", "minT": "最低氣溫 (°C)", "pop_num": "降雨機率 (%)"})

            st.line_chart(
                chart_df.set_index("時段標籤")[["最高氣溫 (°C)", "最低氣溫 (°C)"]],
                color=["#EF4444", "#3B82F6"],
                height=260
            )

            st.markdown(f"**{selected_trend_county} 36 小時預報明細卡：**")
            detail_cols = st.columns(len(df_county))
            for idx, (_, row) in enumerate(df_county.iterrows()):
                with detail_cols[idx % len(detail_cols)]:
                    t_color = get_temperature_color(row['maxT'])
                    emoji, _ = get_weather_info(row.get('wx', ''))
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 0.75rem; text-align: center;">
                        <div style="font-size: 0.72rem; color: #94A3B8;">{format_date_label(row['dataDate'])}</div>
                        <div style="font-size: 1.2rem; margin: 2px 0;">{emoji}</div>
                        <div style="font-size: 1.05rem; font-weight: 700; color: {t_color};">{row['minT']}° ~ {row['maxT']}°C</div>
                        <div style="font-size: 0.78rem; color: #CBD5E1;">{row.get('wx', '')}</div>
                        <div style="font-size: 0.75rem; color: #60A5FA; margin-top: 2px;">💧 {row.get('pop', '0')}%</div>
                    </div>
                    """, unsafe_allow_html=True)
    elif data_view_mode.startswith("全台 360+"):
        # Station analytics (O-A0003-001)
        st_view = df_stations.copy()
        if selected_macro != "全台灣 (All)":
            st_view = st_view[st_view["countyName"].isin(available_counties)]
        if selected_county != "全部顯示":
            st_view = st_view[st_view["countyName"].str.contains(selected_county, na=False)]

        st.markdown(f"**{selected_macro} 測站即時氣溫前 10 排行榜：**")
        top_hot = st_view.dropna(subset=["temp"]).sort_values("temp", ascending=False).head(10)
        if not top_hot.empty:
            chart_data = top_hot[["stationName", "temp"]].set_index("stationName")
            chart_data.columns = ["即時氣溫 (°C)"]
            st.bar_chart(chart_data, color="#F59E0B", height=270)
        else:
            st.info("所選分區目前尚無有效測站溫度回傳。")

        st.markdown(f"**當前分區測站數量：** `{len(st_view)}` 站 ｜ **降雨測站數：** `{(st_view['precipitation'] > 0).sum()}` 站")

    elif data_view_mode.startswith("全台空氣品質"):
        aqi_view = df_aqi.copy()
        if selected_macro != "全台灣 (All)":
            aqi_view = aqi_view[aqi_view["county"].isin(available_counties)]
        if selected_county != "全部顯示":
            aqi_view = aqi_view[aqi_view["county"].str.contains(selected_county, na=False)]

        st.markdown(f"**{selected_macro} 空氣品質最差前 10 排行榜：**")
        top_aqi = aqi_view.dropna(subset=["aqi"]).sort_values("aqi", ascending=False).head(10)
        if not top_aqi.empty:
            chart_data = top_aqi[["sitename", "aqi"]].set_index("sitename")
            chart_data.columns = ["AQI 指數"]
            st.bar_chart(chart_data, color="#F59E0B", height=270)
        else:
            st.info("所選分區目前尚無有效空品測站回傳。")

        st.markdown(f"**當前分區空品測站數量：** `{len(aqi_view)}` 站")

# -----------------------------------------------------------------------------
    # 8. Full Data Tables & CSV Download (Tabs)
    # -----------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📋 氣象數據庫總覽與查詢 (Data Explorer)")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 縣市 36h 預報總覽 (F-C0032-001)",
        "📡 全台 360+ 測站即時觀測 (O-A0003-001)",
        "🍃 全台空氣品質即時觀測 (AQX_P_432)",
        "📥 數據資料匯出 (Export CSV)"
    ])

    with tab1:
        view_df = df_weather.copy()
        if selected_macro != "全台灣 (All)":
            view_df = view_df[view_df["regionName"].isin(available_counties)]
        if selected_county != "全部顯示":
            view_df = view_df[view_df["regionName"] == selected_county]

        display_table = view_df[["regionName", "dataDate", "minT", "maxT", "wx", "pop", "updatedAt"]].copy()
        display_table.columns = ["縣市名稱", "預報時段", "最低溫 (°C)", "最高溫 (°C)", "天氣現象", "降雨機率 (%)", "更新時間"]
        display_table = display_table.sort_values(by=["預報時段", "縣市名稱"])

        st.dataframe(
            display_table,
            use_container_width=True,
            hide_index=True,
            height=320
        )

    with tab2:
        st_table = df_stations.copy()
        if selected_macro != "全台灣 (All)":
            st_table = st_table[st_table["countyName"].isin(available_counties)]
        if selected_county != "全部顯示":
            st_table = st_table[st_table["countyName"].str.contains(selected_county, na=False)]

        search_station = st.text_input("🔍 搜尋測站名稱或鄉鎮：", placeholder="輸入測站名稱例如：基隆、板橋、玉山...")
        if search_station:
            st_table = st_table[
                st_table["stationName"].str.contains(search_station, na=False) |
                st_table["townName"].str.contains(search_station, na=False)
            ]

        st_display = st_table[[
            "stationId", "stationName", "countyName", "townName",
            "weather", "temp", "humidity", "precipitation", "windSpeed", "pressure", "obsTime"
        ]].copy()
        st_display.columns = [
            "測站代碼", "測站名稱", "所屬縣市", "鄉鎮區",
            "即時天氣", "氣溫 (°C)", "相對濕度 (%)", "當前降水 (mm)", "風速 (m/s)", "氣壓 (hPa)", "觀測時間"
        ]
        st.dataframe(
            st_display.sort_values("氣溫 (°C)", ascending=False),
            use_container_width=True,
            hide_index=True,
            height=320
        )

    with tab3:
        aqi_table = df_aqi.copy()
        if selected_macro != "全台灣 (All)":
            aqi_table = aqi_table[aqi_table["county"].isin(available_counties)]
        if selected_county != "全部顯示":
            aqi_table = aqi_table[aqi_table["county"].str.contains(selected_county, na=False)]

        search_aqi = st.text_input("🔍 搜尋空品測站名稱或鄉鎮：", placeholder="輸入測站名稱例如：古亭、汐止...")
        if search_aqi:
            aqi_table = aqi_table[
                aqi_table["sitename"].str.contains(search_aqi, na=False) |
                aqi_table["county"].str.contains(search_aqi, na=False)
            ]

        aqi_display = aqi_table[[
            "siteid", "sitename", "county", "aqi",
            "pollutant", "status", "pm25", "pm10", "o3", "publishtime"
        ]].copy()
        aqi_display.columns = [
            "測站代碼", "測站名稱", "所屬縣市", "空氣品質 (AQI)",
            "主要污染物", "狀態", "PM2.5 (μg/m3)", "PM10 (μg/m3)", "臭氧 O3 (ppb)", "發布時間"
        ]
        st.dataframe(
            aqi_display.sort_values("空氣品質 (AQI)", ascending=False),
            use_container_width=True,
            hide_index=True,
            height=320
        )

    with tab4:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**下載縣市 36 小時預報數據 (F-C0032-001)**")
            csv_fc = display_table.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 下載預報資料 CSV",
                data=csv_fc,
                file_name=f"taiwan_forecast_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="primary"
            )
        with c2:
            st.markdown("**下載測站即時觀測數據 (O-A0003-001)**")
            csv_st = df_stations.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 下載 360+ 測站資料 CSV",
                data=csv_st,
                file_name=f"taiwan_station_obs_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        with c3:
            st.markdown("**下載全台空氣品質數據 (AQX_P_432)**")
            csv_aqi = df_aqi.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 下載 AQI 空品資料 CSV",
                data=csv_aqi,
                file_name=f"taiwan_aqi_obs_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

    # -----------------------------------------------------------------------------
# 9. Footer
# -----------------------------------------------------------------------------
st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding: 1.5rem 0; border-top: 1px solid rgba(255,255,255,0.08); color: #64748B; font-size: 0.85rem;">
    Taiwan Weather Map Dashboard ｜ Powered by <b>CWA Open Data & MOENV Open Data</b> ｜ Built with Streamlit & Folium
</div>
""", unsafe_allow_html=True)
