"""Signal definitions for the Market Topping Regime Dashboard.

This module implements seven individual market signals that each produce a
0-100 caution score, plus the Fiscal Dominance structural modifier flag.

Signal overview:
  S1  Breadth Divergence & Concentration — fewer stocks participating in rally
  S2  Valuation — P/E, CAPE, EV/EBITDA stretch
  S3  Credit Complacency — tight HY and IG spreads vs. history
  S4  Sentiment Extremes — AAII, VIX, put/call, Fear & Greed
  S5  Macro Deterioration — LEI, ISM, private-sector LEI (ex-government)
  S6  Margin Debt / Leverage — speculative borrowing levels
  S7  Term Premium / Fiscal Stress — yield-curve signal reinterpreted for
      fiscal dominance (steepening for the "wrong reasons")

Fiscal Dominance Flag:
  Structural modifier that activates when 3 of 4 macro conditions are met.
  When active it adds +10 to the composite score, reweights signals, and
  re-scores Signal 5 using the private-sector LEI.
"""

from dataclasses import dataclass, field


# =========================================================================
# Data classes
# =========================================================================

@dataclass
class SignalReading:
    """A single signal's current state.

    Attributes:
        name:  Human-readable signal name (e.g. "Breadth Divergence")
        score: 0-100 caution score — higher means more danger
        level: Bucketed label derived from score (low/moderate/elevated/high/extreme)
        components: Raw input values used to compute the score
        interpretation: Plain-English summary of what this score means
        fiscal_dominance_note: Additional context when the FD flag is active
    """
    name: str
    score: int
    level: str
    components: dict = field(default_factory=dict)
    interpretation: str = ""
    fiscal_dominance_note: str = ""


def score_to_level(score):
    """Map a 0-100 numeric score to a named caution level.

    Thresholds:
      80-100 → extreme
      60-79  → high
      40-59  → elevated
      20-39  → moderate
       0-19  → low
    """
    if score >= 80:
        return "extreme"
    if score >= 60:
        return "high"
    if score >= 40:
        return "elevated"
    if score >= 20:
        return "moderate"
    return "low"


# =========================================================================
# Signal 1: Breadth Divergence & Concentration Risk
# =========================================================================

def evaluate_breadth(pct_above_200dma=None, advance_decline_line_trend=None,
                     new_highs_vs_new_lows=None, top_10_concentration_pct=None):
    """Score market breadth divergence (S1).

    Four sub-components, each contributing up to ~25-30 points:
      1. % of S&P 500 stocks above their 200-day moving average
      2. Advance/decline line trend (rising / flat / declining)
      3. Ratio of new 52-week highs to new lows
      4. Top-10 stock concentration in trailing 6-month return

    Args:
        pct_above_200dma: Percentage of S&P 500 stocks above 200-day MA.
        advance_decline_line_trend: 'rising', 'flat', or 'declining'.
        new_highs_vs_new_lows: Ratio of new 52-week highs to new lows.
        top_10_concentration_pct: Top-10 stock contribution to trailing 6-month
            SPX return as a percentage. Empirically supported by Leuthold,
            NDR, and BofA — extreme concentration preceded the dot-com crash,
            GFC, 2016 correction, and 2022 bear market.
    """
    score = 0
    components = {}

    # --- Sub-component 1: % above 200-day MA ---
    # Below 40% = severe divergence (market rising but most stocks falling)
    if pct_above_200dma is not None:
        components["pct_above_200dma"] = pct_above_200dma
        if pct_above_200dma < 40:
            score += 30
        elif pct_above_200dma < 55:
            score += 20
        elif pct_above_200dma < 65:
            score += 8

    # --- Sub-component 2: Advance/decline line trend ---
    # A declining A/D line while the index is rising = classic divergence
    if advance_decline_line_trend is not None:
        components["ad_line_trend"] = advance_decline_line_trend
        if advance_decline_line_trend == "declining":
            score += 25
        elif advance_decline_line_trend == "flat":
            score += 12

    # --- Sub-component 3: New highs vs. new lows ---
    # Ratio < 1.0 means more new lows than highs = internal weakness
    if new_highs_vs_new_lows is not None:
        components["highs_lows_ratio"] = new_highs_vs_new_lows
        if new_highs_vs_new_lows < 1.0:
            score += 25
        elif new_highs_vs_new_lows < 2.0:
            score += 12

    # --- Sub-component 4: Top-10 concentration risk ---
    # Historical context for top-10 share of trailing 6-month return:
    #   ~35-45%  Normal broad-based market
    #   ~50-60%  Elevated (2017-2019 FANG era)
    #   ~60-75%  Extreme (pre-2000 dot-com, 2021 Mag7, 2024-present)
    #   >75%     Historically rare, dot-com peak levels
    if top_10_concentration_pct is not None:
        components["top_10_concentration_pct"] = top_10_concentration_pct
        if top_10_concentration_pct > 75:
            score += 25  # Historically rare, dot-com-level concentration
        elif top_10_concentration_pct > 60:
            score += 20  # Extreme — signal fires at this threshold
        elif top_10_concentration_pct > 50:
            score += 10  # Elevated but not yet extreme

    score = min(score, 100)
    return SignalReading(
        name="Breadth Divergence",
        score=score,
        level=score_to_level(score),
        components=components,
        interpretation="Fewer stocks participating in rally = exhaustion signal",
    )


