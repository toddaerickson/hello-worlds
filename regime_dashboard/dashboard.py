"""Main dashboard entry point — orchestrates signal evaluation and scoring.

Two operating modes:
  1. Manual mode — accepts explicitly provided data points (for scenario
     analysis, historical backtesting, and the Streamlit frontend).
  2. Live mode — fetches real-time data from the FRED API. Note: only a
     subset of signals can be sourced from FRED; breadth, sentiment, and
     margin debt require other data sources or manual input.
"""

import json

from .scoring_engine import RegimeAssessment, compute_regime_score
from .signals import (
    evaluate_breadth,
    evaluate_credit,
    evaluate_fiscal_dominance,
    evaluate_leverage,
    evaluate_macro,
    evaluate_sentiment,
    evaluate_term_premium,
    evaluate_valuation,
)


def run_dashboard_manual(
    # Signal 1: Breadth
    pct_above_200dma=None,
    advance_decline_line_trend=None,
    new_highs_vs_new_lows=None,
    top_10_concentration_pct=None,
    # Signal 2: Valuation
    pe_ratio=None,
    cape_ratio=None,
    ev_ebitda=None,
    # Signal 3: Credit (dual-signal approach)
    ccc_bb_spread_bps=None,
    ccc_bb_spread_percentile=None,
    single_b_oas_bps=None,
    single_b_oas_percentile=None,
    single_b_oas_3mo_change_bps=None,
    ig_spread_bps=None,
    hy_spread_bps=None,            # Legacy fallback
    hy_spread_percentile=None,     # Legacy fallback
    # Signal 4: Sentiment
    aaii_bull_bear_spread=None,
    vix=None,
    put_call_ratio=None,
    fear_greed_index=None,
    # Signal 5: Macro
    lei_yoy_change=None,
    lei_monthly_change=None,
    private_lei_yoy_change=None,
    ism_manufacturing=None,
    # Signal 6: Leverage
    margin_debt_yoy_pct=None,
    margin_debt_to_gdp=None,
    margin_debt_percentile=None,
    # Signal 7: Term Premium / Fiscal Stress
    spread_2s10s_bps=None,
    term_premium_10y=None,
    term_premium_5y_avg=None,
    deficit_pct_gdp=None,
    debt_service_pct_revenue=None,
    fed_cutting=None,
    # Fiscal Dominance Flag inputs
    in_recession=False,
    interest_pct_revenue=None,
    fed_funds_rate_declining=None,
    core_pce_yoy=None,
    term_premium_rising=None,
) -> RegimeAssessment:
    """Run the full dashboard with manually provided data.

    Any parameter left as None is simply not scored (scores 0 contribution).
    Returns a RegimeAssessment with all 7 signals and the FD flag evaluated.
    """
    # --- Evaluate all 7 signals ---
    s1 = evaluate_breadth(pct_above_200dma, advance_decline_line_trend,
                          new_highs_vs_new_lows, top_10_concentration_pct)
    s2 = evaluate_valuation(pe_ratio, cape_ratio, ev_ebitda)
    s3 = evaluate_credit(
        ccc_bb_spread_bps=ccc_bb_spread_bps,
        ccc_bb_spread_percentile=ccc_bb_spread_percentile,
        single_b_oas_bps=single_b_oas_bps,
        single_b_oas_percentile=single_b_oas_percentile,
        single_b_oas_3mo_change_bps=single_b_oas_3mo_change_bps,
        ig_spread_bps=ig_spread_bps,
        hy_spread_bps=hy_spread_bps,
        hy_spread_percentile=hy_spread_percentile,
    )
    s4 = evaluate_sentiment(aaii_bull_bear_spread, vix, put_call_ratio, fear_greed_index)
    s5 = evaluate_macro(lei_yoy_change, lei_monthly_change,
                        private_lei_yoy_change, ism_manufacturing)
    s6 = evaluate_leverage(margin_debt_yoy_pct, margin_debt_to_gdp, margin_debt_percentile)
    s7 = evaluate_term_premium(
        spread_2s10s_bps, term_premium_10y, term_premium_5y_avg,
        deficit_pct_gdp, debt_service_pct_revenue, fed_cutting,
    )

    # --- Evaluate fiscal dominance flag ---
    # Use interest_pct_revenue if provided; fall back to debt_service_pct_revenue
    fd_interest = interest_pct_revenue if interest_pct_revenue is not None else debt_service_pct_revenue
    fd_fed_declining = fed_funds_rate_declining if fed_funds_rate_declining is not None else fed_cutting

    fd_flag = evaluate_fiscal_dominance(
        deficit_pct_gdp=deficit_pct_gdp,
        in_recession=in_recession,
        interest_pct_revenue=fd_interest,
        fed_funds_rate_declining=fd_fed_declining,
        core_pce_yoy=core_pce_yoy,
        spread_2s10s_bps=spread_2s10s_bps,
        term_premium_rising=term_premium_rising,
    )

    # --- Compute composite regime score ---
    return compute_regime_score([s1, s2, s3, s4, s5, s6, s7], fd_flag)


