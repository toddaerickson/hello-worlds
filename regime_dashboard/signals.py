"""Signal definitions for the regime dashboard.

Signals 1-6: Core topping signals (breadth, valuation, credit, sentiment, macro, margin debt)
Signal 7: Term Premium / Fiscal Stress
Fiscal Dominance Flag: Structural modifier for all signals
"""

from dataclasses import dataclass, field


@dataclass
class SignalReading:
    """A single signal's current state."""
    name: str
    score: int  # 0-100 scale, higher = more danger
    level: str  # 'low', 'moderate', 'elevated', 'high', 'extreme'
    components: dict = field(default_factory=dict)
    interpretation: str = ""
    fiscal_dominance_note: str = ""


def score_to_level(score):
    """Convert a 0-100 score to a named level."""
    if score >= 80:
        return "extreme"
    if score >= 60:
        return "high"
    if score >= 40:
        return "elevated"
    if score >= 20:
        return "moderate"
    return "low"


# ---------------------------------------------------------------------------
# Signal 1: Breadth Divergence
# ---------------------------------------------------------------------------

def evaluate_breadth(pct_above_200dma=None, advance_decline_line_trend=None,
                     new_highs_vs_new_lows=None):
    """Evaluate market breadth divergence.

    Args:
        pct_above_200dma: Percentage of S&P 500 stocks above 200-day MA
        advance_decline_line_trend: 'rising', 'flat', or 'declining'
        new_highs_vs_new_lows: Ratio of new 52-week highs to new lows
    """
    score = 0
    components = {}

    if pct_above_200dma is not None:
        components["pct_above_200dma"] = pct_above_200dma
        if pct_above_200dma < 40:
            score += 40
        elif pct_above_200dma < 55:
            score += 25
        elif pct_above_200dma < 65:
            score += 10

    if advance_decline_line_trend is not None:
        components["ad_line_trend"] = advance_decline_line_trend
        if advance_decline_line_trend == "declining":
            score += 30
        elif advance_decline_line_trend == "flat":
            score += 15

    if new_highs_vs_new_lows is not None:
        components["highs_lows_ratio"] = new_highs_vs_new_lows
        if new_highs_vs_new_lows < 1.0:
            score += 30
        elif new_highs_vs_new_lows < 2.0:
            score += 15

    score = min(score, 100)
    return SignalReading(
        name="Breadth Divergence",
        score=score,
        level=score_to_level(score),
        components=components,
        interpretation="Fewer stocks participating in rally = exhaustion signal",
    )


# ---------------------------------------------------------------------------
# Signal 2: Valuation
# ---------------------------------------------------------------------------

def evaluate_valuation(pe_ratio=None, cape_ratio=None, ev_ebitda=None):
    """Evaluate market valuation levels."""
    score = 0
    components = {}

    if pe_ratio is not None:
        components["pe_ratio"] = pe_ratio
        if pe_ratio > 25:
            score += 35
        elif pe_ratio > 20:
            score += 20
        elif pe_ratio > 18:
            score += 10

    if cape_ratio is not None:
        components["cape_ratio"] = cape_ratio
        if cape_ratio > 35:
            score += 35
        elif cape_ratio > 28:
            score += 20
        elif cape_ratio > 22:
            score += 10

    if ev_ebitda is not None:
        components["ev_ebitda"] = ev_ebitda
        if ev_ebitda > 16:
            score += 30
        elif ev_ebitda > 13:
            score += 15

    score = min(score, 100)
    return SignalReading(
        name="Valuation",
        score=score,
        level=score_to_level(score),
        components=components,
        interpretation="Expensive valuations = fragile to negative catalysts",
    )


# ---------------------------------------------------------------------------
# Signal 3: Credit Complacency
# ---------------------------------------------------------------------------

def evaluate_credit(hy_spread_bps=None, ig_spread_bps=None,
                    hy_spread_percentile=None):
    """Evaluate credit market complacency.

    Args:
        hy_spread_bps: High-yield OAS spread in basis points
        ig_spread_bps: Investment-grade OAS spread in basis points
        hy_spread_percentile: Current HY spread percentile vs history (0-100, lower = tighter)
    """
    score = 0
    components = {}

    if hy_spread_bps is not None:
        components["hy_spread_bps"] = hy_spread_bps
        if hy_spread_bps < 300:
            score += 40  # Extremely tight
        elif hy_spread_bps < 400:
            score += 25
        elif hy_spread_bps < 500:
            score += 10

    if hy_spread_percentile is not None:
        components["hy_spread_percentile"] = hy_spread_percentile
        if hy_spread_percentile < 10:
            score += 35
        elif hy_spread_percentile < 25:
            score += 20
        elif hy_spread_percentile < 40:
            score += 10

    if ig_spread_bps is not None:
        components["ig_spread_bps"] = ig_spread_bps
        if ig_spread_bps < 80:
            score += 25
        elif ig_spread_bps < 120:
            score += 10

    score = min(score, 100)
    return SignalReading(
        name="Credit Complacency",
        score=score,
        level=score_to_level(score),
        components=components,
        interpretation="Tight spreads = mispriced credit risk",
    )


