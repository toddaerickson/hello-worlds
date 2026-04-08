"""Backtest: evaluate the regime dashboard's historical effectiveness.

Computes forward S&P 500 returns and drawdowns conditional on the composite
regime score, then prints analysis tables and generates a 4-panel PNG chart.

Usage:
    python backtest_regime.py
"""

import math
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from regime_dashboard.historical_scores import compute_historical_scores

# =========================================================================
# Constants
# =========================================================================

QUINTILE_LABELS = ["Q1 (Lowest)", "Q2", "Q3", "Q4", "Q5 (Highest)"]
HORIZONS = [3, 6, 12]
DD_THRESHOLDS = [10, 15, 20]
SCORE_THRESHOLDS = [20, 30, 40]
ROC_THRESHOLDS = [10, 20, 30, 40, 50, 60, 70, 80]

SIGNAL_KEYS = [
    ("s1_breadth", "S1 Breadth"),
    ("s2_valuation", "S2 Valuation"),
    ("s3_credit", "S3 Credit"),
    ("s4_sentiment", "S4 Sentiment"),
    ("s5_macro", "S5 Macro"),
    ("s6_leverage", "S6 Leverage"),
    ("s7_term_premium", "S7 Term Premium"),
]

# Dark theme matching regime_chart.py
BG = "#0a0e17"
PANEL_BG = "#111827"
GRID_COLOR = "#1f2937"
TEXT_COLOR = "#9ca3af"
AMBER = "#f59e0b"

QUINTILE_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6"]

SIGNAL_COLORS = ["#3b82f6", "#ef4444", "#f59e0b", "#10b981",
                 "#8b5cf6", "#ec4899", "#06b6d4"]

SEPARATOR = "=" * 80


# =========================================================================
# Data loading and forward metric computation
# =========================================================================

def load_and_compute():
    """Load historical scores and attach forward return/drawdown metrics + quintile."""
    data = compute_historical_scores()
    n = len(data)

    for i, rec in enumerate(data):
        # Forward returns
        for h in HORIZONS:
            key = f"fwd_{h}m"
            if i + h < n:
                rec[key] = (data[i + h]["spx"] / rec["spx"] - 1) * 100
            else:
                rec[key] = None

        # Max drawdown over next 12 months
        end = min(i + 13, n)
        if end - i < 2:
            rec["max_dd_12m"] = None
        else:
            peak = rec["spx"]
            worst = 0.0
            for j in range(i + 1, end):
                peak = max(peak, data[j]["spx"])
                dd = (data[j]["spx"] - peak) / peak * 100
                worst = min(worst, dd)
            rec["max_dd_12m"] = worst

    # Assign quintiles by score rank (Q1 = lowest scores, Q5 = highest)
    sorted_scores = sorted(r["score"] for r in data)
    breakpoints = []
    for q in range(1, 5):
        idx = int(len(sorted_scores) * q / 5)
        breakpoints.append(sorted_scores[idx])

    for rec in data:
        s = rec["score"]
        if s < breakpoints[0]:
            rec["quintile"] = 0
        elif s < breakpoints[1]:
            rec["quintile"] = 1
        elif s < breakpoints[2]:
            rec["quintile"] = 2
        elif s < breakpoints[3]:
            rec["quintile"] = 3
        else:
            rec["quintile"] = 4

    # Store breakpoints for reporting
    data[0]["_quintile_breakpoints"] = breakpoints

    return data


def _group_by_quintile(data, key):
    """Group non-None values of `key` by score quintile."""
    groups = {q: [] for q in range(5)}
    for rec in data:
        val = rec.get(key)
        if val is not None:
            groups[rec["quintile"]].append(val)
    return groups


def _median(vals):
    return statistics.median(vals) if vals else 0.0


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def _pct_neg(vals):
    return sum(1 for v in vals if v < 0) / len(vals) * 100 if vals else 0.0


# =========================================================================
# Analysis 1: Forward returns by score quintile
# =========================================================================

