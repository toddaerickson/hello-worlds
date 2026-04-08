"""VIX vs Regime Score overlay analysis.

Compares the composite regime score against VIX to identify where the
regime dashboard adds information beyond what implied volatility prices.

Usage:
    python vix_overlay.py
"""

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
AMBER = "#f59e0b"
CYAN = "#06b6d4"

SEP = "=" * 92

VIX_REGIMES = [
    ("Low (<15)", 0, 15),
    ("Normal (15-20)", 15, 20),
    ("Elevated (20-30)", 20, 30),
    ("High (30+)", 30, 200),
]

SCORE_BANDS = [
    ("0-14", 0, 15),
    ("15-24", 15, 25),
    ("25-34", 25, 35),
    ("35+", 35, 200),
]


# =========================================================================
# Helpers
# =========================================================================

def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0

def _median(vals):
    return statistics.median(vals) if vals else 0.0

def _dd_rate(subset, threshold=-10):
    if len(subset) < 3:
        return None
    return sum(1 for r in subset if r["max_dd_12m"] <= threshold) / len(subset) * 100

def _fwd_med(subset, key="fwd_12m"):
    vals = [r[key] for r in subset if r.get(key) is not None]
    return _median(vals) if len(vals) >= 3 else None

def _fmt_pct(val):
    return f"{val:.1f}%" if val is not None else "n/a"

def _fmt_ret(val):
    return f"{val:+.1f}%" if val is not None else "n/a"


# =========================================================================
# Data loading
# =========================================================================

def load_data():
    data = compute_historical_scores()
    n = len(data)
    for i, r in enumerate(data):
        r["fwd_6m"] = (data[i + 6]["spx"] / r["spx"] - 1) * 100 if i + 6 < n else None
        r["fwd_12m"] = (data[i + 12]["spx"] / r["spx"] - 1) * 100 if i + 12 < n else None
        end = min(i + 13, n)
        if end - i < 2:
            r["max_dd_12m"] = None
        else:
            peak = r["spx"]
            worst = 0.0
            for j in range(i + 1, end):
                peak = max(peak, data[j]["spx"])
                worst = min(worst, (data[j]["spx"] - peak) / peak * 100)
            r["max_dd_12m"] = worst
    return data


# =========================================================================
# Analysis 1: Time series correlation
# =========================================================================

def analyze_correlation(data):
    print(f"\n{SEP}")
    print("ANALYSIS 1: VIX vs Regime Score — Time-Series Relationship")
    print(SEP)

    scores = [r["score"] for r in data]
    vix = [r["vix"] for r in data]

    # Pearson correlation
    n = len(scores)
    mean_s = _mean(scores)
    mean_v = _mean(vix)
    cov = sum((s - mean_s) * (v - mean_v) for s, v in zip(scores, vix)) / n
    std_s = (sum((s - mean_s) ** 2 for s in scores) / n) ** 0.5
    std_v = (sum((v - mean_v) ** 2 for v in vix) / n) ** 0.5
    corr = cov / (std_s * std_v) if std_s * std_v > 0 else 0

    print(f"\n  Pearson correlation (VIX, Score):  {corr:+.3f}")
    print(f"  Score mean: {mean_s:.1f}   VIX mean: {mean_v:.1f}")
    print(f"  Score std:  {std_s:.1f}   VIX std:  {std_v:.1f}")

    # Concordance: both high or both low
    both_hi = sum(1 for r in data if r["vix"] >= 20 and r["score"] >= 25)
    both_lo = sum(1 for r in data if r["vix"] < 15 and r["score"] < 15)
    discord_calm_vix = sum(1 for r in data if r["vix"] < 15 and r["score"] >= 25)
    discord_high_vix = sum(1 for r in data if r["vix"] >= 25 and r["score"] < 15)

    print(f"\n  Concordant months:")
    print(f"    Both calm  (VIX<15, Score<15):  {both_lo:>4}  ({both_lo / n * 100:.1f}%)")
    print(f"    Both alert (VIX>=20, Score>=25): {both_hi:>4}  ({both_hi / n * 100:.1f}%)")
    print(f"  Discordant months:")
    print(f"    VIX calm + Score high:           {discord_calm_vix:>4}  ({discord_calm_vix / n * 100:.1f}%)")
    print(f"    VIX high + Score low:            {discord_high_vix:>4}  ({discord_high_vix / n * 100:.1f}%)")


