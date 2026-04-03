"""Allow running as: python -m regime_dashboard"""

import argparse
import sys

from .dashboard import (
    print_dashboard,
    run_dashboard_live,
    run_dashboard_manual,
    to_json,
)


def main():
    parser = argparse.ArgumentParser(description="Regime Dashboard - Market Topping Framework")
    parser.add_argument("--live", action="store_true", help="Fetch live data from FRED API")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--example", action="store_true", help="Run with example April 2026 data")
    args = parser.parse_args()

    if args.example:
        assessment = run_dashboard_manual(
            pct_above_200dma=52,
            advance_decline_line_trend="flat",
            new_highs_vs_new_lows=1.5,
            top_10_concentration_pct=68,
            pe_ratio=23, cape_ratio=33, ev_ebitda=15,
            hy_spread_bps=320, ig_spread_bps=90, hy_spread_percentile=15,
            aaii_bull_bear_spread=18, vix=14, put_call_ratio=0.82, fear_greed_index=68,
            lei_yoy_change=-1.5, lei_monthly_change=-0.3, private_lei_yoy_change=-3.0,
            ism_manufacturing=48.5,
            margin_debt_yoy_pct=18, margin_debt_to_gdp=2.8, margin_debt_percentile=78,
            spread_2s10s_bps=110, term_premium_10y=0.85, term_premium_5y_avg=0.20,
            deficit_pct_gdp=6.5, debt_service_pct_revenue=22, fed_cutting=True,
            in_recession=False, interest_pct_revenue=22, fed_funds_rate_declining=True,
            core_pce_yoy=2.8, term_premium_rising=True,
        )
    elif args.live:
        try:
            assessment = run_dashboard_live()
        except EnvironmentError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        assessment = run_dashboard_manual()

    if args.json:
        print(to_json(assessment))
    else:
        print_dashboard(assessment)


if __name__ == "__main__":
    main()
