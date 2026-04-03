"""Signal 2: Valuation Percentile (Weight: 15%).

Elevated valuations reduce forward return expectations and increase fragility.
Necessary but not sufficient -- valuations can stay stretched for years.
"""


def score_cape_percentile(cape_pctile_30y: float | None) -> float:
    """Sub-signal A: Shiller CAPE percentile vs 30-year distribution.

    Score = max(0, (percentile - 70) / 30 * 100)
    Above 70th percentile starts scoring; 100th = max.
    """
    if cape_pctile_30y is None:
        return 0.0
    return max(0.0, min(100.0, (cape_pctile_30y - 70) / 30 * 100))


def score_buffett_percentile(buffett_pctile_30y: float | None) -> float:
    """Sub-signal B: Buffett Indicator percentile vs 30-year distribution.

    Same percentile-based scoring as CAPE.
    """
    if buffett_pctile_30y is None:
        return 0.0
    return max(0.0, min(100.0, (buffett_pctile_30y - 70) / 30 * 100))


def score_forward_pe(fwd_pe: float | None, mean_10y: float | None) -> float:
    """Sub-signal C: Forward P/E vs trailing 10-year average.

    Score = max(0, (fwd_pe - mean_10y) / mean_10y * 200)
    50% above mean = max score.
    """
    if fwd_pe is None or mean_10y is None or mean_10y <= 0:
        return 0.0
    return max(0.0, min(100.0, (fwd_pe - mean_10y) / mean_10y * 200))


def compute_valuation_score(
    cape_pctile_30y: float | None = None,
    buffett_pctile_30y: float | None = None,
    fwd_pe: float | None = None,
    mean_10y_pe: float | None = None,
) -> float:
    """Compute Signal 2 composite score (0-100).

    Average of available sub-signals.
    """
    scores = []
    a = score_cape_percentile(cape_pctile_30y)
    b = score_buffett_percentile(buffett_pctile_30y)
    c = score_forward_pe(fwd_pe, mean_10y_pe)

    # Include sub-signals that have data
    if cape_pctile_30y is not None:
        scores.append(a)
    if buffett_pctile_30y is not None:
        scores.append(b)
    if fwd_pe is not None and mean_10y_pe is not None:
        scores.append(c)

    if not scores:
        return 0.0
    return sum(scores) / len(scores)
