"""Streamlit dashboard for the Market Regime Topping Conditions Monitor.

Displays:
- Gauge visualization showing caution level (0-100%) with color zones
- Signal breakdown bar chart (6 bars showing each contribution)
- Time series of caution level
- Current values table with thresholds and raw data
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from market_topping_regime.data.store import (
    fetch_regime_caution_history,
    fetch_regime_signals_history,
    fetch_latest_regime_caution,
    init_regime_tables,
)
from market_topping_regime.regime.scoring import WEIGHTS, REGIME_BANDS


# ---------------------------------------------------------------------------
# Color scheme
# ---------------------------------------------------------------------------

REGIME_COLORS = {
    "GREEN": "#2ECC71",
    "YELLOW": "#F1C40F",
    "ORANGE": "#E67E22",
    "RED": "#E74C3C",
    "EXTREME": "#8E44AD",
}

SIGNAL_NAMES = {
    "breadth": "Breadth Divergence",
    "valuation": "Valuation Percentile",
    "credit": "Credit Complacency",
    "sentiment": "Sentiment Extreme",
    "macro": "Macro Deterioration",
    "leverage": "Margin Debt/Leverage",
}


# ---------------------------------------------------------------------------
# Gauge chart
# ---------------------------------------------------------------------------


def create_gauge(caution_level: float, regime: str) -> go.Figure:
    """Create a semicircular gauge chart for the caution level."""
    color = REGIME_COLORS.get(regime, "#95A5A6")

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=caution_level,
            number={"suffix": "%", "font": {"size": 48}},
            title={"text": "Caution Level", "font": {"size": 24}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 2},
                "bar": {"color": color, "thickness": 0.3},
                "bgcolor": "white",
                "steps": [
                    {"range": [0, 20], "color": "#D5F5E3"},
                    {"range": [20, 40], "color": "#FCF3CF"},
                    {"range": [40, 60], "color": "#FDEBD0"},
                    {"range": [60, 80], "color": "#FADBD8"},
                    {"range": [80, 100], "color": "#E8DAEF"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "thickness": 0.8,
                    "value": caution_level,
                },
            },
        )
    )
    fig.update_layout(height=300, margin=dict(t=60, b=0, l=30, r=30))
    return fig


# ---------------------------------------------------------------------------
# Signal breakdown chart
# ---------------------------------------------------------------------------


def create_signal_breakdown(contributions: dict, raw_scores: dict) -> go.Figure:
    """Create a horizontal bar chart showing each signal's contribution."""
    names = list(SIGNAL_NAMES.values())
    keys = list(SIGNAL_NAMES.keys())
    contribs = [contributions.get(k, 0) for k in keys]
    max_contribs = [WEIGHTS[k] * 100 for k in keys]
    raw = [raw_scores.get(k, 0) or 0 for k in keys]

    fig = go.Figure()

    # Max possible contribution (background)
    fig.add_trace(
        go.Bar(
            y=names,
            x=max_contribs,
            orientation="h",
            name="Max Contribution",
            marker_color="rgba(200, 200, 200, 0.3)",
            text=[f"Max: {m:.0f}" for m in max_contribs],
            textposition="inside",
        )
    )

    # Actual contribution
    colors = []
    for c, m in zip(contribs, max_contribs):
        pct = c / m * 100 if m > 0 else 0
        if pct < 33:
            colors.append("#2ECC71")
        elif pct < 66:
            colors.append("#F1C40F")
        else:
            colors.append("#E74C3C")

    fig.add_trace(
        go.Bar(
            y=names,
            x=contribs,
            orientation="h",
            name="Current Contribution",
            marker_color=colors,
            text=[f"{c:.1f} (Score: {r:.0f})" for c, r in zip(contribs, raw)],
            textposition="outside",
        )
    )

    fig.update_layout(
        barmode="overlay",
        height=350,
        margin=dict(t=30, b=30, l=150, r=80),
        xaxis_title="Weighted Contribution",
        showlegend=False,
        xaxis=dict(range=[0, 30]),
    )
    return fig


