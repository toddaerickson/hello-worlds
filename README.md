# hello-worlds

Prep for classes. A collection of projects.

## Grateful Dead Hangman

A single-player hangman game featuring Grateful Dead song titles and multiple other categories. Available as both a Python console game and a mobile-friendly HTML/JS version.

- **Play online**: [https://toddaerickson.github.io/hello-worlds/](https://toddaerickson.github.io/hello-worlds/)
- **Console version**: `python hangman.py`
- **Tests**: `python -m pytest test_hangman.py`

Categories: Grateful Dead, College Music, Fashion, Knitting, Bio, Colors.

## Market Topping Regime Dashboard

7-signal caution-level indicator (0-100) that monitors market conditions for topping risk, with a Fiscal Dominance structural modifier. Companion to the Market Bottom Conviction Screener.

### Signals

| # | Signal | Description |
|---|--------|-------------|
| 1 | Breadth Divergence & Concentration | % above 200d MA, A/D line, new highs/lows, top-10 stock concentration |
| 2 | Valuation | P/E, CAPE, EV/EBITDA |
| 3 | Credit Complacency | HY OAS spread, IG spread, spread percentile |
| 4 | Sentiment Extremes | AAII bull/bear, VIX, put/call ratio, Fear & Greed |
| 5 | Macro Deterioration | LEI, private-sector LEI (ex-government), ISM Manufacturing |
| 6 | Margin Debt / Leverage | Margin debt YoY, debt/GDP, percentile |
| 7 | Term Premium / Fiscal Stress | 2s10s spread, 10y term premium, deficit/GDP, debt service ratio |

### Fiscal Dominance Flag

Structural modifier that activates when 3 of 4 conditions are met:

1. Federal deficit > 5% GDP (non-recession year)
2. Interest expense > 15% of tax revenue
3. Fed easing while core PCE > 2.5%
4. 2s10s > 75 bps with rising term premium

When active: +10 caution modifier, Signal 5 rescored using private-sector LEI, Signal 7 weighted at 1.5x, all signal interpretations adjusted for fiscal distortion.

### Usage

```bash
# Run with example April 2026 data
python -m regime_dashboard --example

# Output as JSON
python -m regime_dashboard --example --json

# Live mode (requires FRED_API_KEY)
export FRED_API_KEY=your_key_here
python -m regime_dashboard --live

# Generate 20-year historical chart (requires matplotlib)
pip install matplotlib
python regime_chart.py

# Run tests (42 tests)
python -m pytest test_regime_dashboard.py -v
```

### Project Structure

```
regime_dashboard/
  signals.py           # All 7 signals + Fiscal Dominance Flag
  scoring_engine.py    # Weighted composite with FD modifier
  dashboard.py         # Manual and live modes, CLI output
  fred_client.py       # FRED API client (stdlib only)
  historical_scores.py # 20-year monthly data (2006-2026)
  generate_chart.py    # Interactive HTML chart (Chart.js)
regime_chart.py        # Static PNG chart (matplotlib)
regime_chart.html      # Interactive chart (open in browser)
regime_chart.png       # Static chart image
test_regime_dashboard.py # 42 tests
```
