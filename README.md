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
| 3 | **Credit Complacency** | HY OAS spread, IG spread, spread percentile vs. history |
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

When active: **+10 caution modifier**, Signal 5 rescored using private-sector LEI (strips government spending distortion), Signal 7 weighted at **1.5x**, all signal interpretations adjusted.

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

# Run tests (42 tests)
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
test_regime_dashboard.py  # 42 unit tests
requirements.txt       # Python dependencies
```

### Historical Data Methodology

The historical backtest uses **keyframe interpolation** rather than a live API:

- ~80 keyframes are defined at significant economic turning points (Volcker peak, Black Monday, LTCM, dot-com, GFC, COVID, etc.)
- Each keyframe contains documented indicator values sourced from FRED, Shiller, CBO, CBOE, ISM, and Leuthold/NDR/BofA research
- Between keyframes, all indicators are linearly interpolated to produce smooth monthly estimates
- NBER recession dates are hardcoded for the Fiscal Dominance deficit-exclusion logic
- S&P 500 monthly close prices are included for the price overlay chart

This approach allows the dashboard to run without any API keys while still producing historically grounded regime scores.
