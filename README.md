# hello-worlds

Prep for classes. A collection of projects.

## Grateful Dead Hangman

A single-player hangman game featuring Grateful Dead song titles and multiple other categories. Available as both a Python console game and a mobile-friendly HTML/JS version.

- **Play online**: [https://toddaerickson.github.io/hello-worlds/](https://toddaerickson.github.io/hello-worlds/)
- **Console version**: `python hangman.py`
- **Tests**: `python -m pytest test_hangman.py`

Categories: Grateful Dead, College Music, Fashion, Knitting, Bio, Colors.

---

## Market Topping Regime Dashboard

7-signal composite caution-level indicator (0-100) that monitors market conditions for topping risk, with a Fiscal Dominance structural modifier. Historical backtest spans **January 1980 through March 2026** (555 monthly data points) with an S&P 500 price overlay.

### Signals

| # | Signal | What it measures |
|---|--------|-----------------|
| 1 | **Breadth Divergence & Concentration** | % above 200d MA, A/D line, new highs/lows, top-10 stock concentration |
| 2 | **Valuation** | P/E, CAPE (Shiller), EV/EBITDA |
| 3 | **Credit Complacency** | CCC-BB spread (primary risk appetite), Single-B OAS (absolute stress), IG spread; WIDENING_FAST override on Single-B 3mo change |
| 4 | **Sentiment Extremes** | AAII bull/bear, VIX, put/call ratio, CNN Fear & Greed |
| 5 | **Macro Deterioration** | Conference Board LEI, private-sector LEI (ex-govt), ISM Manufacturing |
| 6 | **Margin Debt / Leverage** | Margin debt YoY growth, debt/GDP, percentile rank |
| 7 | **Term Premium / Fiscal Stress** | 2s10s spread, 10y term premium, deficit/GDP, debt service ratio |

### Fiscal Dominance Flag

Structural modifier that activates when **3 of 4** conditions are met:

1. Federal deficit > 5% of GDP (non-recession year)
2. Interest expense > 15% of tax revenue
3. Fed easing while core PCE > 2.5% (easing despite above-target inflation)
4. 2s10s > 75 bps with rising term premium (curve steepening for the "wrong reasons")

When active: **+10 caution modifier**, Signal 5 rescored using private-sector LEI (strips government spending distortion), Signal 7 weighted at **1.5x** (vs 0.3x in normal regime), Valuation and Credit up-weighted, Macro de-emphasized, all signal interpretations adjusted.

### Interfaces

The dashboard is available in three formats:

| Format | How to access | Description |
|--------|---------------|-------------|
| **CLI** | `python -m regime_dashboard --example` | Text table output to terminal |
| **Static PNG** | `python regime_chart.py` | Multi-panel chart with S&P 500 overlay |
| **Interactive HTML** | Open `regime_chart.html` in a browser | Chart.js with hover tooltips and signal breakdown |
| **Streamlit** | `streamlit run streamlit_app.py` | Interactive sidebar controls, real-time scoring, historical chart |

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with example April 2026 data (no API key needed)
python -m regime_dashboard --example

# Output as JSON
python -m regime_dashboard --example --json

# Generate static PNG chart (1980-2026, with S&P 500 overlay)
python regime_chart.py

# Launch interactive Streamlit dashboard
streamlit run streamlit_app.py

# Live mode (requires FRED API key)
export FRED_API_KEY=your_key_here
python -m regime_dashboard --live

# Run tests (48 tests)
python -m pytest test_regime_dashboard.py -v
```

### Project Structure

```
regime_dashboard/
  __init__.py          # Package marker with usage notes
  __main__.py          # CLI entry point (python -m regime_dashboard)
  signals.py           # All 7 signal evaluation functions + Fiscal Dominance Flag
  scoring_engine.py    # Weighted composite scoring with FD modifier
  dashboard.py         # Manual and live modes, CLI text output, JSON serialization
  fred_client.py       # FRED API client (stdlib urllib, no external deps)
  historical_scores.py # 46-year monthly data (1980-2026) via keyframe interpolation
  generate_chart.py    # Interactive HTML chart generator (Chart.js)

regime_chart.py        # Static PNG chart generator (matplotlib)
streamlit_app.py       # Streamlit interactive frontend
regime_chart.html      # Generated interactive chart (open in browser)
regime_chart.png       # Generated static chart image
index.html             # GitHub Pages landing page
test_regime_dashboard.py  # 48 unit tests (signals, credit dual-signal, scoring engine, FD flag)
requirements.txt       # Python dependencies
```

### Credit Signal Architecture

Signal 3 uses a **dual-signal credit approach** rather than the composite HY OAS index (BAMLH0A0HYM2), which suffers from composition drift:

1. **CCC-BB spread** (BAMLH0A3HYC minus BAMLH0A1HYBB) — primary risk appetite measure, percentile-ranked on an expanding window
2. **Single-B OAS** (BAMLH0A2HYB) — secondary/confirmation signal retaining absolute stress interpretation
3. **WIDENING_FAST override** — when Single-B 3mo change > +150 bps, credit score floors at 70 (catches fast-moving crises before percentile ranks adjust)
4. **Legacy fallback** — pre-1996 data uses composite HY OAS (sub-indices don't exist)

### Signal Weighting

| Regime | S1 | S2 | S3 | S4 | S5 | S6 | S7 |
|--------|----|----|----|----|----|----|-----|
| **Normal** | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.3 |
| **Fiscal Dominance** | 1.0 | 1.2 | 1.3 | 1.0 | 0.7 | 1.0 | 1.5 |

### Historical Data Methodology

The historical backtest uses **keyframe interpolation** rather than a live API:

- ~80 keyframes are defined at significant economic turning points (Volcker peak, Black Monday, LTCM, dot-com, GFC, COVID, etc.)
- Each keyframe contains 20 indicators per month: CAPE, trailing P/E, HY OAS, VIX, 2s10s spread, Fed Funds Rate, Core PCE, deficit/GDP, ISM PMI, LEI YoY, % above 200d MA, A/D line trend, new highs/lows ratio, AAII bull-bear spread, put/call ratio, margin debt YoY, margin debt/GDP, top-10 concentration, and S&P 500 price
- Between keyframes, numeric indicators are linearly interpolated; categorical fields (A/D line trend) use nearest-neighbor
- Fed cutting detection compares current DFF to 6 months prior (not an absolute threshold)
- Term premium proxy uses `abs(curve_steepness) * 0.5`, allowing inverted curves to contribute positive estimates matching ACM model behavior
- NBER recession dates are hardcoded for the Fiscal Dominance deficit-exclusion logic
- S&P 500 monthly close prices are included for the price overlay chart

This approach allows the dashboard to run without any API keys while still producing historically grounded regime scores.

### Historical Score Validation

Key market tops score appropriately across all eras:

| Date | Score | Context |
|------|-------|---------|
| 1987-08 | 19 | Pre-Black Monday |
| 2000-03 | 46 | Dot-com peak (CAPE 44, extreme concentration, high margin debt) |
| 2007-01 | 36 | Pre-GFC (extremely tight credit, declining LEI, elevated leverage) |
| 2018-01 | 34 | Late cycle (low VIX, high valuations, tight credit) |
| 2021-11 | 47 | Meme bubble (extreme leverage + concentration, FD 2/4) |
| 2026-01 | 62 | Fiscal dominance fully active (4/4 conditions, S7 at 85) |
