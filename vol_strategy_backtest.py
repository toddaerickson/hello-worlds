"""Backtest two vol strategies using VIX/Score discordance signals.

Strategy A  "Buy Tails on Complacent Fragility"
  Signal:  VIX < 15 AND Score >= 25  (structural risk, vol cheap)
  Trade:   Buy 3-month 5% OTM SPX put, sized at 1% of portfolio
  Exit:    Hold to expiry

Strategy B  "Sell Vol on VIX Panic / Score Calm"
  Signal:  VIX >= 25 AND Score < 15  (vol spike on healthy backdrop)
  Trade:   Sell 1-month ATM SPX put, sized at notional = portfolio value
  Exit:    Hold to expiry

Both strategies use weekly-interpolated data derived from monthly keyframes.
Option pricing uses Black-Scholes with VIX as implied volatility.

Usage:
    python vol_strategy_backtest.py
"""

import math
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from regime_dashboard.historical_scores import compute_historical_scores

# =========================================================================
# Constants
# =========================================================================

BG = "#0a0e17"
PANEL_BG = "#111827"
GRID_COLOR = "#1f2937"
TEXT_COLOR = "#9ca3af"
SEP = "=" * 92

RISK_FREE_RATE = 0.03   # approximate average over 1980-2026


# =========================================================================
# Black-Scholes pricing
# =========================================================================

def _norm_cdf(x):
    """Abramowitz & Stegun approximation to the normal CDF."""
    if x >= 0:
        t = 1.0 / (1.0 + 0.2316419 * x)
        d = 0.3989422804 * math.exp(-x * x / 2.0)
        p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478
            + t * (-1.8212560 + t * 1.3302744))))
        return 1.0 - p
    else:
        return 1.0 - _norm_cdf(-x)


def bs_put_price(S, K, T, sigma, r=RISK_FREE_RATE):
    """Black-Scholes European put price.

    Args:
        S: spot price
        K: strike price
        T: time to expiry in years
        sigma: implied volatility (annualized, as decimal e.g. 0.15)
        r: risk-free rate
    Returns:
        put price in same units as S
    """
    if T <= 0 or sigma <= 0:
        return max(K - S, 0.0)
    sqrt_t = math.sqrt(T)
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    put = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
    return max(put, 0.0)


# =========================================================================
# Weekly data interpolation
# =========================================================================

def build_weekly_data(monthly):
    """Interpolate monthly data to ~4 weekly observations per month.

    Each week inherits the month's regime score, VIX, and level.
    SPX is linearly interpolated between month-end values.
    """
    weeks = []
    for i in range(len(monthly)):
        cur = monthly[i]
        prev_spx = monthly[i - 1]["spx"] if i > 0 else cur["spx"]
        cur_spx = cur["spx"]

        for w in range(4):
            t = (w + 1) / 4.0  # 0.25, 0.50, 0.75, 1.00
            spx = prev_spx + (cur_spx - prev_spx) * t
            prev_vix = monthly[i - 1]["vix"] if i > 0 else cur["vix"]
            vix_interp = prev_vix + (cur["vix"] - prev_vix) * t
            weeks.append({
                "week": i * 4 + w,
                "month_idx": i,
                "date": cur["date"],
                "spx": round(spx, 2),
                "vix": round(vix_interp, 1),
                "score": cur["score"],
                "level": cur["level"],
            })
    return weeks


# =========================================================================
# Strategy A: Buy tails on complacent fragility
# =========================================================================