def analyze_forward_returns(data):
    bp = data[0]["_quintile_breakpoints"]
    print(f"\n{SEPARATOR}")
    print("ANALYSIS 1: Forward S&P 500 Returns by Score Quintile")
    print(f"  Breakpoints: Q1 < {bp[0]:.1f} | Q2 < {bp[1]:.1f} | Q3 < {bp[2]:.1f} | Q4 < {bp[3]:.1f} | Q5 >= {bp[3]:.1f}")
    print(SEPARATOR)

    print(f"\n{'':16}{'':>5}  {'--- 3-Month ---':^17}  {'--- 6-Month ---':^17}  {'--- 12-Month ---':^18}")
    print(f"{'Quintile':<16}{'N':>5}  {'Mean':>6} {'Med':>6} {'%Neg':>5}  {'Mean':>6} {'Med':>6} {'%Neg':>5}  {'Mean':>6} {'Med':>6} {'%Neg':>5}")
    print("-" * 84)

    results = {}
    for q in range(5):
        label = QUINTILE_LABELS[q]
        fwd = {}
        for h in HORIZONS:
            vals = [r[f"fwd_{h}m"] for r in data if r["quintile"] == q and r[f"fwd_{h}m"] is not None]
            fwd[h] = vals
        n = len(fwd[HORIZONS[0]]) if fwd[HORIZONS[0]] else 0
        row = f"{label:<16}{n:>5}"
        for h in HORIZONS:
            v = fwd[h]
            row += f"  {_mean(v):>5.1f}% {_median(v):>5.1f}% {_pct_neg(v):>4.0f}%"
        print(row)
        results[q] = fwd

    return results


# =========================================================================
# Analysis 2: Max drawdown by score quintile
# =========================================================================

def analyze_drawdowns(data):
    print(f"\n{SEPARATOR}")
    print("ANALYSIS 2: Maximum 12-Month Forward Drawdown by Score Quintile")
    print(SEPARATOR)

    print(f"\n{'Quintile':<16}{'N':>5}  {'Mean':>7} {'Median':>7} {'Worst':>7}  {'>=10%':>6} {'>=15%':>6} {'>=20%':>6}")
    print("-" * 76)

    groups = _group_by_quintile(data, "max_dd_12m")
    results = {}
    for q in range(5):
        label = QUINTILE_LABELS[q]
        vals = groups[q]
        n = len(vals)
        if n == 0:
            print(f"{label:<16}{0:>5}  {'n/a':>7} {'n/a':>7} {'n/a':>7}  {'n/a':>6} {'n/a':>6} {'n/a':>6}")
            results[q] = vals
            continue
        mean_dd = _mean(vals)
        med_dd = _median(vals)
        worst = min(vals)
        pcts = []
        for thr in DD_THRESHOLDS:
            pcts.append(sum(1 for v in vals if v <= -thr) / n * 100)
        print(f"{label:<16}{n:>5}  {mean_dd:>6.1f}% {med_dd:>6.1f}% {worst:>6.1f}%  {pcts[0]:>5.1f}% {pcts[1]:>5.1f}% {pcts[2]:>5.1f}%")
        results[q] = vals

    return results


# =========================================================================
# Analysis 3: Signal-to-drawdown timing
# =========================================================================

def analyze_threshold_timing(data):
    print(f"\n{SEPARATOR}")
    print("ANALYSIS 3: Months from Score Threshold Crossing to Next 10%+ Drawdown")
    print(SEPARATOR)

    print(f"\n{'Threshold':<12}{'Crossings':>10}{'Hit 10%DD':>10}{'Hit Rate':>10}{'Mean Mo':>10}{'Med Mo':>10}")
    print("-" * 62)

    n = len(data)
    for thr in SCORE_THRESHOLDS:
        # Detect upward crossings
        crossings = []
        for i in range(n):
            if data[i]["score"] >= thr:
                if i == 0 or data[i - 1]["score"] < thr:
                    crossings.append(i)

        months_to_dd = []
        for ci in crossings:
            peak = data[ci]["spx"]
            found = False
            for j in range(ci + 1, n):
                peak = max(peak, data[j]["spx"])
                dd = (data[j]["spx"] - peak) / peak
                if dd <= -0.10:
                    months_to_dd.append(j - ci)
                    found = True
                    break
            if not found:
                months_to_dd.append(None)

        hits = [m for m in months_to_dd if m is not None]
        n_cross = len(crossings)
        n_hit = len(hits)
        rate = n_hit / n_cross * 100 if n_cross else 0
        mean_m = _mean(hits) if hits else 0
        med_m = _median(hits) if hits else 0

        print(f">= {thr:<9}{n_cross:>10}{n_hit:>10}{rate:>9.1f}%{mean_m:>9.1f}{med_m:>10.0f}")


# =========================================================================
# Analysis 4: Hit rates by quintile
# =========================================================================

