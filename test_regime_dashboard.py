"""Tests for the regime dashboard scoring engine, signals, and fiscal dominance flag."""

import pytest

from regime_dashboard.signals import (
    evaluate_breadth,
    evaluate_credit,
    evaluate_fiscal_dominance,
    evaluate_leverage,
    evaluate_macro,
    evaluate_sentiment,
    evaluate_term_premium,
    evaluate_valuation,
    score_to_level,
)
from regime_dashboard.scoring_engine import compute_regime_score


# ---------------------------------------------------------------------------
# score_to_level
# ---------------------------------------------------------------------------

class TestScoreToLevel:
    def test_extreme(self):
        assert score_to_level(52) == "extreme"
        assert score_to_level(100) == "extreme"

    def test_high(self):
        assert score_to_level(38) == "high"
        assert score_to_level(51) == "high"

    def test_elevated(self):
        assert score_to_level(26) == "elevated"
        assert score_to_level(37) == "elevated"

    def test_moderate(self):
        assert score_to_level(14) == "moderate"
        assert score_to_level(25) == "moderate"

    def test_low(self):
        assert score_to_level(0) == "low"
        assert score_to_level(13) == "low"


# ---------------------------------------------------------------------------
# Signal 1: Breadth Divergence
# ---------------------------------------------------------------------------

class TestBreadth:
    def test_no_data_scores_zero(self):
        result = evaluate_breadth()
        assert result.score == 0
        assert result.level == "low"

    def test_poor_breadth_scores_high(self):
        result = evaluate_breadth(
            pct_above_200dma=35,
            advance_decline_line_trend="declining",
            new_highs_vs_new_lows=0.8,
        )
        assert result.score >= 80
        assert result.level == "extreme"

    def test_healthy_breadth_scores_low(self):
        result = evaluate_breadth(
            pct_above_200dma=75,
            advance_decline_line_trend="rising",
            new_highs_vs_new_lows=5.0,
            top_10_concentration_pct=35,
        )
        assert result.score == 0
        assert result.level == "low"

    def test_extreme_concentration_adds_to_score(self):
        """Top-10 > 60% of returns fires the concentration sub-component."""
        result = evaluate_breadth(top_10_concentration_pct=70)
        assert result.score == 20
        assert result.components["top_10_concentration_pct"] == 70

    def test_dotcom_level_concentration(self):
        """Top-10 > 75% = historically rare, maximum score."""
        result = evaluate_breadth(top_10_concentration_pct=80)
        assert result.score == 25

    def test_concentration_plus_poor_breadth(self):
        """Concentration + breadth deterioration together = stronger signal."""
        result = evaluate_breadth(
            pct_above_200dma=35,
            advance_decline_line_trend="declining",
            new_highs_vs_new_lows=0.8,
            top_10_concentration_pct=70,
        )
        assert result.score == 100  # Capped at 100
        assert result.level == "extreme"

    def test_moderate_concentration_below_threshold(self):
        """Top-10 at 45% (normal range) = no contribution."""
        result = evaluate_breadth(top_10_concentration_pct=45)
        assert result.score == 0


# ---------------------------------------------------------------------------
# Signal 2: Valuation
# ---------------------------------------------------------------------------

class TestValuation:
    def test_no_data_scores_zero(self):
        assert evaluate_valuation().score == 0

    def test_expensive_market(self):
        result = evaluate_valuation(pe_ratio=28, cape_ratio=38, ev_ebitda=18)
        assert result.score >= 80

    def test_cheap_market(self):
        result = evaluate_valuation(pe_ratio=14, cape_ratio=18, ev_ebitda=10)
        assert result.score == 0


# ---------------------------------------------------------------------------
# Signal 3: Credit Complacency
# ---------------------------------------------------------------------------