# ---------------------------------------------------------------------------
# Signal 4: Sentiment Extremes
# ---------------------------------------------------------------------------

def evaluate_sentiment(aaii_bull_bear_spread=None, vix=None,
                       put_call_ratio=None, fear_greed_index=None):
    """Evaluate investor sentiment extremes."""
    score = 0
    components = {}

    if aaii_bull_bear_spread is not None:
        components["aaii_bull_bear_spread"] = aaii_bull_bear_spread
        if aaii_bull_bear_spread > 30:
            score += 30  # Extreme bullishness
        elif aaii_bull_bear_spread > 15:
            score += 15

    if vix is not None:
        components["vix"] = vix
        if vix < 12:
            score += 25  # Extreme complacency
        elif vix < 15:
            score += 15

    if put_call_ratio is not None:
        components["put_call_ratio"] = put_call_ratio
        if put_call_ratio < 0.7:
            score += 25  # Too many calls relative to puts
        elif put_call_ratio < 0.85:
            score += 10

    if fear_greed_index is not None:
        components["fear_greed_index"] = fear_greed_index
        if fear_greed_index > 80:
            score += 20
        elif fear_greed_index > 65:
            score += 10

    score = min(score, 100)
    return SignalReading(
        name="Sentiment Extremes",
        score=score,
        level=score_to_level(score),
        components=components,
        interpretation="Extreme optimism = contrarian warning",
    )


# ---------------------------------------------------------------------------
# Signal 5: Macro Deterioration (LEI)
# ---------------------------------------------------------------------------

def evaluate_macro(lei_yoy_change=None, lei_monthly_change=None,
                   private_lei_yoy_change=None, ism_manufacturing=None):
    """Evaluate macro deterioration via Leading Economic Indicators.

    Args:
        lei_yoy_change: Conference Board LEI year-over-year % change
        lei_monthly_change: LEI month-over-month % change
        private_lei_yoy_change: Private-sector LEI (ex-government) YoY % change
        ism_manufacturing: ISM Manufacturing PMI
    """
    score = 0
    components = {}

    if lei_yoy_change is not None:
        components["lei_yoy_change"] = lei_yoy_change
        if lei_yoy_change < -5:
            score += 35
        elif lei_yoy_change < -2:
            score += 25
        elif lei_yoy_change < 0:
            score += 15

    if lei_monthly_change is not None:
        components["lei_monthly_change"] = lei_monthly_change
        if lei_monthly_change < -0.5:
            score += 20
        elif lei_monthly_change < -0.2:
            score += 10

    if ism_manufacturing is not None:
        components["ism_manufacturing"] = ism_manufacturing
        if ism_manufacturing < 45:
            score += 25
        elif ism_manufacturing < 48:
            score += 15
        elif ism_manufacturing < 50:
            score += 10

    # Private-sector LEI is used under fiscal dominance (see scoring engine)
    if private_lei_yoy_change is not None:
        components["private_lei_yoy_change"] = private_lei_yoy_change

    score = min(score, 100)
    return SignalReading(
        name="Macro Deterioration",
        score=score,
        level=score_to_level(score),
        components=components,
        interpretation="Declining LEI = rising recession probability",
    )


# ---------------------------------------------------------------------------
# Signal 6: Margin Debt / Leverage
# ---------------------------------------------------------------------------

