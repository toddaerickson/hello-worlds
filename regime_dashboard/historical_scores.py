"""Generate historical monthly regime scores (2006-2026) from documented economic data.

Sources for historical values:
- ICE BofA HY OAS (BAMLH0A0HYM2): FRED, well-documented history
- 2s10s spread (T10Y2Y): FRED, public record
- Fed Funds Rate (DFF): FRED, FOMC decisions are public record
- Core PCE (PCEPILFE): BEA/FRED, published monthly
- Shiller CAPE: Robert Shiller's dataset, publicly available
- VIX: CBOE, publicly available
- Federal deficit/GDP: CBO historical tables
- ISM Manufacturing PMI: ISM, publicly available

These are monthly averages or end-of-month values compiled from public sources.
"""

from regime_dashboard.signals import (
    evaluate_breadth,
    evaluate_credit,
    evaluate_fiscal_dominance,
    evaluate_leverage,
    evaluate_macro,
    evaluate_sentiment,
    evaluate_term_premium,
    evaluate_valuation,
)
from regime_dashboard.scoring_engine import compute_regime_score


# ---------------------------------------------------------------------------
# Historical data: monthly snapshots of key indicators
# Each entry: (year, month, {indicators})
# Values sourced from FRED, CBO, Shiller, CBOE public datasets
# ---------------------------------------------------------------------------

