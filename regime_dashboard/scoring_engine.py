"""Scoring engine that aggregates all signals into a regime assessment.

When the Fiscal Dominance Flag is active:
1. +10 point modifier to the overall caution level
2. Signal 5 (Macro) reweighted to use private-sector LEI
3. Signal 7 (Term Premium) added to the scored set
4. All signal interpretations adjusted for fiscal distortion
"""

from dataclasses import dataclass, field

from .signals import (
    FiscalDominanceFlag,
    SignalReading,
    score_to_level,
)


@dataclass
class RegimeAssessment:
    """Complete regime dashboard output."""
    signals: list  # List of SignalReading
    fiscal_dominance: FiscalDominanceFlag
    raw_composite_score: float
    adjusted_composite_score: float
    regime_level: str  # 'low', 'moderate', 'elevated', 'high', 'extreme'
    warnings: list = field(default_factory=list)

    @property
    def signal_count(self):
        return len(self.signals)

    def to_dict(self):
        """Serialize to dict for JSON output / dashboard rendering."""
        return {
            "regime_level": self.regime_level,
            "raw_composite_score": round(self.raw_composite_score, 1),
            "adjusted_composite_score": round(self.adjusted_composite_score, 1),
            "fiscal_dominance_active": self.fiscal_dominance.active,
            "fiscal_dominance_conditions_met": self.fiscal_dominance.conditions_met,
            "fiscal_dominance_modifier": self.fiscal_dominance.caution_modifier,
            "warnings": self.warnings,
            "signals": [
                {
                    "name": s.name,
                    "score": s.score,
                    "level": s.level,
                    "components": s.components,
                    "interpretation": s.interpretation,
                    "fiscal_dominance_note": s.fiscal_dominance_note,
                }
                for s in self.signals
            ],
            "fiscal_dominance_details": self.fiscal_dominance.condition_details,
        }


# Default weights for signals 1-6 (normal regime)
NORMAL_WEIGHTS = {
    "Breadth Divergence": 1.0,
    "Valuation": 1.0,
    "Credit Complacency": 1.0,
    "Sentiment Extremes": 1.0,
    "Macro Deterioration": 1.0,
    "Margin Debt / Leverage": 1.0,
}

# Weights when fiscal dominance is active (Signal 7 added, Signal 5 de-emphasized
# because government spending masks private-sector weakness)
FISCAL_DOMINANCE_WEIGHTS = {
    "Breadth Divergence": 1.0,
    "Valuation": 1.2,  # More fragile under fiscal dominance
    "Credit Complacency": 1.3,  # Spreads may be artificially suppressed
    "Sentiment Extremes": 1.0,
    "Macro Deterioration": 0.7,  # LEI distorted by government spending
    "Margin Debt / Leverage": 1.0,
    "Term Premium / Fiscal Stress": 1.5,  # Primary fiscal dominance indicator
}


def compute_regime_score(
    signals: list[SignalReading],
    fiscal_dominance: FiscalDominanceFlag,
) -> RegimeAssessment:
    """Compute the overall regime assessment from individual signals.

    Args:
        signals: List of SignalReading objects (signals 1-7)
        fiscal_dominance: The fiscal dominance flag evaluation

    Returns:
        RegimeAssessment with composite score and interpretation
    """
    warnings = []

    # Select weight set
    if fiscal_dominance.active:
        weights = FISCAL_DOMINANCE_WEIGHTS
        warnings.append(
            "FISCAL DOMINANCE FLAG ACTIVE: Signal readings may be distorted by "
            "fiscal conditions. +10 caution modifier applied."
        )
    else:
        weights = NORMAL_WEIGHTS

    # Apply fiscal dominance interpretation overrides
    overrides = fiscal_dominance.signal_interpretation_overrides
    for signal in signals:
        if signal.name in overrides:
            signal.fiscal_dominance_note = overrides[signal.name]

    # Under fiscal dominance, if Signal 5 has private-sector LEI data,
    # substitute it for the headline LEI score
    if fiscal_dominance.active:
        for signal in signals:
            if signal.name == "Macro Deterioration":
                private_lei = signal.components.get("private_lei_yoy_change")
                if private_lei is not None:
                    # Re-score using private LEI only
                    if private_lei < -5:
                        signal.score = 80
                    elif private_lei < -2:
                        signal.score = 60
                    elif private_lei < 0:
                        signal.score = 40
                    else:
                        signal.score = 15
                    signal.level = score_to_level(signal.score)
                    signal.interpretation = (
                        "Rescored using private-sector LEI (ex-government). "
                        "Headline LEI is distorted by fiscal stimulus."
                    )
                    warnings.append(
                        "Signal 5 (Macro) rescored using private-sector LEI to strip "
                        "government spending distortion."
                    )

    # Compute weighted composite
    total_weight = 0
    weighted_sum = 0
    scored_signals = []

    for signal in signals:
        weight = weights.get(signal.name)
        if weight is None:
            # Signal not in weight set (e.g., Signal 7 in normal regime) - skip
            if not fiscal_dominance.active and signal.name == "Term Premium / Fiscal Stress":
                # Still display but don't score in normal regime
                signal.fiscal_dominance_note = (
                    "Not scored in normal regime. Monitored for fiscal dominance detection."
                )
            continue
        scored_signals.append(signal)
        weighted_sum += signal.score * weight
        total_weight += weight

    if total_weight > 0:
        raw_composite = weighted_sum / total_weight
    else:
        raw_composite = 0

    # Apply fiscal dominance modifier
    adjusted_composite = min(raw_composite + fiscal_dominance.caution_modifier, 100)

    # Generate additional warnings based on composite
    if adjusted_composite >= 80:
        warnings.append(
            "EXTREME CAUTION: Multiple topping signals firing simultaneously. "
            "Risk of significant drawdown is elevated."
        )
    elif adjusted_composite >= 60:
        warnings.append(
            "HIGH CAUTION: Several signals indicating market fragility. "
            "Consider reducing risk exposure."
        )

    # Check for individual extreme signals
    extreme_signals = [s for s in signals if s.score >= 80]
    if len(extreme_signals) >= 2:
        names = ", ".join(s.name for s in extreme_signals)
        warnings.append(f"Multiple extreme signals: {names}")

    return RegimeAssessment(
        signals=signals,
        fiscal_dominance=fiscal_dominance,
        raw_composite_score=raw_composite,
        adjusted_composite_score=adjusted_composite,
        regime_level=score_to_level(adjusted_composite),
        warnings=warnings,
    )
