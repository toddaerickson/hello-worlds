"""Streamlit frontend for the Market Topping Regime Dashboard.

Run: streamlit run streamlit_app.py
Deploy: Push to GitHub, connect to Streamlit Cloud (free for public repos).
"""

import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from regime_dashboard.dashboard import run_dashboard_manual
from regime_dashboard.historical_scores import compute_historical_scores

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Market Topping Regime Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar: Signal Inputs
# ---------------------------------------------------------------------------
st.sidebar.title("Signal Inputs")
st.sidebar.markdown("Adjust values to run scenarios. Defaults approximate April 2026.")

with st.sidebar.expander("Signal 1: Breadth Divergence & Concentration", expanded=False):
    pct_above_200dma = st.slider("% Stocks Above 200d MA", 5, 95, 52)
    ad_trend = st.selectbox("A/D Line Trend", ["rising", "flat", "declining"], index=1)
    highs_lows = st.slider("New Highs / New Lows Ratio", 0.2, 10.0, 1.5, 0.1)
    top10_conc = st.slider("Top-10 Concentration (% of 6mo return)", 20, 90, 68)

with st.sidebar.expander("Signal 2: Valuation", expanded=False):
    pe = st.slider("P/E Ratio", 10.0, 40.0, 23.0, 0.5)
    cape = st.slider("CAPE (Shiller P/E)", 10.0, 50.0, 33.0, 0.5)
    ev_ebitda = st.slider("EV/EBITDA", 8.0, 22.0, 15.0, 0.5)

with st.sidebar.expander("Signal 3: Credit Complacency", expanded=False):
    st.caption("Primary: CCC-BB spread (risk appetite)")
    ccc_bb_bps = st.slider("CCC-BB Spread (bps)", 200, 2000, 480, 10)
    ccc_bb_pctile = st.slider("CCC-BB Percentile (lower=tighter)", 0, 100, 15)
    st.caption("Secondary: Single-B OAS (absolute stress)")
    single_b_bps = st.slider("Single-B OAS (bps)", 150, 1500, 260, 10)
    single_b_pctile = st.slider("Single-B Percentile (lower=tighter)", 0, 100, 12)
    single_b_3mo = st.slider("Single-B 3mo Change (bps)", -200, 500, -10, 5)
    st.caption("Tertiary: IG confirmation")
    ig_spread = st.slider("IG OAS Spread (bps)", 40, 300, 90, 5)

with st.sidebar.expander("Signal 4: Sentiment Extremes", expanded=False):
    aaii = st.slider("AAII Bull-Bear Spread", -40.0, 50.0, 18.0, 1.0)
    vix = st.slider("VIX", 8.0, 50.0, 14.0, 0.5)
    put_call = st.slider("Put/Call Ratio", 0.4, 1.5, 0.82, 0.01)
    fear_greed = st.slider("CNN Fear & Greed Index", 0, 100, 68)

with st.sidebar.expander("Signal 5: Macro Deterioration", expanded=False):
    lei_yoy = st.slider("LEI YoY Change (%)", -10.0, 10.0, -1.5, 0.5)
    lei_mom = st.slider("LEI MoM Change (%)", -2.0, 2.0, -0.3, 0.1)
    private_lei = st.slider("Private LEI YoY (ex-govt) (%)", -10.0, 10.0, -3.0, 0.5)
    ism = st.slider("ISM Manufacturing PMI", 30.0, 65.0, 48.5, 0.5)

with st.sidebar.expander("Signal 6: Margin Debt / Leverage", expanded=False):
    margin_yoy = st.slider("Margin Debt YoY (%)", -20.0, 50.0, 18.0, 1.0)
    margin_gdp = st.slider("Margin Debt / GDP (%)", 1.0, 5.0, 2.8, 0.1)
    margin_pctile = st.slider("Margin Debt Percentile", 0, 100, 78)