def run_dashboard_live():
    """Run the dashboard fetching live data from the FRED API.

    Requires the FRED_API_KEY environment variable to be set.
    Only a subset of signals can be sourced from FRED (yield curve, PCE,
    Fed Funds rate). Breadth, sentiment, and margin debt data require
    non-FRED sources and will default to 0 when not provided.
    """
    from .fred_client import fetch_series, get_latest_value

    # Fetch available FRED series
    t10y2y = get_latest_value("T10Y2Y")       # 2s10s spread (%)
    dff_data = fetch_series("DFF", observation_start="2025-01-01")  # Fed Funds Rate
    pce_data = get_latest_value("PCEPILFE")    # Core PCE YoY

    # Derive input values
    spread_2s10s_bps = t10y2y["value"] * 100 if t10y2y else None
    core_pce = pce_data["value"] if pce_data else None

    # Determine if Fed is cutting: compare latest FFR to start-of-year
    fed_cutting = None
    if len(dff_data) >= 2:
        recent_ffr = dff_data[-1]["value"]
        older_ffr = dff_data[0]["value"]
        fed_cutting = recent_ffr < older_ffr

    # Run with available data (many signals will score 0)
    return run_dashboard_manual(
        spread_2s10s_bps=spread_2s10s_bps,
        core_pce_yoy=core_pce,
        fed_cutting=fed_cutting,
        fed_funds_rate_declining=fed_cutting,
    )


def print_dashboard(assessment: RegimeAssessment):
    """Print a formatted dashboard summary to stdout."""
    data = assessment.to_dict()

    print("=" * 72)
    print("  REGIME DASHBOARD - MARKET TOPPING FRAMEWORK")
    print("=" * 72)
    print()

    level = data["regime_level"].upper()
    score = data["adjusted_composite_score"]
    raw = data["raw_composite_score"]

    print(f"  REGIME LEVEL:     {level}")
    print(f"  COMPOSITE SCORE:  {score}/100", end="")
    if data["fiscal_dominance_active"]:
        print(f"  (raw: {raw} + {data['fiscal_dominance_modifier']} fiscal dominance modifier)")
    else:
        print()
    print()

    # Fiscal dominance flag status
    if data["fiscal_dominance_active"]:
        print("  *** FISCAL DOMINANCE FLAG: ACTIVE ***")
        print(f"  Conditions met: {data['fiscal_dominance_conditions_met']}/4")
        for name, detail in data["fiscal_dominance_details"].items():
            status = "MET" if detail.get("met") else "NOT MET"
            print(f"    [{status}] {name}")
        print()

    # Warnings
    for warning in data["warnings"]:
        print(f"  WARNING: {warning}")
    if data["warnings"]:
        print()

    # Individual signal scores
    print("-" * 72)
    print(f"  {'Signal':<32} {'Score':>6} {'Level':<12}")
    print("-" * 72)

    for sig in data["signals"]:
        print(f"  {sig['name']:<32} {sig['score']:>6} {sig['level']:<12}")

        if sig.get("fiscal_dominance_note"):
            print(f"    FD: {sig['fiscal_dominance_note']}")

        if sig.get("components"):
            for k, v in sig["components"].items():
                print(f"    {k}: {v}")

    print("-" * 72)
    print()


def to_json(assessment: RegimeAssessment) -> str:
    """Serialize assessment to a formatted JSON string."""
    return json.dumps(assessment.to_dict(), indent=2)
