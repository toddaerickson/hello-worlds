"""Main dashboard entry point.

Orchestrates data fetching, signal evaluation, and regime assessment.
Can operate in two modes:
1. Live mode: Fetches data from FRED API
2. Manual mode: Accepts manually provided data points
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
    # Signal 3: Credit
    hy_spread_bps=None,
    ig_spread_bps=None,
    hy_spread_percentile=None,
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

    Returns a RegimeAssessment with all signals scored and the fiscal
    dominance flag evaluated.
    """
    # Evaluate all 7 signals
    s1 = evaluate_breadth(pct_above_200dma, advance_decline_line_trend, new_highs_vs_new_lows, top_10_concentration_pct)
    s2 = evaluate_valuation(pe_ratio, cape_ratio, ev_ebitda)
    s3 = evaluate_credit(hy_spread_bps, ig_spread_bps, hy_spread_percentile)
    s4 = evaluate_sentiment(aaii_bull_bear_spread, vix, put_call_ratio, fear_greed_index)
    s5 = evaluate_macro(lei_yoy_change, lei_monthly_change, private_lei_yoy_change, ism_manufacturing)
    s6 = evaluate_leverage(margin_debt_yoy_pct, margin_debt_to_gdp, margin_debt_percentile)
    s7 = evaluate_term_premium(
        spread_2s10s_bps, term_premium_10y, term_premium_5y_avg,
        deficit_pct_gdp, debt_service_pct_revenue, fed_cutting,
    )

    # Evaluate fiscal dominance flag
    # Use interest_pct_revenue if provided, fall back to debt_service_pct_revenue
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

    # Compute regime score
    all_signals = [s1, s2, s3, s4, s5, s6, s7]
    return compute_regime_score(all_signals, fd_flag)


def run_dashboard_live():
    """Run the dashboard fetching live data from FRED.

    Requires FRED_API_KEY environment variable to be set.

    Returns a RegimeAssessment. Note: Some signals (breadth, sentiment,
    margin debt) require non-FRED data sources and will need manual input.
    """
    from .fred_client import fetch_series, get_latest_value

    # Fetch FRED data
    t10y2y = get_latest_value("T10Y2Y")
    dff_data = fetch_series("DFF", observation_start="2025-01-01")
    pce_data = get_latest_value("PCEPILFE")
    # Derive values
    spread_2s10s_bps = t10y2y["value"] * 100 if t10y2y else None
    core_pce = pce_data["value"] if pce_data else None

    # Determine if Fed is cutting (compare current FFR to 6-month-ago FFR)
    fed_cutting = None
    if len(dff_data) >= 2:
        recent_ffr = dff_data[-1]["value"]
        older_ffr = dff_data[0]["value"]
        fed_cutting = recent_ffr < older_ffr

    # Run with available data (many signals will score 0 due to missing data)
    return run_dashboard_manual(
        spread_2s10s_bps=spread_2s10s_bps,
        core_pce_yoy=core_pce,
        fed_cutting=fed_cutting,
        fed_funds_rate_declining=fed_cutting,
    )


def print_dashboard(assessment: RegimeAssessment):
    """Print a formatted dashboard to stdout."""
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

    # Fiscal dominance flag
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

    # Individual signals
    print("-" * 72)
    print(f"  {'Signal':<32} {'Score':>6} {'Level':<12}")
    print("-" * 72)

    for sig in data["signals"]:
        name = sig["name"]
        score = sig["score"]
        level = sig["level"]
        print(f"  {name:<32} {score:>6} {level:<12}")

        if sig.get("fiscal_dominance_note"):
            # Wrap long notes
            note = sig["fiscal_dominance_note"]
            print(f"    FD: {note}")

        if sig.get("components"):
            for k, v in sig["components"].items():
                print(f"    {k}: {v}")

    print("-" * 72)
    print()


def to_json(assessment: RegimeAssessment) -> str:
    """Serialize assessment to JSON string."""
    return json.dumps(assessment.to_dict(), indent=2)


# CLI entry point
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Regime Dashboard - Market Topping Framework")
    parser.add_argument("--live", action="store_true", help="Fetch live data from FRED API")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--example", action="store_true", help="Run with example April 2026 data")
    args = parser.parse_args()

    if args.example:
        # Example: Approximate April 2026 conditions based on the analysis
        assessment = run_dashboard_manual(
            # Signal 1: Breadth - moderately concerning
            pct_above_200dma=52,
            advance_decline_line_trend="flat",
            new_highs_vs_new_lows=1.5,
            # Signal 2: Valuation - elevated
            pe_ratio=23,
            cape_ratio=33,
            ev_ebitda=15,
            # Signal 3: Credit - complacent
            hy_spread_bps=320,
            ig_spread_bps=90,
            hy_spread_percentile=15,
            # Signal 4: Sentiment - moderately bullish
            aaii_bull_bear_spread=18,
            vix=14,
            put_call_ratio=0.82,
            fear_greed_index=68,
            # Signal 5: Macro - mixed (headline OK, private weak)
            lei_yoy_change=-1.5,
            lei_monthly_change=-0.3,
            private_lei_yoy_change=-3.0,
            ism_manufacturing=48.5,
            # Signal 6: Leverage - elevated
            margin_debt_yoy_pct=18,
            margin_debt_to_gdp=2.8,
            margin_debt_percentile=78,
            # Signal 7: Term Premium / Fiscal Stress
            spread_2s10s_bps=110,
            term_premium_10y=0.85,
            term_premium_5y_avg=0.20,
            deficit_pct_gdp=6.5,
            debt_service_pct_revenue=22,
            fed_cutting=True,
            # Fiscal Dominance Flag
            in_recession=False,
            interest_pct_revenue=22,
            fed_funds_rate_declining=True,
            core_pce_yoy=2.8,
            term_premium_rising=True,
        )
    elif args.live:
        try:
            assessment = run_dashboard_live()
        except EnvironmentError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Run with no data (all signals score 0)
        assessment = run_dashboard_manual()

    if args.json:
        print(to_json(assessment))
    else:
        print_dashboard(assessment)
