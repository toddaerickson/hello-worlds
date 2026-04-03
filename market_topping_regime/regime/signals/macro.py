"""Signal 5: Macro Deterioration (Weight: 15%).

Leading economic indicators have preceded all recessions since 1960.
Market tops often occur near LEI inflection points.
"""


def score_lei_roc(lei_6m_roc: float | None) -> float:
    """Sub-signal A: LEI 6-month rate of change.

    Score = max(0, -LEI_6m_ROC / 5 * 100)
    Negative ROC starts scoring; -5% = max. 0 if positive.
    """
    if lei_6m_roc is None:
        return 0.0
    if lei_6m_roc >= 0:
        return 0.0
    return max(0.0, min(100.0, -lei_6m_roc / 5 * 100))


def score_ism_new_orders(ism_no: float | None) -> float:
    """Sub-signal B: ISM Manufacturing New Orders Index (3-month trend).

    Score = max(0, (50 - ISM_NO) / 15 * 100)
    Below 50 starts scoring; below 35 = max.
    """
    if ism_no is None:
        return 0.0
    return max(0.0, min(100.0, (50 - ism_no) / 15 * 100))


def score_initial_claims(claims_4w_vs_26w_pct: float | None) -> float:
    """Sub-signal C: Initial claims trend.

    4-week MA vs 26-week MA percentage difference.
    Score = 100 if 4w MA > 26w MA by > 10%.
    Score = 50 if 4w > 26w by 0-10%.
    Else 0.
    """
    if claims_4w_vs_26w_pct is None:
        return 0.0
    if claims_4w_vs_26w_pct > 10:
        return 100.0
    if claims_4w_vs_26w_pct > 0:
        return 50.0
    return 0.0


def compute_macro_score(
    lei_6m_roc: float | None = None,
    ism_new_orders: float | None = None,
    claims_4w_vs_26w: float | None = None,
) -> float:
    """Compute Signal 5 composite score (0-100).

    Average of available sub-signals.
    """
    scores = []
    if lei_6m_roc is not None:
        scores.append(score_lei_roc(lei_6m_roc))
    if ism_new_orders is not None:
        scores.append(score_ism_new_orders(ism_new_orders))
    if claims_4w_vs_26w is not None:
        scores.append(score_initial_claims(claims_4w_vs_26w))

    if not scores:
        return 0.0
    return sum(scores) / len(scores)
