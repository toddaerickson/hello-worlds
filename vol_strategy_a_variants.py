"""Backtest three Strategy A variants to find a profitable tail-buying approach.

The original Strategy A (3-month 5% OTM puts on complacent fragility) went 0/12.
The regime score identifies slow-building fragility — options expire before crashes arrive.

Three variants tested:

  A1: LEAPS — 12-month 10% OTM puts
      Gives fragility 4x longer to materialize.

  A2: Rolling Tail Hedge — continuous 1-month 10% OTM puts
      Monthly refresh while signal active.  0.25% portfolio/month bleed.
      Pure insurance model: does crash payout cover the bleed?

  A3: Catalyst-Confirmed — 6-month 5% OTM puts, but only when score is RISING
      Score > score 3 months ago narrows to periods of actively building fragility.
      Filters out stale elevated scores from recovery periods.

Usage:
    python vol_strategy_a_variants.py
"""

import math
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from regime_dashboard.historical_scores import compute_historical_scores
from vol_strategy_backtest import (
    bs_put_price, build_weekly_data,
    BG, PANEL_BG, GRID_COLOR, TEXT_COLOR, RISK_FREE_RATE,
)

SEP = "=" * 92
DASH = "-" * 92


# =========================================================================
# Variant A1: LEAPS — 12-month 10% OTM puts
# =========================================================================

def run_a1_leaps(monthly, weeks):
    """Buy 12-month 10% OTM puts when VIX<15 and Score>=25.

    Hold to expiry (52 weeks).  1% of portfolio per trade.
    No stacking.
    """
    portfolio = 100.0
    trades = []
    position = None
    n_weeks = len(weeks)

    for i, m in enumerate(monthly):
        if m["vix"] >= 15 or m["score"] < 25:
            continue

        entry_week = i * 4
        expiry_week = entry_week + 52  # 12 months

        if expiry_week >= n_weeks:
            continue
        if position and entry_week < position["expiry_week"]:
            continue

        S = weeks[entry_week]["spx"]
        K = S * 0.90  # 10% OTM
        T = 52 / 52.0  # 1 year
        sigma = m["vix"] / 100.0
        premium = bs_put_price(S, K, T, sigma)
        premium_pct = premium / S * 100

        S_expiry = weeks[expiry_week]["spx"]
        intrinsic = max(K - S_expiry, 0.0)
        pnl_per_unit = intrinsic - premium
        pnl_pct = pnl_per_unit / S * 100

        budget = portfolio * 0.01
        n_units = budget / premium if premium > 0 else 0
        dollar_pnl = n_units * pnl_per_unit
        portfolio += dollar_pnl

        # Track worst SPX during holding
        spx_min = min(weeks[j]["spx"] for j in range(entry_week, expiry_week + 1))
        max_decline = (spx_min - S) / S * 100

        # Also track the max intrinsic value during holding (could we have exited early?)
        max_intrinsic = max(max(K - weeks[j]["spx"], 0.0) for j in range(entry_week, expiry_week + 1))
        peak_value_pct = max_intrinsic / S * 100

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
            "peak_value_pct": peak_value_pct,
            "pnl_pct": pnl_pct,
            "portfolio": portfolio,
        })

        position = {"expiry_week": expiry_week}

    return trades, portfolio


# =========================================================================
# Variant A2: Rolling Tail Hedge
# =========================================================================

def run_a2_rolling(monthly, weeks):
    """Buy 1-month 10% OTM puts every month while VIX<15 and Score>=25.

    0.25% of portfolio per month.  4-week expiry.
    Refreshed each month the signal stays active — this is a continuous hedge.
    """
    portfolio = 100.0
    trades = []
    n_weeks = len(weeks)

    for i, m in enumerate(monthly):
        if m["vix"] >= 15 or m["score"] < 25:
            continue

        entry_week = i * 4
        expiry_week = entry_week + 4  # 1 month

        if expiry_week >= n_weeks:
            continue

        S = weeks[entry_week]["spx"]
        K = S * 0.90  # 10% OTM
        T = 4 / 52.0  # 1 month
        sigma = m["vix"] / 100.0
        premium = bs_put_price(S, K, T, sigma)
        premium_pct = premium / S * 100

        if premium <= 0:
            continue

        S_expiry = weeks[expiry_week]["spx"]
        intrinsic = max(K - S_expiry, 0.0)
        pnl_per_unit = intrinsic - premium
        pnl_pct = pnl_per_unit / S * 100

        budget = portfolio * 0.0025  # 0.25% per month
        n_units = budget / premium
        dollar_pnl = n_units * pnl_per_unit
        portfolio += dollar_pnl

        spx_min = min(weeks[j]["spx"] for j in range(entry_week, expiry_week + 1))
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
            "portfolio": portfolio,
        })

    return trades, portfolio


