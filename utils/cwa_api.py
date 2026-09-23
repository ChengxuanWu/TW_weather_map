"""
CWA API Client Module (utils/cwa_api.py)
Handles authenticated REST API requests to Central Weather Administration (CWA) Open Data Platform.
"""

import os
import requests
from typing import Dict, List, Any, Optional

DEFAULT_API_KEY = "CWA-D6679119-D9FE-4EA3-B33A-F56FFA1CA0F1"
BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"


class CWAApiClient:
    """Client for interacting with CWA Open Data REST APIs."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the API client.

        Args:
            api_key: Optional CWA authorization key. If omitted, checks CWA_API_KEY env var,
                     or falls back to DEFAULT_API_KEY.
        """
        self.api_key = (
            api_key
            or os.getenv("CWA_API_KEY")
            or DEFAULT_API_KEY
        )
        self.base_url = BASE_URL

    def fetch_dataset(self, dataset_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch raw JSON data for a specific CWA dataset ID.

        Args:
            dataset_id: CWA Data ID (e.g., 'F-C0032-001', 'F-D0047-091', 'O-A0001-001')
            params: Optional query parameters for filtering dataset requests.

        Returns:
            Dict containing parsed JSON response from CWA API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        url = f"{self.base_url}/{dataset_id}"
        headers = {
            "Authorization": self.api_key,
            "Accept": "application/json",
        }
        query_params = params or {}

        try:
            response = requests.get(url, headers=headers, params=query_params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError:
            # Fallback for Windows SSL certificate store chain validation issues
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(url, headers=headers, params=query_params, timeout=15, verify=False)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def parse_temperature_forecast_36h(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse 'F-C0032-001' (General 36-Hour Forecast) into structured temperature records.

        Returns:
            List of dicts: [
                {
                    "regionName": "臺北市",
                    "dataDate": "2026-09-23 12:00:00",
                    "minT": 24.0,
                    "maxT": 31.0,
                    "wx": "多雲短暫陣雨",
                    "pop": "30"
                }, ...
            ]
        """
        records = []
        try:
            locations = raw_data.get("records", {}).get("location", [])
            for loc in locations:
                region_name = loc.get("locationName", "Unknown")
                weather_elements = loc.get("weatherElement", [])

                element_map = {elem.get("elementName"): elem.get("time", []) for elem in weather_elements}
                min_t_times = element_map.get("MinT", [])
                max_t_times = element_map.get("MaxT", [])
                wx_times = element_map.get("Wx", [])
                pop_times = element_map.get("PoP", [])

                # Align element data by time slot index
                num_slots = min(len(min_t_times), len(max_t_times))
                for i in range(num_slots):
                    min_item = min_t_times[i]
                    max_item = max_t_times[i]
                    start_time = min_item.get("startTime", "")
                    
                    min_val = float(min_item.get("parameter", {}).get("parameterName", 0.0))
                    max_val = float(max_item.get("parameter", {}).get("parameterName", 0.0))

                    wx_val = wx_times[i].get("parameter", {}).get("parameterName", "") if i < len(wx_times) else ""
                    pop_val = pop_times[i].get("parameter", {}).get("parameterName", "0") if i < len(pop_times) else "0"

                    records.append({
                        "regionName": region_name,
                        "dataDate": start_time,
                        "minT": min_val,
                        "maxT": max_val,
                        "wx": wx_val,
                        "pop": pop_val
                    })
        except Exception as err:
            print(f"[CWAApiClient] Error parsing 36h forecast data: {err}")

        return records

    @staticmethod
    def parse_township_forecast(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse township 7-day or 2-day forecast dataset (e.g. 'F-D0047-091' / 'F-D0047-089').

        Returns:
            List of dicts with township location and element metrics.
        """
        records = []
        try:
            records_data = raw_data.get("records", {})
            locations_container = records_data.get("locations", [{}])
            locations = locations_container[0].get("location", []) if locations_container else []

            for loc in locations:
                township_name = loc.get("locationName", "")
                elements = loc.get("weatherElement", [])
                
                # Extract T, MinT, MaxT, AT if available
                element_dict = {e.get("elementName"): e.get("time", []) for e in elements}
                t_times = element_dict.get("T", [])
                
                for t_item in t_times:
                    data_time = t_item.get("dataTime") or t_item.get("startTime", "")
                    element_val = t_item.get("elementValue", [{}])[0].get("value", None)
                    if element_val is not None:
                        try:
                            t_val = float(element_val)
                        except ValueError:
                            continue
                        records.append({
                            "townshipName": township_name,
                            "dataDate": data_time,
                            "temp": t_val
                        })
        except Exception as err:
            print(f"[CWAApiClient] Error parsing township forecast data: {err}")

        return records
