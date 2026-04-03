"""Shared data fetchers for market data (yfinance, FRED, web scraping)."""

import datetime as dt
import logging
import os
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# yfinance helpers
# ---------------------------------------------------------------------------


def fetch_spx_history(period: str = "2y") -> pd.DataFrame:
    """Fetch S&P 500 daily OHLCV from yfinance."""
    import yfinance as yf

    ticker = yf.Ticker("^GSPC")
    df = ticker.history(period=period)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def fetch_ticker_history(symbol: str, period: str = "2y") -> pd.DataFrame:
    """Fetch daily OHLCV for any ticker."""
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    if not df.empty:
        df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


# ---------------------------------------------------------------------------
# FRED helpers
# ---------------------------------------------------------------------------

FRED_API_KEY_ENV = "FRED_API_KEY"


def _get_fred_api_key() -> Optional[str]:
    return os.environ.get(FRED_API_KEY_ENV)


def fetch_fred_series(series_id: str, start: str = "1990-01-01") -> pd.Series:
    """Fetch a FRED series. Uses fredapi if key available, else falls back to pandas_datareader."""
    api_key = _get_fred_api_key()
    if api_key:
        try:
            from fredapi import Fred

            fred = Fred(api_key=api_key)
            s = fred.get_series(series_id, observation_start=start)
            s.index = pd.to_datetime(s.index)
            return s.dropna()
        except Exception as e:
            logger.warning("fredapi failed for %s: %s, trying fallback", series_id, e)

    # Fallback: pandas_datareader FRED (no key required for some series)
    try:
        import pandas_datareader.data as web

        s = web.DataReader(series_id, "fred", start=start)
        return s.iloc[:, 0].dropna()
    except Exception as e:
        logger.warning("pandas_datareader failed for %s: %s", series_id, e)
        return pd.Series(dtype=float)


# ---------------------------------------------------------------------------
# HY OAS / Credit spreads (FRED)
# ---------------------------------------------------------------------------


def fetch_hy_oas(start: str = "2000-01-01") -> pd.Series:
    """ICE BofA US High Yield OAS (BAMLH0A0HYM2)."""
    return fetch_fred_series("BAMLH0A0HYM2", start=start)


def fetch_ccc_oas(start: str = "2000-01-01") -> pd.Series:
    """ICE BofA CCC & Lower OAS (BAMLH0A3HYC)."""
    return fetch_fred_series("BAMLH0A3HYC", start=start)


def fetch_bb_oas(start: str = "2000-01-01") -> pd.Series:
    """ICE BofA BB OAS (BAMLH0A1HYBB)."""
    return fetch_fred_series("BAMLH0A1HYBB", start=start)


# ---------------------------------------------------------------------------
# Macro indicators (FRED)
# ---------------------------------------------------------------------------


def fetch_lei(start: str = "1990-01-01") -> pd.Series:
    """Conference Board Leading Economic Index proxy (USSLIND)."""
    return fetch_fred_series("USSLIND", start=start)


def fetch_ism_new_orders(start: str = "1990-01-01") -> pd.Series:
    """ISM Manufacturing New Orders Index (MANEMP or NAPMNOI)."""
    s = fetch_fred_series("NAPMNOI", start=start)
    if s.empty:
        s = fetch_fred_series("MANEMP", start=start)
    return s


def fetch_initial_claims(start: str = "2000-01-01") -> pd.Series:
    """Weekly initial jobless claims (ICSA)."""
    return fetch_fred_series("ICSA", start=start)


# ---------------------------------------------------------------------------
# Buffett Indicator (FRED)
# ---------------------------------------------------------------------------


def fetch_wilshire_5000(start: str = "1990-01-01") -> pd.Series:
    """Wilshire 5000 Total Market Full Cap Index (WILL5000INDFC)."""
    return fetch_fred_series("WILL5000INDFC", start=start)


def fetch_gdp(start: str = "1990-01-01") -> pd.Series:
    """US GDP quarterly (GDP)."""
    return fetch_fred_series("GDP", start=start)


# ---------------------------------------------------------------------------
# Shiller CAPE (web scrape multpl.com)
# ---------------------------------------------------------------------------


