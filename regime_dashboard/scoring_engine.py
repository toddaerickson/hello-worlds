"""Scoring engine — aggregates all signals into a single regime assessment.

This module takes a list of SignalReading objects (one per signal) plus a
FiscalDominanceFlag, and produces a weighted composite score (0-100).

Scoring logic:
  1. Select weight set (normal vs. fiscal dominance).
  2. Apply FD interpretation overrides to each signal.
  3. Under FD, re-score Signal 5 (Macro) using private-sector LEI.
  4. Compute weighted average of all active signals.
  5. Add the FD modifier (+10 when active).
  6. Generate warnings based on composite and individual signal levels.
"""

from dataclasses import dataclass, field

from .signals import (
    FiscalDominanceFlag,
    SignalReading,
    score_to_level,
)


# =========================================================================
# Output data class
# =========================================================================

@dataclass
class RegimeAssessment:
    """Complete regime dashboard output.

    Attributes:
        signals: All 7 SignalReading objects (scored and annotated).
        fiscal_dominance: The evaluated FiscalDominanceFlag.
        raw_composite_score: Weighted average before the FD modifier.
        adjusted_composite_score: Final score after FD modifier (capped at 100).
        regime_level: Named level derived from adjusted score.
        warnings: List of human-readable warning strings.
    """
    signals: list
    fiscal_dominance: FiscalDominanceFlag
    raw_composite_score: float
    adjusted_composite_score: float
    regime_level: str
    warnings: list = field(default_factory=list)

    @property
    def signal_count(self):
        return len(self.signals)

    def to_dict(self):
        """Serialize to a plain dict for JSON output or dashboard rendering."""
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


# =========================================================================
# Weight sets
# =========================================================================

# Normal regime: Signals 1-6 scored equally, Signal 7 is monitored but not scored.
NORMAL_WEIGHTS = {
    "Breadth Divergence": 1.0,
    "Valuation": 1.0,
    "Credit Complacency": 1.0,
    "Sentiment Extremes": 1.0,
    "Macro Deterioration": 1.0,
    "Margin Debt / Leverage": 1.0,
}

# Fiscal dominance regime: Signal 7 added at 1.5x, Valuation and Credit
# up-weighted (more fragile), Macro de-emphasized (government spending
# inflates headline LEI).
FISCAL_DOMINANCE_WEIGHTS = {
    "Breadth Divergence": 1.0,
    "Valuation": 1.2,               # More fragile under FD
    "Credit Complacency": 1.3,      # Spreads may be artificially suppressed
    "Sentiment Extremes": 1.0,
    "Macro Deterioration": 0.7,     # LEI distorted by government spending
    "Margin Debt / Leverage": 1.0,
    "Term Premium / Fiscal Stress": 1.5,  # Primary fiscal dominance indicator
}


# =========================================================================
# Main scoring function
# =========================================================================

def compute_regime_score(
    signals: list[SignalReading],
    fiscal_dominance: FiscalDominanceFlag,
) -> RegimeAssessment:
    """Compute the overall regime assessment from individual signals.

    Args:
        signals: List of SignalReading objects (typically signals 1-7).
        fiscal_dominance: The evaluated fiscal dominance flag.

    Returns:
        RegimeAssessment with composite score, level, and warnings.
    """
    warnings = []

    # --- Step 1: Select weight set based on FD flag ---
    if fiscal_dominance.active:
        weights = FISCAL_DOMINANCE_WEIGHTS
        warnings.append(
            "FISCAL DOMINANCE FLAG ACTIVE: Signal readings may be distorted by "
            "fiscal conditions. +10 caution modifier applied."
        )
    else:
        weights = NORMAL_WEIGHTS

    # --- Step 2: Apply FD interpretation overrides ---
    # Each signal gets an additional note explaining how fiscal dominance
    # changes its interpretation
    overrides = fiscal_dominance.signal_interpretation_overrides
    for signal in signals:
        if signal.name in overrides:
            signal.fiscal_dominance_note = overrides[signal.name]

    # --- Step 3: Re-score Signal 5 under FD using private-sector LEI ---
    # Headline LEI includes government spending components that mask
    # private-sector weakness during fiscal dominance periods
    if fiscal_dominance.active:
        for signal in signals:
            if signal.name == "Macro Deterioration":
                private_lei = signal.components.get("private_lei_yoy_change")
                if private_lei is not None:
                    # Re-score using private LEI thresholds
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

    # --- Step 4: Compute weighted composite ---
    total_weight = 0
    weighted_sum = 0

    for signal in signals:
        weight = weights.get(signal.name)
        if weight is None:
            # Signal not in weight set — e.g., Signal 7 in normal regime.
            # Still displayed but not scored.
            if not fiscal_dominance.active and signal.name == "Term Premium / Fiscal Stress":
                signal.fiscal_dominance_note = (
                    "Not scored in normal regime. Monitored for fiscal dominance detection."
                )
            continue
        weighted_sum += signal.score * weight
        total_weight += weight

    raw_composite = weighted_sum / total_weight if total_weight > 0 else 0

    # --- Step 5: Apply FD modifier (+10, capped at 100) ---
    adjusted_composite = min(raw_composite + fiscal_dominance.caution_modifier, 100)

    # --- Step 6: Generate warnings ---
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

    # Flag when 2+ individual signals are at extreme levels
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