def analyze_hit_rates(data):
    print(f"\n{SEPARATOR}")
    print("ANALYSIS 4: Hit Rates -- % of Months Experiencing Forward 12m Drawdown")
    print(SEPARATOR)

    print(f"\n{'Quintile':<16}{'N':>5}  {'>=10% DD':>9} {'>=15% DD':>9} {'>=20% DD':>9}")
    print("-" * 54)

    groups = _group_by_quintile(data, "max_dd_12m")
    for q in range(5):
        label = QUINTILE_LABELS[q]
        vals = groups[q]
        n = len(vals)
        if n == 0:
            print(f"{label:<16}{0:>5}  {'n/a':>9} {'n/a':>9} {'n/a':>9}")
            continue
        pcts = []
        for thr in DD_THRESHOLDS:
            pcts.append(sum(1 for v in vals if v <= -thr) / n * 100)
        print(f"{label:<16}{n:>5}  {pcts[0]:>8.1f}% {pcts[1]:>8.1f}% {pcts[2]:>8.1f}%")


# =========================================================================
# Analysis 5: Individual signal predictive power
# =========================================================================

def analyze_individual_signals(data):
    print(f"\n{SEPARATOR}")
    print("ANALYSIS 5: Individual Signal Predictive Power (Signal >= 50 predicts 10%+ DD)")
    print(SEPARATOR)

    # Subset with valid drawdown data
    valid = [r for r in data if r["max_dd_12m"] is not None]
    total_pos = sum(1 for r in valid if r["max_dd_12m"] <= -10)  # actual 10%+ DD
    total_neg = len(valid) - total_pos
    base_rate = total_pos / len(valid) * 100 if valid else 0

    print(f"\nBase rate of 10%+ drawdown: {base_rate:.1f}% ({total_pos}/{len(valid)} months)")
    print(f"\n{'Signal':<22}{'TP Rate':>9}{'FP Rate':>9}{'Precision':>11}{'Lift':>7}")
    print("-" * 58)

    roc_data = {}
    all_signals = list(SIGNAL_KEYS) + [("score", "Composite")]

    for key, label in all_signals:
        # Binary classifier: signal >= 50
        tp = sum(1 for r in valid if r[key] >= 50 and r["max_dd_12m"] <= -10)
        fp = sum(1 for r in valid if r[key] >= 50 and r["max_dd_12m"] > -10)
        fn = sum(1 for r in valid if r[key] < 50 and r["max_dd_12m"] <= -10)
        tn = sum(1 for r in valid if r[key] < 50 and r["max_dd_12m"] > -10)

        tpr = tp / (tp + fn) * 100 if (tp + fn) else 0
        fpr = fp / (fp + tn) * 100 if (fp + tn) else 0
        prec = tp / (tp + fp) * 100 if (tp + fp) else 0
        hit_when_fired = tp / (tp + fp) if (tp + fp) else 0
        lift = (hit_when_fired / (base_rate / 100)) if base_rate else 0

        print(f"{label:<22}{tpr:>8.1f}%{fpr:>8.1f}%{prec:>10.1f}%{lift:>6.2f}x")

        # ROC curve: multiple thresholds
        roc_points = []
        for t in ROC_THRESHOLDS:
            t_tp = sum(1 for r in valid if r[key] >= t and r["max_dd_12m"] <= -10)
            t_fp = sum(1 for r in valid if r[key] >= t and r["max_dd_12m"] > -10)
            t_fn = sum(1 for r in valid if r[key] < t and r["max_dd_12m"] <= -10)
            t_tn = sum(1 for r in valid if r[key] < t and r["max_dd_12m"] > -10)
            t_tpr = t_tp / (t_tp + t_fn) if (t_tp + t_fn) else 0
            t_fpr = t_fp / (t_fp + t_tn) if (t_fp + t_tn) else 0
            roc_points.append((t_fpr, t_tpr))
        # Add endpoints
        roc_points.append((0.0, 0.0))
        roc_points.append((1.0, 1.0))
        roc_points.sort()
        roc_data[key] = roc_points

    return roc_data


# =========================================================================
# Summary statistics
# =========================================================================

def print_summary(data):
    print(f"\n{SEPARATOR}")
    print("SUMMARY STATISTICS")
    print(SEPARATOR)

    valid = [r for r in data if r["max_dd_12m"] is not None]
    print(f"\nTotal months analyzed:            {len(data)}  ({data[0]['date']} to {data[-1]['date']})")
    print(f"Months with 12m forward data:     {len(valid)}")

    bp = data[0]["_quintile_breakpoints"]
    print("\nScore quintile distribution:")
    for q in range(5):
        label = QUINTILE_LABELS[q]
        cnt = sum(1 for r in data if r["quintile"] == q)
        scores = sorted(r["score"] for r in data if r["quintile"] == q)
        lo, hi = scores[0], scores[-1]
        print(f"  {label:<16} {cnt:>4} months  (score {lo:>5.1f} - {hi:>5.1f})")

    all_dd = [r["max_dd_12m"] for r in valid]
    print(f"\nOverall 12-month drawdown statistics:")
    print(f"  Mean max drawdown:     {_mean(all_dd):>6.1f}%")
    print(f"  Median max drawdown:   {_median(all_dd):>6.1f}%")
    for thr in DD_THRESHOLDS:
        pct = sum(1 for v in all_dd if v <= -thr) / len(all_dd) * 100
        print(f"  Base rate {thr}%+ DD:    {pct:>5.1f}%")


