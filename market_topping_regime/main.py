"""Main entry point for the Market Regime Dashboard.

Usage:
    python -m market_topping_regime.main --regime       # Run regime data pipeline
    python -m market_topping_regime.main --dashboard    # Launch Streamlit dashboard
"""

import argparse
import datetime as dt
import logging
import sys

import numpy as np
import pandas as pd

from market_topping_regime.data.store import (
    init_regime_tables,
    upsert_regime_caution,
    upsert_regime_signals,
)
from market_topping_regime.regime.fetchers import (
    get_credit_data,
    get_leverage_data,
    get_macro_data,
    get_sentiment_data,
    get_spx_breadth_data,
    get_valuation_data,
)
from market_topping_regime.regime.scoring import (
    compute_caution_level,
    format_caution_summary,
)
from market_topping_regime.regime.signals.breadth import compute_breadth_score
from market_topping_regime.regime.signals.credit import compute_credit_score
from market_topping_regime.regime.signals.leverage import compute_leverage_score
from market_topping_regime.regime.signals.macro import compute_macro_score
from market_topping_regime.regime.signals.sentiment import compute_sentiment_score
from market_topping_regime.regime.signals.valuation import compute_valuation_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_regime_pipeline():
    """Fetch data, compute all 6 signals, and store results."""
    today = dt.date.today().isoformat()
    logger.info("Running regime pipeline for %s", today)

    init_regime_tables()

    # -----------------------------------------------------------------------
    # Signal 1: Breadth Divergence
    # -----------------------------------------------------------------------
    logger.info("Fetching breadth data...")
    breadth_data = get_spx_breadth_data()
    spx = breadth_data.get("spx")

    spx_close = None
    spx_near_52w_high = False
    pct_above_200d = None
    nh_nl_ratio_20d = None
    ad_line_20d_roc = None
    spx_20d_roc = None

    if spx is not None and not spx.empty:
        spx_close = float(spx["Close"].iloc[-1])
        high_52w = spx["Close"].rolling(252).max().iloc[-1]
        spx_near_52w_high = spx_close >= high_52w * 0.95
        spx_20d_roc = float(spx["Close"].pct_change(20).iloc[-1] * 100)

    # Proxy: use breadth ratio for pct_above_200d estimation
    breadth_ratio = breadth_data.get("breadth_ratio")
    if breadth_ratio is not None and not breadth_ratio.empty:
        # Map ratio to approximate percentage (rough proxy)
        latest_ratio = breadth_ratio.dropna().iloc[-1] if not breadth_ratio.dropna().empty else 1.0
        pct_above_200d = max(0, min(100, latest_ratio * 50))

    ad_roc = breadth_data.get("ad_line_20d_roc")
    if ad_roc is not None and not ad_roc.empty:
        ad_line_20d_roc = float(ad_roc.iloc[-1])

    breadth_score = compute_breadth_score(
        pct_above_200d=pct_above_200d,
        spx_near_52w_high=spx_near_52w_high,
        nh_nl_ratio_20d=nh_nl_ratio_20d,
        ad_line_20d_roc=ad_line_20d_roc,
        spx_20d_roc=spx_20d_roc,
    )
    logger.info("Signal 1 (Breadth): %.1f", breadth_score)

    # -----------------------------------------------------------------------
    # Signal 2: Valuation Percentile
    # -----------------------------------------------------------------------
    logger.info("Fetching valuation data...")
    val_data = get_valuation_data()

    shiller_cape = val_data.get("current_cape")
    cape_pctile = val_data.get("cape_pctile_30y")
    buffett_ind = val_data.get("current_buffett")
    buffett_pctile = val_data.get("buffett_pctile_30y")

    valuation_score = compute_valuation_score(
        cape_pctile_30y=cape_pctile,
        buffett_pctile_30y=buffett_pctile,
    )
    logger.info("Signal 2 (Valuation): %.1f", valuation_score)

    # -----------------------------------------------------------------------
    # Signal 3: Credit Complacency
    # -----------------------------------------------------------------------
    logger.info("Fetching credit data...")
    cred_data = get_credit_data()

    hy_oas = cred_data.get("current_hy_oas")
    hy_oas_pctile = cred_data.get("hy_oas_pctile_5y")
    ccc_bb = cred_data.get("current_ccc_bb_ratio")
    ccc_bb_median = None
    if "ccc_bb_ratio" in cred_data:
        ratio_series = cred_data["ccc_bb_ratio"]
        ccc_bb_median = float(ratio_series.tail(252 * 5).median())

    hy_oas_20d_change = None
    if "hy_oas" in cred_data:
        hy_series = cred_data["hy_oas"]
        if len(hy_series) >= 21:
            hy_oas_20d_change = float(hy_series.iloc[-1] - hy_series.iloc[-21])

    credit_score = compute_credit_score(
        hy_oas_pctile_5y=hy_oas_pctile,
        ccc_bb_ratio=ccc_bb,
        ccc_bb_median_5y=ccc_bb_median,
        hy_oas_20d_change=hy_oas_20d_change,
    )
    logger.info("Signal 3 (Credit): %.1f", credit_score)

    # -----------------------------------------------------------------------
    # Signal 4: Sentiment Extreme
    # -----------------------------------------------------------------------
    logger.info("Fetching sentiment data...")
    sent_data = get_sentiment_data()

    aaii_4w = sent_data.get("current_aaii_4w")
    aaii_weeks = sent_data.get("aaii_weeks_above_25")
    fear_greed = sent_data.get("fear_greed")

    sentiment_score = compute_sentiment_score(
        aaii_bull_bear_4w=aaii_4w,
        aaii_weeks_above_25=aaii_weeks,
        fear_greed=fear_greed,
    )
    logger.info("Signal 4 (Sentiment): %.1f", sentiment_score)

    # -----------------------------------------------------------------------
    # Signal 5: Macro Deterioration
    # -----------------------------------------------------------------------
    logger.info("Fetching macro data...")
    macro_data = get_macro_data()

    lei_roc = macro_data.get("lei_6m_roc")
    ism_no = macro_data.get("current_ism_no")
    claims_pct = macro_data.get("claims_4w_vs_26w")

    macro_score = compute_macro_score(
        lei_6m_roc=lei_roc,
        ism_new_orders=ism_no,
        claims_4w_vs_26w=claims_pct,
    )
    logger.info("Signal 5 (Macro): %.1f", macro_score)

    # -----------------------------------------------------------------------
    # Signal 6: Margin Debt / Leverage
    # -----------------------------------------------------------------------
    logger.info("Fetching leverage data...")
    lev_data = get_leverage_data()

    margin_yoy = lev_data.get("margin_debt_yoy")
    free_credit_dec = lev_data.get("free_credit_declining")

    leverage_score = compute_leverage_score(
        margin_debt_yoy=margin_yoy,
        free_credit_declining=free_credit_dec,
    )
    logger.info("Signal 6 (Leverage): %.1f", leverage_score)

    # -----------------------------------------------------------------------
    # Composite Caution Level
    # -----------------------------------------------------------------------
    scores = {
        "breadth": breadth_score,
        "valuation": valuation_score if val_data else None,
        "credit": credit_score if cred_data else None,
        "sentiment": sentiment_score if sent_data else None,
        "macro": macro_score if macro_data else None,
        "leverage": leverage_score if lev_data else None,
    }

    result = compute_caution_level(scores)

    # Print summary
    print(format_caution_summary(result))

    # -----------------------------------------------------------------------
    # Store results
    # -----------------------------------------------------------------------
    signals_data = {
        "spx_close": spx_close,
        "spx_near_52w_high": int(spx_near_52w_high),
        "pct_above_200d": pct_above_200d,
        "nh_nl_ratio_20d": nh_nl_ratio_20d,
        "ad_line_20d_roc": ad_line_20d_roc,
        "breadth_score": breadth_score,
        "shiller_cape": shiller_cape,
        "cape_pctile_30y": cape_pctile,
        "buffett_indicator": buffett_ind,
        "fwd_pe": None,  # Would need FactSet or proxy
        "valuation_score": valuation_score,
        "hy_oas": hy_oas,
        "hy_oas_pctile_5y": hy_oas_pctile,
        "ccc_bb_ratio": ccc_bb,
        "credit_score": credit_score,
        "aaii_bull_bear_4w": aaii_4w,
        "aaii_weeks_above_25": aaii_weeks,
        "fear_greed": fear_greed,
        "sentiment_score": sentiment_score,
        "lei_6m_roc": lei_roc,
        "ism_new_orders": ism_no,
        "claims_4w_vs_26w": claims_pct,
        "macro_score": macro_score,
        "margin_debt_yoy": margin_yoy,
        "free_credit_declining": free_credit_dec,
        "leverage_score": leverage_score,
    }
    upsert_regime_signals(today, signals_data)

    caution_data = {
        "caution_level": result.caution_level,
        "regime": result.regime,
        "stale_flag": int(result.stale_flag),
        "breadth_contrib": result.contributions.get("breadth", 0),
        "valuation_contrib": result.contributions.get("valuation", 0),
        "credit_contrib": result.contributions.get("credit", 0),
        "sentiment_contrib": result.contributions.get("sentiment", 0),
        "macro_contrib": result.contributions.get("macro", 0),
        "leverage_contrib": result.contributions.get("leverage", 0),
    }
    upsert_regime_caution(today, caution_data)

    logger.info("Regime data stored for %s", today)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Market Regime Dashboard - Topping Conditions Monitor"
    )
    parser.add_argument(
        "--regime",
        action="store_true",
        help="Run the regime data pipeline (fetch + compute + store)",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the Streamlit dashboard",
    )
    args = parser.parse_args()

    if args.dashboard:
        import subprocess

        dashboard_path = "market_topping_regime/regime/dashboard.py"
        subprocess.run(
            ["streamlit", "run", dashboard_path],
            check=True,
        )
    elif args.regime:
        run_regime_pipeline()
    else:
        # Default: run pipeline
        run_regime_pipeline()


if __name__ == "__main__":
    main()