# =========================================================================
# Variant A3: Catalyst-Confirmed (rising score + 6-month puts)
# =========================================================================

def run_a3_catalyst(monthly, weeks):
    """Buy 6-month 5% OTM puts when VIX<15, Score>=25, AND score is rising.

    Rising = current score > score 3 months ago.
    This filters out stale elevated scores during recoveries.
    Hold to expiry (26 weeks).  1% of portfolio per trade.  No stacking.
    """
    portfolio = 100.0
    trades = []
    position = None
    n_weeks = len(weeks)

    for i, m in enumerate(monthly):
        if m["vix"] >= 15 or m["score"] < 25:
            continue
        if i < 3:
            continue

        # Catalyst: score rising over past 3 months
        score_3m_ago = monthly[i - 3]["score"]
        if m["score"] <= score_3m_ago:
            continue

        entry_week = i * 4
        expiry_week = entry_week + 26  # 6 months

        if expiry_week >= n_weeks:
            continue
        if position and entry_week < position["expiry_week"]:
            continue

        S = weeks[entry_week]["spx"]
        K = S * 0.95  # 5% OTM
        T = 26 / 52.0  # 6 months
        sigma = m["vix"] / 100.0
        premium = bs_put_price(S, K, T, sigma)
        premium_pct = premium / S * 100

        S_expiry = weeks[expiry_week]["spx"]
        intrinsic = max(K - S_expiry, 0.0)
        pnl_per_unit = intrinsic - premium
        pnl_pct = pnl_per_unit / S * 100

        budget = portfolio * 0.01
        n_units = budget / premium if premium > 0 else 0
        dollar_pnl = n_units * pnl_per_unit
        portfolio += dollar_pnl

        spx_min = min(weeks[j]["spx"] for j in range(entry_week, expiry_week + 1))
        max_decline = (spx_min - S) / S * 100
        max_intrinsic = max(max(K - weeks[j]["spx"], 0.0) for j in range(entry_week, expiry_week + 1))
        peak_value_pct = max_intrinsic / S * 100

        trades.append({
            "entry_date": m["date"],
            "entry_spx": S,
            "strike": K,
            "vix": m["vix"],
            "score": m["score"],
            "score_3m_ago": score_3m_ago,
            "premium_pct": premium_pct,
            "expiry_spx": S_expiry,
            "spx_return": (S_expiry - S) / S * 100,
            "max_decline": max_decline,
            "peak_value_pct": peak_value_pct,
            "pnl_pct": pnl_pct,
            "portfolio": portfolio,
        })

        position = {"expiry_week": expiry_week}

    return trades, portfolio


# =========================================================================
# Bonus: Combined A3 + B  (best tail buy paired with vol selling)
# =========================================================================

