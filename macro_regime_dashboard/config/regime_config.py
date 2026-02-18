"""Regime ontology — the formal taxonomy of macroeconomic states.

This module defines:
- Four regime dimension enums (Growth, Inflation, Liquidity, Risk)
- Threshold configuration dataclasses for each dimension
- Sub-state overlay definitions (Fragile, Crowded, Capitulation)
- The RegimeTransitionEngine that classifies indicator snapshots into regimes
- The RegimeState dataclass returned by the engine

Everything downstream (data pipeline, models, dashboard) consumes these
definitions.  Phase 0 is rules-based; Phase 4A will replace the probability
model with HMM posteriors while keeping this same ontology.

Runtime: Python 3.11+, stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# 1. Regime dimension enums
# ---------------------------------------------------------------------------

class GrowthRegime(Enum):
    """Business-cycle phase based on leading and coincident recession indicators.

    Uses a vote-counting approach across 8 recession indicators:
      0-2 active  ->  EXPANSION
      3-4 active  ->  PEAK_LATE_CYCLE
      5+  active  ->  CONTRACTION

    TROUGH_EARLY_RECOVERY is reached when claims peak and decline,
    M2 growth bottoms, and the Fed begins easing — the exit path from
    CONTRACTION.
    """

    EXPANSION = "expansion"
    PEAK_LATE_CYCLE = "peak_late_cycle"
    CONTRACTION = "contraction"
    TROUGH_EARLY_RECOVERY = "trough_early_recovery"


class InflationRegime(Enum):
    """Inflation environment based on price and expectation indicators.

    Core PCE YoY, 5Y5Y forward breakeven (T5YIFR), and Michigan 1Y
    inflation expectations (MICH) are the primary inputs.

    STAGFLATION is a compound state: inflation elevated AND growth
    deteriorating (CONTRACTION).  It is set as an override after both
    the growth and inflation dimensions are evaluated independently.
    """

    DISINFLATION = "disinflation"
    REFLATION = "reflation"
    INFLATIONARY = "inflationary"
    STAGFLATION = "stagflation"


class LiquidityRegime(Enum):
    """Financial-conditions regime based on stress and lending indicators.

    Primary inputs: NFCI, HY OAS (BAMLH0A0HYM2), St. Louis Financial
    Stress Index (STLFSI4), and Senior Loan Officer Opinion Survey
    (SLOOS) net tightening for C&I loans.
    """

    LOOSE = "loose"
    NEUTRAL = "neutral"
    TIGHT = "tight"
    CRISIS = "crisis"


class RiskRegime(Enum):
    """Aggregate risk-appetite regime from a composite percentile index.

    The composite is a normalised average of VIX (inverted), HY OAS
    (inverted), S&P 500 vs 200-day MA, DXY (inverted), and copper
    momentum.  Higher composite percentile = more risk-on.
    """

    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    TRANSITIONAL = "transitional"


# ---------------------------------------------------------------------------
# 2. Threshold infrastructure
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DirectionalThreshold:
    """A threshold with entry/exit hysteresis for a single indicator.

    When *above* is True the indicator is "active" (recessionary / stressed)
    when its value >= *entry*.  Once active, it only deactivates when the
    value drops below *exit* (which is stricter, i.e. lower).

    When *above* is False the logic is mirrored: active when value <= entry,
    deactivates when value > exit.
    """

    entry: float
    exit: float
    above: bool = True


@dataclass(frozen=True)
class IndicatorThresholdSpec:
    """Named directional threshold for a single recession/stress indicator."""

    indicator_key: str
    name: str
    threshold: DirectionalThreshold


# ---------------------------------------------------------------------------
# 3. Dimension-specific threshold configs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GrowthThresholdConfig:
    """Threshold configuration for the Growth dimension.

    Eight recession indicators, each with a directional threshold that
    determines whether it is "active" (signalling recession risk).

    Vote counting maps the active count to a regime:
      0-2  ->  EXPANSION
      3-4  ->  PEAK_LATE_CYCLE
      5+   ->  CONTRACTION

    TROUGH_EARLY_RECOVERY is triggered when the engine is in CONTRACTION
    and the active count drops below the contraction-exit threshold.

    Persistence: the *candidate* regime must persist for
    ``confirmation_periods`` consecutive steps before a transition is
    confirmed.
    """

    indicators: tuple[IndicatorThresholdSpec, ...] = (
        # Yield curve: inverted (< 0) is recessionary
        IndicatorThresholdSpec(
            "t10y3m", "Treasury 10Y-3M spread",
            DirectionalThreshold(entry=0.0, exit=0.10, above=False),
        ),
        # HY OAS: > 500 bp is credit stress
        IndicatorThresholdSpec(
            "hy_oas", "High-Yield OAS (BAMLH0A0HYM2)",
            DirectionalThreshold(entry=500.0, exit=400.0, above=True),
        ),
        # NFCI: > 0 is tightening financial conditions
        IndicatorThresholdSpec(
            "nfci", "Chicago Fed NFCI",
            DirectionalThreshold(entry=0.0, exit=-0.20, above=True),
        ),
        # Initial claims 4-wk MA: > 10% above 6-month low signals deterioration.
        # We use the *level* here; the caller supplies the transformed value
        # (percentage above trough) directly as "icsa_pct_above_trough".
        IndicatorThresholdSpec(
            "icsa_pct_above_trough", "Initial Claims (% above 6-mo low)",
            DirectionalThreshold(entry=10.0, exit=5.0, above=True),
        ),
        # Sahm Rule
        IndicatorThresholdSpec(
            "sahm_rule", "Sahm Rule Real-Time Indicator",
            DirectionalThreshold(entry=0.50, exit=0.30, above=True),
        ),
        # CFNAI MA3
        IndicatorThresholdSpec(
            "cfnaima3", "Chicago Fed National Activity Index (3-mo MA)",
            DirectionalThreshold(entry=-0.70, exit=-0.30, above=False),
        ),
        # Building permits YoY
        IndicatorThresholdSpec(
            "permit_yoy", "Building Permits YoY %",
            DirectionalThreshold(entry=-20.0, exit=-10.0, above=False),
        ),
        # Freight (Cass Freight Index or similar): declining 3+ months
        # Caller supplies months-of-consecutive-decline as the value.
        IndicatorThresholdSpec(
            "freight_decline_months", "Freight consecutive decline (months)",
            DirectionalThreshold(entry=3.0, exit=1.0, above=True),
        ),
    )

    # Vote-count -> regime boundaries (with hysteresis)
    expansion_max_votes: int = 2       # 0-2 active = EXPANSION
    peak_entry_votes: int = 3          # >= 3 enters PEAK_LATE_CYCLE
    peak_exit_votes: int = 2           # <= 2 exits PEAK back to EXPANSION
    contraction_entry_votes: int = 5   # >= 5 enters CONTRACTION
    contraction_exit_votes: int = 4    # <= 4 exits CONTRACTION back to PEAK

    confirmation_periods: int = 2      # consecutive steps the candidate must hold


@dataclass(frozen=True)
class InflationThresholdConfig:
    """Threshold configuration for the Inflation dimension.

    Three indicators with per-regime ranges.  The regime whose ranges
    the majority of indicators fall into wins the vote.

    Stagflation is NOT determined here — it is a compound override applied
    after both growth and inflation are evaluated.

    Ranges below are (lower_bound, upper_bound) for each regime.
    A value falls into the range if lower <= value < upper.
    """

    # Core PCE YoY (%)
    core_pce_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "DISINFLATION": (-999.0, 1.5),
        "REFLATION": (1.5, 2.5),
        "INFLATIONARY": (2.5, 999.0),
    })
    # 5Y5Y Forward Breakeven — T5YIFR (%)
    t5yifr_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "DISINFLATION": (-999.0, 2.0),
        "REFLATION": (2.0, 2.5),
        "INFLATIONARY": (2.5, 999.0),
    })
    # Michigan 1Y Inflation Expectations — MICH (%)
    mich_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "DISINFLATION": (-999.0, 3.0),
        "REFLATION": (3.0, 4.0),
        "INFLATIONARY": (4.0, 999.0),
    })

    confirmation_periods: int = 2


@dataclass(frozen=True)
class LiquidityThresholdConfig:
    """Threshold configuration for the Liquidity dimension.

    Four indicators with per-regime ranges.  The regime whose ranges
    the majority of indicators fall into wins the vote (3 of 4 needed
    for CRISIS, 2 of 4 for other transitions).

    Hysteresis is implemented at the regime level: once in a regime,
    the engine uses exit thresholds before transitioning out.  For
    practical purposes we encode entry/exit ranges where the exit
    ranges are slightly wider.

    Entry ranges (used when NOT currently in this regime):
      LOOSE:   NFCI < -0.5,   HY OAS < 350,   STLFSI4 < 0.5,  SLOOS < 0 (easing)
      NEUTRAL: NFCI -0.5–0.0, HY OAS 350–500, STLFSI4 0.5–1.0, SLOOS 0–20
      TIGHT:   NFCI > 0.0,    HY OAS > 500,   STLFSI4 > 1.0,  SLOOS > 20
      CRISIS:  NFCI > 1.5,    HY OAS > 800,   STLFSI4 > 5.0,  (SLOOS N/A)

    Exit ranges (used when CURRENTLY in this regime — wider to prevent whipsaw):
      TIGHT exit -> requires NFCI < -0.2 (not just < 0.0)
    """

    # Entry ranges per indicator per regime: (lower, upper)
    nfci_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "LOOSE": (-999.0, -0.5),
        "NEUTRAL": (-0.5, 0.0),
        "TIGHT": (0.0, 1.5),
        "CRISIS": (1.5, 999.0),
    })
    # Exit ranges — wider bounds for hysteresis (only for transitions OUT)
    nfci_exit_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "LOOSE": (-999.0, -0.3),
        "NEUTRAL": (-0.7, 0.2),
        "TIGHT": (-0.2, 1.7),
        "CRISIS": (1.3, 999.0),
    })

    hy_oas_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "LOOSE": (-999.0, 350.0),
        "NEUTRAL": (350.0, 500.0),
        "TIGHT": (500.0, 800.0),
        "CRISIS": (800.0, 99999.0),
    })
    hy_oas_exit_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "LOOSE": (-999.0, 400.0),
        "NEUTRAL": (300.0, 550.0),
        "TIGHT": (450.0, 850.0),
        "CRISIS": (750.0, 99999.0),
    })

    stlfsi4_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "LOOSE": (-999.0, 0.5),
        "NEUTRAL": (0.5, 1.0),
        "TIGHT": (1.0, 5.0),
        "CRISIS": (5.0, 999.0),
    })
    stlfsi4_exit_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "LOOSE": (-999.0, 0.7),
        "NEUTRAL": (0.3, 1.2),
        "TIGHT": (0.8, 5.5),
        "CRISIS": (4.5, 999.0),
    })

    sloos_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "LOOSE": (-999.0, 0.0),
        "NEUTRAL": (0.0, 20.0),
        "TIGHT": (20.0, 999.0),
        "CRISIS": (20.0, 999.0),  # SLOOS not a primary crisis indicator
    })
    sloos_exit_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "LOOSE": (-999.0, 5.0),
        "NEUTRAL": (-5.0, 25.0),
        "TIGHT": (15.0, 999.0),
        "CRISIS": (15.0, 999.0),
    })

    confirmation_periods: int = 2


@dataclass(frozen=True)
class RiskThresholdConfig:
    """Threshold configuration for the Risk dimension.

    Uses a single composite risk-appetite percentile (0-100).
    Higher percentile = more risk-on.

    Entry ranges:
      RISK_ON:       > 70th percentile
      TRANSITIONAL:  30th-70th percentile
      RISK_OFF:      < 30th percentile

    COT (Commitment of Traders) composite percentile is used for
    sub-state detection (Crowded / Capitulation) — those thresholds
    live here for co-location.
    """

    # Entry ranges: (lower, upper)
    composite_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "RISK_ON": (70.0, 999.0),
        "TRANSITIONAL": (30.0, 70.0),
        "RISK_OFF": (-999.0, 30.0),
    })
    # Exit ranges (wider to prevent whipsaw)
    composite_exit_ranges: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "RISK_ON": (65.0, 999.0),
        "TRANSITIONAL": (25.0, 75.0),
        "RISK_OFF": (-999.0, 35.0),
    })

    # Sub-state thresholds
    crowded_entry: float = 80.0     # COT composite percentile for Crowded
    crowded_exit: float = 70.0
    crowded_high_conf: float = 90.0  # High-confidence crowded

    capitulation_entry: float = 20.0  # COT composite percentile for Capitulation
    capitulation_exit: float = 30.0   # (below entry = capitulation)
    capitulation_high_conf: float = 10.0  # High-confidence capitulation

    confirmation_periods: int = 1  # Risk regimes can shift faster


@dataclass(frozen=True)
class FragileThresholdConfig:
    """Threshold configuration for the Fragile sub-state overlay.

    ALL FOUR conditions must be met simultaneously for Fragile = TRUE.
    This captures the Sept 2019 scenario: no visible credit stress
    (NFCI negative) but the plumbing is fragile (ON-RRP depleted,
    QT draining reserves, SOFR above IORB floor).

    Conditions:
      1. NFCI < 0             (surface conditions appear loose)
      2. ON_RRP < $50B        (liquidity buffer depleted)
      3. WALCL_yoy < 0%       (QT ongoing, reserves draining)
      4. SOFR-IORB spread > 0 (funding rate above floor, reserve scarcity)
    """

    nfci_max: float = 0.0
    nfci_exit: float = 0.2

    on_rrp_max: float = 50.0       # billions USD
    on_rrp_exit: float = 100.0

    walcl_yoy_max: float = 0.0     # percent
    walcl_yoy_exit: float = 0.0    # exit when >= 0 (back to positive growth)

    sofr_iorb_min: float = 0.0     # basis points
    sofr_iorb_exit: float = 0.0    # exit when <= 0

    # Margins for confidence interpolation: how far past the threshold
    # gives full confidence.
    nfci_full_margin: float = 0.5       # NFCI at -0.5 -> full confidence
    on_rrp_full_margin: float = 40.0    # ON_RRP at $10B -> full confidence
    walcl_full_margin: float = 3.0      # WALCL_yoy at -3% -> full confidence
    sofr_iorb_full_margin: float = 5.0  # spread at +5bp -> full confidence


# ---------------------------------------------------------------------------
# 4. RegimeState dataclass
# ---------------------------------------------------------------------------

@dataclass
class RegimeState:
    """Immutable snapshot of the macroeconomic regime at a point in time.

    Produced by ``RegimeTransitionEngine.step()`` on each call.
    Contains the base regime for each of the four dimensions, probability
    distributions across regimes, sub-state overlay flags with confidence
    scores, and metadata about which indicators drove the classification.
    """

    timestamp: datetime

    # Primary dimensions
    growth: GrowthRegime
    growth_probs: dict[GrowthRegime, float]

    inflation: InflationRegime
    inflation_probs: dict[InflationRegime, float]

    liquidity: LiquidityRegime
    liquidity_probs: dict[LiquidityRegime, float]

    risk_appetite: RiskRegime
    risk_probs: dict[RiskRegime, float]

    # Sub-state overlays
    fragile: bool = False
    fragile_confidence: float = 0.0

    crowded: bool = False
    crowded_confidence: float = 0.0

    capitulation: bool = False
    capitulation_confidence: float = 0.0

    # Metadata
    model_version: str = "rules_v1"
    indicators_used: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable regime summary string."""
        parts = [
            f"Growth: {self.growth.value} (P={self.growth_probs.get(self.growth, 0):.0%})",
            f"Inflation: {self.inflation.value} (P={self.inflation_probs.get(self.inflation, 0):.0%})",
            f"Liquidity: {self.liquidity.value} (P={self.liquidity_probs.get(self.liquidity, 0):.0%})",
            f"Risk: {self.risk_appetite.value} (P={self.risk_probs.get(self.risk_appetite, 0):.0%})",
        ]
        if self.fragile:
            parts.append(f"⚠ FRAGILE (conf={self.fragile_confidence:.0%})")
        if self.crowded:
            parts.append(f"⚠ CROWDED (conf={self.crowded_confidence:.0%})")
        if self.capitulation:
            parts.append(f"🟢 CAPITULATION (conf={self.capitulation_confidence:.0%})")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# 5. RegimeTransitionEngine