with st.sidebar.expander("Signal 7: Term Premium / Fiscal Stress", expanded=False):
    spread_2s10s = st.slider("2s10s Spread (bps)", -150, 300, 110, 5)
    tp_10y = st.slider("10y Term Premium (%)", -1.0, 2.5, 0.85, 0.05)
    tp_5y_avg = st.slider("Term Premium 5y Avg (%)", -0.5, 1.5, 0.20, 0.05)
    deficit_gdp = st.slider("Deficit / GDP (%)", 0.0, 15.0, 6.5, 0.5)
    debt_svc = st.slider("Debt Service / Revenue (%)", 5.0, 35.0, 22.0, 1.0)
    fed_cutting = st.checkbox("Fed in Cutting Cycle", value=True)

with st.sidebar.expander("Fiscal Dominance Flag Inputs", expanded=False):
    in_recession = st.checkbox("Economy in Recession", value=False)
    core_pce = st.slider("Core PCE YoY (%)", 0.5, 8.0, 2.8, 0.1)
    tp_rising = st.checkbox("Term Premium Rising (3mo trend)", value=True)

# ---------------------------------------------------------------------------
# Run the dashboard
# ---------------------------------------------------------------------------
assessment = run_dashboard_manual(
    pct_above_200dma=pct_above_200dma,
    advance_decline_line_trend=ad_trend,
    new_highs_vs_new_lows=highs_lows,
    top_10_concentration_pct=top10_conc,
    pe_ratio=pe, cape_ratio=cape, ev_ebitda=ev_ebitda,
    ccc_bb_spread_bps=ccc_bb_bps, ccc_bb_spread_percentile=ccc_bb_pctile,
    single_b_oas_bps=single_b_bps, single_b_oas_percentile=single_b_pctile,
    single_b_oas_3mo_change_bps=single_b_3mo, ig_spread_bps=ig_spread,
    aaii_bull_bear_spread=aaii, vix=vix, put_call_ratio=put_call, fear_greed_index=fear_greed,
    lei_yoy_change=lei_yoy, lei_monthly_change=lei_mom,
    private_lei_yoy_change=private_lei, ism_manufacturing=ism,
    margin_debt_yoy_pct=margin_yoy, margin_debt_to_gdp=margin_gdp,
    margin_debt_percentile=margin_pctile,
    spread_2s10s_bps=spread_2s10s, term_premium_10y=tp_10y,
    term_premium_5y_avg=tp_5y_avg, deficit_pct_gdp=deficit_gdp,
    debt_service_pct_revenue=debt_svc, fed_cutting=fed_cutting,
    in_recession=in_recession, interest_pct_revenue=debt_svc,
    fed_funds_rate_declining=fed_cutting, core_pce_yoy=core_pce,
    term_premium_rising=tp_rising,
)

data = assessment.to_dict()

# ---------------------------------------------------------------------------
# Header: Regime gauge
# ---------------------------------------------------------------------------
st.title("Market Topping Regime Dashboard")