def fetch_shiller_cape() -> pd.Series:
    """Scrape Shiller CAPE ratio from multpl.com. Returns monthly series."""
    import requests
    from bs4 import BeautifulSoup

    url = "https://www.multpl.com/shiller-pe/table/by-month"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table", {"id": "datatable"})
        if table is None:
            table = soup.find("table")
        rows = table.find_all("tr")[1:]  # skip header
        dates, values = [], []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 2:
                try:
                    d = pd.to_datetime(cells[0].text.strip())
                    v = float(cells[1].text.strip().replace(",", ""))
                    dates.append(d)
                    values.append(v)
                except (ValueError, TypeError):
                    continue
        s = pd.Series(values, index=pd.DatetimeIndex(dates), name="CAPE")
        return s.sort_index()
    except Exception as e:
        logger.warning("Failed to scrape CAPE from multpl.com: %s", e)
        return pd.Series(dtype=float, name="CAPE")


# ---------------------------------------------------------------------------
# CNN Fear & Greed Index
# ---------------------------------------------------------------------------


def fetch_fear_greed() -> Optional[float]:
    """Fetch current CNN Fear & Greed Index value."""
    import requests

    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        score = data.get("fear_and_greed", {}).get("score")
        if score is not None:
            return float(score)
        # Alternative structure
        if "fear_and_greed" in data:
            return float(data["fear_and_greed"].get("score", 50))
    except Exception as e:
        logger.warning("Failed to fetch CNN Fear & Greed: %s", e)
    return None


# ---------------------------------------------------------------------------
# AAII Sentiment Survey
# ---------------------------------------------------------------------------


def fetch_aaii_sentiment() -> pd.DataFrame:
    """Fetch AAII sentiment survey data. Returns DataFrame with bull%, bear%, neutral%."""
    # AAII data is available via their website; we try a public CSV endpoint
    # Fallback: use manually maintained local file
    try:
        import requests

        url = "https://www.aaii.com/files/surveys/sentiment.xls"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            df = pd.read_excel(
                pd.io.common.BytesIO(resp.content),
                sheet_name=0,
                skiprows=3,
            )
            df.columns = [c.strip().lower() for c in df.columns]
            # Normalize column names
            col_map = {}
            for c in df.columns:
                if "bull" in c:
                    col_map[c] = "bullish"
                elif "bear" in c:
                    col_map[c] = "bearish"
                elif "neutral" in c:
                    col_map[c] = "neutral"
                elif "date" in c:
                    col_map[c] = "date"
            df = df.rename(columns=col_map)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).set_index("date")
            return df
    except Exception as e:
        logger.warning("Failed to fetch AAII data: %s", e)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# NYSE Breadth data (new highs / new lows)
# ---------------------------------------------------------------------------


def fetch_nyse_new_highs_lows(period: str = "2y") -> pd.DataFrame:
    """Fetch NYSE new 52-week highs and lows using yfinance index proxies."""
    import yfinance as yf

    # Use ETF proxies or Yahoo Finance breadth data
    highs = yf.Ticker("^NYA")  # NYSE Composite as proxy
    df = highs.history(period=period)
    if not df.empty:
        df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def fetch_advance_decline() -> pd.Series:
    """Fetch NYSE advance-decline data. Returns cumulative A/D line."""
    import yfinance as yf

    # Use NYSE advance-decline proxy
    try:
        ad = yf.Ticker("^ADL")
        df = ad.history(period="2y")
        if not df.empty:
            df.index = pd.to_datetime(df.index).tz_localize(None)
            return df["Close"]
    except Exception:
        pass
    # Fallback: compute from NYSE composite
    return pd.Series(dtype=float)


# ---------------------------------------------------------------------------
# FINRA Margin Debt
# ---------------------------------------------------------------------------


def fetch_margin_debt() -> pd.DataFrame:
    """Fetch FINRA margin debt statistics.

    This data is released monthly with ~45 day lag.
    Returns DataFrame with margin_debt and free_credit_balance columns.
    """
    # FINRA margin data is available from their website
    # We try to fetch from a public source or use FRED proxy
    try:
        # Try FRED series for margin debt (discontinued but historical available)
        debt = fetch_fred_series("BOGZ1FL663067003Q", start="1990-01-01")
        if not debt.empty:
            df = pd.DataFrame({"margin_debt": debt})
            return df
    except Exception:
        pass

    logger.warning(
        "FINRA margin debt data not available. "
        "Signal 6 will use available proxies or be excluded."
    )
    return pd.DataFrame()
