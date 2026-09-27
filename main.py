from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
import pandas as pd
import os
import httpx
import re

from utils.db_manager import DBManager
from utils.moenv_api import MOENVApiClient
from utils.cwa_api import CWAApiClient

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/api/sync")
def sync_data():
    try:
        client = CWAApiClient()
        db = DBManager(db_path=DEFAULT_DB_PATH)

        raw_forecast = client.fetch_dataset("F-C0032-001")
        forecast_records = client.parse_temperature_forecast_36h(raw_forecast)
        if forecast_records:
            db.save_temperature_forecasts(forecast_records)

        raw_stations = client.fetch_dataset("O-A0003-001")
        station_records = client.parse_station_observations(raw_stations)
        if station_records:
            db.save_station_observations(station_records)

        moenv_client = MOENVApiClient()
        raw_aqi = moenv_client.fetch_dataset("aqx_p_432")
        aqi_records = moenv_client.parse_aqi_observations(raw_aqi)
        if aqi_records:
            db.save_aqi_observations(aqi_records)
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

DEFAULT_DB_PATH = "data.db"

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/geojson")
def get_geojson():
    with open("taiwan_counties.json", "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/forecast")
def get_forecast():
    db = DBManager(db_path=DEFAULT_DB_PATH)
    df = db.get_all_temperature_forecasts()
    if df.empty:
        return []
    df["minT"] = pd.to_numeric(df["minT"], errors="coerce")
    df["maxT"] = pd.to_numeric(df["maxT"], errors="coerce")
    df["avgT"] = ((df["minT"] + df["maxT"]) / 2.0).round(1)
    df["pop_num"] = pd.to_numeric(df["pop"], errors="coerce").fillna(0)
    return json.loads(df.to_json(orient="records"))

@app.get("/api/station")
def get_station():
    db = DBManager(db_path=DEFAULT_DB_PATH)
    df = db.get_latest_station_observations()
    if df.empty:
        return []
    df["temp"] = pd.to_numeric(df["temp"], errors="coerce")
    df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")
    df["precipitation"] = pd.to_numeric(df["precipitation"], errors="coerce").fillna(0.0)
    df["windSpeed"] = pd.to_numeric(df["windSpeed"], errors="coerce")
    df["pressure"] = pd.to_numeric(df["pressure"], errors="coerce")
    return json.loads(df.to_json(orient="records"))

@app.get("/api/aqi")
def get_aqi():
    db = DBManager(db_path=DEFAULT_DB_PATH)
    df = db.get_latest_aqi_observations()
    if df.empty:
        return []
    df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
    df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")
    return json.loads(df.to_json(orient="records"))