def evaluate_leverage(margin_debt_yoy_pct=None, margin_debt_to_gdp=None,
                      margin_debt_percentile=None):
    """Evaluate speculative leverage levels."""
    score = 0
    components = {}

    if margin_debt_yoy_pct is not None:
        components["margin_debt_yoy_pct"] = margin_debt_yoy_pct
        if margin_debt_yoy_pct > 30:
            score += 40
        elif margin_debt_yoy_pct > 15:
            score += 25
        elif margin_debt_yoy_pct > 5:
            score += 10

    if margin_debt_to_gdp is not None:
        components["margin_debt_to_gdp"] = margin_debt_to_gdp
        if margin_debt_to_gdp > 3.5:
            score += 35
        elif margin_debt_to_gdp > 2.5:
            score += 20

    if margin_debt_percentile is not None:
        components["margin_debt_percentile"] = margin_debt_percentile
        if margin_debt_percentile > 90:
            score += 25
        elif margin_debt_percentile > 75:
            score += 15

    score = min(score, 100)
    return SignalReading(
        name="Margin Debt / Leverage",
        score=score,
        level=score_to_level(score),
        components=components,
        interpretation="Excessive leverage = fragility to forced selling",
    )


# ---------------------------------------------------------------------------
# Signal 7: Term Premium / Fiscal Stress (NEW)
# ---------------------------------------------------------------------------

def evaluate_term_premium(
    spread_2s10s_bps=None,
    term_premium_10y=None,
    term_premium_5y_avg=None,
    deficit_pct_gdp=None,
    debt_service_pct_revenue=None,
    fed_cutting=None,
):
    """Evaluate term premium and fiscal stress indicators.

    This is the yield-curve signal reinterpreted for fiscal dominance.
    Steepening for the 'wrong reasons' (supply/fiscal pressure rather than
    growth expectations) is identified by: steepening curve + rising term
    premium + rising deficit + Fed easing simultaneously.

    Args:
        spread_2s10s_bps: 2s10s spread in basis points (FRED T10Y2Y * 100)
        term_premium_10y: 10-year term premium (NY Fed ACM model, in %)
        term_premium_5y_avg: 5-year average of 10y term premium
        deficit_pct_gdp: Federal deficit as % of GDP (positive = deficit)
        debt_service_pct_revenue: Interest outlays / tax revenue (%)
        fed_cutting: Boolean, whether Fed is currently in a cutting cycle
    """
    score = 0
    components = {}

    # 2s10s slope assessment
    if spread_2s10s_bps is not None:
        components["spread_2s10s_bps"] = spread_2s10s_bps
        if fed_cutting:
            # Steepening while Fed cuts = fiscal dominance stress
            if spread_2s10s_bps > 100:
                score += 30  # Strong fiscal stress signal
            elif spread_2s10s_bps > 75:
                score += 20
            elif spread_2s10s_bps > 50:
                score += 10
        else:
            # Standard interpretation: inversion = recession signal
            if spread_2s10s_bps < -50:
                score += 30  # Deep inversion
            elif spread_2s10s_bps < 0:
                score += 20  # Inverted

    # Term premium assessment
    if term_premium_10y is not None:
        components["term_premium_10y"] = term_premium_10y
        if term_premium_5y_avg is not None:
            components["term_premium_5y_avg"] = term_premium_5y_avg
            premium_excess = term_premium_10y - term_premium_5y_avg
            components["term_premium_excess"] = premium_excess
            if premium_excess > 0.75:
                score += 25  # Bond market demanding significant fiscal risk compensation
            elif premium_excess > 0.50:
                score += 20
            elif premium_excess > 0.25:
                score += 10
        else:
            # Without 5y average, use absolute level
            if term_premium_10y > 1.0:
                score += 20
            elif term_premium_10y > 0.5:
                score += 10

    # Deficit trajectory
    if deficit_pct_gdp is not None:
        components["deficit_pct_gdp"] = deficit_pct_gdp
        if deficit_pct_gdp > 7:
            score += 25
        elif deficit_pct_gdp > 6:
            score += 20
        elif deficit_pct_gdp > 5:
            score += 10

    # Debt service ratio
    if debt_service_pct_revenue is not None:
        components["debt_service_pct_revenue"] = debt_service_pct_revenue
        if debt_service_pct_revenue > 25:
            score += 20
        elif debt_service_pct_revenue > 20:
            score += 15
        elif debt_service_pct_revenue > 15:
            score += 10

    if fed_cutting is not None:
        components["fed_cutting"] = fed_cutting

    score = min(score, 100)
    return SignalReading(
        name="Term Premium / Fiscal Stress",
        score=score,
        level=score_to_level(score),
        components=components,
        interpretation=(
            "Steepening curve under fiscal dominance = bond market losing confidence "
            "in fiscal trajectory, not pricing healthy expansion"
        ),
    )


# ---------------------------------------------------------------------------
# Fiscal Dominance Flag
# ---------------------------------------------------------------------------