# ---------------------------------------------------------------------------
# Time series chart
# ---------------------------------------------------------------------------


def create_timeseries(history: list[dict]) -> go.Figure:
    """Create a time series of caution level with regime color bands."""
    if not history:
        return go.Figure()

    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["date"])

    fig = go.Figure()

    # Background regime bands
    for low, high, label in REGIME_BANDS:
        fig.add_hrect(
            y0=low,
            y1=high,
            fillcolor=REGIME_COLORS[label],
            opacity=0.1,
            line_width=0,
            annotation_text=label,
            annotation_position="top left",
        )

    # Caution level line
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["caution_level"],
            mode="lines",
            name="Caution Level",
            line=dict(color="#2C3E50", width=2),
            fill="tozeroy",
            fillcolor="rgba(44, 62, 80, 0.1)",
        )
    )

    fig.update_layout(
        height=400,
        margin=dict(t=30, b=30),
        yaxis=dict(range=[0, 100], title="Caution Level (%)"),
        xaxis_title="Date",
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Signal details table
# ---------------------------------------------------------------------------


def create_signal_table(signals_row: dict | None) -> pd.DataFrame:
    """Build a detailed table of current signal values and thresholds."""
    if signals_row is None:
        return pd.DataFrame()

    rows = [
        {
            "Signal": "Breadth Divergence",
            "Score": signals_row.get("breadth_score"),
            "Weight": "25%",
            "Key Metric": f"% Above 200d: {signals_row.get('pct_above_200d', 'N/A')}",
            "Threshold": "< 60% when SPX near high",
        },
        {
            "Signal": "Valuation Percentile",
            "Score": signals_row.get("valuation_score"),
            "Weight": "15%",
            "Key Metric": f"CAPE: {signals_row.get('shiller_cape', 'N/A')}",
            "Threshold": "> 70th percentile (30y)",
        },
        {
            "Signal": "Credit Complacency",
            "Score": signals_row.get("credit_score"),
            "Weight": "20%",
            "Key Metric": f"HY OAS: {signals_row.get('hy_oas', 'N/A')}",
            "Threshold": "< 20th percentile (5y)",
        },
        {
            "Signal": "Sentiment Extreme",
            "Score": signals_row.get("sentiment_score"),
            "Weight": "15%",
            "Key Metric": f"AAII B-B 4w: {signals_row.get('aaii_bull_bear_4w', 'N/A')}",
            "Threshold": "Bull-Bear > +15",
        },
        {
            "Signal": "Macro Deterioration",
            "Score": signals_row.get("macro_score"),
            "Weight": "15%",
            "Key Metric": f"LEI 6m ROC: {signals_row.get('lei_6m_roc', 'N/A')}",
            "Threshold": "Negative LEI ROC",
        },
        {
            "Signal": "Margin Debt/Leverage",
            "Score": signals_row.get("leverage_score"),
            "Weight": "10%",
            "Key Metric": f"Margin YoY: {signals_row.get('margin_debt_yoy', 'N/A')}",
            "Threshold": "> 10% YoY growth",
        },
    ]
    df = pd.DataFrame(rows)
    df["Score"] = df["Score"].apply(
        lambda x: f"{x:.1f}" if x is not None else "N/A"
    )
    return df


# ---------------------------------------------------------------------------
# Main dashboard render
# ---------------------------------------------------------------------------


def render_regime_dashboard():
    """Render the full Market Regime Dashboard in Streamlit."""
    st.header("Market Regime Dashboard")
    st.subheader("Topping Conditions Monitor")
    st.caption(
        "Caution-level indicator for gradual risk reduction. "
        "Not binary exit signals."
    )

    init_regime_tables()

    # Load data
    latest = fetch_latest_regime_caution()
    history = fetch_regime_caution_history()

    if latest is None:
        st.warning(
            "No regime data available yet. Run the data pipeline first: "
            "`python -m market_topping_regime.main --regime`"
        )
        return

    caution_level = latest["caution_level"]
    regime = latest["regime"]
    stale = bool(latest.get("stale_flag", 0))

    # Top row: Gauge + Regime badge
    col1, col2 = st.columns([2, 1])
    with col1:
        fig_gauge = create_gauge(caution_level, regime)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        color = REGIME_COLORS.get(regime, "#95A5A6")
        st.markdown(
            f'<div style="background-color:{color}; padding:20px; '
            f'border-radius:10px; text-align:center; margin-top:30px;">'
            f'<h2 style="color:white; margin:0;">{regime}</h2>'
            f'<p style="color:white; margin:5px 0;">Regime</p></div>',
            unsafe_allow_html=True,
        )
        if stale:
            st.warning("Data staleness warning: >2 signals have stale data")

        st.markdown("---")
        st.metric("Caution Level", f"{caution_level:.1f}%")
        st.metric("Date", latest["date"])

        # Suggested action
        actions = {
            "GREEN": "Normal risk posture. No action required.",
            "YELLOW": "Tighten trailing stops. Review positions.",
            "ORANGE": "Trim high-beta by 15-25%. Raise cash to 10-15%.",
            "RED": "Reduce equity to 60-70%. Shift to quality.",
            "EXTREME": "Reduce equity to 40-50%. Hedge exposure.",
        }
        st.info(f"**Suggested Action:** {actions.get(regime, 'Review positions.')}")

    # Signal breakdown
    st.markdown("---")
    st.subheader("Signal Contributions")

    contributions = {
        "breadth": latest.get("breadth_contrib", 0),
        "valuation": latest.get("valuation_contrib", 0),
        "credit": latest.get("credit_contrib", 0),
        "sentiment": latest.get("sentiment_contrib", 0),
        "macro": latest.get("macro_contrib", 0),
        "leverage": latest.get("leverage_contrib", 0),
    }

    # Reconstruct raw scores from contributions / weights
    raw_scores = {}
    for k, w in WEIGHTS.items():
        c = contributions.get(k, 0)
        raw_scores[k] = c / w if w > 0 else 0

    fig_bars = create_signal_breakdown(contributions, raw_scores)
    st.plotly_chart(fig_bars, use_container_width=True)

    # Time series
    if history:
        st.markdown("---")
        st.subheader("Caution Level History")
        fig_ts = create_timeseries(history)
        st.plotly_chart(fig_ts, use_container_width=True)

    # Signal details table
    st.markdown("---")
    st.subheader("Signal Details")

    # Load latest signals row
    signals_history = fetch_regime_signals_history()
    signals_row = signals_history[-1] if signals_history else None
    table_df = create_signal_table(signals_row)
    if not table_df.empty:
        st.dataframe(table_df, use_container_width=True, hide_index=True)

    # Regime band reference
    st.markdown("---")
    st.subheader("Regime Band Reference")
    ref_data = [
        {"Caution Level": "0-20%", "Regime": "GREEN", "Action": "Normal risk posture. Full equity allocation."},
        {"Caution Level": "21-40%", "Regime": "YELLOW", "Action": "Tighten trailing stops on momentum positions."},
        {"Caution Level": "41-60%", "Regime": "ORANGE", "Action": "Trim highest-beta 15-25%. Raise cash 10-15%."},
        {"Caution Level": "61-80%", "Regime": "RED", "Action": "Reduce equity to 60-70%. Shift to quality/defensive."},
        {"Caution Level": "81-100%", "Regime": "EXTREME", "Action": "Reduce equity to 40-50%. Hedge remaining exposure."},
    ]
    st.dataframe(pd.DataFrame(ref_data), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    st.set_page_config(
        page_title="Market Regime Dashboard",
        page_icon="🎯",
        layout="wide",
    )
    render_regime_dashboard()
