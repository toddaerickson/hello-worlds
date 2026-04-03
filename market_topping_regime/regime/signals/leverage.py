"""Signal 6: Margin Debt / Leverage (Weight: 10%).

Excessive margin debt growth amplifies downside when sentiment reverses.
Record margin levels preceded 2000 and 2007 peaks.
Lowest weight due to noise and ~45 day data lag.
"""


def score_margin_debt_yoy(yoy_growth: float | None) -> float:
    """Sub-signal A: Margin debt year-over-year growth.

    Score = max(0, (YoY_growth - 10) / 20 * 100)
    Above 10% starts scoring; above 30% = max.
    """
    if yoy_growth is None:
        return 0.0
    return max(0.0, min(100.0, (yoy_growth - 10) / 20 * 100))


def score_free_credit_declining(months_declining: int | None) -> float:
    """Sub-signal B: Free credit balance declining.

    Score = 100 if declining for 6+ consecutive months.
    Falling free credit = investors fully deployed.
    """
    if months_declining is None:
        return 0.0
    if months_declining >= 6:
        return 100.0
    return 0.0


def compute_leverage_score(
    margin_debt_yoy: float | None = None,
    free_credit_declining: int | None = None,
) -> float:
    """Compute Signal 6 composite score (0-100).

    Average of available sub-signals.
    """
    scores = []
    if margin_debt_yoy is not None:
        scores.append(score_margin_debt_yoy(margin_debt_yoy))
    if free_credit_declining is not None:
        scores.append(score_free_credit_declining(free_credit_declining))

    if not scores:
        return 0.0
    return sum(scores) / len(scores)
