"""
MOENV API Client Module (utils/moenv_api.py)
Handles authenticated REST API requests to Ministry of Environment (MOENV) Open Data Platform.
"""

import os
import requests
from typing import Dict, List, Any, Optional

DEFAULT_API_KEY = "065e7d86-6759-407c-9920-69d83995673c"
BASE_URL = "https://data.moenv.gov.tw/api/v2"


class MOENVApiClient:
    """Client for interacting with MOENV Open Data REST APIs."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the API client.

        Args:
            api_key: Optional MOENV authorization key.
        """
        st_key = None
        try:
            import streamlit as st
            st_key = st.secrets.get("MOENV_API_KEY")
        except Exception:
            pass

        self.api_key = (
            api_key
            or os.getenv("MOENV_API_KEY")
            or st_key
            or DEFAULT_API_KEY
        )
        self.base_url = BASE_URL

    def fetch_dataset(self, dataset_id: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetch raw JSON data for a specific MOENV dataset ID.

        Args:
            dataset_id: MOENV Data ID (e.g., 'aqx_p_432')
            params: Optional query parameters for filtering dataset requests.

        Returns:
            List of dicts containing parsed JSON response records from MOENV API.
        """
        url = f"{self.base_url}/{dataset_id}"
        query_params = params or {}
        query_params["api_key"] = self.api_key

        try:
            response = requests.get(url, params=query_params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data.get("records", [])
            elif isinstance(data, list):
                return data
            return []
        except requests.exceptions.SSLError:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(url, params=query_params, timeout=15, verify=False)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data.get("records", [])
            elif isinstance(data, list):
                return data
            return []

    @staticmethod
    def parse_aqi_observations(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse 'aqx_p_432' (Real-time AQI Observations) dataset.

        Returns:
            List of dicts with station information, coordinates, and AQI elements.
        """
        parsed_records = []
        try:
            for st in records:
                def _safe_float(val: Any) -> Optional[float]:
                    try:
                        if val is None or str(val).strip() == "":
                            return None
                        return float(val)
                    except (ValueError, TypeError):
                        return None

                parsed_records.append({
                    "siteid": st.get("siteid", ""),
                    "sitename": st.get("sitename", ""),
                    "county": st.get("county", ""),
                    "aqi": _safe_float(st.get("aqi")),
                    "pollutant": st.get("pollutant", ""),
                    "status": st.get("status", ""),
                    "so2": _safe_float(st.get("so2")),
                    "co": _safe_float(st.get("co")),
                    "o3": _safe_float(st.get("o3")),
                    "o3_8hr": _safe_float(st.get("o3_8hr")),
                    "pm10": _safe_float(st.get("pm10")),
                    "pm25": _safe_float(st.get("pm2.5")),
                    "no2": _safe_float(st.get("no2")),
                    "nox": _safe_float(st.get("nox")),
                    "no": _safe_float(st.get("no")),
                    "wind_speed": _safe_float(st.get("wind_speed")),
                    "wind_direc": _safe_float(st.get("wind_direc")),
                    "publishtime": st.get("publishtime", ""),
                    "co_8hr": _safe_float(st.get("co_8hr")),
                    "pm25_avg": _safe_float(st.get("pm2.5_avg")),
                    "pm10_avg": _safe_float(st.get("pm10_avg")),
                    "so2_avg": _safe_float(st.get("so2_avg")),
                    "longitude": _safe_float(st.get("longitude")),
                    "latitude": _safe_float(st.get("latitude")),
                })
        except Exception as err:
            print(f"[MOENVApiClient] Error parsing aqx_p_432 station observation data: {err}")

        return parsed_records
