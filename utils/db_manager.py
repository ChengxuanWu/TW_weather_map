"""
Database Manager Module (utils/db_manager.py)
Handles SQLite database creation, schema design, and CRUD operations for weather forecast data.
"""

import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = "data.db"


class DBManager:
    """Manages SQLite database connections and table operations for weather data."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize database manager with specified SQLite database file path."""
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create tables if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # TemperatureForecasts schema (as specified in design.md & README.md Step 9)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS TemperatureForecasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    regionName TEXT NOT NULL,
                    dataDate TEXT NOT NULL,
                    minT REAL NOT NULL,
                    maxT REAL NOT NULL,
                    wx TEXT,
                    pop TEXT,
                    updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(regionName, dataDate) ON CONFLICT REPLACE
                );
            """)

            # TownshipForecasts schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS TownshipForecasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    townshipName TEXT NOT NULL,
                    dataDate TEXT NOT NULL,
                    temp REAL NOT NULL,
                    updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(townshipName, dataDate) ON CONFLICT REPLACE
                );
            """)

            # StationObservations schema (CWA O-A0003-001)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS StationObservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stationId TEXT NOT NULL,
                    stationName TEXT NOT NULL,
                    countyName TEXT NOT NULL,
                    townName TEXT,
                    lat REAL,
                    lng REAL,
                    altitude REAL,
                    obsTime TEXT NOT NULL,
                    weather TEXT,
                    temp REAL,
                    humidity REAL,
                    pressure REAL,
                    windSpeed REAL,
                    windDirection REAL,
                    precipitation REAL,
                    uvIndex REAL,
                    updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stationId, obsTime) ON CONFLICT REPLACE
                );
            """)

            conn.commit()

    def save_temperature_forecasts(self, records: List[Dict[str, Any]]) -> int:
        """Save/Upsert regional temperature forecast records into SQLite database.

        Args:
            records: List of dicts with regionName, dataDate, minT, maxT, wx, pop

        Returns:
            Number of rows saved.
        """
        if not records:
            return 0

        sql = """
            INSERT INTO TemperatureForecasts (regionName, dataDate, minT, maxT, wx, pop)
            VALUES (:regionName, :dataDate, :minT, :maxT, :wx, :pop)
            ON CONFLICT(regionName, dataDate) DO UPDATE SET
                minT = excluded.minT,
                maxT = excluded.maxT,
                wx = excluded.wx,
                pop = excluded.pop,
                updatedAt = CURRENT_TIMESTAMP;
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, records)
            conn.commit()
            return cursor.rowcount

    def save_township_forecasts(self, records: List[Dict[str, Any]]) -> int:
        """Save/Upsert township temperature forecast records into SQLite database."""
        if not records:
            return 0

        sql = """
            INSERT INTO TownshipForecasts (townshipName, dataDate, temp)
            VALUES (:townshipName, :dataDate, :temp)
            ON CONFLICT(townshipName, dataDate) DO UPDATE SET
                temp = excluded.temp,
                updatedAt = CURRENT_TIMESTAMP;
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, records)
            conn.commit()
            return cursor.rowcount

    def get_all_temperature_forecasts(self) -> pd.DataFrame:
        """Query all temperature forecasts from database as a pandas DataFrame."""
        with self.get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM TemperatureForecasts ORDER BY regionName, dataDate", conn)
            return df

    def get_forecasts_by_region(self, region_name: str) -> pd.DataFrame:
        """Query temperature forecasts for a specific region name."""
        with self.get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM TemperatureForecasts WHERE regionName = ? ORDER BY dataDate",
                conn,
                params=(region_name,)
            )
            return df

    def save_station_observations(self, records: List[Dict[str, Any]]) -> int:
        """Save/Upsert real-time station observation records into SQLite database."""
        if not records:
            return 0

        sql = """
            INSERT INTO StationObservations (
                stationId, stationName, countyName, townName, lat, lng, altitude,
                obsTime, weather, temp, humidity, pressure, windSpeed, windDirection,
                precipitation, uvIndex
            )
            VALUES (
                :stationId, :stationName, :countyName, :townName, :lat, :lng, :altitude,
                :obsTime, :weather, :temp, :humidity, :pressure, :windSpeed, :windDirection,
                :precipitation, :uvIndex
            )
            ON CONFLICT(stationId, obsTime) DO UPDATE SET
                stationName = excluded.stationName,
                countyName = excluded.countyName,
                townName = excluded.townName,
                lat = excluded.lat,
                lng = excluded.lng,
                altitude = excluded.altitude,
                weather = excluded.weather,
                temp = excluded.temp,
                humidity = excluded.humidity,
                pressure = excluded.pressure,
                windSpeed = excluded.windSpeed,
                windDirection = excluded.windDirection,
                precipitation = excluded.precipitation,
                uvIndex = excluded.uvIndex,
                updatedAt = CURRENT_TIMESTAMP;
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, records)
            conn.commit()
            return cursor.rowcount

    def get_latest_station_observations(self) -> pd.DataFrame:
        """Query latest weather observation for each station."""
        sql = """
            SELECT s.* FROM StationObservations s
            INNER JOIN (
                SELECT stationId, MAX(obsTime) AS maxObsTime
                FROM StationObservations
                GROUP BY stationId
            ) latest ON s.stationId = latest.stationId AND s.obsTime = latest.maxObsTime
            ORDER BY s.countyName, s.stationName
        """
        with self.get_connection() as conn:
            return pd.read_sql_query(sql, conn)

    def get_station_observations_by_county(self, county_name: str) -> pd.DataFrame:
        """Query latest station observations for a specific county."""
        sql = """
            SELECT s.* FROM StationObservations s
            INNER JOIN (
                SELECT stationId, MAX(obsTime) AS maxObsTime
                FROM StationObservations
                WHERE countyName LIKE ?
                GROUP BY stationId
            ) latest ON s.stationId = latest.stationId AND s.obsTime = latest.maxObsTime
            ORDER BY s.stationName
        """
        with self.get_connection() as conn:
            return pd.read_sql_query(sql, conn, params=(f"%{county_name}%",))