def run_combined(monthly, weeks, trades_a3, trades_b_ref):
    """Run A3 and B simultaneously on one portfolio to see if B funds A3.

    Re-run both strategies sharing the same portfolio balance.
    """
    from vol_strategy_backtest import run_strategy_b

    # Build a merged timeline of all trade events
    events = []
    # Replay A3 signals
    for i, m in enumerate(monthly):
        if m["vix"] >= 15 or m["score"] < 25:
            continue
        if i < 3:
            continue
        score_3m_ago = monthly[i - 3]["score"]
        if m["score"] <= score_3m_ago:
            continue
        events.append(("A3", i, m))

    # Replay B signals
    for i, m in enumerate(monthly):
        if m["vix"] < 25 or m["score"] >= 15:
            continue
        events.append(("B", i, m))

    events.sort(key=lambda e: e[1])

    portfolio = 100.0
    pos_a3 = None
    pos_b = None
    combined_trades = []
    n_weeks = len(weeks)

    for strat, i, m in events:
        if strat == "A3":
            entry_week = i * 4
            expiry_week = entry_week + 26
            if expiry_week >= n_weeks:
                continue
            if pos_a3 and entry_week < pos_a3:
                continue

            S = weeks[entry_week]["spx"]
            K = S * 0.95
            T = 26 / 52.0
            sigma = m["vix"] / 100.0
            premium = bs_put_price(S, K, T, sigma)
            if premium <= 0:
                continue

            S_expiry = weeks[expiry_week]["spx"]
            intrinsic = max(K - S_expiry, 0.0)
            pnl_per_unit = intrinsic - premium
            budget = portfolio * 0.01
            n_units = budget / premium
            dollar_pnl = n_units * pnl_per_unit
            portfolio += dollar_pnl
            pnl_pct = pnl_per_unit / S * 100

            combined_trades.append({
                "type": "A3",
                "entry_date": m["date"],
                "pnl_pct": pnl_pct,
                "portfolio": portfolio,
            })
            pos_a3 = expiry_week

        elif strat == "B":
            entry_week = i * 4
            expiry_week = entry_week + 4
            if expiry_week >= n_weeks:
                continue
            if pos_b and entry_week < pos_b:
                continue

            S = weeks[entry_week]["spx"]
            K = S
            T = 4 / 52.0
            sigma = m["vix"] / 100.0
            premium = bs_put_price(S, K, T, sigma)

            S_expiry = weeks[expiry_week]["spx"]
            intrinsic = max(K - S_expiry, 0.0)
            pnl_per_unit = premium - intrinsic
            n_units = portfolio / S
            dollar_pnl = n_units * pnl_per_unit
            portfolio += dollar_pnl
            pnl_pct = pnl_per_unit / S * 100

            combined_trades.append({
                "type": "B",
                "entry_date": m["date"],
                "pnl_pct": pnl_pct,
                "portfolio": portfolio,
            })
            pos_b = expiry_week

    return combined_trades, portfolio


# =========================================================================
# Reporting
# =========================================================================

def print_variant_trades(trades, label, show_catalyst=False, show_peak=False):
    print(f"\n{SEP}")
    print(f"{label}: Trade-by-Trade Results")
    print(SEP)

    if show_catalyst:
        hdr = (f"  {'Date':<10} {'VIX':>5} {'Score':>6} {'Sc3m':>5} {'SPX':>7} {'Strike':>8}"
               f" {'Prem%':>6} {'ExpSPX':>7} {'SPXRet':>7} {'MaxDrp':>7} {'PkVal%':>7} {'P&L%':>7} {'Portf':>8}")
    elif show_peak:
        hdr = (f"  {'Date':<10} {'VIX':>5} {'Score':>6} {'SPX':>7} {'Strike':>8}"
               f" {'Prem%':>6} {'ExpSPX':>7} {'SPXRet':>7} {'MaxDrp':>7} {'PkVal%':>7} {'P&L%':>7} {'Portf':>8}")
    else:
        hdr = (f"  {'Date':<10} {'VIX':>5} {'Score':>6} {'SPX':>7} {'Strike':>8}"
               f" {'Prem%':>6} {'ExpSPX':>7} {'SPXRet':>7} {'MaxDrp':>7} {'P&L%':>7} {'Portf':>8}")
    print(f"\n{hdr}")
    print(f"  {DASH}")

    for t in trades:
        if show_catalyst:
            print(f"  {t['entry_date']:<10} {t['vix']:>5.1f} {t['score']:>6.1f}"
                  f" {t['score_3m_ago']:>5.1f} {t['entry_spx']:>7.0f} {t['strike']:>8.0f}"
                  f" {t['premium_pct']:>5.2f}% {t['expiry_spx']:>7.0f}"
                  f" {t['spx_return']:>+6.1f}% {t['max_decline']:>+6.1f}%"
                  f" {t['peak_value_pct']:>6.2f}% {t['pnl_pct']:>+6.2f}% {t['portfolio']:>8.2f}")
        elif show_peak:
            print(f"  {t['entry_date']:<10} {t['vix']:>5.1f} {t['score']:>6.1f}"
                  f" {t['entry_spx']:>7.0f} {t['strike']:>8.0f}"
                  f" {t['premium_pct']:>5.2f}% {t['expiry_spx']:>7.0f}"
                  f" {t['spx_return']:>+6.1f}% {t['max_decline']:>+6.1f}%"
                  f" {t['peak_value_pct']:>6.2f}% {t['pnl_pct']:>+6.2f}% {t['portfolio']:>8.2f}")
        else:
            print(f"  {t['entry_date']:<10} {t['vix']:>5.1f} {t['score']:>6.1f}"
                  f" {t['entry_spx']:>7.0f} {t['strike']:>8.0f}"
                  f" {t['premium_pct']:>5.2f}% {t['expiry_spx']:>7.0f}"
                  f" {t['spx_return']:>+6.1f}% {t['max_decline']:>+6.1f}%"
                  f" {t['pnl_pct']:>+6.2f}% {t['portfolio']:>8.2f}")