# =========================================================================
# Analysis 2: Cross-tabulation of DD rates
# =========================================================================

def analyze_cross_tab(data):
    print(f"\n{SEP}")
    print("ANALYSIS 2: Forward 12m Drawdown Rates — VIX Regime x Score Band")
    print(SEP)

    valid = [r for r in data if r["max_dd_12m"] is not None]

    # Header
    print(f"\n{'':>20}", end="")
    for sl, _, _ in SCORE_BANDS:
        print(f" {'Score ' + sl:>14}", end="")
    print()
    print(f"{'VIX Regime':<20}", end="")
    for _ in SCORE_BANDS:
        print(f"  {'N':>4} {'DD10%':>7}", end="")
    print()
    print("-" * 80)

    for vl, v_lo, v_hi in VIX_REGIMES:
        print(f"{vl:<20}", end="")
        for sl, s_lo, s_hi in SCORE_BANDS:
            subset = [r for r in valid if v_lo <= r["vix"] < v_hi and s_lo <= r["score"] < s_hi]
            n = len(subset)
            dd = _dd_rate(subset)
            print(f"  {n:>4} {_fmt_pct(dd):>7}", end="")
        print()

    # Forward 12m returns table
    print(f"\n{'':>20}", end="")
    for sl, _, _ in SCORE_BANDS:
        print(f" {'Score ' + sl:>14}", end="")
    print()
    print(f"{'VIX Regime':<20}", end="")
    for _ in SCORE_BANDS:
        print(f"  {'N':>4} {'Med12m':>7}", end="")
    print()
    print("-" * 80)

    for vl, v_lo, v_hi in VIX_REGIMES:
        print(f"{vl:<20}", end="")
        for sl, s_lo, s_hi in SCORE_BANDS:
            subset = [r for r in valid if v_lo <= r["vix"] < v_hi and s_lo <= r["score"] < s_hi]
            n = len(subset)
            med = _fwd_med(subset)
            print(f"  {n:>4} {_fmt_ret(med):>7}", end="")
        print()


# =========================================================================
# Analysis 3: Discordance deep-dive
# =========================================================================

def analyze_discordance(data):
    print(f"\n{SEP}")
    print("ANALYSIS 3: Discordance — Where VIX and Regime Score Disagree")
    print(SEP)

    valid = [r for r in data if r["max_dd_12m"] is not None]

    quadrants = [
        ("VIX calm (<15) + Score low (<15)",    lambda r: r["vix"] < 15 and r["score"] < 15),
        ("VIX calm (<15) + Score high (>=25)",  lambda r: r["vix"] < 15 and r["score"] >= 25),
        ("VIX high (>=25) + Score low (<15)",   lambda r: r["vix"] >= 25 and r["score"] < 15),
        ("VIX high (>=25) + Score high (>=25)", lambda r: r["vix"] >= 25 and r["score"] >= 25),
    ]

    print(f"\n  {'Condition':<40} {'N':>5}  {'10%DD':>6} {'20%DD':>6}  {'Med 6m':>7} {'Med 12m':>8}")
    print(f"  {'-'*40} {'---':>5}  {'-----':>6} {'-----':>6}  {'------':>7} {'-------':>8}")

    for label, fn in quadrants:
        subset = [r for r in valid if fn(r)]
        n = len(subset)
        dd10 = _dd_rate(subset, -10)
        dd20 = _dd_rate(subset, -20)
        m6 = _fwd_med(subset, "fwd_6m")
        m12 = _fwd_med(subset, "fwd_12m")
        print(f"  {label:<40} {n:>5}  {_fmt_pct(dd10):>6} {_fmt_pct(dd20):>6}  {_fmt_ret(m6):>7} {_fmt_ret(m12):>8}")

    # Show specific "complacent fragility" episodes
    calm_high = [r for r in valid if r["vix"] < 15 and r["score"] >= 25]
    if calm_high:
        print(f"\n  'Complacent fragility' episodes (VIX<15, Score>=25):")
        prev_date = ""
        for r in calm_high:
            # Show first month of each episode
            yr = r["date"][:4]
            if yr != prev_date:
                fwd = r.get("fwd_12m")
                fwd_str = f"fwd12m={fwd:+.1f}%" if fwd is not None else "no fwd data"
                dd = r["max_dd_12m"]
                dd_str = f"maxDD={dd:.1f}%" if dd is not None else ""
                print(f"    {r['date']}  score={r['score']:>5.1f}  vix={r['vix']:>4.1f}  {fwd_str}  {dd_str}")
                prev_date = yr


