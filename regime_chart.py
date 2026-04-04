"""Generate a static PNG chart of historical regime scores."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from regime_dashboard.historical_scores import compute_historical_scores


def generate_png(output_path="regime_chart.png"):
    data = compute_historical_scores()
    dates = [d["date"] for d in data]
    scores = [d["score"] for d in data]
    raw_scores = [d["raw_score"] for d in data]
    fd_active = [d["fd_active"] for d in data]

    signal_keys = [
        ("s1_breadth", "Breadth & Concentration", "#3b82f6"),
        ("s2_valuation", "Valuation", "#ef4444"),
        ("s3_credit", "Credit Complacency", "#f59e0b"),
        ("s4_sentiment", "Sentiment", "#10b981"),
        ("s5_macro", "Macro (LEI/ISM)", "#8b5cf6"),
        ("s6_leverage", "Leverage", "#ec4899"),
        ("s7_term_premium", "Term Premium / Fiscal Stress", "#06b6d4"),
    ]

    spx_prices = [d["spx"] for d in data]

    events = [
        ("1981-06", "Volcker\nPeak", "#e67e22"),
        ("1987-10", "Black\nMonday", "#e74c3c"),
        ("1990-07", "Gulf War\nRecession", "#e74c3c"),
        ("1998-08", "LTCM\nCrisis", "#e67e22"),
        ("2000-03", "Dot-com\nPeak", "#e74c3c"),
        ("2001-09", "9/11", "#e74c3c"),
        ("2007-10", "GFC\nBegins", "#e74c3c"),
        ("2008-09", "Lehman", "#e74c3c"),
        ("2009-03", "Market\nBottom", "#27ae60"),
        ("2018-12", "Fed\nPivot", "#e67e22"),
        ("2020-03", "COVID\nCrash", "#e74c3c"),
        ("2021-11", "Peak\nBubble", "#e74c3c"),
        ("2022-01", "Rate Hikes\nBegin", "#e67e22"),
        ("2025-01", "Fiscal\nDominance", "#9b59b6"),
    ]

    # Use dark theme
    plt.style.use("dark_background")

    fig = plt.figure(figsize=(20, 16), facecolor="#0a0e17")

    # --- Main chart (top) ---
    ax_main = fig.add_axes([0.06, 0.52, 0.88, 0.42])
    ax_main.set_facecolor("#0a0e17")

    x = range(len(dates))

    # Zone bands
    ax_main.axhspan(80, 100, color="#ef4444", alpha=0.08, zorder=0)
    ax_main.axhspan(60, 80, color="#fbbf24", alpha=0.05, zorder=0)

    # Fiscal dominance shading
    fd_start = None
    for i, active in enumerate(fd_active):
        if active and fd_start is None:
            fd_start = i
        if (not active or i == len(fd_active) - 1) and fd_start is not None:
            ax_main.axvspan(fd_start, i, color="#7c3aed", alpha=0.12, zorder=1)
            fd_start = None

    # S&P 500 overlay (secondary y-axis, log scale)
    ax_spx = ax_main.twinx()
    ax_spx.set_facecolor("none")
    ax_spx.plot(x, spx_prices, color="#ffffff", linewidth=1.0, alpha=0.35,
                label="S&P 500", zorder=2)
    ax_spx.set_yscale("log")
    ax_spx.set_ylim(100, 8000)
    ax_spx.set_ylabel("S&P 500 (log scale)", fontsize=10, color="#6b7280")
    ax_spx.tick_params(axis="y", colors="#4b5563", labelsize=8)
    for spine in ax_spx.spines.values():
        spine.set_color("#1f2937")

    # Plot lines
    ax_main.plot(x, raw_scores, color="#f59e0b", alpha=0.25, linewidth=1,
                 linestyle="--", label="Raw Score", zorder=3)
    ax_main.plot(x, scores, color="#f59e0b", linewidth=2.2, label="Adjusted Score", zorder=4)
    ax_main.fill_between(x, 0, scores, color="#f59e0b", alpha=0.08, zorder=2)

    # Event annotations
    for evt_date, evt_label, evt_color in events:
        if evt_date in dates:
            idx = dates.index(evt_date)
            ax_main.axvline(idx, color=evt_color, linewidth=0.8, linestyle=":", alpha=0.6, zorder=2)
            y_pos = 95 if events.index((evt_date, evt_label, evt_color)) % 2 == 0 else 88
            ax_main.annotate(evt_label, xy=(idx, y_pos), fontsize=7,
                           color=evt_color, ha="center", va="top",
                           fontweight="bold", zorder=5)

    # Zone labels
    ax_main.text(len(x) - 2, 90, "EXTREME", fontsize=8, color="#ef4444",
                alpha=0.5, ha="right", va="center")
    ax_main.text(len(x) - 2, 70, "HIGH", fontsize=8, color="#fbbf24",
                alpha=0.5, ha="right", va="center")

    ax_main.set_ylim(0, 100)
    ax_main.set_xlim(0, len(x) - 1)
    ax_main.set_ylabel("Regime Score (0-100)", fontsize=11, color="#9ca3af")

    # X-axis: show year labels
    tick_positions = []
    tick_labels = []
    for i, d in enumerate(dates):
        if d.endswith("-01") and int(d[:4]) % 4 == 0:
            tick_positions.append(i)
            tick_labels.append(d[:4])
    ax_main.set_xticks(tick_positions)
    ax_main.set_xticklabels(tick_labels, fontsize=9, color="#6b7280")
    ax_main.tick_params(axis="y", colors="#6b7280", labelsize=9)
    ax_main.grid(axis="y", color="#1f2937", linewidth=0.5)
    ax_main.grid(axis="x", color="#1f2937", linewidth=0.3)

    # Legend
    handles = [
        plt.Line2D([0], [0], color="#f59e0b", linewidth=2, label="Adjusted Score"),
        plt.Line2D([0], [0], color="#f59e0b", linewidth=1, linestyle="--", alpha=0.4, label="Raw Score"),
        plt.Line2D([0], [0], color="#ffffff", linewidth=1, alpha=0.35, label="S&P 500 (log, right axis)"),
        mpatches.Patch(facecolor="#7c3aed", alpha=0.25, label="Fiscal Dominance Active"),
        mpatches.Patch(facecolor="#ef4444", alpha=0.15, label="Extreme Zone (80+)"),
        mpatches.Patch(facecolor="#fbbf24", alpha=0.1, label="High Zone (60-80)"),
    ]
    ax_main.legend(handles=handles, loc="upper left", fontsize=8,
                  facecolor="#111827", edgecolor="#1f2937", labelcolor="#9ca3af")

    ax_main.set_title("Market Topping Regime Score — 7-Signal Composite with Fiscal Dominance Modifier\n"
                      "Monthly · Jan 1980 – Mar 2026",
                      fontsize=14, color="#f9fafb", pad=15, fontweight="bold")

    # Spines
    for spine in ax_main.spines.values():
        spine.set_color("#1f2937")

    # --- Signal sub-charts (bottom 2 rows) ---
    n_signals = len(signal_keys) + 1  # +1 for FD conditions
    cols = 4
    rows = 2
    sub_w = 0.88 / cols
    sub_h = 0.18
    x_start = 0.06
    y_starts = [0.27, 0.05]

    for i, (key, label, color) in enumerate(signal_keys):
        row = i // cols
        col = i % cols
        ax = fig.add_axes([x_start + col * sub_w + 0.01, y_starts[row], sub_w - 0.02, sub_h])
        ax.set_facecolor("#111827")

        values = [d[key] for d in data]
        ax.fill_between(x, 0, values, color=color, alpha=0.15)
        ax.plot(x, values, color=color, linewidth=1.2)
        ax.set_ylim(0, 100)
        ax.set_xlim(0, len(x) - 1)
        ax.set_title(label, fontsize=8, color="#9ca3af", pad=4)
        ax.tick_params(axis="both", labelsize=7, colors="#6b7280")

        # Minimal x ticks
        sparse_ticks = [j for j, d in enumerate(dates) if d.endswith("-01") and int(d[:4]) % 4 == 0]
        sparse_labels = [dates[j][:4] for j in sparse_ticks]
        ax.set_xticks(sparse_ticks)
        ax.set_xticklabels(sparse_labels, fontsize=6, color="#6b7280")
        ax.set_yticks([0, 50, 100])
        ax.grid(axis="y", color="#1f2937", linewidth=0.3)
        for spine in ax.spines.values():
            spine.set_color("#1f2937")

    # FD conditions chart (last slot)
    fd_conditions = [d["fd_conditions"] for d in data]
    row = len(signal_keys) // cols
    col = len(signal_keys) % cols
    ax_fd = fig.add_axes([x_start + col * sub_w + 0.01, y_starts[row], sub_w - 0.02, sub_h])
    ax_fd.set_facecolor("#111827")
    bar_colors = ["#7c3aed" if c >= 3 else "#374151" for c in fd_conditions]
    ax_fd.bar(x, fd_conditions, color=bar_colors, width=1.0)
    ax_fd.axhline(3, color="#a855f7", linewidth=0.8, linestyle="--", alpha=0.7)
    ax_fd.set_ylim(0, 4.5)
    ax_fd.set_xlim(0, len(x) - 1)
    ax_fd.set_title("FD Conditions Met (of 4)", fontsize=8, color="#9ca3af", pad=4)
    ax_fd.tick_params(axis="both", labelsize=7, colors="#6b7280")
    sparse_ticks = [j for j, d in enumerate(dates) if d.endswith("-01") and int(d[:4]) % 4 == 0]
    sparse_labels = [dates[j][:4] for j in sparse_ticks]
    ax_fd.set_xticks(sparse_ticks)
    ax_fd.set_xticklabels(sparse_labels, fontsize=6, color="#6b7280")
    ax_fd.set_yticks([0, 1, 2, 3, 4])
    ax_fd.grid(axis="y", color="#1f2937", linewidth=0.3)
    for spine in ax_fd.spines.values():
        spine.set_color("#1f2937")

    fig.savefig(output_path, dpi=150, facecolor="#0a0e17", bbox_inches="tight")
    plt.close(fig)
    return output_path


if __name__ == "__main__":
    path = generate_png()
    print(f"Chart saved: {path}")
