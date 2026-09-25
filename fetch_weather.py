#!/usr/bin/env python3
"""
Taiwan Weather Data Crawler (fetch_weather.py)
Fetches weather forecast datasets from CWA Open Data Platform API and persists them into SQLite database.

Usage:
    python fetch_weather.py [--api-key YOUR_API_KEY] [--db-path data.db]
"""

import argparse
import sys
import pandas as pd
from utils.cwa_api import CWAApiClient, DEFAULT_API_KEY
from utils.moenv_api import MOENVApiClient
from utils.db_manager import DBManager, DEFAULT_DB_PATH


def main():
    parser = argparse.ArgumentParser(
        description="CWA Weather Forecast Data Crawler & Storage Tool"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=DEFAULT_API_KEY,
        help=f"CWA Open Data Authorization Key (Default: {DEFAULT_API_KEY})"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database file (Default: {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        "--fetch-townships",
        action="store_true",
        help="Optionally fetch detailed township forecasts (F-D0047-091)"
    )

    args = parser.parse_args()

    print("==================================================")
    print("[CWA Weather Data Crawler]")
    print("==================================================")
    print(f"API Key: {args.api_key[:8]}...{args.api_key[-4:]}")
    print(f"Database Path: {args.db_path}")

    # 1. Initialize API Client & DB Manager
    cwa_client = CWAApiClient(api_key=args.api_key)
    db_manager = DBManager(db_path=args.db_path)

    # 2. Fetch General 36-Hour Weather Forecast (F-C0032-001)
    print("\n[Step 1/2] Fetching 36h Regional Weather Forecast (F-C0032-001)...")
    try:
        raw_36h_data = cwa_client.fetch_dataset("F-C0032-001")
        forecast_records = cwa_client.parse_temperature_forecast_36h(raw_36h_data)
        print(f"[OK] Successfully retrieved {len(forecast_records)} forecast records.")

        if forecast_records:
            saved_count = db_manager.save_temperature_forecasts(forecast_records)
            print(f"[OK] Saved/Updated {saved_count} records in 'TemperatureForecasts' database table.")
        else:
            print("[Warning] No valid forecast records found in response.")

    except Exception as err:
        print(f"[ERROR] Failed to fetch dataset F-C0032-001: {err}")
        sys.exit(1)

    # 3. Fetch Real-time Station Weather Observations (O-A0003-001)
    print("\n[Step 2/3] Fetching Real-Time Station Weather Observations (O-A0003-001)...")
    try:
        raw_station_data = cwa_client.fetch_dataset("O-A0003-001")
        station_records = cwa_client.parse_station_observations(raw_station_data)
        print(f"[OK] Successfully retrieved {len(station_records)} real-time weather stations.")

        if station_records:
            saved_stations = db_manager.save_station_observations(station_records)
            print(f"[OK] Saved/Updated {saved_stations} records in 'StationObservations' database table.")
        else:
            print("[Warning] No valid station records found in response.")
    except Exception as err:
        print(f"[Warning] Could not fetch station observations O-A0003-001: {err}")

    # 4. Optional: Fetch Township Weather Forecast (F-D0047-091)
    if args.fetch_townships:
        print("\n[Step 3/3] Fetching Township Weather Forecast (F-D0047-091)...")
        try:
            raw_township_data = cwa_client.fetch_dataset("F-D0047-091")
            township_records = cwa_client.parse_township_forecast(raw_township_data)
            print(f"[OK] Retrieved {len(township_records)} township temperature records.")
            if township_records:
                saved_count = db_manager.save_township_forecasts(township_records)
                print(f"[OK] Saved {saved_count} records in 'TownshipForecasts' database table.")
        except Exception as err:
            print(f"[Warning] Could not fetch township forecast F-D0047-091: {err}")

    # 5. Fetch Real-time AQI Observations (AQX_P_432)
    print("\n[Step 4] Fetching Real-Time AQI Observations (AQX_P_432)...")
    try:
        moenv_client = MOENVApiClient()
        raw_aqi_data = moenv_client.fetch_dataset("aqx_p_432")
        aqi_records = moenv_client.parse_aqi_observations(raw_aqi_data)
        print(f"[OK] Successfully retrieved {len(aqi_records)} real-time AQI stations.")

        if aqi_records:
            saved_aqi = db_manager.save_aqi_observations(aqi_records)
            print(f"[OK] Saved/Updated {saved_aqi} records in 'AQIObservations' database table.")
        else:
            print("[Warning] No valid AQI records found in response.")
    except Exception as err:
        print(f"[Warning] Could not fetch AQI observations AQX_P_432: {err}")

    # 5. Preview Database Summary
    print("\n--------------------------------------------------")
    print("Database Data Summary Preview:")
    print("--------------------------------------------------")
    try:
        df = db_manager.get_all_temperature_forecasts()
        if not df.empty:
            preview_cols = ["regionName", "dataDate", "minT", "maxT", "wx", "pop"]
            avail_cols = [c for c in preview_cols if c in df.columns]
            print("Forecasts (F-C0032-001):")
            print(df[avail_cols].head(5).to_string(index=False))
            print(f"Total Forecast Records in DB: {len(df)}")
        
        df_st = db_manager.get_latest_station_observations()
        if not df_st.empty:
            st_cols = ["stationId", "stationName", "countyName", "weather", "temp", "humidity", "precipitation"]
            avail_st = [c for c in st_cols if c in df_st.columns]
            print("\nStation Observations (O-A0003-001):")
            print(df_st[avail_st].head(5).to_string(index=False))
            print(f"Total Active Stations in DB: {len(df_st)}")
    except Exception as err:
        print(f"Error querying database preview: {err}")

    print("==================================================")
    print("Weather data crawling and storage completed successfully!")
    print("==================================================")


if __name__ == "__main__":
    main()

