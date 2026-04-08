"""Backtest: evaluate the regime dashboard's historical effectiveness.

Computes forward S&P 500 returns and drawdowns conditional on the composite
regime score, then prints analysis tables and generates a 4-panel PNG chart.

Analyses use 5-point score buckets to show the continuous return profile,
and a momentum split (score rising vs falling) to separate pre-crisis
deterioration from post-crisis recovery.

Usage:
    python backtest_regime.py
"""

import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from regime_dashboard.historical_scores import compute_historical_scores

# =========================================================================
# Constants
# =========================================================================

SCORE_BUCKETS = list(range(0, 70, 5))   # [0, 5, 10, ..., 65]
HORIZONS = [6, 12]
DD_THRESHOLDS = [10, 15, 20]
CROSSING_THRESHOLDS = [20, 30, 40]
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

SIGNAL_COLORS = ["#3b82f6", "#ef4444", "#f59e0b", "#10b981",
                 "#8b5cf6", "#ec4899", "#06b6d4"]

SEPARATOR = "=" * 92


# =========================================================================
# Data loading and forward metric computation
# =========================================================================

def load_and_compute():
    """Load historical scores and attach forward returns, drawdowns, and momentum."""
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

        # Score momentum: is current score higher than 6 months ago?
        rec["score_rising"] = rec["score"] > (data[i - 6]["score"] if i >= 6 else rec["score"])

    return data


def _bucket_label(lo):
    return f"{lo:>2}-{lo + 4:<2}"


def _median(vals):
    return statistics.median(vals) if vals else 0.0


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def _pct_neg(vals):
    return sum(1 for v in vals if v < 0) / len(vals) * 100 if vals else 0.0


def _collect_bucket(data, lo, key, filter_fn=None):
    """Collect non-None values of `key` from records in score bucket [lo, lo+5)."""
    out = []
    for r in data:
        if lo <= r["score"] < lo + 5:
            if filter_fn and not filter_fn(r):
                continue
            val = r.get(key)
            if val is not None:
                out.append(val)
    return out


# =========================================================================
# Analysis 1: Forward returns by score level
# =========================================================================

def analyze_forward_returns(data):
    print(f"\n{SEPARATOR}")
    print("ANALYSIS 1: Forward S&P 500 Returns by Score Level (5-point buckets)")
    print(SEPARATOR)

    print(f"\n{'Score':>8} {'N':>5}  {'------- 6-Month -------':^25}  {'------- 12-Month -------':^25}  {'DD Rates':^17}")
    print(f"{'':>8} {'':>5}  {'Mean':>7} {'Median':>7} {'%Neg':>6}  {'Mean':>7} {'Median':>7} {'%Neg':>6}  {'>=10%':>7} {'>=20%':>7}")
    print("-" * 92)

    bucket_data = {}
    for lo in SCORE_BUCKETS:
        fwd6 = _collect_bucket(data, lo, "fwd_6m")
        fwd12 = _collect_bucket(data, lo, "fwd_12m")
        dd = _collect_bucket(data, lo, "max_dd_12m")
        if not fwd12:
            continue

        dd10 = sum(1 for v in dd if v <= -10) / len(dd) * 100 if dd else 0
        dd20 = sum(1 for v in dd if v <= -20) / len(dd) * 100 if dd else 0

        print(f" {_bucket_label(lo):>7} {len(fwd12):>5}"
              f"  {_mean(fwd6):>+6.1f}% {_median(fwd6):>+6.1f}% {_pct_neg(fwd6):>5.0f}%"
              f"  {_mean(fwd12):>+6.1f}% {_median(fwd12):>+6.1f}% {_pct_neg(fwd12):>5.0f}%"
              f"  {dd10:>6.1f}% {dd20:>6.1f}%")

        bucket_data[lo] = {
            "fwd6_mean": _mean(fwd6), "fwd6_med": _median(fwd6),
            "fwd12_mean": _mean(fwd12), "fwd12_med": _median(fwd12),
            "dd10": dd10, "dd20": dd20, "n": len(fwd12),
        }

    return bucket_data


# =========================================================================
# Analysis 2: Forward returns by score level + momentum direction
# =========================================================================

