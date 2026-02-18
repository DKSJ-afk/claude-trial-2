"""Macroeconomic Regime Nowcasting Dashboard.

Phase 0: Regime ontology — enums, thresholds, and transition engine.
Phase 1: Indicator registry — full data catalogue with metadata.
"""
from __future__ import annotations

from macro_regime_dashboard.config.regime_config import (
    GrowthRegime,
    InflationRegime,
    LiquidityRegime,
    RiskRegime,
    RegimeState,
    RegimeTransitionEngine,
)

from macro_regime_dashboard.config.indicator_registry import (
    IndicatorMeta,
    INDICATOR_REGISTRY,
    get_by_tier,
    get_by_dimension,
    get_by_source,
    get_by_sub_state,
    get_fred_ids,
    get_constructed_indicators,
    validate_registry,
)

__all__ = [
    "GrowthRegime",
    "InflationRegime",
    "LiquidityRegime",
    "RiskRegime",
    "RegimeState",
    "RegimeTransitionEngine",
    "IndicatorMeta",
    "INDICATOR_REGISTRY",
    "get_by_tier",
    "get_by_dimension",
    "get_by_source",
    "get_by_sub_state",
    "get_fred_ids",
    "get_constructed_indicators",
    "validate_registry",
]