def print_summary(trades, label, start_val, end_val, months_per_trade):
    print(f"\n  --- {label} Summary ---")
    n = len(trades)
    if n == 0:
        print("  No trades.")
        return

    pnls = [t["pnl_pct"] for t in trades]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p <= 0]

    portfolios = [start_val] + [t["portfolio"] for t in trades]
    peak = portfolios[0]
    max_dd = 0
    for p in portfolios:
        peak = max(peak, p)
        dd = (p - peak) / peak * 100
        max_dd = min(max_dd, dd)

    total_return = (end_val / start_val - 1) * 100
    years = n * (months_per_trade / 12)
    ann_return = ((end_val / start_val) ** (1 / years) - 1) * 100 if years > 0 else 0

    print(f"  Trades:       {n}")
    print(f"  Win rate:     {len(winners) / n * 100:.1f}%  ({len(winners)}W / {len(losers)}L)")
    print(f"  Avg P&L:      {sum(pnls) / n:+.2f}% per trade")
    if winners:
        print(f"  Best trade:   {max(pnls):+.2f}%")
        print(f"  Avg winner:   {sum(winners) / len(winners):+.2f}%")
    if losers:
        print(f"  Worst trade:  {min(pnls):+.2f}%")
        print(f"  Avg loser:    {sum(losers) / len(losers):+.2f}%")
    print(f"  Total return: {total_return:+.1f}%  (${start_val:.0f} -> ${end_val:.2f})")
    print(f"  Approx years: {years:.1f}")
    if years > 0:
        print(f"  Annualized:   {ann_return:+.1f}%")
    print(f"  Max drawdown: {max_dd:.1f}%")


# =========================================================================
# Chart
# =========================================================================

