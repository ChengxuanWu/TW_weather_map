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

# Custom Glassmorphic CSS Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans TC', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header Gradient & Badge */
    .main-title-container {
        padding: 1.2rem 1.5rem;
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.88) 0%, rgba(15, 23, 42, 0.95) 100%);
        border-radius: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        margin-bottom: 1.5rem;
        color: #ffffff;
    }
    
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .sub-title {
        font-size: 0.95rem;
        color: #94A3B8;
        margin-top: 0.4rem;
        margin-bottom: 0;
    }

    /* Metric Card Styling */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    }
    .metric-title {
        font-size: 0.82rem;
        font-weight: 500;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 0.25rem;
        color: #F8FAFC;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #64748B;
        margin-top: 0.2rem;
    }

    /* Legend Pill Badges */
    .badge-pill {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.4rem;
        margin-bottom: 0.3rem;
    }
    .badge-blue { background-color: rgba(59, 130, 246, 0.2); color: #60A5FA; border: 1px solid #3B82F6; }
    .badge-green { background-color: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #10B981; }
    .badge-yellow { background-color: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid #F59E0B; }
    .badge-red { background-color: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #EF4444; }
    .badge-purple { background-color: rgba(139, 92, 246, 0.2); color: #C084FC; border: 1px solid #8B5CF6; }

    /* Map container styling */
    .stFoliumContainer {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    }
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
    """Return color hex matching temperature scales."""
    if temp is None or pd.isna(temp):
        return "#94A3B8"
    if temp < 20.0:
        return "#3B82F6"   # Blue (Cool)
    elif 20.0 <= temp < 25.0:
        return "#10B981"   # Green (Mild)
    elif 25.0 <= temp < 30.0:
        return "#F59E0B"   # Yellow/Amber (Warm)
    else:
        return "#EF4444"   # Red (Hot)


def get_weather_info(wx: str) -> Tuple[str, str]:
    """Return emoji and category color based on weather description."""
    wx_s = str(wx or "")
    if any(k in wx_s for k in ["雷", "雹"]):
        return "⛈️", "#7C3AED"  # Purple
    elif any(k in wx_s for k in ["雨", "陣雨", "短暫雨", "毛毛雨"]):
        return "🌧️", "#0284C7"  # Deep Sky Blue
    elif any(k in wx_s for k in ["陰"]):
        return "☁️", "#64748B"  # Slate Gray
    elif any(k in wx_s for k in ["多雲"]):
        return "⛅", "#0EA5E9"  # Sky Blue
    elif any(k in wx_s for k in ["晴"]):
        return "☀️", "#F59E0B"  # Amber
    elif any(k in wx_s for k in ["霧", "霾"]):
        return "🌫️", "#94A3B8"  # Cool Gray
    else:
        return "🌤️", "#3B82F6"


def get_rain_color(pop: float) -> str:
    """Return color hex matching precipitation probability."""
    if pop is None or pd.isna(pop):
        return "#94A3B8"
    if pop < 20.0:
        return "#10B981"   # Emerald (Dry)
    elif pop < 50.0:
        return "#F59E0B"   # Amber (Scattered chance)
    elif pop < 80.0:
        return "#3B82F6"   # Blue (Likely rain)
    else:
        return "#8B5CF6"   # Purple (Heavy / Very likely)


def get_precipitation_color(precip: float) -> str:
    """Return color hex for real-time mm precipitation."""
    if precip is None or pd.isna(precip) or precip <= 0.0:
        return "#10B981"   # Green (0 mm)
    elif precip < 5.0:
        return "#0EA5E9"   # Light Blue (<5 mm)
    elif precip < 15.0:
        return "#3B82F6"   # Blue (5-15 mm)
    elif precip < 40.0:
        return "#F59E0B"   # Amber (15-40 mm)
    else:
        return "#EF4444"   # Red (>40 mm Heavy rain)


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

        st.cache_data.clear()
        return True
    except Exception as err:
        st.error(f"同步中央氣象署 API 資料失敗: {err}")
        return False


# -----------------------------------------------------------------------------
# 4. Main Application Layout & Header
# -----------------------------------------------------------------------------
st.markdown("""
<div class="main-title-container">
    <h1 class="main-title">🌤️ 台灣天氣預報與即時觀測儀表板</h1>
    <p class="sub-title">中央氣象署 (CWA) 開放資料平台 ． 36小時天氣預報 (F-C0032-001) ✕ 360+ 測站即時觀測 (O-A0003-001)</p>
</div>
""", unsafe_allow_html=True)

# Ensure Database & Load Data
if not os.path.exists(DEFAULT_DB_PATH):
    st.info("💡 尚未偵測到本地資料庫，正在為您從中央氣象署 (CWA) 獲取最新氣象資料...")
    trigger_api_sync()

df_weather = load_weather_data()
df_stations = load_station_data()

if df_weather.empty and df_stations.empty:
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

# View Mode: County Forecast vs. Live Station Observations
data_view_mode = st.sidebar.radio(
    "📊 地圖資料來源 (Data Source Layer)",
    options=["縣市 36h 天氣預報 (F-C0032-001)", "全台 360+ 測站即時觀測 (O-A0003-001)"],
    index=0
)

# Macro Region Selector
selected_macro = st.sidebar.selectbox(
    "📍 選擇分區 (Region Group)",
    options=list(REGION_GROUPS.keys()),
    index=0
)

# County Focus Filter
available_counties = REGION_GROUPS[selected_macro]
selected_county = st.sidebar.selectbox(
    "🏙️ 聚焦縣市 (Focus County/City)",
    options=["全部顯示"] + available_counties,
    index=0
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
else:
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

st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. Interactive Layout: Folium Map (Left) + Temperature Analytics (Right)
# -----------------------------------------------------------------------------
map_col, chart_col = st.columns([1.2, 1], gap="medium")

with map_col:
    st.markdown("### 🗺️ 台灣互動天氣地圖 (Interactive Map)")

    # -------------------------------------------------------------------------
    # Display Mode Switcher (Buttons for Temperature, Forecast Weather, Rainy)
    # -------------------------------------------------------------------------
    display_mode = st.radio(
        "🎯 地圖指標切換 (Switch Map Indicator)：",
        options=["🌡️ 氣溫 (Temperature)", "☁️ 天氣現象 (Weather)", "💧 降雨指標 (Rain / PoP)"],
        horizontal=True,
        index=0
    )

    # Dynamic Legend Banner matching display mode
    if display_mode.startswith("🌡️ 氣溫"):
        st.markdown("""
        <div style="font-size:0.82rem; margin-bottom: 0.6rem;">
            <b>氣溫色階：</b>
            <span class="badge-pill badge-blue">&lt; 20°C 寒冷/涼爽</span>
            <span class="badge-pill badge-green">20 ~ 25°C 舒適宜人</span>
            <span class="badge-pill badge-yellow">25 ~ 30°C 溫暖微熱</span>
            <span class="badge-pill badge-red">&gt; 30°C 炎熱高溫</span>
        </div>
        """, unsafe_allow_html=True)
    elif display_mode.startswith("☁️ 天氣"):
        st.markdown("""
        <div style="font-size:0.82rem; margin-bottom: 0.6rem;">
            <b>天氣現象標籤：</b>
            <span class="badge-pill badge-yellow">☀️ 晴朗</span>
            <span class="badge-pill badge-blue">⛅ 多雲</span>
            <span class="badge-pill badge-green">☁️ 陰天</span>
            <span class="badge-pill badge-blue">🌧️ 降雨/陣雨</span>
            <span class="badge-pill badge-purple">⛈️ 雷雨</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="font-size:0.82rem; margin-bottom: 0.6rem;">
            <b>降雨指標色階：</b>
            <span class="badge-pill badge-green">&lt; 20% / 0mm 乾爽舒適</span>
            <span class="badge-pill badge-yellow">20 ~ 50% / &lt;5mm 局部有雨</span>
            <span class="badge-pill badge-blue">50 ~ 80% / 5~15mm 降雨顯著</span>
            <span class="badge-pill badge-purple">&gt; 80% / &gt;15mm 慎防大雨</span>
        </div>
        """, unsafe_allow_html=True)

    # Center map on Taiwan or focused county
    if selected_county != "全部顯示" and selected_county in TAIWAN_LOCATIONS:
        map_center = [TAIWAN_LOCATIONS[selected_county]["lat"], TAIWAN_LOCATIONS[selected_county]["lng"]]
        zoom_level = 9
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

    tw_map = folium.Map(
        location=map_center,
        zoom_start=zoom_level,
        tiles="CartoDB positron",
        control_scale=True,
    )
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(tw_map)
    folium.TileLayer("CartoDB dark_matter", name="Dark Matter (暗色夜覽)").add_to(tw_map)

    # -------------------------------------------------------------------------
    # Render Markers: County Forecast vs Live Station Observation
    # -------------------------------------------------------------------------
    if data_view_mode.startswith("縣市"):
        # Plot County Level Forecasts
        for _, row in df_slot.iterrows():
            county = row["regionName"]
            if county not in TAIWAN_LOCATIONS:
                continue

            if selected_county != "全部顯示" and county != selected_county:
                continue
            elif selected_county == "全部顯示" and county not in available_counties:
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

            folium.CircleMarker(
                location=[coords["lat"], coords["lng"]],
                radius=16,
                color=marker_color,
                weight=3,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.8,
                tooltip=f"{county}: {wx_desc} ｜ {min_t}~{max_t}°C ｜ 💧{pop_desc}%",
                popup=folium.Popup(popup_html, max_width=280)
            ).add_to(tw_map)

            folium.Marker(
                location=[coords["lat"], coords["lng"]],
                icon=folium.DivIcon(
                    icon_size=(50, 20),
                    icon_anchor=(25, 10),
                    html=f"""
                    <div style="font-size: {icon_font_size}; font-weight: 700; color: #ffffff; text-align: center; text-shadow: 0px 1px 3px rgba(0,0,0,0.85); pointer-events: none;">
                        {icon_text}
                    </div>
                    """
                )
            ).add_to(tw_map)

    else:
        # Plot 360+ Real-Time Stations (O-A0003-001)
        st_view = df_stations.dropna(subset=["lat", "lng"]).copy()
        if selected_macro != "全台灣 (All)":
            st_view = st_view[st_view["countyName"].isin(available_counties)]
        if selected_county != "全部顯示":
            st_view = st_view[st_view["countyName"].str.contains(selected_county, na=False)]

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

            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=11,
                color=marker_color,
                weight=2,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.75,
                tooltip=f"{st_name} ({st_county}): {st_temp}°C ｜ {st_wx} ｜ 💧{st_precip}mm",
                popup=folium.Popup(popup_html, max_width=280)
            ).add_to(tw_map)

            folium.Marker(
                location=[row["lat"], row["lng"]],
                icon=folium.DivIcon(
                    icon_size=(40, 18),
                    icon_anchor=(20, 9),
                    html=f"""
                    <div style="font-size: {icon_font_size}; font-weight: 700; color: #ffffff; text-align: center; text-shadow: 0px 1px 3px rgba(0,0,0,0.9); pointer-events: none;">
                        {icon_text}
                    </div>
                    """
                )
            ).add_to(tw_map)

    folium.LayerControl(position="topright").add_to(tw_map)
    st_folium(tw_map, width=None, height=530, use_container_width=True)

with chart_col:
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
    else:
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

# -----------------------------------------------------------------------------
# 8. Full Data Tables & CSV Download (Tabs)
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 📋 氣象數據庫總覽與查詢 (Data Explorer)")

tab1, tab2, tab3 = st.tabs([
    "📊 縣市 36h 預報總覽 (F-C0032-001)",
    "📡 全台 360+ 測站即時觀測 (O-A0003-001)",
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
    c1, c2 = st.columns(2)
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

# -----------------------------------------------------------------------------
# 9. Footer
# -----------------------------------------------------------------------------
st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding: 1.5rem 0; border-top: 1px solid rgba(255,255,255,0.08); color: #64748B; font-size: 0.85rem;">
    Taiwan Weather Map Dashboard ｜ Powered by <b>CWA Open Data (交通部中央氣象署 F-C0032-001 & O-A0003-001)</b> ｜ Built with Streamlit & Folium
</div>
""", unsafe_allow_html=True)