def analyze_momentum_split(data):
    print(f"\n{SEPARATOR}")
    print("ANALYSIS 2: Forward 12-Month Returns — Score RISING vs FALLING")
    print("  Rising  = score > score 6 months ago (fragility building)")
    print("  Falling = score <= score 6 months ago (fragility receding / recovery)")
    print(SEPARATOR)

    print(f"\n{'':>8}  {'--------- RISING (risk building) ---------':^44}  {'--------- FALLING (risk receding) ---------':^44}")
    print(f"{'Score':>8}  {'N':>4} {'Mean':>7} {'Median':>7} {'%Neg':>5} {'>=10%DD':>8}  {'N':>4} {'Mean':>7} {'Median':>7} {'%Neg':>5} {'>=10%DD':>8}")
    print("-" * 100)

    rising_data = {}
    falling_data = {}

    for lo in SCORE_BUCKETS:
        rising = _collect_bucket(data, lo, "fwd_12m", lambda r: r["score_rising"])
        falling = _collect_bucket(data, lo, "fwd_12m", lambda r: not r["score_rising"])
        dd_r = _collect_bucket(data, lo, "max_dd_12m", lambda r: r["score_rising"])
        dd_f = _collect_bucket(data, lo, "max_dd_12m", lambda r: not r["score_rising"])

        if not rising and not falling:
            continue

        def _fmt(vals, dd_vals):
            if not vals:
                return f"{'':>4} {'':>7} {'':>7} {'':>5} {'':>8}"
            dd10 = sum(1 for v in dd_vals if v <= -10) / len(dd_vals) * 100 if dd_vals else 0
            return (f"{len(vals):>4} {_mean(vals):>+6.1f}% {_median(vals):>+6.1f}%"
                    f" {_pct_neg(vals):>4.0f}% {dd10:>6.1f}%")

        print(f" {_bucket_label(lo):>7}  {_fmt(rising, dd_r)}  {_fmt(falling, dd_f)}")

        if rising:
            rising_data[lo] = {"med": _median(rising), "n": len(rising),
                               "dd10": sum(1 for v in dd_r if v <= -10) / len(dd_r) * 100 if dd_r else 0}
        if falling:
            falling_data[lo] = {"med": _median(falling), "n": len(falling),
                                "dd10": sum(1 for v in dd_f if v <= -10) / len(dd_f) * 100 if dd_f else 0}

    return rising_data, falling_data


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
    for thr in CROSSING_THRESHOLDS:
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
# Analysis 4: Individual signal predictive power
# =========================================================================

def analyze_individual_signals(data):
    print(f"\n{SEPARATOR}")
    print("ANALYSIS 4: Individual Signal Predictive Power (Signal >= 50 predicts 10%+ DD)")
    print(SEPARATOR)

    valid = [r for r in data if r["max_dd_12m"] is not None]
    total_pos = sum(1 for r in valid if r["max_dd_12m"] <= -10)
    base_rate = total_pos / len(valid) * 100 if valid else 0

    print(f"\nBase rate of 10%+ drawdown: {base_rate:.1f}% ({total_pos}/{len(valid)} months)")
    print(f"\n{'Signal':<22}{'TP Rate':>9}{'FP Rate':>9}{'Precision':>11}{'Lift':>7}")
    print("-" * 58)

    roc_data = {}
    all_signals = list(SIGNAL_KEYS) + [("score", "Composite")]

    for key, label in all_signals:
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

        roc_points = []
        for t in ROC_THRESHOLDS:
            t_tp = sum(1 for r in valid if r[key] >= t and r["max_dd_12m"] <= -10)
            t_fp = sum(1 for r in valid if r[key] >= t and r["max_dd_12m"] > -10)
            t_fn = sum(1 for r in valid if r[key] < t and r["max_dd_12m"] <= -10)
            t_tn = sum(1 for r in valid if r[key] < t and r["max_dd_12m"] > -10)
            t_tpr = t_tp / (t_tp + t_fn) if (t_tp + t_fn) else 0
            t_fpr = t_fp / (t_fp + t_tn) if (t_fp + t_tn) else 0
            roc_points.append((t_fpr, t_tpr))
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

    scores = [r["score"] for r in data]
    print(f"\nScore range:  {min(scores):.1f} - {max(scores):.1f}")
    print(f"Score mean:   {_mean(scores):.1f}")
    print(f"Score median: {_median(scores):.1f}")

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