# =========================================================================
# Analysis 4: Incremental predictive value
# =========================================================================

def analyze_incremental_value(data):
    print(f"\n{SEP}")
    print("ANALYSIS 4: Does the Regime Score Add Information Beyond VIX?")
    print(SEP)

    valid = [r for r in data if r["max_dd_12m"] is not None]

    # For each VIX regime, does higher score predict worse outcomes?
    print(f"\n  Within each VIX regime, compare low-score vs high-score months:")
    print(f"\n  {'VIX Regime':<20} {'Score<20':^22} {'Score>=20':^22} {'Difference':^12}")
    print(f"  {'':20} {'N':>4} {'DD10%':>7} {'Med12m':>8} {'N':>4} {'DD10%':>7} {'Med12m':>8} {'DD10 gap':>10}")
    print(f"  {'-'*90}")

    for vl, v_lo, v_hi in VIX_REGIMES:
        lo_s = [r for r in valid if v_lo <= r["vix"] < v_hi and r["score"] < 20]
        hi_s = [r for r in valid if v_lo <= r["vix"] < v_hi and r["score"] >= 20]

        dd_lo = _dd_rate(lo_s, -10)
        dd_hi = _dd_rate(hi_s, -10)
        m12_lo = _fwd_med(lo_s, "fwd_12m")
        m12_hi = _fwd_med(hi_s, "fwd_12m")

        gap = ""
        if dd_lo is not None and dd_hi is not None:
            gap = f"{dd_hi - dd_lo:+.1f}pp"

        print(f"  {vl:<20} {len(lo_s):>4} {_fmt_pct(dd_lo):>7} {_fmt_ret(m12_lo):>8}"
              f" {len(hi_s):>4} {_fmt_pct(dd_hi):>7} {_fmt_ret(m12_hi):>8} {gap:>10}")

    print(f"\n  A positive 'DD10 gap' means the regime score adds drawdown-predictive")
    print(f"  information beyond what VIX alone tells you.")


# =========================================================================
# Chart generation
# =========================================================================