# ---------------------------------------------------------------------------

class RegimeTransitionEngine:
    """Stateful engine that classifies macroeconomic regimes.

    Usage::

        engine = RegimeTransitionEngine()
        state = engine.step({"sahm_rule": 0.6, "nfci": 0.3, ...}, datetime.now())

    The engine maintains internal state across ``step()`` calls:

    * **Current regime** per dimension — determines which threshold set
      (entry vs exit) to use on the next call (hysteresis).
    * **Confirmation counters** — a candidate regime must persist for
      *N* consecutive steps before the engine transitions (persistence rule).
    * **Per-indicator activation** — for the Growth dimension's
      vote-counting, individual indicators track whether they are currently
      "active" so that exit thresholds (stricter than entry) apply.
    * **Sub-state flags** — tracked for exit-hysteresis on overlays.

    Call ``reset()`` to return to initial defaults.
    """

    def __init__(
        self,
        growth_config: GrowthThresholdConfig | None = None,
        inflation_config: InflationThresholdConfig | None = None,
        liquidity_config: LiquidityThresholdConfig | None = None,
        risk_config: RiskThresholdConfig | None = None,
        fragile_config: FragileThresholdConfig | None = None,
    ) -> None:
        self._growth_cfg = growth_config or GrowthThresholdConfig()
        self._inflation_cfg = inflation_config or InflationThresholdConfig()
        self._liquidity_cfg = liquidity_config or LiquidityThresholdConfig()
        self._risk_cfg = risk_config or RiskThresholdConfig()
        self._fragile_cfg = fragile_config or FragileThresholdConfig()

        self._init_state()

    def _init_state(self) -> None:
        """Initialise (or re-initialise) all mutable state."""
        # Current confirmed regimes
        self._current_growth = GrowthRegime.EXPANSION
        self._current_inflation = InflationRegime.DISINFLATION
        self._current_liquidity = LiquidityRegime.LOOSE
        self._current_risk = RiskRegime.TRANSITIONAL

        # Confirmation tracking per dimension: (candidate, consecutive_count)
        self._growth_candidate: GrowthRegime | None = None
        self._growth_confirm: int = 0

        self._inflation_candidate: InflationRegime | None = None
        self._inflation_confirm: int = 0

        self._liquidity_candidate: LiquidityRegime | None = None
        self._liquidity_confirm: int = 0

        self._risk_candidate: RiskRegime | None = None
        self._risk_confirm: int = 0

        # Per-indicator activation state (for growth vote hysteresis)
        self._indicator_active: dict[str, bool] = {}

        # Sub-state tracking (for exit hysteresis)
        self._fragile_active: bool = False
        self._crowded_active: bool = False
        self._capitulation_active: bool = False

        self._step_count: int = 0

    def reset(self) -> None:
        """Clear all internal state, returning the engine to initial defaults."""
        self._init_state()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def step(
        self,
        indicators: dict[str, float],
        timestamp: datetime,
    ) -> RegimeState:
        """Process one period of indicator data and return the updated regime.

        Args:
            indicators: Mapping of indicator keys to their current numeric
                values.  Missing indicators are silently skipped — only
                supplied indicators participate in vote counting.
            timestamp: The observation timestamp.

        Returns:
            A ``RegimeState`` snapshot.
        """
        self._step_count += 1
        used = sorted(k for k in indicators)

        # 1. Evaluate each dimension
        growth, growth_probs, active_count = self._evaluate_growth(indicators)
        inflation, inflation_probs = self._evaluate_inflation(indicators)
        liquidity, liquidity_probs = self._evaluate_liquidity(indicators)
        risk, risk_probs = self._evaluate_risk(indicators)

        # 2. Stagflation override
        alerts: list[str] = []
        if growth == GrowthRegime.CONTRACTION and inflation == InflationRegime.INFLATIONARY:
            inflation = InflationRegime.STAGFLATION
            inflation_probs[InflationRegime.STAGFLATION] = inflation_probs.get(
                InflationRegime.INFLATIONARY, 0.0
            )
            alerts.append("Stagflation override: inflation elevated + growth contraction")
        # Also check if growth is PEAK_LATE_CYCLE with strong contraction signals
        # and inflation is inflationary — spec says PMI < 50 and falling with elevated CPI/PCE
        if (
            growth in (GrowthRegime.CONTRACTION, GrowthRegime.PEAK_LATE_CYCLE)
            and inflation == InflationRegime.INFLATIONARY
            and indicators.get("pmi_composite", 999) < 50
        ):
            inflation = InflationRegime.STAGFLATION
            inflation_probs[InflationRegime.STAGFLATION] = inflation_probs.get(
                InflationRegime.INFLATIONARY, 0.0
            )
            if "Stagflation" not in " ".join(alerts):
                alerts.append("Stagflation: PMI < 50 with elevated inflation")

        # 3. Sub-state overlays
        fragile, fragile_conf = self._evaluate_fragile(indicators)
        crowded, crowded_conf = self._evaluate_crowded(indicators)
        capitulation, cap_conf = self._evaluate_capitulation(indicators)

        return RegimeState(
            timestamp=timestamp,
            growth=growth,
            growth_probs=growth_probs,
            inflation=inflation,
            inflation_probs=inflation_probs,
            liquidity=liquidity,
            liquidity_probs=liquidity_probs,
            risk_appetite=risk,
            risk_probs=risk_probs,
            fragile=fragile,
            fragile_confidence=fragile_conf,
            crowded=crowded,
            crowded_confidence=crowded_conf,
            capitulation=capitulation,
            capitulation_confidence=cap_conf,
            model_version="rules_v1",
            indicators_used=used,
            alerts=alerts,
        )

    # ------------------------------------------------------------------
    # Growth dimension (vote counting)
    # ------------------------------------------------------------------

    def _evaluate_growth(
        self,
        indicators: dict[str, float],
    ) -> tuple[GrowthRegime, dict[GrowthRegime, float], int]:
        """Evaluate the growth dimension using recession indicator vote counting.

        Returns:
            (confirmed_regime, probability_dict, active_indicator_count)
        """
        cfg = self._growth_cfg
        active_count = 0
        present_count = 0

        for spec in cfg.indicators:
            key = spec.indicator_key
            if key not in indicators:
                continue
            present_count += 1
            value = indicators[key]
            th = spec.threshold
            was_active = self._indicator_active.get(key, False)

            if th.above:
                # Active when value >= entry; deactivate when value < exit
                if was_active:
                    is_active = value >= th.exit
                else:
                    is_active = value >= th.entry
            else:
                # Active when value <= entry; deactivate when value > exit
                if was_active:
                    is_active = value <= th.exit
                else:
                    is_active = value <= th.entry

            self._indicator_active[key] = is_active
            if is_active:
                active_count += 1

        # Compute probability as vote fraction
        prob_contraction = active_count / max(present_count, 1)
        prob_expansion = 1.0 - prob_contraction

        # Determine candidate regime from vote count + hysteresis
        candidate = self._vote_count_to_growth_regime(active_count)

        # Apply confirmation
        growth, self._growth_confirm, self._growth_candidate = self._apply_confirmation(
            candidate=candidate,
            current=self._current_growth,
            prev_candidate=self._growth_candidate,
            confirm_count=self._growth_confirm,
            periods=cfg.confirmation_periods,
        )
        self._current_growth = growth

        # Build probability dict
        probs: dict[GrowthRegime, float] = {
            GrowthRegime.EXPANSION: 0.0,
            GrowthRegime.PEAK_LATE_CYCLE: 0.0,
            GrowthRegime.CONTRACTION: 0.0,
            GrowthRegime.TROUGH_EARLY_RECOVERY: 0.0,
        }
        # Distribute probability based on vote fraction
        if present_count > 0:
            frac = active_count / present_count
            if frac <= 2.0 / present_count:
                probs[GrowthRegime.EXPANSION] = 1.0 - frac
                probs[GrowthRegime.PEAK_LATE_CYCLE] = frac * 0.5
                probs[GrowthRegime.CONTRACTION] = frac * 0.5
            elif frac <= 4.0 / present_count:
                probs[GrowthRegime.EXPANSION] = max(0, 1.0 - frac * 2)
                probs[GrowthRegime.PEAK_LATE_CYCLE] = 1.0 - abs(frac - 0.5)
                probs[GrowthRegime.CONTRACTION] = frac
            else:
                probs[GrowthRegime.CONTRACTION] = frac
                probs[GrowthRegime.PEAK_LATE_CYCLE] = 1.0 - frac
        else:
            probs[self._current_growth] = 1.0

        # Ensure the confirmed regime has at least the plurality probability
        max_other = max(
            (v for k, v in probs.items() if k != growth), default=0.0
        )
        if probs[growth] < max_other:
            probs[growth] = max_other + 0.01
        # Normalise
        total = sum(probs.values())
        if total > 0:
            probs = {k: v / total for k, v in probs.items()}

        return growth, probs, active_count

    def _vote_count_to_growth_regime(self, active: int) -> GrowthRegime:
        """Map recession indicator vote count to a candidate growth regime.

        Uses hysteresis based on the current confirmed regime.
        """
        cfg = self._growth_cfg
        current = self._current_growth

        if current == GrowthRegime.EXPANSION:
            if active >= cfg.peak_entry_votes:
                if active >= cfg.contraction_entry_votes:
                    return GrowthRegime.CONTRACTION
                return GrowthRegime.PEAK_LATE_CYCLE
            return GrowthRegime.EXPANSION

        if current == GrowthRegime.PEAK_LATE_CYCLE:
            if active >= cfg.contraction_entry_votes:
                return GrowthRegime.CONTRACTION
            if active <= cfg.peak_exit_votes:
                return GrowthRegime.EXPANSION
            return GrowthRegime.PEAK_LATE_CYCLE

        if current == GrowthRegime.CONTRACTION:
            if active <= cfg.contraction_exit_votes:
                if active <= cfg.peak_exit_votes:
                    return GrowthRegime.TROUGH_EARLY_RECOVERY
                return GrowthRegime.PEAK_LATE_CYCLE
            return GrowthRegime.CONTRACTION

        if current == GrowthRegime.TROUGH_EARLY_RECOVERY:
            # Recovery -> expansion once indicators stay low
            if active <= cfg.expansion_max_votes:
                return GrowthRegime.EXPANSION
            if active >= cfg.peak_entry_votes:
                return GrowthRegime.PEAK_LATE_CYCLE
            return GrowthRegime.TROUGH_EARLY_RECOVERY

        return current  # pragma: no cover

    # ------------------------------------------------------------------
    # Inflation dimension (range voting)
    # ------------------------------------------------------------------

    def _evaluate_inflation(
        self,
        indicators: dict[str, float],
    ) -> tuple[InflationRegime, dict[InflationRegime, float]]:
        """Evaluate the inflation dimension using range-based indicator voting.

        Three indicators (core_pce, t5yifr, mich) each vote for a regime.
        The majority vote wins.  Ties are broken in favour of the current regime.
        """
        cfg = self._inflation_cfg
        indicator_configs: list[tuple[str, dict[str, tuple[float, float]]]] = [
            ("core_pce", cfg.core_pce_ranges),
            ("t5yifr", cfg.t5yifr_ranges),
            ("mich", cfg.mich_ranges),
        ]

        votes: dict[str, int] = {}
        present_count = 0

        for key, ranges in indicator_configs:
            if key not in indicators:
                continue
            present_count += 1
            value = indicators[key]
            regime_name = self._classify_into_range(value, ranges)
            if regime_name:
                votes[regime_name] = votes.get(regime_name, 0) + 1

        # Determine winning regime
        candidate_name = self._current_inflation.name
        if votes:
            max_votes = max(votes.values())
            # Prefer current regime on tie
            winners = [name for name, count in votes.items() if count == max_votes]
            if self._current_inflation.name in winners:
                candidate_name = self._current_inflation.name
            else:
                candidate_name = winners[0]

        # Map name to enum (STAGFLATION is handled externally)
        name_to_enum = {r.name: r for r in InflationRegime if r != InflationRegime.STAGFLATION}
        candidate = name_to_enum.get(candidate_name, self._current_inflation)

        # Apply confirmation
        inflation, self._inflation_confirm, self._inflation_candidate = self._apply_confirmation(
            candidate=candidate,
            current=self._current_inflation,
            prev_candidate=self._inflation_candidate,
            confirm_count=self._inflation_confirm,
            periods=cfg.confirmation_periods,
        )
        self._current_inflation = inflation

        # Build probability dict from vote fractions
        probs: dict[InflationRegime, float] = {r: 0.0 for r in InflationRegime}
        if present_count > 0:
            for name, count in votes.items():
                if name in name_to_enum:
                    probs[name_to_enum[name]] = count / present_count
        if not any(probs.values()):
            probs[inflation] = 1.0
        # Normalise
        total = sum(probs.values())
        if total > 0:
            probs = {k: v / total for k, v in probs.items()}

        return inflation, probs

    # ------------------------------------------------------------------
    # Liquidity dimension (range voting with hysteresis)
    # ------------------------------------------------------------------

    def _evaluate_liquidity(
        self,
        indicators: dict[str, float],
    ) -> tuple[LiquidityRegime, dict[LiquidityRegime, float]]:
        """Evaluate the liquidity dimension using range-based voting.

        Four indicators (nfci, hy_oas, stlfsi4, sloos_ci) each vote for
        a regime.  Entry ranges are used when evaluating transitions INTO
        a new regime; exit ranges (wider) are used to keep the current
        regime sticky.
        """
        cfg = self._liquidity_cfg
        current_name = self._current_liquidity.name

        # Indicator key -> (entry_ranges, exit_ranges)
        indicator_configs: list[tuple[str, dict[str, tuple[float, float]], dict[str, tuple[float, float]]]] = [
            ("nfci", cfg.nfci_ranges, cfg.nfci_exit_ranges),
            ("hy_oas", cfg.hy_oas_ranges, cfg.hy_oas_exit_ranges),
            ("stlfsi4", cfg.stlfsi4_ranges, cfg.stlfsi4_exit_ranges),
            ("sloos_ci", cfg.sloos_ranges, cfg.sloos_exit_ranges),
        ]

        votes: dict[str, int] = {}
        present_count = 0

        for key, entry_ranges, exit_ranges in indicator_configs:
            if key not in indicators:
                continue
            present_count += 1
            value = indicators[key]

            # Check if value stays in current regime (using exit range)
            stays_in_current = False
            if current_name in exit_ranges:
                lo, hi = exit_ranges[current_name]
                if lo <= value < hi:
                    stays_in_current = True

            if stays_in_current:
                votes[current_name] = votes.get(current_name, 0) + 1
            else:
                # Classify using entry ranges
                regime_name = self._classify_into_range(value, entry_ranges)
                if regime_name:
                    votes[regime_name] = votes.get(regime_name, 0) + 1

        # Determine winning regime
        candidate_name = current_name
        if votes:
            max_votes = max(votes.values())
            winners = [name for name, count in votes.items() if count == max_votes]
            if current_name in winners:
                candidate_name = current_name
            else:
                candidate_name = winners[0]

        name_to_enum = {r.name: r for r in LiquidityRegime}
        candidate = name_to_enum.get(candidate_name, self._current_liquidity)

        # Apply confirmation
        liquidity, self._liquidity_confirm, self._liquidity_candidate = self._apply_confirmation(
            candidate=candidate,
            current=self._current_liquidity,
            prev_candidate=self._liquidity_candidate,
            confirm_count=self._liquidity_confirm,
            periods=cfg.confirmation_periods,
        )
        self._current_liquidity = liquidity

        # Build probability dict
        probs: dict[LiquidityRegime, float] = {r: 0.0 for r in LiquidityRegime}
        if present_count > 0:
            for name, count in votes.items():
                if name in name_to_enum:
                    probs[name_to_enum[name]] = count / present_count
        if not any(probs.values()):
            probs[liquidity] = 1.0
        total = sum(probs.values())
        if total > 0:
            probs = {k: v / total for k, v in probs.items()}

        return liquidity, probs

    # ------------------------------------------------------------------
    # Risk dimension (composite percentile)
    # ------------------------------------------------------------------

    def _evaluate_risk(
        self,
        indicators: dict[str, float],
    ) -> tuple[RiskRegime, dict[RiskRegime, float]]:
        """Evaluate the risk dimension using a composite risk-appetite percentile.

        Higher percentile = more risk-on.  The composite is supplied by
        the caller as ``risk_appetite_pct`` (0-100).
        """
        cfg = self._risk_cfg
        current_name = self._current_risk.name
        name_to_enum = {r.name: r for r in RiskRegime}

        if "risk_appetite_pct" not in indicators:
            # No data -> stay in current regime
            probs = {r: 0.0 for r in RiskRegime}
            probs[self._current_risk] = 1.0
            return self._current_risk, probs

        value = indicators["risk_appetite_pct"]

        # Check if value stays in current regime (exit range)
        stays = False
        if current_name in cfg.composite_exit_ranges:
            lo, hi = cfg.composite_exit_ranges[current_name]
            if lo <= value < hi:
                stays = True

        if stays:
            candidate_name = current_name
        else:
            candidate_name = self._classify_into_range(value, cfg.composite_ranges) or current_name

        candidate = name_to_enum.get(candidate_name, self._current_risk)

        # Apply confirmation
        risk, self._risk_confirm, self._risk_candidate = self._apply_confirmation(
            candidate=candidate,
            current=self._current_risk,
            prev_candidate=self._risk_candidate,
            confirm_count=self._risk_confirm,
            periods=cfg.confirmation_periods,
        )
        self._current_risk = risk

        # Probability: distance-based across ranges
        probs = self._range_probabilities(value, cfg.composite_ranges, name_to_enum)

        return risk, probs

    # ------------------------------------------------------------------
    # Sub-state overlays
    # ------------------------------------------------------------------

    def _evaluate_fragile(
        self,
        indicators: dict[str, float],
    ) -> tuple[bool, float]:
        """Evaluate the Fragile sub-state overlay.

        All four conditions must be met simultaneously:
          1. NFCI < 0 (surface calm)
          2. ON_RRP < $50B (liquidity buffer depleted)
          3. WALCL_yoy < 0% (QT ongoing)
          4. SOFR-IORB spread > 0 (reserve scarcity)

        Confidence is the minimum of the four individual condition
        confidences (AND-logic: weakest link).
        """
        cfg = self._fragile_cfg
        required_keys = ["nfci", "on_rrp", "walcl_yoy", "sofr_iorb_spread"]
        if not all(k in indicators for k in required_keys):
            # Cannot evaluate — if currently fragile, stay fragile with reduced confidence
            if self._fragile_active:
                return True, 0.5
            return False, 0.0

        nfci = indicators["nfci"]
        on_rrp = indicators["on_rrp"]
        walcl = indicators["walcl_yoy"]
        sofr = indicators["sofr_iorb_spread"]

        # Use exit thresholds if currently fragile (hysteresis)
        if self._fragile_active:
            cond_nfci = nfci < cfg.nfci_exit
            cond_rrp = on_rrp < cfg.on_rrp_exit
            cond_walcl = walcl < cfg.walcl_yoy_exit
            cond_sofr = sofr > cfg.sofr_iorb_exit
        else:
            cond_nfci = nfci < cfg.nfci_max
            cond_rrp = on_rrp < cfg.on_rrp_max
            cond_walcl = walcl < cfg.walcl_yoy_max
            cond_sofr = sofr > cfg.sofr_iorb_min

        all_met = cond_nfci and cond_rrp and cond_walcl and cond_sofr
        self._fragile_active = all_met

        if not all_met:
            return False, 0.0

        # Confidence: linear interpolation per condition, take minimum
        conf_nfci = self._confidence_below(nfci, cfg.nfci_max, cfg.nfci_full_margin)
        conf_rrp = self._confidence_below(on_rrp, cfg.on_rrp_max, cfg.on_rrp_full_margin)
        conf_walcl = self._confidence_below(walcl, cfg.walcl_yoy_max, cfg.walcl_full_margin)
        conf_sofr = self._confidence_above(sofr, cfg.sofr_iorb_min, cfg.sofr_iorb_full_margin)

        confidence = min(conf_nfci, conf_rrp, conf_walcl, conf_sofr)
        return True, confidence

    def _evaluate_crowded(
        self,
        indicators: dict[str, float],
    ) -> tuple[bool, float]:
        """Evaluate the Crowded Risk-On sub-state overlay.

        Requires:
          - risk_appetite_pct > 70th percentile (RISK_ON base state)
          - cot_composite > 80th percentile (extreme long positioning)

        Confidence scales linearly from the 80th to the 90th percentile
        of COT composite.
        """
        cfg = self._risk_cfg

        risk_pct = indicators.get("risk_appetite_pct")
        cot = indicators.get("cot_composite")
        if risk_pct is None or cot is None:
            self._crowded_active = False
            return False, 0.0

        # Risk appetite must be in risk-on territory
        risk_on = risk_pct >= cfg.composite_ranges["RISK_ON"][0]

        if self._crowded_active:
            # Exit hysteresis: use exit thresholds
            cot_condition = cot >= cfg.crowded_exit
        else:
            cot_condition = cot >= cfg.crowded_entry

        is_crowded = risk_on and cot_condition
        self._crowded_active = is_crowded

        if not is_crowded:
            return False, 0.0

        # Confidence: linear interpolation from entry to high-confidence
        margin = cfg.crowded_high_conf - cfg.crowded_entry
        confidence = self._confidence_above(cot, cfg.crowded_entry, margin if margin > 0 else 10.0)
        return True, confidence

    def _evaluate_capitulation(
        self,
        indicators: dict[str, float],
    ) -> tuple[bool, float]:
        """Evaluate the Capitulation sub-state overlay.

        Requires:
          - risk_appetite_pct < 30th percentile (RISK_OFF base state)
          - cot_composite < 20th percentile (extreme short positioning)

        Confidence scales linearly from the 20th down to the 10th percentile.
        """
        cfg = self._risk_cfg

        risk_pct = indicators.get("risk_appetite_pct")
        cot = indicators.get("cot_composite")
        if risk_pct is None or cot is None:
            self._capitulation_active = False
            return False, 0.0

        # Risk appetite must be in risk-off territory
        risk_off = risk_pct < cfg.composite_ranges["RISK_OFF"][1]

        if self._capitulation_active:
            cot_condition = cot <= cfg.capitulation_exit
        else:
            cot_condition = cot <= cfg.capitulation_entry

        is_cap = risk_off and cot_condition
        self._capitulation_active = is_cap

        if not is_cap:
            return False, 0.0

        margin = cfg.capitulation_entry - cfg.capitulation_high_conf
        confidence = self._confidence_below(cot, cfg.capitulation_entry, margin if margin > 0 else 10.0)
        return True, confidence

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_confirmation(
        candidate: Any,
        current: Any,
        prev_candidate: Any,
        confirm_count: int,
        periods: int,
    ) -> tuple[Any, int, Any]:
        """Apply the persistence / confirmation rule.

        A candidate regime must be the same for *periods* consecutive
        steps before the engine transitions.  If the candidate is already
        the current regime, no confirmation is needed.

        Returns:
            (resolved_regime, new_confirm_count, new_candidate)
        """
        if candidate == current:
            # No transition needed — already in this regime
            return current, 0, None

        if candidate == prev_candidate:
            new_count = confirm_count + 1
        else:
            new_count = 1

        if new_count >= periods:
            # Confirmed — transition
            return candidate, 0, None

        # Not yet confirmed — stay in current regime
        return current, new_count, candidate

    @staticmethod
    def _classify_into_range(
        value: float,
        ranges: dict[str, tuple[float, float]],
    ) -> str | None:
        """Return the regime name whose range contains *value*, or None."""
        for name, (lo, hi) in ranges.items():
            if lo <= value < hi:
                return name
        return None

    @staticmethod
    def _confidence_above(value: float, threshold: float, full_margin: float) -> float:
        """Confidence that value is above threshold (linear, clamped 0-1)."""
        if full_margin <= 0:
            return 1.0 if value >= threshold else 0.0
        raw = (value - threshold) / full_margin
        return max(0.0, min(1.0, raw))

    @staticmethod
    def _confidence_below(value: float, threshold: float, full_margin: float) -> float:
        """Confidence that value is below threshold (linear, clamped 0-1)."""
        if full_margin <= 0:
            return 1.0 if value <= threshold else 0.0
        raw = (threshold - value) / full_margin
        return max(0.0, min(1.0, raw))

    @staticmethod
    def _range_probabilities(
        value: float,
        ranges: dict[str, tuple[float, float]],
        name_to_enum: dict[str, Any],
    ) -> dict[Any, float]:
        """Compute probability-like scores based on distance from range midpoints."""
        probs: dict[Any, float] = {}
        scores: dict[str, float] = {}

        for name, (lo, hi) in ranges.items():
            # Clamp extreme bounds for midpoint calculation
            effective_lo = max(lo, -100)
            effective_hi = min(hi, 200)
            mid = (effective_lo + effective_hi) / 2
            half_width = max((effective_hi - effective_lo) / 2, 1.0)
            dist = abs(value - mid) / half_width
            score = max(0.0, 1.0 - dist * 0.5)
            scores[name] = score

        total = sum(scores.values())
        for name, enum_val in name_to_enum.items():
            if total > 0 and name in scores:
                probs[enum_val] = scores[name] / total
            else:
                probs[enum_val] = 0.0

        return probs