class TestCredit:
    def test_tight_ccc_bb_and_single_b_score_high(self):
        """Tight CCC-BB percentile + tight Single-B + tight IG = extreme."""
        result = evaluate_credit(
            ccc_bb_spread_percentile=5, single_b_oas_percentile=5,
            ig_spread_bps=70,
        )
        assert result.score >= 80

    def test_wide_ccc_bb_and_single_b_score_low(self):
        """Wide CCC-BB + wide Single-B + wide IG = no signal."""
        result = evaluate_credit(
            ccc_bb_spread_percentile=60, single_b_oas_percentile=60,
            ig_spread_bps=180,
        )
        assert result.score == 0

    def test_legacy_fallback_tight(self):
        """When no CCC-BB or Single-B provided, legacy HY OAS is used."""
        result = evaluate_credit(hy_spread_bps=250, hy_spread_percentile=5,
                                 ig_spread_bps=70)
        assert result.score >= 80

    def test_legacy_fallback_wide(self):
        """Legacy path: wide spreads = no signal."""
        result = evaluate_credit(hy_spread_bps=600, hy_spread_percentile=60,
                                 ig_spread_bps=180)
        assert result.score == 0

    def test_widening_fast_override(self):
        """Single-B 3mo change > 150 bps floors score at 70."""
        # Without the override, these percentiles would score low
        result = evaluate_credit(
            ccc_bb_spread_percentile=50,
            single_b_oas_percentile=50,
            single_b_oas_3mo_change_bps=200,
        )
        assert result.score >= 70
        assert result.components.get("widening_fast") is True

    def test_widening_fast_does_not_lower_score(self):
        """WIDENING_FAST only floors — doesn't reduce an already-high score."""
        result = evaluate_credit(
            ccc_bb_spread_percentile=5,
            single_b_oas_percentile=5,
            ig_spread_bps=70,
            single_b_oas_3mo_change_bps=200,
        )
        assert result.score >= 80  # Already high, override doesn't lower

    def test_ccc_bb_bps_fallback(self):
        """CCC-BB absolute bps used when percentile not available."""
        result = evaluate_credit(ccc_bb_spread_bps=350)
        assert result.score >= 30  # < 400 = tight

    def test_single_b_bps_fallback(self):
        """Single-B absolute bps used when percentile not available."""
        result = evaluate_credit(single_b_oas_bps=250)
        assert result.score >= 25  # < 300 = tight


# ---------------------------------------------------------------------------
# Signal 4: Sentiment
# ---------------------------------------------------------------------------

class TestSentiment:
    def test_extreme_greed(self):
        result = evaluate_sentiment(
            aaii_bull_bear_spread=35, vix=11, put_call_ratio=0.6, fear_greed_index=85,
        )
        assert result.score >= 80

    def test_neutral_sentiment(self):
        result = evaluate_sentiment(
            aaii_bull_bear_spread=5, vix=20, put_call_ratio=1.0, fear_greed_index=50,
        )
        assert result.score == 0


# ---------------------------------------------------------------------------
# Signal 5: Macro Deterioration
# ---------------------------------------------------------------------------

class TestMacro:
    def test_declining_lei(self):
        result = evaluate_macro(lei_yoy_change=-6, lei_monthly_change=-0.6, ism_manufacturing=44)
        assert result.score >= 60

    def test_strong_macro(self):
        result = evaluate_macro(lei_yoy_change=3, lei_monthly_change=0.3, ism_manufacturing=55)
        assert result.score == 0

    def test_private_lei_stored(self):
        result = evaluate_macro(private_lei_yoy_change=-4.0)
        assert result.components["private_lei_yoy_change"] == -4.0


# ---------------------------------------------------------------------------
# Signal 6: Leverage
# ---------------------------------------------------------------------------

class TestLeverage:
    def test_excessive_leverage(self):
        result = evaluate_leverage(
            margin_debt_yoy_pct=35, margin_debt_to_gdp=4.0, margin_debt_percentile=95,
        )
        assert result.score >= 80

    def test_normal_leverage(self):
        result = evaluate_leverage(margin_debt_yoy_pct=3, margin_debt_to_gdp=2.0)
        assert result.score == 0


# ---------------------------------------------------------------------------
# Signal 7: Term Premium / Fiscal Stress
# ---------------------------------------------------------------------------

class TestTermPremium:
    def test_no_data_scores_zero(self):
        assert evaluate_term_premium().score == 0

    def test_fiscal_stress_steepening(self):
        """Steepening > 100bps while Fed is cutting + high deficit + high debt service."""
        result = evaluate_term_premium(
            spread_2s10s_bps=120,
            term_premium_10y=1.0,
            term_premium_5y_avg=0.2,
            deficit_pct_gdp=7.5,
            debt_service_pct_revenue=22,
            fed_cutting=True,
        )
        # Should score high: 30 (curve) + 25 (term premium excess 0.8) + 25 (deficit) + 15 (debt service)
        assert result.score >= 80
        assert result.level == "extreme"

    def test_normal_steepening_not_alarming(self):
        """Mild steepening while Fed is NOT cutting = not stressed."""
        result = evaluate_term_premium(
            spread_2s10s_bps=80,
            deficit_pct_gdp=3,
            fed_cutting=False,
        )
        assert result.score == 0

    def test_inverted_curve_conventional(self):
        """Deep inversion in non-fiscal-dominance = recession signal."""
        result = evaluate_term_premium(
            spread_2s10s_bps=-60,
            fed_cutting=False,
        )
        assert result.score >= 20
        assert result.components["spread_2s10s_bps"] == -60

    def test_term_premium_excess(self):
        """Rising term premium above 5y average."""
        result = evaluate_term_premium(
            term_premium_10y=1.2,
            term_premium_5y_avg=0.3,
        )
        assert result.components["term_premium_excess"] == pytest.approx(0.9)
        assert result.score >= 20


