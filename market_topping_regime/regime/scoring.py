"""Weighted caution level computation for the Market Regime Dashboard.

Combines 6 signal scores into a single caution level (0-100%) with
regime classification and missing-data proportional re-weighting.
"""

import datetime as dt
from dataclasses import dataclass
from typing import Optional

# Signal weights (must sum to 1.0)
WEIGHTS = {
    "breadth": 0.25,
    "valuation": 0.15,
    "credit": 0.20,
    "sentiment": 0.15,
    "macro": 0.15,
    "leverage": 0.10,
}

# Expected update frequencies (days)
UPDATE_FREQUENCIES = {
    "breadth": 1,
    "valuation": 30,
    "credit": 1,
    "sentiment": 7,
    "macro": 30,
    "leverage": 45,
}

# Regime thresholds
REGIME_BANDS = [
    (0, 20, "GREEN"),
    (20, 40, "YELLOW"),
    (40, 60, "ORANGE"),
    (60, 80, "RED"),
    (80, 100, "EXTREME"),
]


@dataclass
class CautionResult:
    """Result of the caution level computation."""

    caution_level: float
    regime: str
    stale_flag: bool
    contributions: dict[str, float]  # signal_name -> weighted contribution
    raw_scores: dict[str, Optional[float]]  # signal_name -> raw score (0-100)


def classify_regime(caution_level: float) -> str:
    """Map caution level (0-100) to regime label."""
    for low, high, label in REGIME_BANDS:
        if low <= caution_level <= high:
            return label
    return "EXTREME" if caution_level > 100 else "GREEN"


def compute_caution_level(
    scores: dict[str, Optional[float]],
    staleness_days: dict[str, int] | None = None,
) -> CautionResult:
    """Compute the weighted composite caution level.

    Args:
        scores: Dict mapping signal name to score (0-100) or None if unavailable.
                Keys: breadth, valuation, credit, sentiment, macro, leverage
        staleness_days: Optional dict mapping signal name to days since last update.
                        Used to flag stale data.

    Returns:
        CautionResult with caution_level, regime, stale_flag, and contributions.
    """
    # Filter to available signals
    available = {k: v for k, v in scores.items() if v is not None}

    if not available:
        return CautionResult(
            caution_level=0.0,
            regime="GREEN",
            stale_flag=True,
            contributions={k: 0.0 for k in WEIGHTS},
            raw_scores=scores,
        )

    # Re-weight proportionally for missing signals
    total_available_weight = sum(WEIGHTS[k] for k in available)
    reweighted = {k: WEIGHTS[k] / total_available_weight for k in available}

    # Compute weighted contributions
    contributions = {}
    for name in WEIGHTS:
        if name in available:
            contributions[name] = reweighted[name] * available[name]
        else:
            contributions[name] = 0.0

    caution_level = sum(contributions.values())
    caution_level = max(0.0, min(100.0, caution_level))

    # Check staleness
    stale_count = 0
    if staleness_days:
        for name, days in staleness_days.items():
            expected = UPDATE_FREQUENCIES.get(name, 30)
            if days > expected + 7:
                stale_count += 1
    stale_flag = stale_count > 2

    regime = classify_regime(caution_level)

    return CautionResult(
        caution_level=caution_level,
        regime=regime,
        stale_flag=stale_flag,
        contributions=contributions,
        raw_scores=scores,
    )


def format_caution_summary(result: CautionResult) -> str:
    """Format a text summary of the caution level for terminal output."""
    lines = [
        "=" * 60,
        "  MARKET REGIME DASHBOARD - Topping Conditions Monitor",
        "=" * 60,
        "",
        f"  CAUTION LEVEL: {result.caution_level:.1f}%  [{result.regime}]",
        f"  {'*** STALE DATA WARNING ***' if result.stale_flag else ''}",
        "",
        "  Signal Contributions:",
        "  " + "-" * 50,
    ]

    signal_labels = {
        "breadth": "Breadth Divergence",
        "valuation": "Valuation Percentile",
        "credit": "Credit Complacency",
        "sentiment": "Sentiment Extreme",
        "macro": "Macro Deterioration",
        "leverage": "Margin Debt/Leverage",
    }

    for name, label in signal_labels.items():
        raw = result.raw_scores.get(name)
        contrib = result.contributions.get(name, 0)
        weight = WEIGHTS[name]
        raw_str = f"{raw:.1f}" if raw is not None else "N/A"
        bar_len = int(contrib / max(weight * 100, 1) * 20)
        bar = "#" * bar_len + "." * (20 - bar_len)
        lines.append(
            f"  {label:<25s} Score: {raw_str:>5s}  "
            f"Contrib: {contrib:>5.1f}/{weight*100:.0f}  [{bar}]"
        )

    lines.extend([
        "",
        "  Regime Bands:",
        "  GREEN (0-20)  YELLOW (21-40)  ORANGE (41-60)  RED (61-80)  EXTREME (81-100)",
        "=" * 60,
    ])

    return "\n".join(lines)
