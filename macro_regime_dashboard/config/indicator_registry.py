"""Indicator registry — stub for Phase 1.

This module will map external data source series IDs (FRED, CFTC, Yahoo Finance,
etc.) to the internal indicator keys consumed by the RegimeTransitionEngine.

Phase 1 will populate INDICATOR_REGISTRY with entries for every series the
dashboard ingests, including fetch/cache/transform metadata.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IndicatorMeta:
    """Metadata for a single economic indicator series.

    Attributes:
        series_id: External identifier (e.g. FRED series ID like 'CFNAIMA3').
        name: Human-readable indicator name.
        source: Data provider — one of 'fred', 'cftc', 'yfinance', 'binance', 'coingecko'.
        frequency: Publication cadence — 'daily', 'weekly', 'monthly', or 'quarterly'.
        tier: Priority tier (1 = critical leading, 2 = confirming, 3 = supplementary).
        regime_dimension: Which regime axis this indicator informs —
            'growth', 'inflation', 'liquidity', or 'risk'.
        transform: How the raw value is transformed before threshold comparison —
            'level', 'yoy_pct', 'spread', 'percentile', or 'z_score'.
        inverted: If True, higher raw values indicate more contractionary / risk-off
            conditions. The engine flips the sign before threshold checks.
        publication_lag_days: Typical delay between reference period and data release.
    """

    series_id: str
    name: str
    source: str
    frequency: str
    tier: int
    regime_dimension: str
    transform: str
    inverted: bool = False
    publication_lag_days: int = 0


# Phase 1 will populate this mapping: indicator_key -> IndicatorMeta
INDICATOR_REGISTRY: dict[str, IndicatorMeta] = {}