# =========================================================================
# Signal 2: Valuation
# =========================================================================

def evaluate_valuation(pe_ratio=None, cape_ratio=None, ev_ebitda=None):
    """Score market valuation levels (S2).

    Three sub-components measuring how expensive the market is relative to
    earnings. High valuations don't cause crashes, but they make the market
    more fragile to negative catalysts.

    Args:
        pe_ratio:  Trailing P/E ratio for the S&P 500.
        cape_ratio: Shiller Cyclically-Adjusted P/E (CAPE) — smooths over
            10 years of earnings to filter out cyclical noise.
        ev_ebitda: Enterprise-value-to-EBITDA ratio for the S&P 500.
    """
    score = 0
    components = {}

    # Trailing P/E: >25 is historically expensive
    if pe_ratio is not None:
        components["pe_ratio"] = pe_ratio
        if pe_ratio > 25:
            score += 35
        elif pe_ratio > 20:
            score += 20
        elif pe_ratio > 18:
            score += 10

    # CAPE: >35 is rare territory (dot-com peak was ~44)
    if cape_ratio is not None:
        components["cape_ratio"] = cape_ratio
        if cape_ratio > 35:
            score += 35
        elif cape_ratio > 28:
            score += 20
        elif cape_ratio > 22:
            score += 10

    # EV/EBITDA: >16 suggests stretched enterprise valuations
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


# =========================================================================
# Signal 3: Credit Complacency
# =========================================================================

def evaluate_credit(hy_spread_bps=None, ig_spread_bps=None,
                    hy_spread_percentile=None):
    """Score credit market complacency (S3).

    Tight credit spreads indicate investors are not demanding enough
    compensation for default risk — a classic late-cycle signal.

    Args:
        hy_spread_bps: High-yield OAS spread in basis points (ICE BofA index).
        ig_spread_bps: Investment-grade OAS spread in basis points.
        hy_spread_percentile: Current HY spread percentile vs. its own
            history (0-100). Lower = tighter = more complacent.
    """
    score = 0
    components = {}

    # HY OAS < 300 bps = extremely tight (historical median ~450)
    if hy_spread_bps is not None:
        components["hy_spread_bps"] = hy_spread_bps
        if hy_spread_bps < 300:
            score += 40
        elif hy_spread_bps < 400:
            score += 25
        elif hy_spread_bps < 500:
            score += 10

    # Percentile: below 10th percentile = historically rare tightness
    if hy_spread_percentile is not None:
        components["hy_spread_percentile"] = hy_spread_percentile
        if hy_spread_percentile < 10:
            score += 35
        elif hy_spread_percentile < 25:
            score += 20
        elif hy_spread_percentile < 40:
            score += 10

    # IG spreads add confirmation
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


# =========================================================================
# Signal 4: Sentiment Extremes
# =========================================================================

def evaluate_sentiment(aaii_bull_bear_spread=None, vix=None,
                       put_call_ratio=None, fear_greed_index=None):
    """Score investor sentiment extremes (S4).

    Extreme bullishness and low volatility are contrarian warning signs.
    When "everyone" is bullish, there are few marginal buyers left.

    Args:
        aaii_bull_bear_spread: AAII weekly survey bull% minus bear%. >30 = extreme.
        vix: CBOE VIX index. <12 = extreme complacency.
        put_call_ratio: Equity put/call ratio. <0.7 = too many calls.
        fear_greed_index: CNN Fear & Greed Index (0=fear, 100=greed).
    """
    score = 0
    components = {}

    # AAII: spread > 30 = extreme bullish consensus
    if aaii_bull_bear_spread is not None:
        components["aaii_bull_bear_spread"] = aaii_bull_bear_spread
        if aaii_bull_bear_spread > 30:
            score += 30
        elif aaii_bull_bear_spread > 15:
            score += 15

    # VIX: < 12 = extreme complacency (no hedging demand)
    if vix is not None:
        components["vix"] = vix
        if vix < 12:
            score += 25
        elif vix < 15:
            score += 15

    # Put/Call: < 0.7 = too many calls relative to puts
    if put_call_ratio is not None:
        components["put_call_ratio"] = put_call_ratio
        if put_call_ratio < 0.7:
            score += 25
        elif put_call_ratio < 0.85:
            score += 10

    # Fear & Greed: > 80 = extreme greed
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