def run_strategy_a(monthly, weeks):
    """Buy 3-month 5% OTM puts when VIX<15 and Score>=25.

    Entry at first week of each signal month.  Hold to expiry (13 weeks).
    No stacking — skip if already in a position.
    Budget: 1% of portfolio per trade (premium is the max loss).
    """
    portfolio = 100.0    # starting value
    trades = []
    position = None      # {"entry_week", "expiry_week", "strike", "premium", "entry_spx", ...}

    n_weeks = len(weeks)

    for i, m in enumerate(monthly):
        if m["vix"] >= 15 or m["score"] < 25:
            continue

        entry_week_idx = i * 4  # first week of this month
        expiry_week_idx = entry_week_idx + 13  # ~3 months

        if expiry_week_idx >= n_weeks:
            continue

        # Skip if already holding
        if position and entry_week_idx < position["expiry_week"]:
            continue

        S = weeks[entry_week_idx]["spx"]
        K = S * 0.95                              # 5% OTM
        T = 13 / 52.0                             # 3 months
        sigma = m["vix"] / 100.0                  # VIX as implied vol
        premium = bs_put_price(S, K, T, sigma)
        premium_pct = premium / S * 100           # as % of spot

        # At expiry
        S_expiry = weeks[expiry_week_idx]["spx"]
        intrinsic = max(K - S_expiry, 0.0)
        pnl_per_unit = intrinsic - premium
        pnl_pct = pnl_per_unit / S * 100          # P&L as % of spot

        # Size: allocate 1% of portfolio to premium
        # Number of "units" (each unit = 1 put on $S of notional)
        budget = portfolio * 0.01
        n_units = budget / premium if premium > 0 else 0
        dollar_pnl = n_units * pnl_per_unit
        portfolio += dollar_pnl

        # Track SPX min during holding period
        spx_min = min(weeks[j]["spx"] for j in range(entry_week_idx, expiry_week_idx + 1))
        max_decline = (spx_min - S) / S * 100

        trades.append({
            "entry_date": m["date"],
            "entry_spx": S,
            "strike": K,
            "vix": m["vix"],
            "score": m["score"],
            "premium_pct": premium_pct,
            "expiry_spx": S_expiry,
            "spx_return": (S_expiry - S) / S * 100,
            "max_decline": max_decline,
            "intrinsic": intrinsic,
            "pnl_pct": pnl_pct,
            "dollar_pnl": dollar_pnl,
            "portfolio": portfolio,
        })

        position = {"expiry_week": expiry_week_idx}

    return trades, portfolio


# =========================================================================
# Strategy B: Sell vol on VIX panic / score calm
# =========================================================================

def run_strategy_b(monthly, weeks):
    """Sell 1-month ATM puts when VIX>=25 and Score<15.

    Entry at first week of each signal month.  Hold to expiry (4 weeks).
    No stacking.  Collect premium; lose if SPX drops below strike.
    Notional = portfolio value (selling 1 put per $SPX of portfolio).
    """
    portfolio = 100.0
    trades = []
    position = None

    n_weeks = len(weeks)

    for i, m in enumerate(monthly):
        if m["vix"] < 25 or m["score"] >= 15:
            continue

        entry_week_idx = i * 4
        expiry_week_idx = entry_week_idx + 4  # 1 month

        if expiry_week_idx >= n_weeks:
            continue

        if position and entry_week_idx < position["expiry_week"]:
            continue

        S = weeks[entry_week_idx]["spx"]
        K = S                                      # ATM
        T = 4 / 52.0                               # 1 month
        sigma = m["vix"] / 100.0
        premium = bs_put_price(S, K, T, sigma)
        premium_pct = premium / S * 100

        S_expiry = weeks[expiry_week_idx]["spx"]
        intrinsic = max(K - S_expiry, 0.0)
        pnl_per_unit = premium - intrinsic          # short put P&L
        pnl_pct = pnl_per_unit / S * 100

        # Size: sell puts on notional = portfolio value
        n_units = portfolio / S
        dollar_pnl = n_units * pnl_per_unit
        portfolio += dollar_pnl

        # SPX min during holding period
        spx_min = min(weeks[j]["spx"] for j in range(entry_week_idx, expiry_week_idx + 1))
        max_decline = (spx_min - S) / S * 100

        trades.append({
            "entry_date": m["date"],
            "entry_spx": S,
            "strike": K,
            "vix": m["vix"],
            "score": m["score"],
            "premium_pct": premium_pct,
            "expiry_spx": S_expiry,
            "spx_return": (S_expiry - S) / S * 100,
            "max_decline": max_decline,
            "pnl_pct": pnl_pct,
            "dollar_pnl": dollar_pnl,
            "portfolio": portfolio,
        })

        position = {"expiry_week": expiry_week_idx}

    return trades, portfolio


