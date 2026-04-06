"""CLI entry point: python -m regime_dashboard

Modes:
  --example   Run with hardcoded April 2026 scenario data (no API key needed)
  --live      Fetch real-time data from the FRED API (requires FRED_API_KEY)
  --json      Output the assessment as formatted JSON instead of a text table
  (no flags)  Run with all inputs as None (all signals score 0)
"""

import argparse
import sys

from .dashboard import (
    print_dashboard,
    run_dashboard_live,
    run_dashboard_manual,
    to_json,
)


def main():
    parser = argparse.ArgumentParser(
        description="Regime Dashboard - Market Topping Framework"
    )
    parser.add_argument("--live", action="store_true",
                        help="Fetch live data from FRED API")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--example", action="store_true",
                        help="Run with example April 2026 data")
    args = parser.parse_args()

    if args.example:
        # Hardcoded scenario: approximate April 2026 conditions
        # All 4 FD conditions are met → fiscal dominance flag is active
        assessment = run_dashboard_manual(
            # Signal 1: Breadth — moderately concerning
            pct_above_200dma=52,
            advance_decline_line_trend="flat",
            new_highs_vs_new_lows=1.5,
            top_10_concentration_pct=68,
            # Signal 2: Valuation — elevated
            pe_ratio=23, cape_ratio=33, ev_ebitda=15,
            # Signal 3: Credit — complacent (tight CCC-BB and Single-B spreads)
            ccc_bb_spread_bps=480, ccc_bb_spread_percentile=15,
            single_b_oas_bps=260, single_b_oas_percentile=12,
            single_b_oas_3mo_change_bps=-10, ig_spread_bps=90,
            # Signal 4: Sentiment — moderately bullish
            aaii_bull_bear_spread=18, vix=14, put_call_ratio=0.82,
            fear_greed_index=68,
            # Signal 5: Macro — mixed (headline OK, private weak)
            lei_yoy_change=-1.5, lei_monthly_change=-0.3,
            private_lei_yoy_change=-3.0, ism_manufacturing=48.5,
            # Signal 6: Leverage — elevated
            margin_debt_yoy_pct=18, margin_debt_to_gdp=2.8,
            margin_debt_percentile=78,
            # Signal 7: Term Premium / Fiscal Stress
            spread_2s10s_bps=110, term_premium_10y=0.85,
            term_premium_5y_avg=0.20, deficit_pct_gdp=6.5,
            debt_service_pct_revenue=22, fed_cutting=True,
            # Fiscal Dominance Flag inputs
            in_recession=False, interest_pct_revenue=22,
            fed_funds_rate_declining=True, core_pce_yoy=2.8,
            term_premium_rising=True,
        )
    elif args.live:
        try:
            assessment = run_dashboard_live()
        except EnvironmentError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # No data → all signals score 0 (useful for testing)
        assessment = run_dashboard_manual()

    if args.json:
        print(to_json(assessment))
    else:
        print_dashboard(assessment)


if __name__ == "__main__":
    main()