def generate_chart(monthly, trades_a1, trades_a2, trades_a3, combined_trades):
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(20, 14), facecolor=BG)
    fig.suptitle("Strategy A Variants — Finding a Profitable Tail Hedge (1980-2026)",
                 color="white", fontsize=16, fontweight="bold", y=0.97)

    dates = [m["date"] for m in monthly]
    x = range(len(dates))

    # Build equity curves
    def equity_series(trades):
        eq = {}
        for t in trades:
            eq[t["entry_date"]] = t["portfolio"]
        series = []
        last = 100.0
        for d in dates:
            if d in eq:
                last = eq[d]
            series.append(last)
        return series

    eq_a1 = equity_series(trades_a1)
    eq_a2 = equity_series(trades_a2)
    eq_a3 = equity_series(trades_a3)
    eq_comb = equity_series(combined_trades)

    tick_locs, tick_labels = [], []
    for i, d in enumerate(dates):
        if d.endswith("-01") and int(d[:4]) % 5 == 0:
            tick_locs.append(i)
            tick_labels.append(d[:4])

    # ----- Panel 1: Equity curves -----
    ax1 = fig.add_axes([0.06, 0.56, 0.88, 0.36])
    ax1.set_facecolor(PANEL_BG)

    ax1.plot(x, eq_a1, color="#60a5fa", linewidth=2, alpha=0.9,
             label="A1: LEAPS (12m, 10% OTM)")
    ax1.plot(x, eq_a2, color="#f97316", linewidth=2, alpha=0.9,
             label="A2: Rolling Tail Hedge (1m, 10% OTM, 0.25%/mo)")
    ax1.plot(x, eq_a3, color="#a78bfa", linewidth=2, alpha=0.9,
             label="A3: Catalyst-Confirmed (6m, rising score)")
    ax1.plot(x, eq_comb, color="#10b981", linewidth=2.5, alpha=0.9,
             label="A3 + B Combined Portfolio", linestyle="--")
    ax1.axhline(100, color=GRID_COLOR, linewidth=1, linestyle="--")

    ax1.set_xticks(tick_locs)
    ax1.set_xticklabels(tick_labels, color=TEXT_COLOR, fontsize=9)
    ax1.set_ylabel("Portfolio Value ($)", color=TEXT_COLOR, fontsize=11)
    ax1.set_title("Cumulative Equity Curves — $100 Starting Capital", color="white", fontsize=12)
    ax1.legend(fontsize=9, loc="upper left",
               facecolor=PANEL_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    ax1.tick_params(colors=TEXT_COLOR)
    ax1.grid(color=GRID_COLOR, alpha=0.3)

    # ----- Panel 2: Per-trade P&L for A1 -----
    ax2 = fig.add_axes([0.06, 0.07, 0.27, 0.38])
    ax2.set_facecolor(PANEL_BG)
    if trades_a1:
        pnls = [t["pnl_pct"] for t in trades_a1]
        colors = ["#10b981" if p > 0 else "#ef4444" for p in pnls]
        ax2.bar(range(len(pnls)), pnls, color=colors, alpha=0.8)
        ax2.axhline(0, color=GRID_COLOR, linewidth=1)
        for i, t in enumerate(trades_a1):
            ax2.text(i, pnls[i] + (0.3 if pnls[i] > 0 else -0.5),
                     t["entry_date"][:7], fontsize=5, color=TEXT_COLOR,
                     ha="center", rotation=60)
    ax2.set_title("A1: LEAPS", color="white", fontsize=10)
    ax2.set_ylabel("P&L (% of spot)", color=TEXT_COLOR, fontsize=9)
    ax2.tick_params(colors=TEXT_COLOR, labelsize=8)
    ax2.grid(axis="y", color=GRID_COLOR, alpha=0.3)

    # ----- Panel 3: Per-trade P&L for A2 (rolling) -----
    ax3 = fig.add_axes([0.39, 0.07, 0.27, 0.38])
    ax3.set_facecolor(PANEL_BG)
    if trades_a2:
        pnls = [t["pnl_pct"] for t in trades_a2]
        colors = ["#10b981" if p > 0 else "#ef4444" for p in pnls]
        ax3.bar(range(len(pnls)), pnls, color=colors, alpha=0.8)
        ax3.axhline(0, color=GRID_COLOR, linewidth=1)
    ax3.set_title("A2: Rolling Hedge", color="white", fontsize=10)
    ax3.set_xlabel("Trade #", color=TEXT_COLOR, fontsize=9)
    ax3.tick_params(colors=TEXT_COLOR, labelsize=8)
    ax3.grid(axis="y", color=GRID_COLOR, alpha=0.3)

    # ----- Panel 4: Per-trade P&L for A3 (catalyst) -----
    ax4 = fig.add_axes([0.72, 0.07, 0.27, 0.38])
    ax4.set_facecolor(PANEL_BG)
    if trades_a3:
        pnls = [t["pnl_pct"] for t in trades_a3]
        colors = ["#10b981" if p > 0 else "#ef4444" for p in pnls]
        ax4.bar(range(len(pnls)), pnls, color=colors, alpha=0.8)
        ax4.axhline(0, color=GRID_COLOR, linewidth=1)
        for i, t in enumerate(trades_a3):
            ax4.text(i, pnls[i] + (0.3 if pnls[i] > 0 else -0.5),
                     t["entry_date"][:7], fontsize=5, color=TEXT_COLOR,
                     ha="center", rotation=60)
    ax4.set_title("A3: Catalyst-Confirmed", color="white", fontsize=10)
    ax4.tick_params(colors=TEXT_COLOR, labelsize=8)
    ax4.grid(axis="y", color=GRID_COLOR, alpha=0.3)

    fig.savefig("vol_strategy_a_variants.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


# =========================================================================
# Main
# =========================================================================

def main():
    monthly = compute_historical_scores()
    weeks = build_weekly_data(monthly)

    print(f"{SEP}")
    print("STRATEGY A VARIANTS — FINDING A PROFITABLE TAIL HEDGE")
    print(f"Weekly data: {len(monthly)} months -> {len(weeks)} weeks")
    print(f"Period: {monthly[0]['date']} to {monthly[-1]['date']}")
    print(SEP)

    print("""
  Original A failed: 0% win rate over 12 trades (3-month 5% OTM puts).
  The regime score spots slow-building fragility that materializes over quarters.
  Testing three variants to match the hedge to the signal's timeline:

  A1: LEAPS              12-month, 10% OTM, 1% budget, no stacking
  A2: Rolling Tail Hedge  1-month, 10% OTM, 0.25%/mo continuous while signal active
  A3: Catalyst-Confirmed  6-month, 5% OTM, 1% budget, requires score rising vs 3m ago
""")

    # --- A1: LEAPS ---
    trades_a1, final_a1 = run_a1_leaps(monthly, weeks)
    print_variant_trades(trades_a1, "A1: LEAPS (12-month, 10% OTM)", show_peak=True)
    print_summary(trades_a1, "A1: LEAPS", 100.0, final_a1, 12)

    # --- A2: Rolling ---
    trades_a2, final_a2 = run_a2_rolling(monthly, weeks)
    print_variant_trades(trades_a2, "A2: Rolling Tail Hedge (1-month, 10% OTM, 0.25%/mo)")
    print_summary(trades_a2, "A2: Rolling Hedge", 100.0, final_a2, 1)

    # --- A3: Catalyst ---
    trades_a3, final_a3 = run_a3_catalyst(monthly, weeks)
    print_variant_trades(trades_a3, "A3: Catalyst-Confirmed (6-month, rising score)", show_catalyst=True, show_peak=True)
    print_summary(trades_a3, "A3: Catalyst", 100.0, final_a3, 6)

    # --- Combined A3 + B ---
    print(f"\n{SEP}")
    print("BONUS: Combined A3 + Strategy B on One Portfolio")
    print(SEP)
    print("  Can Strategy B's vol-selling profits fund A3's tail hedges?")

    from vol_strategy_backtest import run_strategy_b
    trades_b_standalone, _ = run_strategy_b(monthly, weeks)
    combined_trades, final_combined = run_combined(monthly, weeks, trades_a3, trades_b_standalone)

    a3_in_comb = [t for t in combined_trades if t["type"] == "A3"]
    b_in_comb = [t for t in combined_trades if t["type"] == "B"]

    print(f"\n  Combined portfolio: $100 -> ${final_combined:.2f}")
    total_ret = (final_combined / 100 - 1) * 100
    print(f"  Total return: {total_ret:+.1f}%")
    print(f"  Trades: {len(a3_in_comb)} A3 + {len(b_in_comb)} B = {len(combined_trades)} total")

    # Equity curve walk
    portfolios = [100.0] + [t["portfolio"] for t in combined_trades]
    peak = portfolios[0]
    max_dd = 0
    for p in portfolios:
        peak = max(peak, p)
        dd = (p - peak) / peak * 100
        max_dd = min(max_dd, dd)
    print(f"  Max drawdown: {max_dd:.1f}%")

    n_years = len(combined_trades) * 0.25  # rough: mixed trade lengths
    if n_years > 0:
        ann = ((final_combined / 100) ** (1 / n_years) - 1) * 100
        print(f"  Approx annualized: {ann:+.1f}%")

    print(f"\n  Trade log:")
    for t in combined_trades:
        print(f"    [{t['type']:>2}] {t['entry_date']:<10}  P&L: {t['pnl_pct']:>+6.2f}%  Portfolio: ${t['portfolio']:.2f}")

    # --- Verdict ---
    print(f"\n{SEP}")
    print("VERDICT")
    print(SEP)

    results = [
        ("Original A (3m, 5% OTM)", 100.0, 88.64, 12, 0),
        ("A1: LEAPS (12m, 10% OTM)", 100.0, final_a1, len(trades_a1),
         len([t for t in trades_a1 if t["pnl_pct"] > 0])),
        ("A2: Rolling (1m, 10% OTM)", 100.0, final_a2, len(trades_a2),
         len([t for t in trades_a2 if t["pnl_pct"] > 0])),
        ("A3: Catalyst (6m, rising)", 100.0, final_a3, len(trades_a3),
         len([t for t in trades_a3 if t["pnl_pct"] > 0])),
        ("A3 + B Combined", 100.0, final_combined, len(combined_trades),
         len([t for t in combined_trades if t["pnl_pct"] > 0])),
    ]

    print(f"\n  {'Strategy':<30} {'Trades':>7} {'Wins':>5} {'WinRate':>8} {'Return':>8} {'Final':>8}")
    print(f"  {'-'*72}")
    for name, start, end, n, w in results:
        wr = f"{w/n*100:.0f}%" if n > 0 else "N/A"
        ret = f"{(end/start-1)*100:+.1f}%"
        print(f"  {name:<30} {n:>7} {w:>5} {wr:>8} {ret:>8} ${end:>7.2f}")

    generate_chart(monthly, trades_a1, trades_a2, trades_a3, combined_trades)
    print(f"\nChart saved: vol_strategy_a_variants.png")


if __name__ == "__main__":
    main()