# =========================================================================
# Reporting
# =========================================================================

def print_trades(trades, label, strategy_type):
    print(f"\n{SEP}")
    print(f"STRATEGY {label}: Trade-by-Trade Results")
    print(SEP)

    if strategy_type == "A":
        print(f"\n  {'Date':<10} {'VIX':>5} {'Score':>6} {'SPX':>7} {'Strike':>8}"
              f" {'Prem%':>6} {'Exp SPX':>8} {'SPX Ret':>8} {'MaxDrop':>8} {'P&L%':>7} {'Portf':>8}")
    else:
        print(f"\n  {'Date':<10} {'VIX':>5} {'Score':>6} {'SPX':>7}"
              f" {'Prem%':>6} {'Exp SPX':>8} {'SPX Ret':>8} {'MaxDrop':>8} {'P&L%':>7} {'Portf':>8}")
    print(f"  {'-'*90}")

    for t in trades:
        if strategy_type == "A":
            print(f"  {t['entry_date']:<10} {t['vix']:>5.1f} {t['score']:>6.1f}"
                  f" {t['entry_spx']:>7.0f} {t['strike']:>8.0f}"
                  f" {t['premium_pct']:>5.2f}% {t['expiry_spx']:>8.0f}"
                  f" {t['spx_return']:>+7.1f}% {t['max_decline']:>+7.1f}%"
                  f" {t['pnl_pct']:>+6.2f}% {t['portfolio']:>8.2f}")
        else:
            print(f"  {t['entry_date']:<10} {t['vix']:>5.1f} {t['score']:>6.1f}"
                  f" {t['entry_spx']:>7.0f}"
                  f" {t['prem%' if 'prem%' in t else 'premium_pct']:>5.2f}%"
                  f" {t['expiry_spx']:>8.0f}"
                  f" {t['spx_return']:>+7.1f}% {t['max_decline']:>+7.1f}%"
                  f" {t['pnl_pct']:>+6.2f}% {t['portfolio']:>8.2f}")


def print_summary(trades, label, start_val, end_val):
    print(f"\n{SEP}")
    print(f"STRATEGY {label}: Summary Statistics")
    print(SEP)

    n = len(trades)
    if n == 0:
        print("  No trades.")
        return

    pnls = [t["pnl_pct"] for t in trades]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p <= 0]
    portfolios = [start_val] + [t["portfolio"] for t in trades]

    # Drawdown on portfolio equity curve
    peak = portfolios[0]
    max_dd = 0
    for p in portfolios:
        peak = max(peak, p)
        dd = (p - peak) / peak * 100
        max_dd = min(max_dd, dd)

    total_return = (end_val / start_val - 1) * 100
    years = n * (3 / 12) if label == "A" else n * (1 / 12)  # approximate
    ann_return = ((end_val / start_val) ** (1 / years) - 1) * 100 if years > 0 else 0

    print(f"\n  Trades:           {n}")
    print(f"  Win rate:         {len(winners) / n * 100:.1f}%  ({len(winners)}W / {len(losers)}L)")
    print(f"  Avg P&L (per trade, % of spot):  {sum(pnls) / n:+.2f}%")
    print(f"  Best trade:       {max(pnls):+.2f}%")
    print(f"  Worst trade:      {min(pnls):+.2f}%")
    if winners:
        print(f"  Avg winner:       {sum(winners) / len(winners):+.2f}%")
    if losers:
        print(f"  Avg loser:        {sum(losers) / len(losers):+.2f}%")
    print(f"  Total return:     {total_return:+.1f}%  (${start_val:.0f} -> ${end_val:.2f})")
    print(f"  Approx years:     {years:.1f}")
    if years > 0:
        print(f"  Annualized:       {ann_return:+.1f}%")
    print(f"  Max drawdown:     {max_dd:.1f}%")


