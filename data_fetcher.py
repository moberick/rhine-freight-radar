"""
data_fetcher.py – Rhine River Water Level Fetcher (Multi-Station)
================================================================
Fetches current water levels and short-term forecasts from the
German Federal Waterways & Shipping Administration (WSV) PEGELONLINE API.

API docs: https://www.pegelonline.wsv.de/webservices/rest-api/v2
"""

import requests
import pandas as pd
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"

STATIONS = {
    "Kaub": "1d26e504-7f9e-480a-b52c-5932be6549ab",
    "Ruhrort": "c0f51e35-d0e8-4318-afaf-c5fcbc29f4c1",
    "Maxau": "b6c6d5c8-e2d5-4469-8dd8-fa972ef7eaea",
}

REQUEST_TIMEOUT = 15  # seconds


def _station_uuid(station_name: str) -> str:
    """Look up a station UUID by name, raising KeyError if unknown."""
    return STATIONS[station_name]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_current_level(station_name: str = "Kaub") -> dict:
    """Return the latest water level in cm and its ISO-8601 timestamp.

    Parameters
    ----------
    station_name : str
        Key in the STATIONS dictionary (default: 'Kaub').

    Returns
    -------
    dict  {"timestamp": str, "value": float, "unit": str,
           "state_mnw_mhw": str | None, "state_nsw_hsw": str | None}
    """
    try:
        uuid = _station_uuid(station_name)
        url = f"{BASE_URL}/stations/{uuid}.json?includeTimeseries=true&includeCurrentMeasurement=true"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # Find the "W" (Wasserstand / water-level) timeseries
        for ts in data.get("timeseries", []):
            if ts.get("shortname") == "W":
                cm = ts["currentMeasurement"]
                return {
                    "timestamp": cm["timestamp"],
                    "value": cm["value"],
                    "unit": ts.get("unit", "cm"),
                    "state_mnw_mhw": cm.get("stateMnwMhw"),
                    "state_nsw_hsw": cm.get("stateNswHsw"),
                }

        return {"error": "Water-level timeseries (W) not found in API response."}

    except requests.exceptions.ConnectionError:
        return {"error": "Connection error – could not reach PEGELONLINE API."}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out while contacting PEGELONLINE API."}
    except requests.exceptions.HTTPError as exc:
        return {"error": f"HTTP error: {exc.response.status_code}"}
    except Exception as exc:
        return {"error": f"Unexpected error: {exc}"}


def get_forecast(station_name: str = "Kaub") -> dict:
    """Return forecast water levels for the next ~3 days from the WV timeseries.

    Parameters
    ----------
    station_name : str
        Key in the STATIONS dictionary (default: 'Kaub').

    The PEGELONLINE WV (Wasserstandvorhersage) timeseries provides
    2-hourly forecast values.  Entries with type='forecast' are modelled
    predictions; type='estimate' are less-certain extrapolations.

    Returns
    -------
    dict  {"initialized": str, "forecasts": list[dict], "count": int}
          Each forecast dict: {"timestamp": str, "value": float, "type": str}
    """
    try:
        uuid = _station_uuid(station_name)
        url = f"{BASE_URL}/stations/{uuid}/WV/measurements.json"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return {"error": f"No forecast data currently available for {station_name}."}

        # Filter to only future timestamps
        now = datetime.now(timezone.utc)
        future = []
        for entry in data:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts >= now:
                future.append({
                    "timestamp": entry["timestamp"],
                    "value": entry["value"],
                    "type": entry.get("type", "unknown"),
                })

        initialized = data[0].get("initialized", "unknown")

        return {
            "initialized": initialized,
            "forecasts": future,
            "count": len(future),
        }

    except requests.exceptions.ConnectionError:
        return {"error": "Connection error – could not reach PEGELONLINE API."}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out while contacting PEGELONLINE API."}
    except requests.exceptions.HTTPError as exc:
        return {"error": f"HTTP error: {exc.response.status_code}"}
    except Exception as exc:
        return {"error": f"Unexpected error: {exc}"}


def get_historical_data(station_name: str = "Kaub", days: int = 30) -> pd.DataFrame:
    """Fetch historical water-level measurements for the last *days* days.

    Parameters
    ----------
    station_name : str
        Key in the STATIONS dictionary (default: 'Kaub').
    days : int
        Number of past days to retrieve (default: 30).

    Returns
    -------
    pd.DataFrame  columns=['timestamp', 'value'] or empty on error.
    """
    try:
        uuid = _station_uuid(station_name)
        url = (
            f"{BASE_URL}/stations/{uuid}/W/measurements.json"
            f"?start=P{days}D"
        )
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return pd.DataFrame(columns=["timestamp", "value"])

        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["value"] = df["value"].astype(float)
        return df[["timestamp", "value"]]

    except Exception as exc:
        print(f"⚠  get_historical_data error: {exc}")
        return pd.DataFrame(columns=["timestamp", "value"])


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    for name in STATIONS:
        print("=" * 60)
        print(f"  Rhine River – {name} Station")
        print("=" * 60)

        # --- Current level ---
        print("\n📍 Current Water Level")
        print("-" * 40)
        current = get_current_level(name)

        if "error" in current:
            print(f"  ⚠  {current['error']}")
        else:
            ts = datetime.fromisoformat(current["timestamp"])
            print(f"  Level     : {current['value']:.0f} {current['unit']}")
            print(f"  Timestamp : {ts.strftime('%Y-%m-%d %H:%M %Z')}")
            if current["state_mnw_mhw"]:
                print(f"  Status    : {current['state_mnw_mhw']}")

        # --- Forecast ---
        print("\n🔮 Water Level Forecast (next ~3 days)")
        print("-" * 40)
        forecast = get_forecast(name)

        if "error" in forecast:
            print(f"  ⚠  {forecast['error']}")
        else:
            print(f"  Forecast issued : {forecast['initialized']}")
            print(f"  Data points     : {forecast['count']}\n")
            print(f"  {'Timestamp':<28} {'Level (cm)':>10}  {'Type':<10}")
            print(f"  {'—' * 28} {'—' * 10}  {'—' * 10}")
            for entry in forecast["forecasts"]:
                ts = datetime.fromisoformat(entry["timestamp"])
                print(
                    f"  {ts.strftime('%Y-%m-%d %H:%M %Z'):<28}"
                    f" {entry['value']:>10.0f}"
                    f"  {entry['type']:<10}"
                )

        print("\n")