@dataclass
class FiscalDominanceFlag:
    """Structural modifier that changes interpretation of all signals.

    Activates when 3 of 4 conditions are met simultaneously:
    1. Federal deficit / GDP > 5% in non-recession year
    2. Interest expense / tax revenue > 15%
    3. Fed easing while inflation > target (FFR declining AND core PCE > 2.5%)
    4. 2s10s steepening + rising term premium (2s10s > 75 bps AND term premium rising)
    """
    active: bool = False
    conditions_met: int = 0
    condition_details: dict = field(default_factory=dict)
    caution_modifier: int = 0  # +10 when active

    @property
    def signal_interpretation_overrides(self):
        """Return modified interpretations when fiscal dominance is active."""
        if not self.active:
            return {}
        return {
            "Breadth Divergence": (
                "May be masked by fiscal-stimulus-beneficiary sectors "
                "(defense, infrastructure) inflating breadth artificially"
            ),
            "Valuation": (
                "Even more fragile - earnings are partially fiscal-stimulus-driven "
                "and not sustainable at current deficit levels"
            ),
            "Credit Complacency": (
                "Tight spreads may reflect forced-easy monetary policy, not credit health. "
                "MORE dangerous, not less"
            ),
            "Sentiment Extremes": (
                "Fiscal stimulus sustains narrative longer - 'this time is different "
                "because government spending supports growth'"
            ),
            "Macro Deterioration": (
                "LEI may be artificially supported by government spending. "
                "Private-sector LEI (ex-government) is the relevant signal"
            ),
            "Margin Debt / Leverage": "Same interpretation applies under fiscal dominance",
            "Term Premium / Fiscal Stress": (
                "This signal is the direct measure of fiscal dominance stress - "
                "its score should be weighted more heavily"
            ),
        }


def evaluate_fiscal_dominance(
    deficit_pct_gdp=None,
    in_recession=False,
    interest_pct_revenue=None,
    fed_funds_rate_declining=None,
    core_pce_yoy=None,
    spread_2s10s_bps=None,
    term_premium_rising=None,
):
    """Evaluate whether the fiscal dominance flag should be active.

    Args:
        deficit_pct_gdp: Federal deficit as % of GDP (positive = deficit)
        in_recession: Whether the economy is officially in recession
        interest_pct_revenue: Interest expense / tax revenue (%)
        fed_funds_rate_declining: Whether the Fed funds rate is in a declining trend
        core_pce_yoy: Core PCE year-over-year (%)
        spread_2s10s_bps: 2s10s spread in basis points
        term_premium_rising: Whether the 10y term premium is on a rising 3-month trend
    """
    conditions_met = 0
    details = {}

    # Condition 1: Deficit > 5% of GDP in non-recession year
    if deficit_pct_gdp is not None:
        cond1 = deficit_pct_gdp > 5 and not in_recession
        details["deficit_gt_5pct"] = {
            "met": cond1,
            "value": deficit_pct_gdp,
            "threshold": 5.0,
            "note": "Non-recession year" if not in_recession else "In recession (excluded)",
        }
        if cond1:
            conditions_met += 1

    # Condition 2: Interest expense / tax revenue > 15%
    if interest_pct_revenue is not None:
        cond2 = interest_pct_revenue > 15
        details["interest_gt_15pct_revenue"] = {
            "met": cond2,
            "value": interest_pct_revenue,
            "threshold": 15.0,
        }
        if cond2:
            conditions_met += 1

    # Condition 3: Fed easing while inflation > target
    if fed_funds_rate_declining is not None and core_pce_yoy is not None:
        cond3 = fed_funds_rate_declining and core_pce_yoy > 2.5
        details["fed_easing_above_target"] = {
            "met": cond3,
            "fed_declining": fed_funds_rate_declining,
            "core_pce": core_pce_yoy,
            "pce_threshold": 2.5,
        }
        if cond3:
            conditions_met += 1

    # Condition 4: 2s10s steepening + rising term premium
    if spread_2s10s_bps is not None and term_premium_rising is not None:
        cond4 = spread_2s10s_bps > 75 and term_premium_rising
        details["curve_steepening_with_term_premium"] = {
            "met": cond4,
            "spread_2s10s_bps": spread_2s10s_bps,
            "spread_threshold": 75,
            "term_premium_rising": term_premium_rising,
        }
        if cond4:
            conditions_met += 1

    active = conditions_met >= 3
    return FiscalDominanceFlag(
        active=active,
        conditions_met=conditions_met,
        condition_details=details,
        caution_modifier=10 if active else 0,
    )
