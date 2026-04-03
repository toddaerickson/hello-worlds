"""Regime-specific data fetchers that augment the shared data layer.

Wraps shared fetchers with caching and regime-specific transformations.
"""

import datetime as dt
import logging
from typing import Optional

import numpy as np
import pandas as pd

from market_topping_regime.data.fetchers import (
    fetch_advance_decline,
    fetch_bb_oas,
    fetch_ccc_oas,
    fetch_fear_greed,
    fetch_fred_series,
    fetch_gdp,
    fetch_hy_oas,
    fetch_initial_claims,
    fetch_ism_new_orders,
    fetch_lei,
    fetch_margin_debt,
    fetch_aaii_sentiment,
    fetch_nyse_new_highs_lows,
    fetch_shiller_cape,
    fetch_spx_history,
    fetch_ticker_history,
    fetch_wilshire_5000,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Breadth data aggregation
# ---------------------------------------------------------------------------


def get_spx_breadth_data(period: str = "2y") -> dict:
    """Collect all breadth-related data for Signal 1.

    Returns dict with:
      - spx: S&P 500 daily closes
      - pct_above_200d: estimated % of constituents above 200d MA
      - nh_nl_ratio_20d: 20d MA of new highs ratio
      - ad_line_20d_roc: A/D line 20-day ROC
    """
    spx = fetch_spx_history(period=period)
    result = {"spx": spx}

    # % above 200d MA: use S&P 500 equal-weight proxy
    # In production, compute from constituent data. Here use proxy.
    try:
        ew = fetch_ticker_history("RSP", period=period)  # Equal-weight S&P 500 ETF
        if not ew.empty and not spx.empty:
            # Proxy: ratio of RSP performance to SPY as breadth indicator
            spy = fetch_ticker_history("SPY", period=period)
            if not spy.empty:
                rsp_ret = ew["Close"].pct_change(20)
                spy_ret = spy["Close"].pct_change(20)
                # When RSP underperforms SPY, breadth is narrowing
                breadth_ratio = rsp_ret / spy_ret.where(spy_ret != 0, np.nan)
                # Map to approximate % above 200d MA (rough proxy)
                result["breadth_ratio"] = breadth_ratio
    except Exception as e:
        logger.warning("Breadth proxy failed: %s", e)

    # A/D line
    ad_line = fetch_advance_decline()
    if not ad_line.empty:
        result["ad_line"] = ad_line
        result["ad_line_20d_roc"] = ad_line.pct_change(20) * 100

    return result


# ---------------------------------------------------------------------------
# Valuation data aggregation
# ---------------------------------------------------------------------------


def get_valuation_data() -> dict:
    """Collect valuation data for Signal 2."""
    result = {}

    # Shiller CAPE
    cape = fetch_shiller_cape()
    if not cape.empty:
        result["cape_series"] = cape
        result["current_cape"] = cape.iloc[-1]
        # 30-year percentile
        cape_30y = cape.last("30Y") if hasattr(cape, "last") else cape.tail(360)
        if len(cape_30y) > 0:
            current = cape.iloc[-1]
            pctile = (cape_30y < current).mean() * 100
            result["cape_pctile_30y"] = pctile

    # Buffett Indicator
    wilshire = fetch_wilshire_5000()
    gdp = fetch_gdp()
    if not wilshire.empty and not gdp.empty:
        # Forward-fill GDP to daily
        gdp_daily = gdp.resample("D").ffill()
        # Align
        common = wilshire.index.intersection(gdp_daily.index)
        if len(common) > 0:
            buffett = (wilshire.loc[common] / gdp_daily.loc[common]) * 100
            buffett = buffett.dropna()
            if not buffett.empty:
                result["buffett_series"] = buffett
                result["current_buffett"] = buffett.iloc[-1]
                buff_30y = buffett.tail(360 * 30)  # approximate
                pctile = (buff_30y < buffett.iloc[-1]).mean() * 100
                result["buffett_pctile_30y"] = pctile

    return result


# ---------------------------------------------------------------------------
# Credit data aggregation
# ---------------------------------------------------------------------------


def get_credit_data() -> dict:
    """Collect credit spread data for Signal 3."""
    result = {}

    hy = fetch_hy_oas()
    if not hy.empty:
        result["hy_oas"] = hy
        result["current_hy_oas"] = hy.iloc[-1]
        # 5-year percentile (lower = tighter = more complacent)
        hy_5y = hy.last("5Y") if hasattr(hy, "last") else hy.tail(252 * 5)
        if len(hy_5y) > 0:
            pctile = (hy_5y < hy.iloc[-1]).mean() * 100
            result["hy_oas_pctile_5y"] = pctile

    ccc = fetch_ccc_oas()
    bb = fetch_bb_oas()
    if not ccc.empty and not bb.empty:
        common = ccc.index.intersection(bb.index)
        if len(common) > 0:
            ratio = ccc.loc[common] / bb.loc[common]
            result["ccc_bb_ratio"] = ratio
            result["current_ccc_bb_ratio"] = ratio.iloc[-1]

    return result


# ---------------------------------------------------------------------------
# Sentiment data aggregation
# ---------------------------------------------------------------------------


def get_sentiment_data() -> dict:
    """Collect sentiment data for Signal 4."""
    result = {}

    # AAII
    aaii = fetch_aaii_sentiment()
    if not aaii.empty and "bullish" in aaii.columns and "bearish" in aaii.columns:
        spread = aaii["bullish"] - aaii["bearish"]
        spread_4w = spread.rolling(4).mean()
        result["aaii_spread"] = spread
        result["aaii_spread_4w"] = spread_4w
        if not spread_4w.empty:
            result["current_aaii_4w"] = spread_4w.iloc[-1]
        # Consecutive weeks above 25
        recent = spread.tail(52)
        weeks_above = 0
        for val in reversed(recent.values):
            if val > 25:
                weeks_above += 1
            else:
                break
        result["aaii_weeks_above_25"] = weeks_above

    # CNN Fear & Greed
    fg = fetch_fear_greed()
    if fg is not None:
        result["fear_greed"] = fg

    return result


# ---------------------------------------------------------------------------
# Macro data aggregation
# ---------------------------------------------------------------------------


def get_macro_data() -> dict:
    """Collect macro data for Signal 5."""
    result = {}

    # LEI
    lei = fetch_lei()
    if not lei.empty:
        result["lei"] = lei
        # 6-month ROC
        if len(lei) >= 7:
            roc_6m = (lei.iloc[-1] / lei.iloc[-7] - 1) * 100
            result["lei_6m_roc"] = roc_6m

    # ISM New Orders
    ism = fetch_ism_new_orders()
    if not ism.empty:
        result["ism_new_orders"] = ism
        result["current_ism_no"] = ism.iloc[-1]

    # Initial Claims
    claims = fetch_initial_claims()
    if not claims.empty:
        result["claims"] = claims
        ma_4w = claims.rolling(4).mean()
        ma_26w = claims.rolling(26).mean()
        if not ma_4w.empty and not ma_26w.empty:
            latest_4w = ma_4w.iloc[-1]
            latest_26w = ma_26w.iloc[-1]
            if latest_26w > 0:
                pct_diff = (latest_4w / latest_26w - 1) * 100
                result["claims_4w_vs_26w"] = pct_diff

    return result


# ---------------------------------------------------------------------------
# Leverage data aggregation
# ---------------------------------------------------------------------------


def get_leverage_data() -> dict:
    """Collect margin debt / leverage data for Signal 6."""
    result = {}

    margin = fetch_margin_debt()
    if not margin.empty and "margin_debt" in margin.columns:
        debt = margin["margin_debt"].dropna()
        if len(debt) >= 13:
            yoy = (debt.iloc[-1] / debt.iloc[-13] - 1) * 100
            result["margin_debt_yoy"] = yoy

        if "free_credit_balance" in margin.columns:
            fcb = margin["free_credit_balance"].dropna()
            declining_months = 0
            for i in range(len(fcb) - 1, 0, -1):
                if fcb.iloc[i] < fcb.iloc[i - 1]:
                    declining_months += 1
                else:
                    break
            result["free_credit_declining"] = declining_months

    return result