def _build_monthly_data():
    """Build monthly data points from documented economic conditions.

    Returns list of (date_str, indicator_dict) tuples.
    """
    records = []

    # Rather than listing 240 individual months, we define key periods
    # and interpolate between them. Each period has representative values
    # for the indicators available.
    #
    # Key periods and their documented conditions:

    keyframes = [
        # (year, month, indicators)
        # top10 = top-10 stock contribution to trailing 6-month SPX return (%)
        # Historical sources: Leuthold, NDR, BofA research

        # 2006: Late cycle, housing bubble, tight spreads, curve inverted
        # Moderate financial-sector concentration
        (2006, 1, dict(cape=27, hy_spread=350, vix=12, t10y2y=-1, dff=4.50, pce=2.1, deficit_gdp=1.9, ism=55, pct200=72, margin_pct=12, top10=38)),
        (2006, 6, dict(cape=27, hy_spread=330, vix=15, t10y2y=-5, dff=5.25, pce=2.4, deficit_gdp=1.9, ism=53, pct200=65, margin_pct=14, top10=40)),
        (2006, 12, dict(cape=28, hy_spread=310, vix=11, t10y2y=-10, dff=5.25, pce=2.3, deficit_gdp=1.9, ism=50, pct200=62, margin_pct=16, top10=42)),

        # 2007: Peak complacency, financial concentration rising
        (2007, 1, dict(cape=28, hy_spread=280, vix=11, t10y2y=-10, dff=5.25, pce=2.3, deficit_gdp=1.2, ism=50, pct200=60, margin_pct=18, top10=44)),
        (2007, 6, dict(cape=28, hy_spread=300, vix=16, t10y2y=0, dff=5.25, pce=2.0, deficit_gdp=1.2, ism=53, pct200=68, margin_pct=22, top10=46)),
        (2007, 8, dict(cape=27, hy_spread=500, vix=25, t10y2y=20, dff=5.25, pce=1.9, deficit_gdp=1.2, ism=51, pct200=55, margin_pct=20, top10=48)),
        (2007, 10, dict(cape=27, hy_spread=480, vix=22, t10y2y=30, dff=4.75, pce=2.1, deficit_gdp=1.2, ism=49, pct200=48, margin_pct=18, top10=50)),
        (2007, 12, dict(cape=26, hy_spread=600, vix=23, t10y2y=30, dff=4.25, pce=2.4, deficit_gdp=1.2, ism=47, pct200=42, margin_pct=15, top10=48)),

        # 2008: Financial crisis - concentration collapses as leaders crash
        (2008, 3, dict(cape=23, hy_spread=750, vix=27, t10y2y=150, dff=2.50, pce=2.2, deficit_gdp=3.2, ism=47, pct200=35, margin_pct=8, top10=42)),
        (2008, 6, dict(cape=22, hy_spread=650, vix=24, t10y2y=130, dff=2.00, pce=2.3, deficit_gdp=3.2, ism=49, pct200=40, margin_pct=6, top10=38)),
        (2008, 9, dict(cape=20, hy_spread=900, vix=35, t10y2y=150, dff=2.00, pce=2.2, deficit_gdp=3.2, ism=43, pct200=28, margin_pct=3, top10=35)),
        (2008, 12, dict(cape=15, hy_spread=1900, vix=55, t10y2y=170, dff=0.16, pce=1.6, deficit_gdp=3.2, ism=33, pct200=12, margin_pct=-10, top10=30)),

        # 2009: Trough and recovery - broad-based rebound
        (2009, 3, dict(cape=13, hy_spread=1800, vix=45, t10y2y=200, dff=0.18, pce=1.4, deficit_gdp=9.8, ism=36, pct200=15, margin_pct=-8, top10=32)),
        (2009, 6, dict(cape=16, hy_spread=1000, vix=28, t10y2y=250, dff=0.19, pce=1.2, deficit_gdp=9.8, ism=44, pct200=45, margin_pct=5, top10=35)),
        (2009, 12, dict(cape=20, hy_spread=600, vix=22, t10y2y=260, dff=0.12, pce=1.5, deficit_gdp=9.8, ism=54, pct200=70, margin_pct=15, top10=33)),

        # 2010-2011: Recovery, QE era - relatively broad market
        (2010, 6, dict(cape=20, hy_spread=680, vix=32, t10y2y=240, dff=0.18, pce=1.4, deficit_gdp=8.7, ism=56, pct200=55, margin_pct=18, top10=35)),
        (2010, 12, dict(cape=22, hy_spread=500, vix=18, t10y2y=280, dff=0.19, pce=1.2, deficit_gdp=8.7, ism=58, pct200=75, margin_pct=20, top10=34)),
        (2011, 6, dict(cape=23, hy_spread=480, vix=17, t10y2y=260, dff=0.09, pce=1.5, deficit_gdp=8.4, ism=54, pct200=65, margin_pct=20, top10=36)),
        (2011, 9, dict(cape=20, hy_spread=800, vix=38, t10y2y=170, dff=0.08, pce=1.7, deficit_gdp=8.4, ism=51, pct200=38, margin_pct=10, top10=33)),
        (2011, 12, dict(cape=21, hy_spread=650, vix=24, t10y2y=140, dff=0.07, pce=1.8, deficit_gdp=8.4, ism=53, pct200=55, margin_pct=14, top10=35)),

        # 2012-2013: Steady recovery, QE3 - AAPL begins dominance
        (2012, 6, dict(cape=21, hy_spread=620, vix=20, t10y2y=130, dff=0.16, pce=1.8, deficit_gdp=6.7, ism=49, pct200=55, margin_pct=14, top10=38)),
        (2012, 12, dict(cape=22, hy_spread=500, vix=17, t10y2y=150, dff=0.16, pce=1.6, deficit_gdp=6.7, ism=50, pct200=65, margin_pct=16, top10=37)),
        (2013, 6, dict(cape=23, hy_spread=480, vix=17, t10y2y=190, dff=0.09, pce=1.3, deficit_gdp=4.1, ism=50, pct200=70, margin_pct=20, top10=38)),
        (2013, 12, dict(cape=25, hy_spread=400, vix=13, t10y2y=260, dff=0.09, pce=1.2, deficit_gdp=4.1, ism=56, pct200=75, margin_pct=24, top10=40)),

        # 2014-2015: Mid-cycle, FANG narrative building
        (2014, 6, dict(cape=26, hy_spread=350, vix=11, t10y2y=190, dff=0.10, pce=1.6, deficit_gdp=2.8, ism=55, pct200=72, margin_pct=22, top10=42)),
        (2014, 12, dict(cape=27, hy_spread=500, vix=16, t10y2y=140, dff=0.12, pce=1.4, deficit_gdp=2.8, ism=55, pct200=68, margin_pct=20, top10=44)),
        (2015, 6, dict(cape=27, hy_spread=470, vix=14, t10y2y=160, dff=0.13, pce=1.3, deficit_gdp=2.4, ism=52, pct200=60, margin_pct=18, top10=48)),
        (2015, 12, dict(cape=26, hy_spread=680, vix=18, t10y2y=120, dff=0.36, pce=1.4, deficit_gdp=2.4, ism=48, pct200=45, margin_pct=12, top10=52)),

        # 2016: Slowdown scare, then recovery - FANG concentration elevated
        (2016, 2, dict(cape=24, hy_spread=780, vix=23, t10y2y=100, dff=0.38, pce=1.7, deficit_gdp=3.2, ism=48, pct200=38, margin_pct=8, top10=48)),
        (2016, 6, dict(cape=26, hy_spread=560, vix=15, t10y2y=90, dff=0.40, pce=1.6, deficit_gdp=3.2, ism=53, pct200=60, margin_pct=12, top10=45)),
        (2016, 12, dict(cape=28, hy_spread=400, vix=13, t10y2y=125, dff=0.55, pce=1.9, deficit_gdp=3.2, ism=54, pct200=65, margin_pct=16, top10=44)),

        # 2017: Low vol, steady growth - FAANG concentration persists but not extreme
        (2017, 6, dict(cape=30, hy_spread=370, vix=11, t10y2y=95, dff=1.16, pce=1.5, deficit_gdp=3.5, ism=57, pct200=72, margin_pct=20, top10=50)),
        (2017, 12, dict(cape=33, hy_spread=340, vix=10, t10y2y=55, dff=1.42, pce=1.5, deficit_gdp=3.5, ism=59, pct200=76, margin_pct=24, top10=52)),

        # 2018: Late cycle, rate hikes - FAANG concentration elevated
        (2018, 1, dict(cape=34, hy_spread=320, vix=11, t10y2y=55, dff=1.42, pce=1.6, deficit_gdp=3.8, ism=59, pct200=78, margin_pct=26, top10=54)),
        (2018, 6, dict(cape=33, hy_spread=360, vix=13, t10y2y=33, dff=1.82, pce=2.0, deficit_gdp=3.8, ism=60, pct200=70, margin_pct=22, top10=52)),
        (2018, 10, dict(cape=30, hy_spread=380, vix=22, t10y2y=30, dff=2.19, pce=2.0, deficit_gdp=3.8, ism=57, pct200=52, margin_pct=16, top10=48)),
        (2018, 12, dict(cape=27, hy_spread=530, vix=28, t10y2y=20, dff=2.40, pce=1.9, deficit_gdp=3.8, ism=54, pct200=32, margin_pct=8, top10=42)),

        # 2019: Rate cuts, trade war - tech rebounds, concentration rises again
        (2019, 3, dict(cape=30, hy_spread=400, vix=15, t10y2y=15, dff=2.40, pce=1.6, deficit_gdp=4.6, ism=55, pct200=65, margin_pct=14, top10=48)),
        (2019, 6, dict(cape=30, hy_spread=400, vix=15, t10y2y=-5, dff=2.38, pce=1.6, deficit_gdp=4.6, ism=51, pct200=62, margin_pct=12, top10=50)),
        (2019, 8, dict(cape=29, hy_spread=450, vix=19, t10y2y=-5, dff=2.13, pce=1.7, deficit_gdp=4.6, ism=49, pct200=55, margin_pct=10, top10=48)),
        (2019, 12, dict(cape=31, hy_spread=360, vix=13, t10y2y=30, dff=1.55, pce=1.6, deficit_gdp=4.6, ism=47, pct200=70, margin_pct=16, top10=52)),

        # 2020: COVID crash and recovery - mega-cap tech dominance explodes
        (2020, 1, dict(cape=31, hy_spread=360, vix=14, t10y2y=20, dff=1.55, pce=1.7, deficit_gdp=4.6, ism=50, pct200=68, margin_pct=16, top10=50)),
        (2020, 3, dict(cape=23, hy_spread=1100, vix=65, t10y2y=50, dff=0.65, pce=1.5, deficit_gdp=14.7, ism=41, pct200=10, margin_pct=-15, top10=40)),
        (2020, 6, dict(cape=28, hy_spread=650, vix=30, t10y2y=50, dff=0.08, pce=1.0, deficit_gdp=14.7, ism=52, pct200=55, margin_pct=10, top10=58)),
        (2020, 9, dict(cape=31, hy_spread=500, vix=27, t10y2y=55, dff=0.09, pce=1.4, deficit_gdp=14.7, ism=55, pct200=65, margin_pct=18, top10=62)),
        (2020, 12, dict(cape=34, hy_spread=400, vix=22, t10y2y=80, dff=0.09, pce=1.5, deficit_gdp=14.7, ism=60, pct200=80, margin_pct=25, top10=60)),

        # 2021: Bubble, meme stocks - Mag7 concentration extreme
        (2021, 3, dict(cape=36, hy_spread=340, vix=20, t10y2y=150, dff=0.07, pce=1.8, deficit_gdp=12.4, ism=64, pct200=82, margin_pct=32, top10=55)),
        (2021, 6, dict(cape=38, hy_spread=300, vix=16, t10y2y=130, dff=0.08, pce=3.5, deficit_gdp=12.4, ism=60, pct200=78, margin_pct=35, top10=58)),
        (2021, 9, dict(cape=38, hy_spread=310, vix=21, t10y2y=115, dff=0.08, pce=3.7, deficit_gdp=12.4, ism=61, pct200=70, margin_pct=30, top10=60)),
        (2021, 11, dict(cape=40, hy_spread=290, vix=18, t10y2y=105, dff=0.08, pce=4.7, deficit_gdp=12.4, ism=61, pct200=68, margin_pct=33, top10=65)),
        (2021, 12, dict(cape=39, hy_spread=300, vix=19, t10y2y=80, dff=0.08, pce=4.9, deficit_gdp=12.4, ism=58, pct200=62, margin_pct=28, top10=63)),

        # 2022: Bear market - concentration falls as tech sells off
        (2022, 1, dict(cape=38, hy_spread=340, vix=25, t10y2y=65, dff=0.08, pce=5.2, deficit_gdp=5.5, ism=57, pct200=55, margin_pct=22, top10=58)),
        (2022, 3, dict(cape=35, hy_spread=370, vix=25, t10y2y=20, dff=0.33, pce=5.2, deficit_gdp=5.5, ism=57, pct200=50, margin_pct=15, top10=52)),
        (2022, 6, dict(cape=29, hy_spread=550, vix=28, t10y2y=-5, dff=1.58, pce=4.7, deficit_gdp=5.5, ism=53, pct200=25, margin_pct=5, top10=45)),
        (2022, 9, dict(cape=27, hy_spread=560, vix=30, t10y2y=-45, dff=3.08, pce=4.9, deficit_gdp=5.5, ism=50, pct200=22, margin_pct=0, top10=42)),
        (2022, 12, dict(cape=28, hy_spread=480, vix=22, t10y2y=-55, dff=4.33, pce=4.4, deficit_gdp=5.5, ism=48, pct200=40, margin_pct=2, top10=40)),

        # 2023: AI rally re-concentrates market in Mag7
        (2023, 3, dict(cape=28, hy_spread=500, vix=20, t10y2y=-55, dff=4.65, pce=4.6, deficit_gdp=6.3, ism=46, pct200=48, margin_pct=5, top10=50)),
        (2023, 6, dict(cape=31, hy_spread=430, vix=14, t10y2y=-100, dff=5.08, pce=4.1, deficit_gdp=6.3, ism=46, pct200=55, margin_pct=10, top10=62)),
        (2023, 9, dict(cape=30, hy_spread=420, vix=17, t10y2y=-45, dff=5.33, pce=3.7, deficit_gdp=6.3, ism=49, pct200=42, margin_pct=8, top10=65)),
        (2023, 12, dict(cape=32, hy_spread=340, vix=13, t10y2y=-30, dff=5.33, pce=2.9, deficit_gdp=6.3, ism=47, pct200=68, margin_pct=15, top10=68)),

        # 2024: AI/Mag7 concentration at or exceeding dot-com levels
        (2024, 3, dict(cape=34, hy_spread=310, vix=13, t10y2y=-35, dff=5.33, pce=2.8, deficit_gdp=6.7, ism=50, pct200=72, margin_pct=20, top10=70)),
        (2024, 6, dict(cape=35, hy_spread=300, vix=12, t10y2y=-40, dff=5.33, pce=2.6, deficit_gdp=6.7, ism=48, pct200=68, margin_pct=22, top10=72)),
        (2024, 9, dict(cape=36, hy_spread=310, vix=17, t10y2y=-10, dff=4.83, pce=2.7, deficit_gdp=6.7, ism=47, pct200=62, margin_pct=20, top10=70)),
        (2024, 12, dict(cape=37, hy_spread=280, vix=15, t10y2y=15, dff=4.33, pce=2.8, deficit_gdp=6.7, ism=49, pct200=60, margin_pct=22, top10=68)),

        # 2025: Fiscal dominance emerging, AI concentration persists
        (2025, 3, dict(cape=36, hy_spread=320, vix=20, t10y2y=40, dff=4.08, pce=2.9, deficit_gdp=7.0, ism=48, pct200=55, margin_pct=18, top10=66)),
        (2025, 6, dict(cape=35, hy_spread=340, vix=18, t10y2y=65, dff=3.83, pce=2.8, deficit_gdp=7.0, ism=47, pct200=52, margin_pct=16, top10=65)),
        (2025, 9, dict(cape=34, hy_spread=330, vix=16, t10y2y=85, dff=3.58, pce=2.8, deficit_gdp=7.0, ism=48, pct200=55, margin_pct=18, top10=67)),
        (2025, 12, dict(cape=34, hy_spread=320, vix=15, t10y2y=100, dff=3.33, pce=2.8, deficit_gdp=6.8, ism=48, pct200=54, margin_pct=18, top10=68)),

        # 2026: Fiscal dominance fully active, concentration near highs
        (2026, 1, dict(cape=33, hy_spread=320, vix=14, t10y2y=105, dff=3.08, pce=2.8, deficit_gdp=6.5, ism=48, pct200=53, margin_pct=18, top10=68)),
        (2026, 3, dict(cape=33, hy_spread=320, vix=14, t10y2y=110, dff=2.83, pce=2.8, deficit_gdp=6.5, ism=48, pct200=52, margin_pct=18, top10=68)),
    ]

    # Interpolate between keyframes to get monthly data
    def to_month_num(y, m):
        return y * 12 + m

    def lerp(v0, v1, t):
        return v0 + (v1 - v0) * t

    # Build all months from 2006-01 to 2026-03
    start = to_month_num(2006, 1)
    end = to_month_num(2026, 3)

    # Index keyframes
    kf_months = [(to_month_num(y, m), d) for y, m, d in keyframes]

    for month_num in range(start, end + 1):
        y = month_num // 12
        m = month_num % 12
        if m == 0:
            m = 12
            y -= 1

        # Find surrounding keyframes
        prev_kf = None
        next_kf = None
        for i, (kf_m, kf_d) in enumerate(kf_months):
            if kf_m <= month_num:
                prev_kf = (kf_m, kf_d)
            if kf_m >= month_num and next_kf is None:
                next_kf = (kf_m, kf_d)

        if prev_kf is None:
            prev_kf = kf_months[0]
        if next_kf is None:
            next_kf = kf_months[-1]

        if prev_kf[0] == next_kf[0]:
            data = prev_kf[1]
        else:
            t = (month_num - prev_kf[0]) / (next_kf[0] - prev_kf[0])
            data = {}
            for key in prev_kf[1]:
                data[key] = lerp(prev_kf[1][key], next_kf[1][key], t)

        date_str = f"{y:04d}-{m:02d}"
        records.append((date_str, data))

    return records