# =========================================================================
# Chart generation
# =========================================================================

def generate_chart(data, fwd_results, dd_results, roc_data):
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(20, 16), facecolor=BG)
    fig.suptitle("Regime Dashboard Backtest -- Historical Drawdown Analysis (1980-2026)",
                 color="white", fontsize=16, fontweight="bold", y=0.97)

    # -----------------------------------------------------------------
    # Panel 1 (top-left): Forward returns by quintile
    # -----------------------------------------------------------------
    ax1 = fig.add_axes([0.06, 0.55, 0.42, 0.36])
    ax1.set_facecolor(PANEL_BG)

    bar_w = 0.22
    horizon_colors = ["#3b82f6", "#10b981", "#f59e0b"]
    x_pos = list(range(5))
    q_labels = ["Q1\nLowest", "Q2", "Q3", "Q4", "Q5\nHighest"]

    for hi, h in enumerate(HORIZONS):
        medians = []
        for q in range(5):
            vals = fwd_results.get(q, {}).get(h, [])
            medians.append(_median(vals) if vals else 0)
        offsets = [x + (hi - 1) * bar_w for x in x_pos]
        ax1.bar(offsets, medians, bar_w * 0.9, color=horizon_colors[hi],
                label=f"{h}-month", alpha=0.85)

    ax1.axhline(0, color=GRID_COLOR, linewidth=1)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(q_labels, color=TEXT_COLOR, fontsize=9)
    ax1.set_ylabel("Median Forward Return (%)", color=TEXT_COLOR, fontsize=10)
    ax1.set_title("Forward S&P 500 Returns by Score Quintile", color="white", fontsize=12)
    ax1.legend(fontsize=9, loc="upper right")
    ax1.tick_params(colors=TEXT_COLOR)
    ax1.grid(axis="y", color=GRID_COLOR, alpha=0.5)

    # -----------------------------------------------------------------
    # Panel 2 (top-right): Max drawdown by quintile
    # -----------------------------------------------------------------
    ax2 = fig.add_axes([0.56, 0.55, 0.42, 0.36])
    ax2.set_facecolor(PANEL_BG)

    mean_dds = []
    worst_dds = []
    for q in range(5):
        vals = dd_results.get(q, [])
        mean_dds.append(_mean(vals) if vals else 0)
        worst_dds.append(min(vals) if vals else 0)

    ax2.bar(x_pos, mean_dds, 0.5, color=QUINTILE_COLORS, alpha=0.8, label="Mean DD")
    ax2.scatter(x_pos, worst_dds, color="white", marker="v", s=80, zorder=5, label="Worst DD")

    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(q_labels, color=TEXT_COLOR, fontsize=9)
    ax2.set_ylabel("Drawdown (%)", color=TEXT_COLOR, fontsize=10)
    ax2.set_title("12-Month Max Drawdown by Score Quintile", color="white", fontsize=12)
    ax2.legend(fontsize=9, loc="lower left")
    ax2.tick_params(colors=TEXT_COLOR)
    ax2.grid(axis="y", color=GRID_COLOR, alpha=0.5)

    # -----------------------------------------------------------------
    # Panel 3 (bottom-left): Score + SPX with drawdown shading
    # -----------------------------------------------------------------
    ax3 = fig.add_axes([0.06, 0.06, 0.42, 0.36])
    ax3.set_facecolor(PANEL_BG)

    scores = [r["score"] for r in data]
    spx = [r["spx"] for r in data]
    x = range(len(data))

    ax3.plot(x, scores, color=AMBER, linewidth=1.2, alpha=0.9, label="Regime Score")
    ax3.set_ylabel("Composite Score", color=AMBER, fontsize=10)
    ax3.set_ylim(0, 100)
    ax3.tick_params(axis="y", colors=AMBER)

    # SPX on secondary axis
    ax3b = ax3.twinx()
    ax3b.plot(x, spx, color="white", linewidth=0.8, alpha=0.35)
    ax3b.set_yscale("log")
    ax3b.set_ylabel("S&P 500 (log)", color="#6b7280", fontsize=10)
    ax3b.tick_params(axis="y", colors="#6b7280")

    # Shade drawdown periods (SPX >= 10% below trailing peak)
    peak = spx[0]
    for i in range(len(spx)):
        peak = max(peak, spx[i])
        dd = (spx[i] - peak) / peak
        if dd <= -0.10:
            ax3.axvspan(i - 0.5, i + 0.5, color="#ef4444", alpha=0.12)

    # X-axis ticks every 5 years
    tick_locs = []
    tick_labels = []
    for i, r in enumerate(data):
        if r["date"].endswith("-01") and int(r["date"][:4]) % 5 == 0:
            tick_locs.append(i)
            tick_labels.append(r["date"][:4])
    ax3.set_xticks(tick_locs)
    ax3.set_xticklabels(tick_labels, color=TEXT_COLOR, fontsize=9)
    ax3.set_title("Regime Score vs S&P 500 (Red = 10%+ Drawdown)", color="white", fontsize=12)
    ax3.grid(axis="y", color=GRID_COLOR, alpha=0.3)

    # -----------------------------------------------------------------
    # Panel 4 (bottom-right): ROC curves
    # -----------------------------------------------------------------
    ax4 = fig.add_axes([0.56, 0.06, 0.42, 0.36])
    ax4.set_facecolor(PANEL_BG)

    # Diagonal reference
    ax4.plot([0, 1], [0, 1], color="#4b5563", linestyle="--", linewidth=1,
             label="Random", alpha=0.6)

    # Individual signals
    for idx, (key, label) in enumerate(SIGNAL_KEYS):
        pts = roc_data.get(key, [])
        if pts:
            fpr_vals = [p[0] for p in pts]
            tpr_vals = [p[1] for p in pts]
            ax4.plot(fpr_vals, tpr_vals, color=SIGNAL_COLORS[idx],
                     linewidth=1.5, alpha=0.8, label=label)

    # Composite
    pts = roc_data.get("score", [])
    if pts:
        ax4.plot([p[0] for p in pts], [p[1] for p in pts],
                 color="white", linewidth=2.5, linestyle="--", label="Composite")

    ax4.set_xlabel("False Positive Rate", color=TEXT_COLOR, fontsize=10)
    ax4.set_ylabel("True Positive Rate", color=TEXT_COLOR, fontsize=10)
    ax4.set_title("Signal ROC: Predicting 10%+ Drawdown (12m)", color="white", fontsize=12)
    ax4.set_xlim(-0.02, 1.02)
    ax4.set_ylim(-0.02, 1.02)
    ax4.legend(fontsize=8, loc="lower right", ncol=2)
    ax4.tick_params(colors=TEXT_COLOR)
    ax4.grid(color=GRID_COLOR, alpha=0.3)

    fig.savefig("backtest_results.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


# =========================================================================
# Disclaimer
# =========================================================================

def print_disclaimer():
    print(SEPARATOR)
    print("  IMPORTANT DISCLAIMER: LOOK-AHEAD BIAS IN KEYFRAME DATA")
    print(SEPARATOR)
    print("""
These results use regime scores derived from keyframe-interpolated economic
indicators, NOT from live data feeds. The keyframes were placed at known
historical turning points (recessions, crises, market peaks), which means:

  1. The indicator values at keyframes reflect knowledge of events that had
     already occurred -- the keyframe author knew where the turning points were.
  2. Interpolation between keyframes produces smooth transitions that real-time
     data would not have shown (e.g., credit spreads widen gradually before
     crises, whereas in reality they often spike suddenly).
  3. This backtest is a CALIBRATION CHECK -- verifying that the scoring
     framework's thresholds produce reasonable relationships with outcomes --
     NOT evidence of real-time predictive performance.

The regime dashboard is a fragility classifier, not a trading signal. These
results characterize the relationship between measured market conditions and
subsequent outcomes, subject to the data limitations described above.
""")
    print(SEPARATOR)


# =========================================================================
# Main
# =========================================================================

def main():
    print_disclaimer()
    data = load_and_compute()
    fwd_results = analyze_forward_returns(data)
    dd_results = analyze_drawdowns(data)
    analyze_threshold_timing(data)
    analyze_hit_rates(data)
    roc_data = analyze_individual_signals(data)
    print_summary(data)
    generate_chart(data, fwd_results, dd_results, roc_data)
    print(f"\nChart saved: backtest_results.png")


if __name__ == "__main__":
    main()
