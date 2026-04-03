"""Signal 4: Sentiment Extreme (Weight: 15%).

Extreme optimism among retail and professional investors is a contrarian
indicator. NDR: extreme optimism corresponds to negative forward S&P returns.
"""


def score_aaii_bull_bear(spread_4w: float | None) -> float:
    """Sub-signal A: AAII Bull-Bear spread (4-week MA).

    Score = max(0, (spread_4w - 15) / 25 * 100)
    Above +15 starts scoring; above +40 = max.
    """
    if spread_4w is None:
        return 0.0
    return max(0.0, min(100.0, (spread_4w - 15) / 25 * 100))


def score_aaii_persistence(weeks_above_25: int | None) -> float:
    """Sub-signal B: AAII persistence.

    Consecutive weeks with Bull-Bear > 25.
    Score = min(100, weeks_above_25 * 25). 4+ weeks = max.
    """
    if weeks_above_25 is None:
        return 0.0
    return min(100.0, weeks_above_25 * 25.0)


def score_fear_greed(fg_index: float | None) -> float:
    """Sub-signal C: CNN Fear & Greed extreme.

    Score = max(0, (FG - 70) / 30 * 100). Above 70 starts; 100 = max.
    """
    if fg_index is None:
        return 0.0
    return max(0.0, min(100.0, (fg_index - 70) / 30 * 100))


def compute_sentiment_score(
    aaii_bull_bear_4w: float | None = None,
    aaii_weeks_above_25: int | None = None,
    fear_greed: float | None = None,
) -> float:
    """Compute Signal 4 composite score (0-100).

    Average of available sub-signals.
    """
    scores = []
    if aaii_bull_bear_4w is not None:
        scores.append(score_aaii_bull_bear(aaii_bull_bear_4w))
    if aaii_weeks_above_25 is not None:
        scores.append(score_aaii_persistence(aaii_weeks_above_25))
    if fear_greed is not None:
        scores.append(score_fear_greed(fear_greed))

    if not scores:
        return 0.0
    return sum(scores) / len(scores)
