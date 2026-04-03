"""Signal 3: Credit Complacency (Weight: 20%).

Extremely tight HY spreads signal investors are under-pricing default risk.
HY OAS at historically low levels achieved only a few times (May 2007, Jul 2021, Nov 2024).
"""

import numpy as np


def score_hy_oas_percentile(hy_oas_pctile_5y: float | None) -> float:
    """Sub-signal A: HY OAS percentile within trailing 5-year window.

    Score = max(0, (20 - percentile) / 20 * 100)
    Below 20th percentile starts scoring; 0th = max.
    """
    if hy_oas_pctile_5y is None:
        return 0.0
    return max(0.0, min(100.0, (20 - hy_oas_pctile_5y) / 20 * 100))


def score_ccc_bb_compression(
    ccc_bb_ratio: float | None, ccc_bb_median_5y: float | None
) -> float:
    """Sub-signal B: CCC-BB compression.

    Low ratio = risk-seeking. Score rises as ratio falls below median.
    """
    if ccc_bb_ratio is None or ccc_bb_median_5y is None or ccc_bb_median_5y <= 0:
        return 0.0
    if ccc_bb_ratio >= ccc_bb_median_5y:
        return 0.0
    # Score increases as ratio drops below median
    deviation = (ccc_bb_median_5y - ccc_bb_ratio) / ccc_bb_median_5y
    return max(0.0, min(100.0, deviation * 200))


def score_hy_oas_tightening(
    hy_oas_20d_change: float | None, hy_oas_pctile_5y: float | None
) -> float:
    """Sub-signal C: HY OAS rate of change.

    Score = 100 if OAS is tightening while already < 10th percentile. 0 if widening.
    """
    if hy_oas_20d_change is None or hy_oas_pctile_5y is None:
        return 0.0
    if hy_oas_20d_change < 0 and hy_oas_pctile_5y < 10:
        return 100.0
    return 0.0


def compute_credit_score(
    hy_oas_pctile_5y: float | None = None,
    ccc_bb_ratio: float | None = None,
    ccc_bb_median_5y: float | None = None,
    hy_oas_20d_change: float | None = None,
) -> float:
    """Compute Signal 3 composite score (0-100).

    Average of three sub-signals.
    """
    a = score_hy_oas_percentile(hy_oas_pctile_5y)
    b = score_ccc_bb_compression(ccc_bb_ratio, ccc_bb_median_5y)
    c = score_hy_oas_tightening(hy_oas_20d_change, hy_oas_pctile_5y)
    return (a + b + c) / 3.0