# ---------------------------------------------------------------------------
# Fiscal Dominance Flag
# ---------------------------------------------------------------------------

class TestFiscalDominanceFlag:
    def test_no_data_inactive(self):
        flag = evaluate_fiscal_dominance()
        assert not flag.active
        assert flag.conditions_met == 0
        assert flag.caution_modifier == 0

    def test_all_conditions_met(self):
        """All 4 conditions met = active."""
        flag = evaluate_fiscal_dominance(
            deficit_pct_gdp=7.0,
            in_recession=False,
            interest_pct_revenue=20,
            fed_funds_rate_declining=True,
            core_pce_yoy=3.0,
            spread_2s10s_bps=100,
            term_premium_rising=True,
        )
        assert flag.active
        assert flag.conditions_met == 4
        assert flag.caution_modifier == 10

    def test_three_conditions_activates(self):
        """3 of 4 conditions met = active."""
        flag = evaluate_fiscal_dominance(
            deficit_pct_gdp=6.0,
            in_recession=False,
            interest_pct_revenue=18,
            fed_funds_rate_declining=True,
            core_pce_yoy=3.0,
            spread_2s10s_bps=50,  # Below 75 threshold - condition 4 NOT met
            term_premium_rising=True,
        )
        assert flag.active
        assert flag.conditions_met == 3

    def test_two_conditions_inactive(self):
        """Only 2 of 4 conditions met = inactive."""
        flag = evaluate_fiscal_dominance(
            deficit_pct_gdp=6.0,
            in_recession=False,
            interest_pct_revenue=10,  # Below 15% - NOT met
            fed_funds_rate_declining=True,
            core_pce_yoy=3.0,
            spread_2s10s_bps=50,  # Below 75 - NOT met
            term_premium_rising=False,
        )
        assert not flag.active
        assert flag.conditions_met == 2

    def test_recession_excludes_deficit_condition(self):
        """Deficit condition requires non-recession year."""
        flag = evaluate_fiscal_dominance(
            deficit_pct_gdp=8.0,
            in_recession=True,  # In recession - deficit condition excluded
            interest_pct_revenue=10,
            fed_funds_rate_declining=True,
            core_pce_yoy=3.0,
            spread_2s10s_bps=100,
            term_premium_rising=True,
        )
        # Deficit excluded, interest not met, fed+pce met, curve+tp met = 2/4
        assert flag.conditions_met == 2
        assert not flag.active

    def test_condition_details_populated(self):
        flag = evaluate_fiscal_dominance(
            deficit_pct_gdp=6.0,
            in_recession=False,
            interest_pct_revenue=20,
        )
        assert "deficit_gt_5pct" in flag.condition_details
        assert flag.condition_details["deficit_gt_5pct"]["met"] is True
        assert flag.condition_details["interest_gt_15pct_revenue"]["met"] is True


# ---------------------------------------------------------------------------
# Scoring Engine
# ---------------------------------------------------------------------------

