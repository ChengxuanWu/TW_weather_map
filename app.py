"""
Taiwan Weather Forecast Web App (app.py)
Interactive weather dashboard visualizing CWA temperature forecasts across Taiwan.
Built with Streamlit, Folium, Pandas, and SQLite.
"""

import os
import sqlite3
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
    page_title="台灣天氣預報 | Taiwan Weather Map",
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
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%);
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
    }
    .badge-blue { background-color: rgba(59, 130, 246, 0.2); color: #60A5FA; border: 1px solid #3B82F6; }
    .badge-green { background-color: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #10B981; }
    .badge-yellow { background-color: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid #F59E0B; }
    .badge-red { background-color: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #EF4444; }

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
    """Return color hex matching workflow step 17 color scales.
    
    < 20°C: Blue (#3B82F6)
    20 - 25°C: Green (#10B981)
    25 - 30°C: Yellow (#F59E0B)
    > 30°C: Red (#EF4444)
    """
    if temp < 20.0:
        return "#3B82F6"
    elif 20.0 <= temp < 25.0:
        return "#10B981"
    elif 25.0 <= temp < 30.0:
        return "#F59E0B"
    else:
        return "#EF4444"


# -----------------------------------------------------------------------------
# 3. Data Ingestion & Caching Functions
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_weather_data() -> pd.DataFrame:
    """Load temperature forecast records from SQLite database into pandas DataFrame."""
    db = DBManager(db_path=DEFAULT_DB_PATH)
    df = db.get_all_temperature_forecasts()
    if not df.empty:
        # Normalize types
        df["minT"] = pd.to_numeric(df["minT"], errors="coerce")
        df["maxT"] = pd.to_numeric(df["maxT"], errors="coerce")
        df["avgT"] = ((df["minT"] + df["maxT"]) / 2.0).round(1)
        df["pop_num"] = pd.to_numeric(df["pop"], errors="coerce").fillna(0)
    return df


def trigger_api_sync() -> bool:
    """Trigger real-time fetch from CWA API and update SQLite database."""
    try:
        client = CWAApiClient()
        db = DBManager(db_path=DEFAULT_DB_PATH)
        raw_data = client.fetch_dataset("F-C0032-001")
        records = client.parse_temperature_forecast_36h(raw_data)
        if records:
            db.save_temperature_forecasts(records)
            st.cache_data.clear()
            return True
        return False
    except Exception as err:
        st.error(f"同步中央氣象署 API 資料失敗: {err}")
        return False


# -----------------------------------------------------------------------------
# 4. Main Application Layout
# -----------------------------------------------------------------------------
# Header Banner
st.markdown("""
<div class="main-title-container">
    <h1 class="main-title">🌤️ 台灣天氣預報儀表板 Taiwan Weather Map</h1>
    <p class="sub-title">基於中央氣象署 (CWA) 開放資料平台 API ． 實時氣候觀測與 36 小時預報可視化</p>
</div>
""", unsafe_allow_html=True)

# Ensure Database & Load Data
if not os.path.exists(DEFAULT_DB_PATH):
    st.info("💡 尚未偵測到本地資料庫，正在為您從中央氣象署 (CWA) 獲取最新氣象資料...")
    trigger_api_sync()

df_weather = load_weather_data()

if df_weather.empty:
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
st.sidebar.markdown("### 🎛️ 觀測與控制選項")

# Macro Region Selector
selected_macro = st.sidebar.selectbox(
    "📍 選擇分區 (Region Group)",
    options=list(REGION_GROUPS.keys()),
    index=0
)

# Filter counties based on selected macro group
available_counties = REGION_GROUPS[selected_macro]
selected_county = st.sidebar.selectbox(
    "🏙️ 聚焦縣市 (Focus County/City)",
    options=["全部顯示"] + available_counties,
    index=0
)

# Date / Time Period Selector
distinct_dates = sorted(df_weather["dataDate"].dropna().unique().tolist())

def format_date_label(date_str: str) -> str:
    """Format date string into readable Chinese time label."""
    try:
        dt = pd.to_datetime(date_str)
        time_tag = "上午" if dt.hour < 12 else ("下午" if dt.hour < 18 else "晚上")
        return f"{dt.strftime('%m/%d %H:%M')} ({time_tag})"
    except Exception:
        return str(date_str)

selected_date = st.sidebar.selectbox(
    "⏱️ 預報時段 (Forecast Time Slot)",
    options=distinct_dates,
    index=0,
    format_func=format_date_label
)

st.sidebar.markdown("---")
# Manual Sync Button in Sidebar
if st.sidebar.button("🔄 同步氣象署最新資料", use_container_width=True):
    with st.spinner("向中央氣象署更新資料中..."):
        if trigger_api_sync():
            st.sidebar.success("更新完畢！")
            st.rerun()

st.sidebar.markdown("""
<div style="font-size:0.8rem; color:#94A3B8; margin-top: 1rem;">
    <b>氣溫色階說明 (Color Scales):</b><br/>
    <span class="badge-pill badge-blue">&lt; 20°C 寒冷/涼爽</span><br/>
    <span class="badge-pill badge-green">20 ~ 25°C 舒適宜人</span><br/>
    <span class="badge-pill badge-yellow">25 ~ 30°C 溫暖微熱</span><br/>
    <span class="badge-pill badge-red">&gt; 30°C 炎熱高溫</span>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. KPI Metric Cards
# -----------------------------------------------------------------------------
# Slice data for the selected time slot
df_slot = df_weather[df_weather["dataDate"] == selected_date]

if not df_slot.empty:
    max_row = df_slot.loc[df_slot["maxT"].idxmax()]
    min_row = df_slot.loc[df_slot["minT"].idxmin()]
    avg_max_temp = df_slot["maxT"].mean()
    avg_pop = df_slot["pop_num"].mean()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🔥 全台最高溫預報</div>
            <div class="metric-value">{max_row['maxT']}°C</div>
            <div class="metric-sub">{max_row['regionName']} ({max_row.get('wx', '')})</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">❄️ 全台最低溫預報</div>
            <div class="metric-value">{min_row['minT']}°C</div>
            <div class="metric-sub">{min_row['regionName']} ({min_row.get('wx', '')})</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🌡️ 平均最高溫</div>
            <div class="metric-value">{avg_max_temp:.1f}°C</div>
            <div class="metric-sub">全台 22 縣市綜合平均</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">💧 平均降雨機率</div>
            <div class="metric-value">{avg_pop:.0f}%</div>
            <div class="metric-sub">預報時段全島降雨概況</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. Interactive Layout: Folium Map (Left) + Temperature Analytics (Right)
# -----------------------------------------------------------------------------
map_col, chart_col = st.columns([1.15, 1], gap="medium")

with map_col:
    st.markdown("### 🗺️ 台灣互動天氣地圖 (Interactive Map)")
    st.caption(f"觀測時段：{format_date_label(selected_date)} ｜ 點擊圓圈標記查看各縣市詳細氣象數據")

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

    # Initialize Folium Map
    tw_map = folium.Map(
        location=map_center,
        zoom_start=zoom_level,
        tiles="CartoDB positron",
        control_scale=True,
    )

    # Add alternative base map layers
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(tw_map)
    folium.TileLayer("CartoDB dark_matter", name="Dark Matter (暗色夜覽)").add_to(tw_map)

    # Plot markers for counties in selected time slot
    for _, row in df_slot.iterrows():
        county = row["regionName"]
        if county not in TAIWAN_LOCATIONS:
            continue

        # Filter by region/county selection if not All
        if selected_county != "全部顯示" and county != selected_county:
            continue
        elif selected_county == "全部顯示" and county not in available_counties:
            continue

        coords = TAIWAN_LOCATIONS[county]
        avg_t = row.get("avgT", row["maxT"])
        max_t = row["maxT"]
        min_t = row["minT"]
        wx_desc = row.get("wx", "無資料")
        pop_desc = row.get("pop", "0")
        color = get_temperature_color(max_t)

        # Rich HTML Popup
        popup_html = f"""
        <div style="font-family: 'Noto Sans TC', sans-serif; min-width: 170px; padding: 4px;">
            <h4 style="margin: 0 0 6px 0; color: #1E293B; border-bottom: 2px solid {color}; padding-bottom: 4px;">
                {county}
            </h4>
            <div style="font-size: 13px; color: #475569; line-height: 1.6;">
                <div><b>天氣狀況：</b> {wx_desc}</div>
                <div><b>氣溫範圍：</b> <span style="color:#2563EB; font-weight:bold;">{min_t}°C</span> ~ <span style="color:#DC2626; font-weight:bold;">{max_t}°C</span></div>
                <div><b>降雨機率：</b> 💧 <b>{pop_desc}%</b></div>
                <div style="font-size: 11px; color: #94A3B8; margin-top: 4px;">時段: {format_date_label(selected_date)}</div>
            </div>
        </div>
        """

        # CircleMarker
        folium.CircleMarker(
            location=[coords["lat"], coords["lng"]],
            radius=15,
            color=color,
            weight=3,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            tooltip=f"{county}: {min_t}°C ~ {max_t}°C ({wx_desc})",
            popup=folium.Popup(popup_html, max_width=260)
        ).add_to(tw_map)

        # Label icon showing temperature
        folium.Marker(
            location=[coords["lat"], coords["lng"]],
            icon=folium.DivIcon(
                icon_size=(50, 20),
                icon_anchor=(25, 10),
                html=f"""
                <div style="font-size: 10px; font-weight: 700; color: #ffffff; text-align: center; text-shadow: 0px 1px 3px rgba(0,0,0,0.8); pointer-events: none;">
                    {int(round(max_t))}°
                </div>
                """
            )
        ).add_to(tw_map)

    # Add Layer Control
    folium.LayerControl(position="topright").add_to(tw_map)

    # Render Folium Map in Streamlit
    st_folium(tw_map, width=None, height=520, use_container_width=True)

with chart_col:
    st.markdown("### 📈 氣溫變化與趨勢分析 (Trend Charts)")

    # Select county for trend visualization
    chart_county = selected_county if selected_county != "全部顯示" else (available_counties[0] if available_counties else "臺北市")
    
    selected_trend_county = st.selectbox(
        "選擇趨勢圖縣市：",
        options=available_counties,
        index=available_counties.index(chart_county) if chart_county in available_counties else 0
    )

    df_county = df_weather[df_weather["regionName"] == selected_trend_county].sort_values("dataDate")

    if not df_county.empty:
        # Create chart dataframe with friendly labels
        chart_df = df_county.copy()
        chart_df["時段標籤"] = chart_df["dataDate"].apply(format_date_label)
        chart_df = chart_df.rename(columns={"maxT": "最高氣溫 (°C)", "minT": "最低氣溫 (°C)"})
        
        st.line_chart(
            chart_df.set_index("時段標籤")[["最高氣溫 (°C)", "最低氣溫 (°C)"]],
            color=["#EF4444", "#3B82F6"],
            height=280
        )

        # Forecast cards for this county
        st.markdown(f"**{selected_trend_county} 36 小時預報明細：**")
        detail_cols = st.columns(len(df_county))
        for idx, (_, row) in enumerate(df_county.iterrows()):
            with detail_cols[idx % len(detail_cols)]:
                t_color = get_temperature_color(row['maxT'])
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 0.75rem; text-align: center;">
                    <div style="font-size: 0.75rem; color: #94A3B8;">{format_date_label(row['dataDate'])}</div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: {t_color}; margin: 4px 0;">{row['minT']}° ~ {row['maxT']}°C</div>
                    <div style="font-size: 0.8rem; color: #CBD5E1;">{row.get('wx', '')}</div>
                    <div style="font-size: 0.75rem; color: #60A5FA; margin-top: 2px;">💧 {row.get('pop', '0')}%</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info(f"查無 {selected_trend_county} 的時序預報數據。")

# -----------------------------------------------------------------------------
# 8. Full Weather Forecast Data Table & CSV Download
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 📋 全台各分區氣象預報總覽資料表 (Data Overview)")

# Filter view according to selected region & county
view_df = df_weather.copy()
if selected_macro != "全台灣 (All)":
    view_df = view_df[view_df["regionName"].isin(available_counties)]
if selected_county != "全部顯示":
    view_df = view_df[view_df["regionName"] == selected_county]

display_table = view_df[["regionName", "dataDate", "minT", "maxT", "wx", "pop", "updatedAt"]].copy()
display_table.columns = ["縣市名稱", "預報時段", "最低溫 (°C)", "最高溫 (°C)", "天氣現象", "降雨機率 (%)", "更新時間"]
display_table = display_table.sort_values(by=["預報時段", "縣市名稱"])

tab1, tab2 = st.tabs(["📊 結構化資料表", "📥 資料下載 (Export)"])

with tab1:
    st.dataframe(
        display_table,
        use_container_width=True,
        hide_index=True,
        height=320
    )

with tab2:
    csv_data = display_table.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 下載預報資料為 CSV (UTF-8 with BOM)",
        data=csv_data,
        file_name=f"taiwan_weather_forecast_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        type="primary"
    )

# -----------------------------------------------------------------------------
# 9. Footer
# -----------------------------------------------------------------------------
st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding: 1.5rem 0; border-top: 1px solid rgba(255,255,255,0.08); color: #64748B; font-size: 0.85rem;">
    Taiwan Weather Forecast Web App ｜ Powered by <b>CWA Open Data (交通部中央氣象署)</b> ｜ Built with Streamlit & Folium
</div>
""", unsafe_allow_html=True)
