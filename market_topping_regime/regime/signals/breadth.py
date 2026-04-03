"""Signal 1: Breadth Divergence (Weight: 25%).

Market index makes new highs while participation narrows.
Breadth deterioration precedes major tops by 3-6 months.
"""

import numpy as np
import pandas as pd


def score_pct_above_200d(pct_above_200d: float | None, spx_near_high: bool) -> float:
    """Sub-signal A: % above 200d MA divergence.

    SPX near 52-week high while % above 200d MA declining.
    Score = max(0, (60 - pct_above_200d) / 40 * 100)
    Below 60% starts scoring; below 20% = max score.
    Only scores when SPX is near 52-week high.
    """
    if pct_above_200d is None or not spx_near_high:
        return 0.0
    return max(0.0, min(100.0, (60 - pct_above_200d) / 40 * 100))


def score_new_highs_ratio(nh_nl_ratio_20d: float | None) -> float:
    """Sub-signal B: New Highs vs New Lows ratio (20d MA).

    Score = max(0, (50 - nh_ratio) / 50 * 100)
    Below 50% starts scoring; approaching 0% = max.
    """
    if nh_nl_ratio_20d is None:
        return 0.0
    return max(0.0, min(100.0, (50 - nh_nl_ratio_20d) / 50 * 100))


def score_ad_divergence(
    ad_line_20d_roc: float | None, spx_20d_roc: float | None, divergence_days: int = 0
) -> float:
    """Sub-signal C: Advance/Decline divergence.

    A/D line 20d ROC negative while SPX 20d ROC positive.
    Binary: 100 if divergence persists > 10 days, else 0.
    """
    if ad_line_20d_roc is None or spx_20d_roc is None:
        return 0.0
    if ad_line_20d_roc < 0 and spx_20d_roc > 0 and divergence_days > 10:
        return 100.0
    return 0.0


def compute_breadth_score(
    pct_above_200d: float | None = None,
    spx_near_52w_high: bool = False,
    nh_nl_ratio_20d: float | None = None,
    ad_line_20d_roc: float | None = None,
    spx_20d_roc: float | None = None,
    divergence_days: int = 0,
) -> float:
    """Compute Signal 1 composite score (0-100).

    Average of three sub-signals.
    """
    a = score_pct_above_200d(pct_above_200d, spx_near_52w_high)
    b = score_new_highs_ratio(nh_nl_ratio_20d)
    c = score_ad_divergence(ad_line_20d_roc, spx_20d_roc, divergence_days)
    return (a + b + c) / 3.0