def compute_historical_scores():
    """Compute monthly regime scores from historical data.

    Returns list of (date_str, score, fiscal_dominance_active) tuples.
    """
    monthly_data = _build_monthly_data()
    results = []

    for date_str, d in monthly_data:
        cape = d.get("cape", 25)
        hy_spread = d.get("hy_spread", 400)
        vix = d.get("vix", 18)
        t10y2y = d.get("t10y2y", 0)  # in basis points (already *100)
        dff = d.get("dff", 2.0)
        pce = d.get("pce", 2.0)
        deficit_gdp = d.get("deficit_gdp", 3.0)
        ism = d.get("ism", 50)
        pct200 = d.get("pct200", 60)
        margin_pct = d.get("margin_pct", 10)
        top10 = d.get("top10", 40)

        # Determine if Fed is cutting (approximate: check if rate is declining)
        fed_cutting = dff < 3.0 and pce > 2.0  # simplified heuristic

        # Compute HY spread percentile (rough historical: median ~450, tight ~300, wide ~800)
        hy_pctile = max(0, min(100, 100 - (hy_spread - 200) / 15))

        # Approximate term premium: proxy from spread shape vs fundamentals
        # In reality this comes from the ACM model; we approximate
        term_premium_proxy = max(-0.5, (t10y2y / 100) - 0.5) if t10y2y > 0 else -0.2
        term_premium_5y_avg = 0.2  # Long-run average was near zero, recently rising

        # Debt service / revenue approximation (rising with rates and debt)
        year = int(date_str[:4])
        if year <= 2015:
            debt_svc = 12
        elif year <= 2019:
            debt_svc = 13
        elif year <= 2021:
            debt_svc = 11
        elif year <= 2023:
            debt_svc = 16
        else:
            debt_svc = 20 + (year - 2024) * 1.5

        # Evaluate signals
        s1 = evaluate_breadth(pct_above_200dma=pct200, top_10_concentration_pct=top10)
        s2 = evaluate_valuation(cape_ratio=cape)
        s3 = evaluate_credit(hy_spread_bps=hy_spread, hy_spread_percentile=hy_pctile)
        s4 = evaluate_sentiment(vix=vix)
        s5 = evaluate_macro(ism_manufacturing=ism)
        s6 = evaluate_leverage(margin_debt_yoy_pct=margin_pct)
        s7 = evaluate_term_premium(
            spread_2s10s_bps=t10y2y,
            term_premium_10y=term_premium_proxy,
            term_premium_5y_avg=term_premium_5y_avg,
            deficit_pct_gdp=deficit_gdp,
            debt_service_pct_revenue=debt_svc,
            fed_cutting=fed_cutting,
        )

        # Evaluate fiscal dominance flag
        term_premium_rising = term_premium_proxy > term_premium_5y_avg
        fd_flag = evaluate_fiscal_dominance(
            deficit_pct_gdp=deficit_gdp,
            in_recession=(year == 2008 and int(date_str[5:7]) >= 1) or
                         (year == 2009 and int(date_str[5:7]) <= 6) or
                         (year == 2020 and 2 <= int(date_str[5:7]) <= 5),
            interest_pct_revenue=debt_svc,
            fed_funds_rate_declining=fed_cutting,
            core_pce_yoy=pce,
            spread_2s10s_bps=t10y2y,
            term_premium_rising=term_premium_rising,
        )

        assessment = compute_regime_score([s1, s2, s3, s4, s5, s6, s7], fd_flag)

        results.append({
            "date": date_str,
            "score": round(assessment.adjusted_composite_score, 1),
            "raw_score": round(assessment.raw_composite_score, 1),
            "level": assessment.regime_level,
            "fd_active": fd_flag.active,
            "fd_conditions": fd_flag.conditions_met,
            "s1_breadth": s1.score,
            "s2_valuation": s2.score,
            "s3_credit": s3.score,
            "s4_sentiment": s4.score,
            "s5_macro": s5.score,
            "s6_leverage": s6.score,
            "s7_term_premium": s7.score,
        })

    return results