level_colors = {
    "low": "#22c55e",
    "moderate": "#84cc16",
    "elevated": "#eab308",
    "high": "#f97316",
    "extreme": "#ef4444",
}
level = data["regime_level"]
color = level_colors.get(level, "#6b7280")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown(
        f'<div style="background:#111827;border:2px solid {color};border-radius:12px;'
        f'padding:24px;text-align:center">'
        f'<div style="font-size:3rem;font-weight:bold;color:{color}">'
        f'{data["adjusted_composite_score"]:.0f}</div>'
        f'<div style="font-size:1.2rem;color:{color};text-transform:uppercase;'
        f'letter-spacing:2px;font-weight:600">{level}</div>'
        f'<div style="font-size:0.8rem;color:#6b7280;margin-top:4px">'
        f'Raw: {data["raw_composite_score"]:.0f}'
        f'{" + " + str(data["fiscal_dominance_modifier"]) + " FD modifier" if data["fiscal_dominance_active"] else ""}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

with col2:
    fd_status = "🟣 ACTIVE" if data["fiscal_dominance_active"] else "⚪ Inactive"
    st.metric("Fiscal Dominance Flag", fd_status)
    st.metric("Conditions Met", f'{data["fiscal_dominance_conditions_met"]} / 4')

with col3:
    signal_count = len(data["signals"])
    extreme_count = sum(1 for s in data["signals"] if s["level"] == "extreme")
    high_count = sum(1 for s in data["signals"] if s["level"] == "high")
    st.metric("Signals", signal_count)
    st.metric("Extreme / High", f"{extreme_count} / {high_count}")

# Warnings
for warning in data["warnings"]:
    st.warning(warning)

# ---------------------------------------------------------------------------
# Signal breakdown
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Signal Breakdown")

signal_colors = {
    "Breadth Divergence": "#3b82f6",
    "Valuation": "#ef4444",
    "Credit Complacency": "#f59e0b",
    "Sentiment Extremes": "#10b981",
    "Macro Deterioration": "#8b5cf6",
    "Margin Debt / Leverage": "#ec4899",
    "Term Premium / Fiscal Stress": "#06b6d4",
}

cols = st.columns(len(data["signals"]))
for i, sig in enumerate(data["signals"]):
    with cols[i]:
        sig_color = signal_colors.get(sig["name"], "#6b7280")
        sig_level_color = level_colors.get(sig["level"], "#6b7280")

        st.markdown(
            f'<div style="background:#111827;border-radius:8px;padding:12px;'
            f'border-left:4px solid {sig_color};min-height:140px">'
            f'<div style="font-size:0.75rem;color:#9ca3af;margin-bottom:4px">'
            f'S{i+1}</div>'
            f'<div style="font-size:1.8rem;font-weight:bold;color:{sig_level_color}">'
            f'{sig["score"]}</div>'
            f'<div style="font-size:0.7rem;color:{sig_level_color};text-transform:uppercase">'
            f'{sig["level"]}</div>'
            f'<div style="font-size:0.65rem;color:#6b7280;margin-top:6px">'
            f'{sig["name"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Signal details table
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Signal Details")

for sig in data["signals"]:
    with st.expander(f'{sig["name"]} — Score: {sig["score"]} ({sig["level"].upper()})'):
        st.markdown(f'**Interpretation:** {sig["interpretation"]}')
        if sig.get("fiscal_dominance_note"):
            st.info(f'**Under Fiscal Dominance:** {sig["fiscal_dominance_note"]}')

        if sig["components"]:
            comp_cols = st.columns(min(len(sig["components"]), 4))
            for j, (k, v) in enumerate(sig["components"].items()):
                with comp_cols[j % len(comp_cols)]:
                    display_val = f"{v:.2f}" if isinstance(v, float) else str(v)
                    st.metric(k, display_val)

# ---------------------------------------------------------------------------
# Fiscal Dominance Flag details
# ---------------------------------------------------------------------------
if data["fiscal_dominance_details"]:
    st.markdown("---")
    st.subheader("Fiscal Dominance Flag — Condition Details")

    fd_cols = st.columns(len(data["fiscal_dominance_details"]))
    for i, (cond_name, cond_detail) in enumerate(data["fiscal_dominance_details"].items()):
        with fd_cols[i]:
            met = cond_detail.get("met", False)
            icon = "✅" if met else "❌"
            st.markdown(
                f'<div style="background:#111827;border-radius:8px;padding:12px;'
                f'border:1px solid {"#7c3aed" if met else "#374151"}">'
                f'<div style="font-size:1.2rem">{icon}</div>'
                f'<div style="font-size:0.75rem;color:#9ca3af;margin-top:4px">'
                f'{cond_name.replace("_", " ").title()}</div></div>',
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# Historical chart
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Historical Regime Score (1980–2026)")

hist_data = compute_historical_scores()

df = pd.DataFrame(hist_data)
df["date"] = pd.to_datetime(df["date"])
df = df.set_index("date")

# Main score chart
chart_tab1, chart_tab2 = st.tabs(["Composite Score", "Signal Breakdown"])

with chart_tab1:
    events_main = [
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

    fig, ax = plt.subplots(figsize=(16, 6), facecolor="#0a0e17")
    ax.set_facecolor("#0a0e17")

    x = np.arange(len(df))
    scores_arr = df["score"].values
    raw_arr = df["raw_score"].values
    spx_arr = df["spx"].values
    fd_arr = df["fd_active"].values
    date_strs = [d.strftime("%Y-%m") for d in df.index]

    # Zone bands
    ax.axhspan(80, 100, color="#ef4444", alpha=0.08, zorder=0)
    ax.axhspan(60, 80, color="#fbbf24", alpha=0.05, zorder=0)

    # Fiscal dominance shading
    fd_start = None
    for i, active in enumerate(fd_arr):
        if active and fd_start is None:
            fd_start = i
        if (not active or i == len(fd_arr) - 1) and fd_start is not None:
            ax.axvspan(fd_start, i, color="#7c3aed", alpha=0.12, zorder=1)
            fd_start = None

    # S&P 500 overlay (secondary y-axis, log scale)
    ax_spx = ax.twinx()
    ax_spx.set_facecolor("none")
    ax_spx.plot(x, spx_arr, color="#ffffff", linewidth=1.0, alpha=0.35, zorder=2)
    ax_spx.set_yscale("log")
    ax_spx.set_ylim(100, 8000)
    ax_spx.set_ylabel("S&P 500 (log scale)", fontsize=10, color="#6b7280")
    ax_spx.tick_params(axis="y", colors="#4b5563", labelsize=8)
    for spine in ax_spx.spines.values():
        spine.set_color("#1f2937")

    # Regime score lines
    ax.plot(x, raw_arr, color="#f59e0b", alpha=0.25, linewidth=1,
            linestyle="--", label="Raw Score", zorder=3)
    ax.plot(x, scores_arr, color="#f59e0b", linewidth=2.2,
            label="Adjusted Score", zorder=4)
    ax.fill_between(x, 0, scores_arr, color="#f59e0b", alpha=0.08, zorder=2)

    # Event annotations
    for evt_idx, (evt_date, evt_label, evt_color) in enumerate(events_main):
        if evt_date in date_strs:
            idx = date_strs.index(evt_date)
            ax.axvline(idx, color=evt_color, linewidth=0.8, linestyle=":",
                       alpha=0.6, zorder=2)
            y_pos = 95 if evt_idx % 2 == 0 else 88
            ax.annotate(evt_label, xy=(idx, y_pos), fontsize=7,
                        color=evt_color, ha="center", va="top",
                        fontweight="bold", zorder=5)

    # Zone labels
    ax.text(len(x) - 2, 90, "EXTREME", fontsize=8, color="#ef4444",
            alpha=0.5, ha="right", va="center")
    ax.text(len(x) - 2, 70, "HIGH", fontsize=8, color="#fbbf24",
            alpha=0.5, ha="right", va="center")

    ax.set_ylim(0, 100)
    ax.set_xlim(0, len(x) - 1)
    ax.set_ylabel("Regime Score (0-100)", fontsize=11, color="#9ca3af")

    # X-axis ticks
    tick_pos = [i for i, d in enumerate(date_strs)
                if d.endswith("-01") and int(d[:4]) % 4 == 0]
    tick_lbl = [date_strs[i][:4] for i in tick_pos]
    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_lbl, fontsize=9, color="#6b7280")
    ax.tick_params(axis="y", colors="#6b7280", labelsize=9)
    ax.grid(axis="y", color="#1f2937", linewidth=0.5)
    ax.grid(axis="x", color="#1f2937", linewidth=0.3)

    # Legend
    handles = [
        plt.Line2D([0], [0], color="#f59e0b", linewidth=2, label="Adjusted Score"),
        plt.Line2D([0], [0], color="#f59e0b", linewidth=1, linestyle="--",
                    alpha=0.4, label="Raw Score"),
        plt.Line2D([0], [0], color="#ffffff", linewidth=1, alpha=0.35,
                    label="S&P 500 (log, right axis)"),
        mpatches.Patch(facecolor="#7c3aed", alpha=0.25,
                       label="Fiscal Dominance Active"),
        mpatches.Patch(facecolor="#ef4444", alpha=0.15,
                       label="Extreme Zone (80+)"),
        mpatches.Patch(facecolor="#fbbf24", alpha=0.1,
                       label="High Zone (60-80)"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8,
              facecolor="#111827", edgecolor="#1f2937", labelcolor="#9ca3af")

    ax.set_title(
        "Market Topping Regime Score — 7-Signal Composite with Fiscal Dominance Modifier\n"
        "Monthly · Jan 1980 – Mar 2026",
        fontsize=13, color="#f9fafb", pad=15, fontweight="bold",
    )

    for spine in ax.spines.values():
        spine.set_color("#1f2937")

    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # FD periods annotation
    fd_periods = df[df["fd_active"]].index
    if len(fd_periods) > 0:
        st.caption(
            f"Fiscal Dominance active: {fd_periods[0].strftime('%b %Y')} – "
            f"{fd_periods[-1].strftime('%b %Y')}"
        )

with chart_tab2:
    signal_rename = {
        "s1_breadth": "Breadth & Concentration",
        "s2_valuation": "Valuation",
        "s3_credit": "Credit",
        "s4_sentiment": "Sentiment",
        "s5_macro": "Macro",
        "s6_leverage": "Leverage",
        "s7_term_premium": "Term Premium",
    }
    signal_colors_chart = {
        "Breadth & Concentration": "#3b82f6",
        "Valuation": "#ef4444",
        "Credit": "#f59e0b",
        "Sentiment": "#10b981",
        "Macro": "#8b5cf6",
        "Leverage": "#ec4899",
        "Term Premium": "#06b6d4",
    }
    signal_df = df[list(signal_rename.keys())].rename(columns=signal_rename)
    selected = st.multiselect(
        "Select signals to display",
        signal_df.columns.tolist(),
        default=["Breadth & Concentration", "Term Premium", "Credit"],
    )
    if selected:
        fig2, ax2 = plt.subplots(figsize=(14, 5), facecolor="#0a0e17")
        ax2.set_facecolor("#0a0e17")
        x2 = np.arange(len(signal_df))
        for col in selected:
            ax2.plot(x2, signal_df[col].values, color=signal_colors_chart.get(col, "#9ca3af"),
                     linewidth=1.5, label=col)
        ax2.set_ylim(0, 100)
        ax2.set_xlim(0, len(x2) - 1)
        ax2.set_ylabel("Signal Score (0-100)", fontsize=9, color="#9ca3af")
        date_strs2 = [d.strftime("%Y-%m") for d in signal_df.index]
        tp2 = [i for i, d in enumerate(date_strs2) if d.endswith("-01") and int(d[:4]) % 4 == 0]
        tl2 = [date_strs2[i][:4] for i in tp2]
        ax2.set_xticks(tp2)
        ax2.set_xticklabels(tl2, fontsize=8, color="#6b7280")
        ax2.tick_params(axis="y", colors="#6b7280", labelsize=8)
        ax2.grid(axis="y", color="#1f2937", linewidth=0.5)
        ax2.grid(axis="x", color="#1f2937", linewidth=0.3)
        ax2.legend(loc="upper left", fontsize=7, facecolor="#111827",
                   edgecolor="#1f2937", labelcolor="#9ca3af")
        for spine in ax2.spines.values():
            spine.set_color("#1f2937")
        fig2.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Market Topping Regime Dashboard · 7-Signal Composite with Fiscal Dominance Modifier · "
    "[GitHub](https://github.com/toddaerickson/hello-worlds)"
)
