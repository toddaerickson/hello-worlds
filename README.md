# Market Topping Regime Dashboard

Topping Conditions Monitor for gradual risk reduction. Companion to the Market Bottom Conviction Screener.

## Overview

Accumulating caution-level indicator (0-100%) that monitors six market signals for topping conditions. Outputs a graduated regime (GREEN / YELLOW / ORANGE / RED / EXTREME) with suggested portfolio actions. Not binary exit signals.

## Signals

| # | Signal | Weight | Update Freq |
|---|--------|--------|-------------|
| 1 | Breadth Divergence | 25% | Daily |
| 2 | Valuation Percentile | 15% | Monthly |
| 3 | Credit Complacency | 20% | Daily |
| 4 | Sentiment Extreme | 15% | Weekly/Daily |
| 5 | Macro Deterioration | 15% | Monthly |
| 6 | Margin Debt/Leverage | 10% | Monthly |

## Regime Bands

| Caution Level | Regime | Action |
|---------------|--------|--------|
| 0-20% | GREEN | Normal risk posture |
| 21-40% | YELLOW | Tighten trailing stops |
| 41-60% | ORANGE | Trim high-beta 15-25%, raise cash 10-15% |
| 61-80% | RED | Reduce equity to 60-70%, shift to quality |
| 81-100% | EXTREME | Reduce equity to 40-50%, hedge exposure |

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Set FRED API key (optional, enables full data access)
export FRED_API_KEY=your_key_here

# Run the data pipeline
python -m market_topping_regime.main --regime

# Launch Streamlit dashboard
python -m market_topping_regime.main --dashboard
```

## Data Sources

- **yfinance**: S&P 500, NYSE breadth proxies
- **FRED**: HY OAS, CCC OAS, LEI, ISM, Initial Claims, Wilshire 5000, GDP
- **multpl.com**: Shiller CAPE ratio
- **CNN**: Fear & Greed Index
- **AAII**: Sentiment Survey
- **FINRA**: Margin debt statistics

## Project Structure

```
market_topping_regime/
  data/
    fetchers.py          # Shared data fetchers (yfinance, FRED, web)
    store.py             # SQLite database helpers
  regime/
    signals/
      breadth.py         # Signal 1: Breadth divergence
      valuation.py       # Signal 2: CAPE, Buffett, forward P/E
      credit.py          # Signal 3: HY OAS, CCC-BB compression
      sentiment.py       # Signal 4: AAII, Fear & Greed
      macro.py           # Signal 5: LEI, ISM, claims
      leverage.py        # Signal 6: Margin debt, free credit
    scoring.py           # Weighted caution level computation
    dashboard.py         # Streamlit dashboard
    fetchers.py          # Regime-specific data aggregation
  main.py                # Entry point
```