class TestScoringEngine:
    def test_empty_signals(self):
        from regime_dashboard.signals import FiscalDominanceFlag
        result = compute_regime_score([], FiscalDominanceFlag())
        assert result.raw_composite_score == 0
        assert result.regime_level == "low"

    def test_fiscal_dominance_adds_modifier(self):
        """Active fiscal dominance adds +10 to composite score."""
        from regime_dashboard.signals import FiscalDominanceFlag

        signals = [
            evaluate_valuation(pe_ratio=22, cape_ratio=30),
            evaluate_credit(single_b_oas_bps=350),
        ]

        # Without fiscal dominance
        fd_inactive = FiscalDominanceFlag(active=False, caution_modifier=0)
        result_normal = compute_regime_score(signals, fd_inactive)

        # With fiscal dominance
        fd_active = FiscalDominanceFlag(active=True, caution_modifier=10, conditions_met=3)
        result_fd = compute_regime_score(signals, fd_active)

        # The +10 modifier is applied, but weighting differences may shift the raw score slightly
        assert result_fd.fiscal_dominance.caution_modifier == 10
        assert result_fd.adjusted_composite_score == pytest.approx(
            result_fd.raw_composite_score + 10, abs=0.1
        )
        assert result_fd.adjusted_composite_score > result_normal.adjusted_composite_score

    def test_signal7_scored_under_fiscal_dominance(self):
        """Signal 7 is included in scoring when fiscal dominance is active."""
        from regime_dashboard.signals import FiscalDominanceFlag

        s7 = evaluate_term_premium(
            spread_2s10s_bps=120, deficit_pct_gdp=7, fed_cutting=True,
        )
        fd_active = FiscalDominanceFlag(active=True, caution_modifier=10, conditions_met=3)
        result = compute_regime_score([s7], fd_active)
        # Signal 7 should be scored with weight 1.5
        assert result.raw_composite_score > 0

    def test_signal7_excluded_from_normal_regime(self):
        """Signal 7 has weight 0 in normal regime (only contributes under FD)."""
        from regime_dashboard.signals import FiscalDominanceFlag

        s7 = evaluate_term_premium(spread_2s10s_bps=120, deficit_pct_gdp=7, fed_cutting=True)
        fd_inactive = FiscalDominanceFlag(active=False, caution_modifier=0)
        result = compute_regime_score([s7], fd_inactive)
        # S7 excluded from normal composite — near-random standalone predictor
        assert result.raw_composite_score == 0

    def test_private_lei_rescoring_under_fd(self):
        """Under fiscal dominance, Signal 5 is rescored using private-sector LEI."""
        from regime_dashboard.signals import FiscalDominanceFlag

        s5 = evaluate_macro(lei_yoy_change=1.0, private_lei_yoy_change=-3.5)
        fd_active = FiscalDominanceFlag(active=True, caution_modifier=10, conditions_met=3)
        result = compute_regime_score([s5], fd_active)

        # With private LEI of -3.5, Signal 5 should be rescored to 60
        macro_signal = [s for s in result.signals if s.name == "Macro Deterioration"][0]
        assert macro_signal.score == 60

    def test_full_dashboard_example(self):
        """Full integration test with approximate April 2026 conditions."""
        from regime_dashboard.dashboard import run_dashboard_manual

        assessment = run_dashboard_manual(
            pct_above_200dma=52,
            advance_decline_line_trend="flat",
            new_highs_vs_new_lows=1.5,
            top_10_concentration_pct=68,
            pe_ratio=23,
            cape_ratio=33,
            ev_ebitda=15,
            ccc_bb_spread_bps=480,
            ccc_bb_spread_percentile=15,
            single_b_oas_bps=260,
            single_b_oas_percentile=12,
            single_b_oas_3mo_change_bps=-10,
            ig_spread_bps=90,
            aaii_bull_bear_spread=18,
            vix=14,
            put_call_ratio=0.82,
            fear_greed_index=68,
            lei_yoy_change=-1.5,
            lei_monthly_change=-0.3,
            private_lei_yoy_change=-3.0,
            ism_manufacturing=48.5,
            margin_debt_yoy_pct=18,
            margin_debt_to_gdp=2.8,
            margin_debt_percentile=78,
            spread_2s10s_bps=110,
            term_premium_10y=0.85,
            term_premium_5y_avg=0.20,
            deficit_pct_gdp=6.5,
            debt_service_pct_revenue=22,
            fed_cutting=True,
            in_recession=False,
            interest_pct_revenue=22,
            fed_funds_rate_declining=True,
            core_pce_yoy=2.8,
            term_premium_rising=True,
        )

        # Fiscal dominance should be active (all 4 conditions met)
        assert assessment.fiscal_dominance.active
        assert assessment.fiscal_dominance.conditions_met == 4

        # Composite should be elevated or higher
        assert assessment.adjusted_composite_score >= 40

        # Should have warnings
        assert len(assessment.warnings) >= 1

        # All 7 signals should be present
        assert len(assessment.signals) == 7

    def test_to_dict_serializable(self):
        """Assessment can be serialized to dict/JSON."""
        import json
        from regime_dashboard.dashboard import run_dashboard_manual

        assessment = run_dashboard_manual(pe_ratio=20, deficit_pct_gdp=6)
        data = assessment.to_dict()
        json_str = json.dumps(data)
        assert "regime_level" in json_str