# =========================================================================
# Signal 5: Macro Deterioration (LEI / ISM)
# =========================================================================

def evaluate_macro(lei_yoy_change=None, lei_monthly_change=None,
                   private_lei_yoy_change=None, ism_manufacturing=None):
    """Score macro deterioration via Leading Economic Indicators (S5).

    The Conference Board LEI has a strong track record of leading recessions
    by 6-12 months. Under fiscal dominance, the headline LEI may be inflated
    by government spending; the private-sector LEI (ex-government components)
    is used instead — see the scoring engine for the re-scoring logic.

    Args:
        lei_yoy_change: Conference Board LEI year-over-year % change.
        lei_monthly_change: LEI month-over-month % change.
        private_lei_yoy_change: Private-sector LEI (ex-government) YoY %.
        ism_manufacturing: ISM Manufacturing PMI (50 = expansion/contraction boundary).
    """
    score = 0
    components = {}

    # LEI YoY: negative = economy weakening; < -5% = recession imminent
    if lei_yoy_change is not None:
        components["lei_yoy_change"] = lei_yoy_change
        if lei_yoy_change < -5:
            score += 35
        elif lei_yoy_change < -2:
            score += 25
        elif lei_yoy_change < 0:
            score += 15

    # LEI MoM: consecutive monthly declines amplify the signal
    if lei_monthly_change is not None:
        components["lei_monthly_change"] = lei_monthly_change
        if lei_monthly_change < -0.5:
            score += 20
        elif lei_monthly_change < -0.2:
            score += 10

    # ISM Manufacturing: < 50 = contraction, < 45 = severe contraction
    if ism_manufacturing is not None:
        components["ism_manufacturing"] = ism_manufacturing
        if ism_manufacturing < 45:
            score += 25
        elif ism_manufacturing < 48:
            score += 15
        elif ism_manufacturing < 50:
            score += 10

    # Private-sector LEI is stored here but scored in the scoring engine
    # when the Fiscal Dominance flag is active (strips out government spending)
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


# =========================================================================
# Signal 6: Margin Debt / Leverage
# =========================================================================

def evaluate_leverage(margin_debt_yoy_pct=None, margin_debt_to_gdp=None,
                      margin_debt_percentile=None):
    """Score speculative leverage levels (S6).

    Excessive margin debt creates fragility: when prices fall, leveraged
    investors face margin calls and are forced to sell, accelerating the
    decline (reflexive feedback loop).

    Args:
        margin_debt_yoy_pct: Year-over-year change in margin debt (%).
        margin_debt_to_gdp: Margin debt as % of GDP.
        margin_debt_percentile: Current margin debt level vs. history (0-100).
    """
    score = 0
    components = {}

    # YoY growth > 30% = speculative excess (2021 peaked at ~70%)
    if margin_debt_yoy_pct is not None:
        components["margin_debt_yoy_pct"] = margin_debt_yoy_pct
        if margin_debt_yoy_pct > 30:
            score += 40
        elif margin_debt_yoy_pct > 15:
            score += 25
        elif margin_debt_yoy_pct > 5:
            score += 10

    # Debt/GDP > 3.5% = historically stretched
    if margin_debt_to_gdp is not None:
        components["margin_debt_to_gdp"] = margin_debt_to_gdp
        if margin_debt_to_gdp > 3.5:
            score += 35
        elif margin_debt_to_gdp > 2.5:
            score += 20

    # Percentile > 90 = near historical highs
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


# =========================================================================
# Signal 7: Term Premium / Fiscal Stress
# =========================================================================