def generate_chart(data, bucket_data, rising_data, falling_data, roc_data):
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(20, 16), facecolor=BG)
    fig.suptitle("Regime Dashboard Backtest -- Historical Return Profile by Score Level (1980-2026)",
                 color="white", fontsize=16, fontweight="bold", y=0.97)

    # Shared x-axis data for score-level panels
    buckets_with_data = sorted(bucket_data.keys())
    x_labels = [_bucket_label(b) for b in buckets_with_data]
    x_pos = list(range(len(buckets_with_data)))

    # -----------------------------------------------------------------
    # Panel 1 (top-left): Median forward returns by score level
    # -----------------------------------------------------------------
    ax1 = fig.add_axes([0.06, 0.55, 0.42, 0.36])
    ax1.set_facecolor(PANEL_BG)

    bar_w = 0.35
    med6 = [bucket_data[b]["fwd6_med"] for b in buckets_with_data]
    med12 = [bucket_data[b]["fwd12_med"] for b in buckets_with_data]

    ax1.bar([x - bar_w / 2 for x in x_pos], med6, bar_w * 0.9,
            color="#3b82f6", label="6-month", alpha=0.85)
    ax1.bar([x + bar_w / 2 for x in x_pos], med12, bar_w * 0.9,
            color="#f59e0b", label="12-month", alpha=0.85)

    # Sample size annotations
    for i, b in enumerate(buckets_with_data):
        n = bucket_data[b]["n"]
        ax1.text(i, max(med6[i], med12[i]) + 0.8, f"n={n}",
                 ha="center", fontsize=7, color="#6b7280")

    ax1.axhline(0, color=GRID_COLOR, linewidth=1)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(x_labels, color=TEXT_COLOR, fontsize=8)
    ax1.set_xlabel("Composite Score", color=TEXT_COLOR, fontsize=10)
    ax1.set_ylabel("Median Forward Return (%)", color=TEXT_COLOR, fontsize=10)
    ax1.set_title("Median Forward S&P 500 Return by Score Level", color="white", fontsize=12)
    ax1.legend(fontsize=9, loc="upper right")
    ax1.tick_params(colors=TEXT_COLOR)
    ax1.grid(axis="y", color=GRID_COLOR, alpha=0.5)

    # -----------------------------------------------------------------
    # Panel 2 (top-right): DD rate by score level
    # -----------------------------------------------------------------
    ax2 = fig.add_axes([0.56, 0.55, 0.42, 0.36])
    ax2.set_facecolor(PANEL_BG)

    dd10_vals = [bucket_data[b]["dd10"] for b in buckets_with_data]
    dd20_vals = [bucket_data[b]["dd20"] for b in buckets_with_data]

    ax2.bar([x - bar_w / 2 for x in x_pos], dd10_vals, bar_w * 0.9,
            color="#ef4444", label=">=10% DD", alpha=0.85)
    ax2.bar([x + bar_w / 2 for x in x_pos], dd20_vals, bar_w * 0.9,
            color="#8b5cf6", label=">=20% DD", alpha=0.85)

    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(x_labels, color=TEXT_COLOR, fontsize=8)
    ax2.set_xlabel("Composite Score", color=TEXT_COLOR, fontsize=10)
    ax2.set_ylabel("% of Months", color=TEXT_COLOR, fontsize=10)
    ax2.set_title("12-Month Forward Drawdown Rate by Score Level", color="white", fontsize=12)
    ax2.legend(fontsize=9, loc="upper left")
    ax2.tick_params(colors=TEXT_COLOR)
    ax2.grid(axis="y", color=GRID_COLOR, alpha=0.5)

    # -----------------------------------------------------------------
    # Panel 3 (bottom-left): Momentum split — median 12m return
    # -----------------------------------------------------------------
    ax3 = fig.add_axes([0.06, 0.06, 0.42, 0.36])
    ax3.set_facecolor(PANEL_BG)

    # Rising data
    r_buckets = sorted(rising_data.keys())
    r_x, r_med = [], []
    for b in r_buckets:
        if b in [buckets_with_data[i] for i in range(len(buckets_with_data))]:
            r_x.append(buckets_with_data.index(b))
            r_med.append(rising_data[b]["med"])

    f_buckets = sorted(falling_data.keys())
    f_x, f_med = [], []
    for b in f_buckets:
        if b in [buckets_with_data[i] for i in range(len(buckets_with_data))]:
            f_x.append(buckets_with_data.index(b))
            f_med.append(falling_data[b]["med"])

    ax3.plot(r_x, r_med, color="#ef4444", linewidth=2, marker="o", markersize=6,
             label="Rising (risk building)", alpha=0.9)
    ax3.plot(f_x, f_med, color="#10b981", linewidth=2, marker="s", markersize=6,
             label="Falling (risk receding)", alpha=0.9)

    ax3.axhline(0, color=GRID_COLOR, linewidth=1)
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(x_labels, color=TEXT_COLOR, fontsize=8)
    ax3.set_xlabel("Composite Score", color=TEXT_COLOR, fontsize=10)
    ax3.set_ylabel("Median 12-Month Return (%)", color=TEXT_COLOR, fontsize=10)
    ax3.set_title("Forward Return by Score Level + Momentum Direction", color="white", fontsize=12)
    ax3.legend(fontsize=9, loc="upper right")
    ax3.tick_params(colors=TEXT_COLOR)
    ax3.grid(color=GRID_COLOR, alpha=0.3)

    # -----------------------------------------------------------------
    # Panel 4 (bottom-right): ROC curves
    # -----------------------------------------------------------------
    ax4 = fig.add_axes([0.56, 0.06, 0.42, 0.36])
    ax4.set_facecolor(PANEL_BG)

    ax4.plot([0, 1], [0, 1], color="#4b5563", linestyle="--", linewidth=1,
             label="Random", alpha=0.6)

    for idx, (key, label) in enumerate(SIGNAL_KEYS):
        pts = roc_data.get(key, [])
        if pts:
            ax4.plot([p[0] for p in pts], [p[1] for p in pts],
                     color=SIGNAL_COLORS[idx], linewidth=1.5, alpha=0.8, label=label)

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
    bucket_data = analyze_forward_returns(data)
    rising_data, falling_data = analyze_momentum_split(data)
    analyze_threshold_timing(data)
    roc_data = analyze_individual_signals(data)
    print_summary(data)
    generate_chart(data, bucket_data, rising_data, falling_data, roc_data)
    print(f"\nChart saved: backtest_results.png")


if __name__ == "__main__":
    main()