def generate_chart(data):
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(20, 14), facecolor=BG)
    fig.suptitle("VIX vs Regime Score — Overlay & Discordance Analysis (1980-2026)",
                 color="white", fontsize=16, fontweight="bold", y=0.97)

    dates = [r["date"] for r in data]
    scores = [r["score"] for r in data]
    vix = [r["vix"] for r in data]
    spx = [r["spx"] for r in data]
    x = range(len(data))

    # Tick positions (every 5 years)
    tick_locs, tick_labels = [], []
    for i, r in enumerate(data):
        if r["date"].endswith("-01") and int(r["date"][:4]) % 5 == 0:
            tick_locs.append(i)
            tick_labels.append(r["date"][:4])

    # -----------------------------------------------------------------
    # Panel 1 (top): VIX and Score time series overlay
    # -----------------------------------------------------------------
    ax1 = fig.add_axes([0.06, 0.56, 0.88, 0.36])
    ax1.set_facecolor(PANEL_BG)

    ax1.plot(x, scores, color=AMBER, linewidth=1.5, alpha=0.9, label="Regime Score", zorder=3)
    ax1.set_ylabel("Regime Score", color=AMBER, fontsize=11)
    ax1.set_ylim(0, 80)
    ax1.tick_params(axis="y", colors=AMBER)

    ax1_vix = ax1.twinx()
    ax1_vix.plot(x, vix, color=CYAN, linewidth=1.2, alpha=0.7, label="VIX", zorder=2)
    ax1_vix.set_ylabel("VIX", color=CYAN, fontsize=11)
    ax1_vix.set_ylim(0, 70)
    ax1_vix.tick_params(axis="y", colors=CYAN)

    # Shade drawdown periods
    peak = spx[0]
    for i in range(len(spx)):
        peak = max(peak, spx[i])
        if (spx[i] - peak) / peak <= -0.10:
            ax1.axvspan(i - 0.5, i + 0.5, color="#ef4444", alpha=0.10, zorder=0)

    ax1.set_xticks(tick_locs)
    ax1.set_xticklabels(tick_labels, color=TEXT_COLOR, fontsize=9)
    ax1.set_title("Regime Score (amber) vs VIX (cyan) — Red = 10%+ Drawdown Periods",
                   color="white", fontsize=12)
    ax1.grid(axis="y", color=GRID_COLOR, alpha=0.3)

    handles = [
        plt.Line2D([0], [0], color=AMBER, linewidth=2, label="Regime Score"),
        plt.Line2D([0], [0], color=CYAN, linewidth=2, label="VIX"),
        mpatches.Patch(facecolor="#ef4444", alpha=0.2, label="10%+ Drawdown"),
    ]
    ax1.legend(handles=handles, loc="upper left", fontsize=9,
               facecolor=PANEL_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)

    # -----------------------------------------------------------------
    # Panel 2 (bottom-left): Discordance scatter
    # -----------------------------------------------------------------
    ax2 = fig.add_axes([0.06, 0.07, 0.42, 0.38])
    ax2.set_facecolor(PANEL_BG)

    valid = [r for r in data if r["max_dd_12m"] is not None]
    vix_v = [r["vix"] for r in valid]
    score_v = [r["score"] for r in valid]
    dd_v = [r["max_dd_12m"] for r in valid]

    # Color by drawdown severity
    colors = []
    for dd in dd_v:
        if dd <= -20:
            colors.append("#ef4444")       # severe DD — red
        elif dd <= -10:
            colors.append("#f59e0b")       # moderate DD — amber
        else:
            colors.append("#10b981")       # benign — green

    ax2.scatter(vix_v, score_v, c=colors, s=18, alpha=0.6, zorder=3)

    # Quadrant lines
    ax2.axhline(25, color="#6b7280", linestyle="--", linewidth=0.8, alpha=0.5)
    ax2.axvline(15, color="#6b7280", linestyle="--", linewidth=0.8, alpha=0.5)

    # Quadrant labels
    ax2.text(8, 58, "COMPLACENT\nFRAGILITY", color="#ef4444", fontsize=9,
             fontweight="bold", ha="center", alpha=0.8)
    ax2.text(40, 58, "BOTH\nALARM", color="#8b5cf6", fontsize=9,
             fontweight="bold", ha="center", alpha=0.8)
    ax2.text(8, 3, "BOTH\nCALM", color="#10b981", fontsize=9,
             fontweight="bold", ha="center", alpha=0.8)
    ax2.text(40, 3, "VIX PANIC\nSCORE CALM", color="#3b82f6", fontsize=9,
             fontweight="bold", ha="center", alpha=0.8)

    ax2.set_xlabel("VIX", color=TEXT_COLOR, fontsize=11)
    ax2.set_ylabel("Regime Score", color=TEXT_COLOR, fontsize=11)
    ax2.set_title("VIX vs Score Scatter (color = fwd 12m drawdown severity)",
                   color="white", fontsize=11)
    ax2.tick_params(colors=TEXT_COLOR)
    ax2.grid(color=GRID_COLOR, alpha=0.3)

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#ef4444",
                    markersize=8, label="20%+ DD", linestyle="None"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#f59e0b",
                    markersize=8, label="10-20% DD", linestyle="None"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#10b981",
                    markersize=8, label="<10% DD", linestyle="None"),
    ]
    ax2.legend(handles=legend_handles, loc="upper right", fontsize=8,
               facecolor=PANEL_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)

    # -----------------------------------------------------------------
    # Panel 3 (bottom-right): DD rate by quadrant bar chart
    # -----------------------------------------------------------------
    ax3 = fig.add_axes([0.56, 0.07, 0.42, 0.38])
    ax3.set_facecolor(PANEL_BG)

    quadrants = [
        ("Both\nCalm",           lambda r: r["vix"] < 15 and r["score"] < 15),
        ("VIX Calm\nScore High", lambda r: r["vix"] < 15 and r["score"] >= 25),
        ("VIX High\nScore Calm", lambda r: r["vix"] >= 25 and r["score"] < 15),
        ("Both\nAlert",          lambda r: r["vix"] >= 25 and r["score"] >= 25),
    ]

    q_labels = []
    dd10_rates = []
    dd20_rates = []
    fwd12_meds = []
    bar_colors = ["#10b981", "#ef4444", "#3b82f6", "#8b5cf6"]

    for label, fn in quadrants:
        subset = [r for r in valid if fn(r)]
        q_labels.append(label)
        dd10 = _dd_rate(subset, -10)
        dd20 = _dd_rate(subset, -20)
        med = _fwd_med(subset, "fwd_12m")
        dd10_rates.append(dd10 if dd10 is not None else 0)
        dd20_rates.append(dd20 if dd20 is not None else 0)
        fwd12_meds.append(med if med is not None else 0)

    qx = list(range(4))
    bar_w = 0.3
    ax3.bar([x - bar_w / 2 for x in qx], dd10_rates, bar_w * 0.9,
            color=bar_colors, alpha=0.8, label="10%+ DD rate")
    ax3.bar([x + bar_w / 2 for x in qx], dd20_rates, bar_w * 0.9,
            color=bar_colors, alpha=0.45, label="20%+ DD rate")

    # Annotate with median 12m return
    for i, med in enumerate(fwd12_meds):
        y = max(dd10_rates[i], dd20_rates[i]) + 2
        ax3.text(i, y, f"med12m\n{med:+.1f}%", ha="center", fontsize=8,
                 color=TEXT_COLOR)

    # Count annotations
    for i, (label, fn) in enumerate(quadrants):
        subset = [r for r in valid if fn(r)]
        ax3.text(i, -4, f"n={len(subset)}", ha="center", fontsize=8, color="#6b7280")

    ax3.set_xticks(qx)
    ax3.set_xticklabels(q_labels, color=TEXT_COLOR, fontsize=9)
    ax3.set_ylabel("Drawdown Rate (%)", color=TEXT_COLOR, fontsize=10)
    ax3.set_title("Forward Drawdown Rate by VIX/Score Quadrant", color="white", fontsize=11)
    ax3.tick_params(colors=TEXT_COLOR)
    ax3.grid(axis="y", color=GRID_COLOR, alpha=0.3)
    ax3.legend(fontsize=8, loc="upper left",
               facecolor=PANEL_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)

    fig.savefig("vix_overlay.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


# =========================================================================
# Main
# =========================================================================

def main():
    data = load_data()
    analyze_correlation(data)
    analyze_cross_tab(data)
    analyze_discordance(data)
    analyze_incremental_value(data)
    generate_chart(data)
    print(f"\nChart saved: vix_overlay.png")


if __name__ == "__main__":
    main()