# =========================================================================
# Chart
# =========================================================================

def generate_chart(monthly, trades_a, trades_b):
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(20, 14), facecolor=BG)
    fig.suptitle("Vol Strategy Backtest — Complacent Fragility vs VIX Panic (1980-2026)",
                 color="white", fontsize=16, fontweight="bold", y=0.97)

    # Build equity curves aligned to monthly timeline
    equity_a = {}
    for t in trades_a:
        equity_a[t["entry_date"]] = t["portfolio"]
    equity_b = {}
    for t in trades_b:
        equity_b[t["entry_date"]] = t["portfolio"]

    dates = [m["date"] for m in monthly]
    x = range(len(dates))

    # Forward-fill equity curves
    eq_a_series = []
    last_a = 100.0
    for d in dates:
        if d in equity_a:
            last_a = equity_a[d]
        eq_a_series.append(last_a)

    eq_b_series = []
    last_b = 100.0
    for d in dates:
        if d in equity_b:
            last_b = equity_b[d]
        eq_b_series.append(last_b)

    # Tick positions
    tick_locs, tick_labels = [], []
    for i, d in enumerate(dates):
        if d.endswith("-01") and int(d[:4]) % 5 == 0:
            tick_locs.append(i)
            tick_labels.append(d[:4])

    # -----------------------------------------------------------------
    # Panel 1 (top): Equity curves
    # -----------------------------------------------------------------
    ax1 = fig.add_axes([0.06, 0.56, 0.88, 0.36])
    ax1.set_facecolor(PANEL_BG)

    ax1.plot(x, eq_a_series, color="#ef4444", linewidth=2, alpha=0.9,
             label="A: Buy Tails (VIX<15, Score>=25)")
    ax1.plot(x, eq_b_series, color="#10b981", linewidth=2, alpha=0.9,
             label="B: Sell Vol (VIX>=25, Score<15)")
    ax1.axhline(100, color=GRID_COLOR, linewidth=1, linestyle="--")

    # Mark trade entries
    for t in trades_a:
        idx = dates.index(t["entry_date"]) if t["entry_date"] in dates else None
        if idx is not None:
            ax1.axvline(idx, color="#ef4444", alpha=0.15, linewidth=1)

    for t in trades_b:
        idx = dates.index(t["entry_date"]) if t["entry_date"] in dates else None
        if idx is not None:
            ax1.axvline(idx, color="#10b981", alpha=0.15, linewidth=1)

    ax1.set_xticks(tick_locs)
    ax1.set_xticklabels(tick_labels, color=TEXT_COLOR, fontsize=9)
    ax1.set_ylabel("Portfolio Value ($)", color=TEXT_COLOR, fontsize=11)
    ax1.set_title("Cumulative Equity Curves — $100 Starting Capital", color="white", fontsize=12)
    ax1.legend(fontsize=10, loc="upper left",
               facecolor=PANEL_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    ax1.tick_params(colors=TEXT_COLOR)
    ax1.grid(color=GRID_COLOR, alpha=0.3)

    # -----------------------------------------------------------------
    # Panel 2 (bottom-left): Strategy A trade P&L distribution
    # -----------------------------------------------------------------
    ax2 = fig.add_axes([0.06, 0.07, 0.42, 0.38])
    ax2.set_facecolor(PANEL_BG)

    if trades_a:
        pnls_a = [t["pnl_pct"] for t in trades_a]
        colors_a = ["#10b981" if p > 0 else "#ef4444" for p in pnls_a]
        ax2.bar(range(len(pnls_a)), pnls_a, color=colors_a, alpha=0.8)
        ax2.axhline(0, color=GRID_COLOR, linewidth=1)

        # Label notable trades
        for i, t in enumerate(trades_a):
            if abs(t["pnl_pct"]) > 1.0:
                ax2.text(i, t["pnl_pct"] + (0.2 if t["pnl_pct"] > 0 else -0.3),
                         t["entry_date"][:7], fontsize=6, color=TEXT_COLOR,
                         ha="center", rotation=45)

    ax2.set_xlabel("Trade #", color=TEXT_COLOR, fontsize=10)
    ax2.set_ylabel("P&L (% of spot)", color=TEXT_COLOR, fontsize=10)
    ax2.set_title("Strategy A: Buy Tails — Per-Trade P&L", color="white", fontsize=11)
    ax2.tick_params(colors=TEXT_COLOR)
    ax2.grid(axis="y", color=GRID_COLOR, alpha=0.3)

    # -----------------------------------------------------------------
    # Panel 3 (bottom-right): Strategy B trade P&L distribution
    # -----------------------------------------------------------------
    ax3 = fig.add_axes([0.56, 0.07, 0.42, 0.38])
    ax3.set_facecolor(PANEL_BG)

    if trades_b:
        pnls_b = [t["pnl_pct"] for t in trades_b]
        colors_b = ["#10b981" if p > 0 else "#ef4444" for p in pnls_b]
        ax3.bar(range(len(pnls_b)), pnls_b, color=colors_b, alpha=0.8)
        ax3.axhline(0, color=GRID_COLOR, linewidth=1)

        for i, t in enumerate(trades_b):
            if abs(t["pnl_pct"]) > 2.0:
                ax3.text(i, t["pnl_pct"] + (0.3 if t["pnl_pct"] > 0 else -0.5),
                         t["entry_date"][:7], fontsize=6, color=TEXT_COLOR,
                         ha="center", rotation=45)

    ax3.set_xlabel("Trade #", color=TEXT_COLOR, fontsize=10)
    ax3.set_ylabel("P&L (% of spot)", color=TEXT_COLOR, fontsize=10)
    ax3.set_title("Strategy B: Sell Vol — Per-Trade P&L", color="white", fontsize=11)
    ax3.tick_params(colors=TEXT_COLOR)
    ax3.grid(axis="y", color=GRID_COLOR, alpha=0.3)

    fig.savefig("vol_strategy_backtest.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


# =========================================================================
# Main
# =========================================================================

def main():
    monthly = compute_historical_scores()
    weeks = build_weekly_data(monthly)

    print(f"{SEP}")
    print("VOL STRATEGY BACKTEST")
    print(f"Weekly-interpolated data, {len(monthly)} months -> {len(weeks)} weeks")
    print(f"Period: {monthly[0]['date']} to {monthly[-1]['date']}")
    print(SEP)

    print("""
  Strategy A: "Buy Tails on Complacent Fragility"
    Signal:   VIX < 15 AND Score >= 25
    Trade:    Buy 3-month 5% OTM SPX put
    Sizing:   1% of portfolio allocated to premium per trade
    Holding:  13 weeks (to expiry), no stacking

  Strategy B: "Sell Vol on VIX Panic / Score Calm"
    Signal:   VIX >= 25 AND Score < 15
    Trade:    Sell 1-month ATM SPX put
    Sizing:   Notional = portfolio value
    Holding:  4 weeks (to expiry), no stacking
""")

    trades_a, final_a = run_strategy_a(monthly, weeks)
    trades_b, final_b = run_strategy_b(monthly, weeks)

    print_trades(trades_a, "A: Buy Tails (VIX<15, Score>=25)", "A")
    print_summary(trades_a, "A", 100.0, final_a)

    print_trades(trades_b, "B: Sell Vol (VIX>=25, Score<15)", "B")
    print_summary(trades_b, "B", 100.0, final_b)

    generate_chart(monthly, trades_a, trades_b)
    print(f"\nChart saved: vol_strategy_backtest.png")


if __name__ == "__main__":
    main()
