"""Test suite for the Phase 0 regime ontology.

Eight scenarios based on known historical episodes serve as acceptance
criteria for the RegimeTransitionEngine.  Each test is self-contained:
it creates a fresh engine, feeds indicator snapshots, and asserts on
the returned RegimeState.

Tests that require confirmation (persistence rule) call ``step()``
multiple times with consistent indicators to satisfy the confirmation
counter before asserting on the final state.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from macro_regime_dashboard.config.regime_config import (
    GrowthRegime,
    InflationRegime,
    LiquidityRegime,
    RiskRegime,
    RegimeState,
    RegimeTransitionEngine,
)


# ---------------------------------------------------------------------------
# Helper: neutral indicator snapshot with overrides
# ---------------------------------------------------------------------------

def _make_neutral(**overrides: float) -> dict[str, float]:
    """Return a full indicator dict with benign / mid-range values.

    All growth indicators are in expansion territory, inflation near target,
    liquidity loose-to-neutral, risk transitional.  Individual tests
    override specific keys to push the engine into the desired regime.
    """
    base: dict[str, float] = {
        # Growth indicators (all benign -> 0 active -> EXPANSION)
        "t10y3m": 1.50,                  # well positive
        "hy_oas": 350.0,                 # moderate
        "nfci": -0.30,                   # slightly loose
        "icsa_pct_above_trough": 2.0,    # low
        "sahm_rule": 0.10,              # well below trigger
        "cfnaima3": 0.20,               # positive activity
        "permit_yoy": 5.0,              # growing permits
        "freight_decline_months": 0.0,   # no decline

        # Inflation indicators (anchored near 2%)
        "core_pce": 2.0,
        "t5yifr": 2.2,
        "mich": 2.8,

        # Liquidity indicators (loose-to-neutral)
        "sloos_ci": 5.0,
        "stlfsi4": 0.1,

        # Risk indicators (transitional)
        "risk_appetite_pct": 50.0,
        "cot_composite": 50.0,

        # Fragile sub-state indicators (not fragile)
        "on_rrp": 300.0,
        "walcl_yoy": 5.0,
        "sofr_iorb_spread": -3.0,
    }
    base.update(overrides)
    return base


def _step_n(engine: RegimeTransitionEngine, indicators: dict[str, float],
            n: int, start: datetime | None = None) -> RegimeState:
    """Step the engine *n* times with the same indicators.

    Returns the RegimeState from the final step.  Useful for satisfying
    confirmation rules.
    """
    ts = start or datetime(2024, 1, 1)
    state = None
    for i in range(n):
        state = engine.step(indicators, ts + timedelta(days=30 * i))
    assert state is not None
    return state


# ===================================================================
# Test 1 — September 2019: pre-repo spike, Fragile detection
# ===================================================================

class TestSept2019Fragile:
    """Surface conditions look loose (NFCI negative, low spreads) but
    plumbing is fragile.  This was the period just before the repo
    market blowup on Sept 16-17, 2019.
    """

    def test_fragile_detected_with_surface_loose(self) -> None:
        engine = RegimeTransitionEngine()
        indicators = _make_neutral(
            # Surface: looks calm
            nfci=-0.60,
            hy_oas=380.0,
            stlfsi4=-0.3,
            sloos_ci=5.0,
            # Plumbing: fragile
            on_rrp=30.0,              # < $50B (depleted)
            walcl_yoy=-3.0,           # QT ongoing
            sofr_iorb_spread=5.0,     # SOFR above IORB
        )

        # Sub-states don't need confirmation, but base regimes may.
        # Step twice to confirm any base regime transitions.
        state = _step_n(engine, indicators, 2, datetime(2019, 9, 1))

        # Fragile must be TRUE
        assert state.fragile is True
        assert state.fragile_confidence > 0.0

        # Base liquidity should still be LOOSE (surface is calm)
        assert state.liquidity == LiquidityRegime.LOOSE

        # Growth should be EXPANSION (all growth indicators benign)
        assert state.growth == GrowthRegime.EXPANSION


# ===================================================================
# Test 2 — March 2009: capitulation + crisis
# ===================================================================

class TestMarch2009Capitulation:
    """Peak financial crisis.  Extreme stress across all dimensions.
    COT at capitulation levels.  Growth in deep contraction.
    """

    def test_capitulation_and_crisis(self) -> None:
        engine = RegimeTransitionEngine()
        indicators = _make_neutral(
            # Growth: deep contraction (6+ indicators active)
            t10y3m=2.50,                 # post-inversion, steep again (not active)
            hy_oas=1800.0,               # extreme credit stress (active)
            nfci=2.50,                   # very tight (active)
            icsa_pct_above_trough=80.0,  # claims surging (active)
            sahm_rule=1.20,              # well above 0.50 (active)
            cfnaima3=-1.50,              # deep negative (active)
            permit_yoy=-35.0,            # collapsed (active)
            freight_decline_months=6.0,  # months of decline (active)

            # Inflation: disinflation (crisis-era low)
            core_pce=1.0,
            t5yifr=1.5,
            mich=2.5,

            # Liquidity: CRISIS
            stlfsi4=6.0,                 # extreme stress
            sloos_ci=80.0,              # massive tightening

            # Risk: extreme risk-off + capitulation
            risk_appetite_pct=5.0,       # 5th percentile
            cot_composite=5.0,           # 5th percentile (extreme shorts)

            # Not fragile (Fed flooding system with liquidity)
            on_rrp=200.0,
            walcl_yoy=50.0,
            sofr_iorb_spread=-10.0,
        )

        # Step multiple times to satisfy confirmation
        state = _step_n(engine, indicators, 3, datetime(2009, 3, 1))

        assert state.risk_appetite == RiskRegime.RISK_OFF
        assert state.capitulation is True
        assert state.capitulation_confidence > 0.0
        assert state.liquidity == LiquidityRegime.CRISIS
        assert state.growth == GrowthRegime.CONTRACTION

        # Should NOT be fragile (Fed response prevents it)
        assert state.fragile is False


# ===================================================================
# Test 3 — Late 2021: crowded risk-on
# ===================================================================

class TestLate2021CrowdedRiskOn:
    """Extreme bullish consensus positioning with risk-on environment.
    Everyone positioned the same way creates snap-back risk.
    """

    def test_crowded_risk_on(self) -> None:
        engine = RegimeTransitionEngine()
        indicators = _make_neutral(
            # Risk: strong risk-on
            risk_appetite_pct=85.0,     # > 70th percentile
            cot_composite=92.0,         # > 80th percentile (extreme longs)
            # Low vol, tight spreads
            hy_oas=290.0,
            nfci=-0.60,
            stlfsi4=-0.5,
            sloos_ci=-5.0,
        )

        state = _step_n(engine, indicators, 2, datetime(2021, 11, 1))

        assert state.risk_appetite == RiskRegime.RISK_ON
        assert state.crowded is True
        assert state.crowded_confidence > 0.0


# ===================================================================
# Test 4 — Mid-2023: expansion + inflationary
# ===================================================================

class TestMid2023ExpansionInflationary:
    """Economy expanding but inflation remains elevated.
    Growth healthy, inflation above target.
    """

    def test_expansion_with_elevated_inflation(self) -> None:
        engine = RegimeTransitionEngine()
        indicators = _make_neutral(
            # Growth: solidly in expansion (0 recession indicators active)
            cfnaima3=0.15,
            sahm_rule=0.10,
            icsa_pct_above_trough=2.0,

            # Inflation: elevated
            core_pce=4.1,               # well above 2.5%
            t5yifr=2.3,                 # in reflation zone, near inflationary
            mich=4.5,                   # > 4.0% (inflationary)

            # Liquidity: neutral
            nfci=-0.30,
        )

        state = _step_n(engine, indicators, 3, datetime(2023, 6, 1))

        assert state.growth == GrowthRegime.EXPANSION
        assert state.inflation == InflationRegime.INFLATIONARY


# ===================================================================
# Test 5 — Hysteresis: NFCI no-whipsaw
# ===================================================================

class TestHysteresisNFCI:
    """NFCI crossing above 0.0 for 1 period should NOT trigger TIGHT.
    Persistence of 4+ periods (>= confirmation_periods) should trigger.
    Then dropping to -0.1 should NOT exit TIGHT (exit requires < -0.2).
    Dropping to -0.25 should exit to NEUTRAL.
    """

    def test_nfci_hysteresis_sequence(self) -> None:
        engine = RegimeTransitionEngine()
        ts = datetime(2023, 1, 1)

        # -- Phase 1: NFCI crosses above 0.0 for only 1 period --
        loose_indicators = _make_neutral(
            nfci=-0.60,
            hy_oas=320.0,
            stlfsi4=0.1,
            sloos_ci=-5.0,
        )
        # Establish base LOOSE state
        state = _step_n(engine, loose_indicators, 3, ts)
        assert state.liquidity == LiquidityRegime.LOOSE

        # Brief spike: NFCI = 0.1 for 1 period only
        spike_indicators = _make_neutral(
            nfci=0.10,
            hy_oas=320.0,
            stlfsi4=0.1,
            sloos_ci=-5.0,
        )
        state = engine.step(spike_indicators, ts + timedelta(days=90))
        # Should NOT have transitioned to TIGHT (only 1 period)
        assert state.liquidity != LiquidityRegime.TIGHT

        # Drop back immediately
        state = engine.step(loose_indicators, ts + timedelta(days=120))
        assert state.liquidity == LiquidityRegime.LOOSE

        # -- Phase 2: NFCI > 0.0 sustained for 5 periods --
        tight_indicators = _make_neutral(
            nfci=0.60,
            hy_oas=550.0,
            stlfsi4=1.2,
            sloos_ci=25.0,
        )
        # Step enough times to exceed confirmation_periods (2)
        for i in range(5):
            state = engine.step(tight_indicators, ts + timedelta(days=150 + 30 * i))

        # NOW should be TIGHT
        assert state.liquidity == LiquidityRegime.TIGHT

        # -- Phase 3: Drop NFCI to -0.1, should STILL be TIGHT --
        # (exit requires NFCI < -0.2 per hysteresis)
        mild_drop = _make_neutral(
            nfci=-0.10,
            hy_oas=480.0,
            stlfsi4=0.9,
            sloos_ci=18.0,
        )
        for i in range(3):
            state = engine.step(mild_drop, ts + timedelta(days=300 + 30 * i))
        # Should still be TIGHT (exit range for TIGHT is [-0.2, 1.7])
        assert state.liquidity == LiquidityRegime.TIGHT

        # -- Phase 4: Drop NFCI to -0.25, NOW exits to NEUTRAL --
        deep_drop = _make_neutral(
            nfci=-0.25,
            hy_oas=420.0,
            stlfsi4=0.6,
            sloos_ci=10.0,
        )
        for i in range(3):
            state = engine.step(deep_drop, ts + timedelta(days=390 + 30 * i))
        assert state.liquidity == LiquidityRegime.NEUTRAL


# ===================================================================
# Test 6 — Confirmation rule: N of M recession indicators
# ===================================================================

class TestConfirmationRule:
    """Exactly 2 of 8 recession indicators active for 3 months -> EXPANSION.
    Activate a 3rd -> after 2 months persistence: PEAK_LATE_CYCLE.
    Activate 5th -> after 2 months: CONTRACTION.
    """

    def test_gradual_recession_indicator_activation(self) -> None:
        engine = RegimeTransitionEngine()
        ts = datetime(2024, 1, 1)

        # -- Step A: 2 indicators active for 3 months -> EXPANSION --
        two_active = _make_neutral(
            sahm_rule=0.55,             # active (>= 0.50)
            cfnaima3=-0.80,             # active (<= -0.70)
            # All other growth indicators benign (not active)
        )
        state = _step_n(engine, two_active, 3, ts)
        assert state.growth == GrowthRegime.EXPANSION

        # -- Step B: Activate 3rd indicator -> candidate PEAK_LATE_CYCLE --
        three_active = _make_neutral(
            sahm_rule=0.55,
            cfnaima3=-0.80,
            hy_oas=550.0,              # active (>= 500)
        )
        # First period with 3: candidate set, count=1
        state = engine.step(three_active, ts + timedelta(days=90))
        # Not confirmed yet — should still be EXPANSION
        assert state.growth == GrowthRegime.EXPANSION

        # Second period: count=2 >= confirmation_periods -> confirmed PEAK
        state = engine.step(three_active, ts + timedelta(days=120))
        assert state.growth == GrowthRegime.PEAK_LATE_CYCLE

        # -- Step C: Activate 5th indicator -> candidate CONTRACTION --
        five_active = _make_neutral(
            sahm_rule=0.55,
            cfnaima3=-0.80,
            hy_oas=550.0,
            icsa_pct_above_trough=15.0,  # active (>= 10)
            permit_yoy=-25.0,            # active (<= -20)
        )
        # First period with 5: candidate set, count=1
        state = engine.step(five_active, ts + timedelta(days=150))
        assert state.growth == GrowthRegime.PEAK_LATE_CYCLE  # not confirmed yet

        # Second period: confirmed CONTRACTION
        state = engine.step(five_active, ts + timedelta(days=180))
        assert state.growth == GrowthRegime.CONTRACTION


# ===================================================================
# Test 7 — Stagflation detection
# ===================================================================

class TestStagflation:
    """Inflation elevated AND growth deteriorating.
    Core PCE = 3.5% (inflationary), CFNAIMA3 = -0.80 (contraction),
    PMI composite = 46 (below 50 and falling).
    """

    def test_stagflation_compound_detection(self) -> None:
        engine = RegimeTransitionEngine()
        indicators = _make_neutral(
            # Growth: deep in contraction (5+ indicators active)
            sahm_rule=0.60,
            cfnaima3=-0.80,
            hy_oas=520.0,
            icsa_pct_above_trough=12.0,
            permit_yoy=-22.0,
            freight_decline_months=4.0,

            # Inflation: elevated
            core_pce=3.5,              # > 2.5%
            t5yifr=2.6,               # > 2.5%
            mich=4.2,                  # > 4.0%

            # PMI for stagflation override
            pmi_composite=46.0,

            # Liquidity: tightening
            nfci=0.30,
            stlfsi4=1.5,
            sloos_ci=30.0,
        )

        # Step enough times to confirm both growth and inflation
        state = _step_n(engine, indicators, 3, datetime(2024, 1, 1))

        assert state.inflation == InflationRegime.STAGFLATION
        assert state.growth == GrowthRegime.CONTRACTION


# ===================================================================
# Test 8 — Sub-states are overlays, not replacements
# ===================================================================

class TestSubStatesAreOverlays:
    """When Fragile = TRUE, the base liquidity state should still be
    LOOSE (not overwritten).  When Crowded = TRUE, the base risk state
    should still be RISK_ON.
    """

    def test_fragile_preserves_base_liquidity(self) -> None:
        engine = RegimeTransitionEngine()

        # Step 1: establish benign base state
        base = _make_neutral(
            nfci=-0.60,
            hy_oas=320.0,
            stlfsi4=-0.3,
            sloos_ci=-5.0,
            on_rrp=300.0,
            walcl_yoy=5.0,
            sofr_iorb_spread=-3.0,
        )
        state = _step_n(engine, base, 2, datetime(2023, 6, 1))
        assert state.liquidity == LiquidityRegime.LOOSE
        assert state.fragile is False

        # Step 2: add fragile plumbing conditions but keep surface calm
        fragile_base = _make_neutral(
            nfci=-0.60,
            hy_oas=320.0,
            stlfsi4=-0.3,
            sloos_ci=-5.0,
            on_rrp=20.0,               # depleted
            walcl_yoy=-2.0,            # QT
            sofr_iorb_spread=5.0,      # SOFR above IORB
        )
        state = engine.step(fragile_base, datetime(2023, 7, 1))

        # Base liquidity UNCHANGED — still LOOSE
        assert state.liquidity == LiquidityRegime.LOOSE
        # Sub-state independently set
        assert state.fragile is True
        assert state.fragile_confidence > 0.0

    def test_crowded_preserves_base_risk(self) -> None:
        engine = RegimeTransitionEngine()

        # Establish risk-on base
        risk_on = _make_neutral(
            risk_appetite_pct=85.0,
            cot_composite=50.0,        # not crowded yet
        )
        state = _step_n(engine, risk_on, 2, datetime(2021, 10, 1))
        assert state.risk_appetite == RiskRegime.RISK_ON
        assert state.crowded is False

        # Now add extreme positioning
        crowded_on = _make_neutral(
            risk_appetite_pct=85.0,
            cot_composite=92.0,        # extreme longs
        )
        state = engine.step(crowded_on, datetime(2021, 11, 1))

        # Base risk state UNCHANGED — still RISK_ON
        assert state.risk_appetite == RiskRegime.RISK_ON
        # Sub-state independently set
        assert state.crowded is True
        assert state.crowded_confidence > 0.0

    def test_capitulation_preserves_base_risk(self) -> None:
        engine = RegimeTransitionEngine()

        # Establish risk-off base
        risk_off = _make_neutral(
            risk_appetite_pct=10.0,
            cot_composite=50.0,
        )
        state = _step_n(engine, risk_off, 2, datetime(2009, 3, 1))
        assert state.risk_appetite == RiskRegime.RISK_OFF
        assert state.capitulation is False

        # Add extreme short positioning
        cap_off = _make_neutral(
            risk_appetite_pct=10.0,
            cot_composite=5.0,         # extreme shorts
        )
        state = engine.step(cap_off, datetime(2009, 4, 1))

        # Base risk state still RISK_OFF
        assert state.risk_appetite == RiskRegime.RISK_OFF
        # Sub-state independently set
        assert state.capitulation is True
        assert state.capitulation_confidence > 0.0