@app.get("/api/sync")
def sync_data():
    try:
        db = DBManager(db_path=DEFAULT_DB_PATH)
        cwa_client = CWAApiClient()
        
        # 1. Fetch Forecast (F-C0032-001)
        raw_forecast = cwa_client.fetch_dataset("F-C0032-001")
        forecast_records = cwa_client.parse_temperature_forecast(raw_forecast)
        if forecast_records:
            db.save_temperature_forecasts(forecast_records)
            
        # 2. Fetch Station Obs (O-A0003-001)
        raw_stations = cwa_client.fetch_dataset("O-A0003-001")
        station_records = cwa_client.parse_station_observations(raw_stations)
        if station_records:
            db.save_station_observations(station_records)

        # 3. Fetch AQI
        moenv_client = MOENVApiClient()
        raw_aqi = moenv_client.fetch_dataset("aqx_p_432")
        aqi_records = moenv_client.parse_aqi_observations(raw_aqi)
        if aqi_records:
            db.save_aqi_observations(aqi_records)
            
        return {"status": "success", "message": "Data synchronized"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/notifications")
async def get_notifications():
    notifications = []
    
    # 1. Fetch CWA Warnings
    try:
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.get("https://www.cwa.gov.tw/Data/js/warn/Warning_Content.js")
            text = res.text
            
            # W29 High Temp
            w29_match = re.search(r"'W29'\s*:\s*\{\s*'C'\s*:\s*\{[^\}]*'content'\s*:\s*'([^']+)'", text)
            if w29_match:
                content = w29_match.group(1).replace('\\n', ' ').strip()
                if content:
                    summary = (content[:80] + '...') if len(content) > 80 else content
                    notifications.append({"type": "高溫資訊", "summary": summary, "url": "https://www.cwa.gov.tw/V8/C/P/Warning/W29.html"})
                    
            # W33 Heavy Rain
            w33_match = re.search(r"'W33'\s*:\s*\{\s*'C'\s*:\s*\{[^\}]*'content'\s*:\s*'([^']+)'", text)
            if w33_match:
                content = w33_match.group(1).replace('\\n', ' ').strip()
                if content:
                    summary = (content[:80] + '...') if len(content) > 80 else content
                    notifications.append({"type": "大雷雨即時訊息", "summary": summary, "url": "https://www.cwa.gov.tw/V8/C/P/Warning/W33.html"})
            
            # TY_WARN Typhoon
            ty_match = re.search(r"'TY_WARN'\s*:\s*\{\s*'C'\s*:\s*\{[^\}]*'content'\s*:\s*'([^']+)'", text)
            if ty_match:
                content = ty_match.group(1).replace('\\n', ' ').strip()
                if content:
                    summary = (content[:80] + '...') if len(content) > 80 else content
                    notifications.append({"type": "颱風警報", "summary": summary, "url": "https://www.cwa.gov.tw/V8/C/P/Typhoon/TY_WARN.html"})

    except Exception as e:
        print("CWA API Error:", e)

    # 2. Fetch AirTW News using AQI data from database
    try:
        from utils.db_manager import DBManager
        db = DBManager(db_path="data.db")
        df_aqi = db.get_latest_aqi_observations()
        if not df_aqi.empty:
            df_aqi['aqi'] = pd.to_numeric(df_aqi['aqi'], errors='coerce')
            bad_air = df_aqi[df_aqi['aqi'] > 100]
            if not bad_air.empty:
                max_row = bad_air.loc[bad_air['aqi'].idxmax()]
                count = len(bad_air)
                summary = f"全台有 {count} 個測站空氣品質達不健康等級 (最高為 {max_row['sitename']} AQI:{int(max_row['aqi'])})，請敏感族群注意防護。"
                notifications.append({"type": "空氣品質警告", "summary": summary, "url": "https://airtw.moenv.gov.tw/CHT/News.aspx"})
    except Exception as e:
        print("AirTW DB Error:", e)
        
    # 3. Fetch Typhoon Open Data (W-C0034-005)
    try:
        from utils.cwa_api import CWAApiClient
        cwa_client = CWAApiClient()
        ty_data = cwa_client.fetch_dataset("W-C0034-005")
        if ty_data:
            records = ty_data.get('records', {})
            tropical_cyclones = records.get('TropicalCyclones', {}).get('TropicalCyclone', [])
            for tc in tropical_cyclones:
                name = tc.get('TyphoonName', 'Unknown')
                analysis = tc.get('AnalysisData', {}).get('Fix', [])
                if analysis:
                    latest = analysis[-1]
                    speed = latest.get('MaxWindSpeed', '未知')
                    direction = latest.get('MovingDirection', '未知')
                    summary = f"颱風 {name} 最新動態：目前最大風速 {speed} m/s，正向 {direction} 移動中，請持續關注氣象署最新颱風消息。"
                    # Only append if we haven't already added a typhoon warning
                    if not any(n["type"] in ["颱風消息", "颱風警報"] for n in notifications):
                        notifications.append({
                            "type": "颱風消息",
                            "summary": summary,
                            "url": "https://www.cwa.gov.tw/V8/C/P/Typhoon/TY_WARN.html"
                        })
    except Exception as e:
        print("Typhoon Open Data API Error:", e)

    return {"status": "success", "data": notifications}