def evaluate_term_premium(
    spread_2s10s_bps=None,
    term_premium_10y=None,
    term_premium_5y_avg=None,
    deficit_pct_gdp=None,
    debt_service_pct_revenue=None,
    fed_cutting=None,
):
    """Score term premium and fiscal stress indicators (S7).

    This is the yield-curve signal reinterpreted for fiscal dominance.
    Traditional view: inversion (negative 2s10s) = recession signal.
    Fiscal dominance view: steepening for the "wrong reasons" — bond supply
    pressure and rising term premium while the Fed is cutting — is a sign
    the bond market is losing confidence in the fiscal trajectory.

    The key tell is: curve steepening + rising term premium + rising deficit
    + Fed easing, all occurring simultaneously.

    Args:
        spread_2s10s_bps: 2s10s spread in basis points (FRED T10Y2Y * 100).
        term_premium_10y: 10-year term premium from NY Fed ACM model (%).
        term_premium_5y_avg: 5-year average of 10y term premium (%).
        deficit_pct_gdp: Federal deficit as % of GDP (positive = deficit).
        debt_service_pct_revenue: Federal interest outlays / tax revenue (%).
        fed_cutting: Boolean — whether the Fed is currently in a cutting cycle.
    """
    score = 0
    components = {}

    # --- 2s10s slope assessment ---
    # Under Fed cuts: steepening = fiscal stress (bond market pushing back)
    # Under Fed hikes: inversion = traditional recession signal
    if spread_2s10s_bps is not None:
        components["spread_2s10s_bps"] = spread_2s10s_bps
        if fed_cutting:
            # Steepening while Fed cuts = fiscal dominance stress signal
            if spread_2s10s_bps > 100:
                score += 30
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

    # --- Term premium assessment ---
    # Compare current to 5-year average; excess = bond market demanding
    # fiscal risk compensation above normal levels
    if term_premium_10y is not None:
        components["term_premium_10y"] = term_premium_10y
        if term_premium_5y_avg is not None:
            components["term_premium_5y_avg"] = term_premium_5y_avg
            premium_excess = term_premium_10y - term_premium_5y_avg
            components["term_premium_excess"] = premium_excess
            if premium_excess > 0.75:
                score += 25
            elif premium_excess > 0.50:
                score += 20
            elif premium_excess > 0.25:
                score += 10
        else:
            # Without 5y average, fall back to absolute level
            if term_premium_10y > 1.0:
                score += 20
            elif term_premium_10y > 0.5:
                score += 10

    # --- Deficit trajectory ---
    # > 7% of GDP outside a recession is historically exceptional
    if deficit_pct_gdp is not None:
        components["deficit_pct_gdp"] = deficit_pct_gdp
        if deficit_pct_gdp > 7:
            score += 25
        elif deficit_pct_gdp > 6:
            score += 20
        elif deficit_pct_gdp > 5:
            score += 10

    # --- Debt service ratio ---
    # Interest outlays > 25% of revenue = fiscal stress territory
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


# =========================================================================
# Fiscal Dominance Flag
# =========================================================================

@dataclass
class FiscalDominanceFlag:
    """Structural modifier that changes interpretation of all signals.

    Activates when 3 of 4 conditions are met simultaneously:
      1. Federal deficit / GDP > 5% in a non-recession year
      2. Interest expense / tax revenue > 15%
      3. Fed easing while inflation > target (FFR declining AND core PCE > 2.5%)
      4. 2s10s steepening > 75 bps + rising term premium (3-month trend)

    When active:
      - +10 point modifier to composite score
      - Signal 5 rescored using private-sector LEI
      - Signal 7 added to the scored set at 1.5x weight
      - All signal interpretations adjusted for fiscal distortion
    """
    active: bool = False
    conditions_met: int = 0
    condition_details: dict = field(default_factory=dict)
    caution_modifier: int = 0  # +10 when active

    @property
    def signal_interpretation_overrides(self):
        """Return modified signal interpretations when fiscal dominance is active."""
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

    The flag fires when 3 of 4 conditions are true. Each condition tests a
    different facet of fiscal/monetary stress:

    Args:
        deficit_pct_gdp: Federal deficit as % of GDP (positive = deficit).
        in_recession: Whether the economy is officially in an NBER recession.
            The deficit condition is excluded during recessions because large
            deficits are expected counter-cyclical policy.
        interest_pct_revenue: Interest expense / tax revenue (%).
        fed_funds_rate_declining: Whether the Fed funds rate is falling.
        core_pce_yoy: Core PCE year-over-year (%).
        spread_2s10s_bps: 2s10s spread in basis points.
        term_premium_rising: Whether 10y term premium is on a rising 3-month trend.
    """
    conditions_met = 0
    details = {}

    # Condition 1: Deficit > 5% of GDP in a non-recession year
    # Large deficits during recessions are normal (automatic stabilizers);
    # large deficits during expansions are the fiscal dominance signal
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
    # When debt service consumes a large share of revenue, the government
    # has less fiscal flexibility and must issue more debt to service existing debt
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
    # The Fed cutting rates while core PCE is still above 2.5% suggests
    # fiscal/political pressure is overriding the inflation mandate
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
    # The curve steepening while term premium is rising = bond market
    # demanding more compensation for holding long-term government debt
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

    # 3-of-4 activation threshold
    active = conditions_met >= 3
    return FiscalDominanceFlag(
        active=active,
        conditions_met=conditions_met,
        condition_details=details,
        caution_modifier=10 if active else 0,
    )
