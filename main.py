from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
import pandas as pd
import os

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
