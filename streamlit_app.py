"""Streamlit frontend for the Market Topping Regime Dashboard.

Run: streamlit run streamlit_app.py
Deploy: Push to GitHub, connect to Streamlit Cloud (free for public repos).
"""

import streamlit as st
import pandas as pd

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
    hy_spread = st.slider("HY OAS Spread (bps)", 150, 1200, 320, 10)
    ig_spread = st.slider("IG OAS Spread (bps)", 40, 300, 90, 5)
    hy_pctile = st.slider("HY Spread Percentile (lower=tighter)", 0, 100, 15)

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
    hy_spread_bps=hy_spread, ig_spread_bps=ig_spread, hy_spread_percentile=hy_pctile,
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
st.subheader("20-Year Historical Regime Score")

hist_data = compute_historical_scores()

df = pd.DataFrame(hist_data)
df["date"] = pd.to_datetime(df["date"])
df = df.set_index("date")

# Main score chart
chart_tab1, chart_tab2 = st.tabs(["Composite Score", "Signal Breakdown"])

with chart_tab1:
    chart_df = df[["score", "raw_score"]].rename(
        columns={"score": "Adjusted Score", "raw_score": "Raw Score"}
    )
    st.line_chart(chart_df, color=["#f59e0b", "#78716c"], height=400)

    # FD periods annotation
    fd_periods = df[df["fd_active"]].index
    if len(fd_periods) > 0:
        st.caption(
            f"Fiscal Dominance active: {fd_periods[0].strftime('%b %Y')} – "
            f"{fd_periods[-1].strftime('%b %Y')} (purple shading in static chart)"
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
    signal_df = df[list(signal_rename.keys())].rename(columns=signal_rename)
    selected = st.multiselect(
        "Select signals to display",
        signal_df.columns.tolist(),
        default=["Breadth & Concentration", "Term Premium", "Credit"],
    )
    if selected:
        st.line_chart(signal_df[selected], height=400)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Market Topping Regime Dashboard · 7-Signal Composite with Fiscal Dominance Modifier · "
    "[GitHub](https://github.com/toddaerickson/hello-worlds)"
)
