"""FRED API client for fetching economic data series.

Uses only Python stdlib (urllib, json) — no external HTTP library required.
Requires a free API key from https://fred.stlouisfed.org/docs/api/api_key.html
set as the FRED_API_KEY environment variable.

Usage:
    from regime_dashboard.fred_client import get_latest_value
    spread = get_latest_value("T10Y2Y")   # latest 2s10s spread
    print(spread["date"], spread["value"])
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta


# FRED API base URL for fetching observation data
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def get_api_key():
    """Read the FRED API key from the FRED_API_KEY environment variable.

    Raises EnvironmentError if the variable is not set.
    """
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise EnvironmentError(
            "FRED_API_KEY environment variable not set. "
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    return key


def fetch_series(series_id, observation_start=None, observation_end=None,
                 frequency=None):
    """Fetch a FRED data series as a list of {date, value} dicts.

    Args:
        series_id: FRED series identifier (e.g. 'T10Y2Y', 'DFF', 'PCEPILFE').
        observation_start: Start date 'YYYY-MM-DD' (default: 2 years ago).
        observation_end: End date 'YYYY-MM-DD' (default: today).
        frequency: Optional resampling frequency ('d', 'w', 'm', 'q', 'a').

    Returns:
        List of dicts with 'date' (str) and 'value' (float) keys,
        sorted ascending by date. Missing values (FRED's '.') are excluded.
    """
    api_key = get_api_key()

    # Default to a 2-year lookback window
    if observation_start is None:
        observation_start = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    if observation_end is None:
        observation_end = datetime.now().strftime("%Y-%m-%d")

    # Build query string
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": observation_start,
        "observation_end": observation_end,
        "sort_order": "asc",
    }
    if frequency:
        params["frequency"] = frequency

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{FRED_BASE_URL}?{query_string}"

    # Make the HTTP request
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "RegimeDashboard/1.0")

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    # Parse observations, skipping FRED's missing-value marker ('.')
    observations = []
    for obs in data.get("observations", []):
        if obs["value"] != ".":
            observations.append({
                "date": obs["date"],
                "value": float(obs["value"]),
            })

    return observations


def get_latest_value(series_id):
    """Get the most recent observation for a FRED series.

    Returns a single {date, value} dict, or None if no data is available.
    """
    obs = fetch_series(series_id)
    if not obs:
        return None
    return obs[-1]


def get_series_as_dict(series_id, **kwargs):
    """Fetch a series and return it as a {date_string: value} dict.

    Useful for quick lookups: values = get_series_as_dict("DFF")
    """
    obs = fetch_series(series_id, **kwargs)
    return {o["date"]: o["value"] for o in obs}


# =========================================================================
# Reference: common FRED series IDs used by the dashboard
# =========================================================================
SERIES = {
    # Signal 3: Credit (dual-signal approach)
    "BAMLH0A3HYC": "ICE BofA CCC & Lower US HY OAS (for CCC-BB spread primary)",
    "BAMLH0A1HYBB": "ICE BofA BB US HY OAS (for CCC-BB spread primary)",
    "BAMLH0A2HYB": "ICE BofA Single-B US HY OAS (secondary / WIDENING_FAST)",
    "BAMLH0A0HYM2": "ICE BofA US HY OAS (legacy composite, fallback)",
    # Signal 7: Term Premium / Fiscal Stress
    "T10Y2Y": "10-Year Treasury Constant Maturity Minus 2-Year (2s10s spread)",
    "DFF": "Effective Federal Funds Rate",
    "PCEPILFE": "Core PCE Price Index (YoY)",
    "FYFSD": "Federal Surplus or Deficit [-] as % of GDP",
    "A091RC1Q027SBEA": "Federal government interest payments",
    "W006RC1Q027SBEA": "Federal government current tax receipts",
    "GFDEGDQ188S": "Federal Debt: Total Public Debt as % of GDP",
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "DGS2": "2-Year Treasury Constant Maturity Rate",
}
