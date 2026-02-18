"""Test suite for the Phase 1 indicator registry.

Ten acceptance tests validate the structure, content, helper functions,
and integrity of the INDICATOR_REGISTRY.  All must pass for Phase 1 to
be accepted.
"""
from __future__ import annotations

from macro_regime_dashboard.config.indicator_registry import (
    INDICATOR_REGISTRY,
    IndicatorMeta,
    get_by_tier,
    get_by_dimension,
    get_by_source,
    get_by_sub_state,
    get_fred_ids,
    get_constructed_indicators,
    validate_registry,
)


# ---------------------------------------------------------------
# Test 1 — Registry completeness
# ---------------------------------------------------------------

class TestRegistryCompleteness:
    """Assert the registry contains exactly the expected number of entries."""

    def test_total_count(self) -> None:
        assert len(INDICATOR_REGISTRY) == 65

    def test_tier_1_count(self) -> None:
        assert len(get_by_tier(1)) == 15

    def test_tier_2_count(self) -> None:
        assert len(get_by_tier(2)) == 40

    def test_tier_3_count(self) -> None:
        assert len(get_by_tier(3)) == 10


# ---------------------------------------------------------------
# Test 2 — Tier 1 coverage of all regime dimensions
# ---------------------------------------------------------------

class TestTier1DimensionCoverage:
    """Assert that Tier 1 indicators collectively cover all four regime
    dimensions (plus 'multi')."""

    def test_growth_tier1(self) -> None:
        tier1 = get_by_tier(1)
        growth_ids = {m.series_id for m in tier1
                      if m.regime_dimension == "growth"}
        expected = {
            "T10Y3M", "T10Y2Y", "SAHMREALTIME", "ICSA",
            "PERMIT", "GACDFSA066MSFRBPHI", "CFNAIMA3",
        }
        assert expected == growth_ids

    def test_inflation_tier1(self) -> None:
        tier1 = get_by_tier(1)
        inflation_ids = {m.series_id for m in tier1
                         if m.regime_dimension == "inflation"}
        assert inflation_ids == {"PCEPILFE", "T5YIFR"}

    def test_liquidity_tier1(self) -> None:
        tier1 = get_by_tier(1)
        liquidity_ids = {m.series_id for m in tier1
                         if m.regime_dimension == "liquidity"}
        assert liquidity_ids == {"NFCI", "DFF"}

    def test_risk_tier1(self) -> None:
        tier1 = get_by_tier(1)
        risk_ids = {m.series_id for m in tier1
                    if m.regime_dimension == "risk"}
        assert risk_ids == {"VIXCLS", "SP500"}

    def test_multi_tier1(self) -> None:
        tier1 = get_by_tier(1)
        multi_ids = {m.series_id for m in tier1
                     if m.regime_dimension == "multi"}
        assert multi_ids == {"BAMLH0A0HYM2", "M2SL"}

    def test_all_four_dimensions_present(self) -> None:
        tier1 = get_by_tier(1)
        dims = {m.regime_dimension for m in tier1}
        assert {"growth", "inflation", "liquidity", "risk"}.issubset(dims)


# ---------------------------------------------------------------
# Test 3 — Fragile sub-state has all required indicators
# ---------------------------------------------------------------

class TestFragileSubState:
    """Assert the Fragile sub-state filter returns the required series."""

    def test_fragile_indicators(self) -> None:
        fragile = get_by_sub_state("fragile")
        fragile_ids = {m.series_id for m in fragile}
        required = {"RRPONTSYD", "SOFR", "IORB", "WALCL", "SOFR_IORB_SPREAD"}
        assert required.issubset(fragile_ids)


# ---------------------------------------------------------------
# Test 4 — Crowded/Capitulation sub-state has all required indicators
# ---------------------------------------------------------------

class TestCrowdedCapitulationSubState:
    """Assert the Crowded/Capitulation sub-state filter returns the
    required COT contracts and composite."""

    def test_crowded_has_required_cot(self) -> None:
        crowded = get_by_sub_state("crowded")
        crowded_ids = {m.series_id for m in crowded}
        required_cot = {"COT_ES", "COT_TY", "COT_GC", "COT_VX", "COT_DX"}
        assert required_cot.issubset(crowded_ids)

    def test_crowded_has_composite(self) -> None:
        crowded = get_by_sub_state("crowded")
        crowded_ids = {m.series_id for m in crowded}
        assert "COT_RISK_COMPOSITE" in crowded_ids

    def test_capitulation_matches_crowded(self) -> None:
        crowded_ids = {m.series_id for m in get_by_sub_state("crowded")}
        cap_ids = {m.series_id for m in get_by_sub_state("capitulation")}
        assert crowded_ids == cap_ids


# ---------------------------------------------------------------
# Test 5 — FRED ID grouping is correct
# ---------------------------------------------------------------

class TestFredIdGrouping:
    """Assert FRED IDs are grouped by frequency correctly and no
    non-FRED series leak in."""

    def test_daily_contains_t10y3m(self) -> None:
        fred_groups = get_fred_ids()
        assert "T10Y3M" in fred_groups["daily"]

    def test_weekly_contains_icsa(self) -> None:
        fred_groups = get_fred_ids()
        assert "ICSA" in fred_groups["weekly"]

    def test_monthly_contains_cfnaima3(self) -> None:
        fred_groups = get_fred_ids()
        assert "CFNAIMA3" in fred_groups["monthly"]

    def test_quarterly_contains_drtscilm(self) -> None:
        fred_groups = get_fred_ids()
        assert "DRTSCILM" in fred_groups["quarterly"]

    def test_no_cftc_in_fred_groups(self) -> None:
        fred_groups = get_fred_ids()
        cftc_ids = {m.series_id for m in get_by_source("cftc")}
        all_fred_ids = set()
        for ids in fred_groups.values():
            all_fred_ids.update(ids)
        assert cftc_ids.isdisjoint(all_fred_ids)

    def test_no_yfinance_in_fred_groups(self) -> None:
        fred_groups = get_fred_ids()
        yf_ids = {m.series_id for m in get_by_source("yfinance")}
        all_fred_ids = set()
        for ids in fred_groups.values():
            all_fred_ids.update(ids)
        assert yf_ids.isdisjoint(all_fred_ids)


# ---------------------------------------------------------------
# Test 6 — Constructed indicators are properly flagged
# ---------------------------------------------------------------

class TestConstructedIndicators:
    """Assert constructed indicators are identified and have formulas."""

    def test_constructed_series_present(self) -> None:
        constructed = get_constructed_indicators()
        constructed_ids = {m.series_id for m in constructed}
        assert {"SOFR_IORB_SPREAD", "COT_RISK_COMPOSITE",
                "RISK_APPETITE_INDEX"} == constructed_ids

    def test_constructed_have_source_detail(self) -> None:
        for m in get_constructed_indicators():
            assert m.source_detail, (
                f"{m.series_id} missing source_detail"
            )

    def test_constructed_not_fred_or_cftc(self) -> None:
        for m in get_constructed_indicators():
            assert m.source == "constructed", (
                f"{m.series_id} has source='{m.source}', expected 'constructed'"
            )


# ---------------------------------------------------------------
# Test 7 — Inversion flags are correct for key series
# ---------------------------------------------------------------

class TestInversionFlags:
    """Assert critical inversion flags are set correctly — a wrong sign
    in composite construction inverts reality."""

    def test_vixcls_inverted(self) -> None:
        assert INDICATOR_REGISTRY["VIXCLS"].inverted is True

    def test_hy_oas_inverted(self) -> None:
        assert INDICATOR_REGISTRY["BAMLH0A0HYM2"].inverted is True

    def test_nfci_inverted(self) -> None:
        assert INDICATOR_REGISTRY["NFCI"].inverted is True

    def test_sp500_not_inverted(self) -> None:
        assert INDICATOR_REGISTRY["SP500"].inverted is False

    def test_pcepilfe_not_inverted(self) -> None:
        assert INDICATOR_REGISTRY["PCEPILFE"].inverted is False

    def test_cot_ty_inverted(self) -> None:
        assert INDICATOR_REGISTRY["COT_TY"].inverted is True

    def test_cot_es_not_inverted(self) -> None:
        assert INDICATOR_REGISTRY["COT_ES"].inverted is False


# ---------------------------------------------------------------
# Test 8 — Validate registry integrity
# ---------------------------------------------------------------

class TestValidateRegistry:
    """Assert validate_registry() returns no errors."""

    def test_no_errors(self) -> None:
        errors = validate_registry()
        assert errors == [], f"Registry validation errors: {errors}"


# ---------------------------------------------------------------
# Test 9 — Publication lag sanity
# ---------------------------------------------------------------

class TestPublicationLag:
    """Assert publication lag values are sensible for different series
    types."""

    def test_daily_market_data_lag_at_most_1(self) -> None:
        """Daily market-data series (yields, VIX, SOFR, ON RRP) should
        have publication_lag_days <= 1."""
        daily_market_ids = [
            "T10Y3M", "T10Y2Y", "BAMLH0A0HYM2", "DFF", "T5YIFR",
            "VIXCLS", "SP500", "DFII10", "T5YIE", "T10YIE",
            "BAMLC0A0CM", "BAA10Y", "DCOILWTICO", "GOLDAMGBD228NLBM",
            "SOFR", "RRPONTSYD",
        ]
        for sid in daily_market_ids:
            meta = INDICATOR_REGISTRY[sid]
            assert meta.publication_lag_days <= 1, (
                f"{sid} has pub_lag={meta.publication_lag_days}, expected <= 1"
            )

    def test_sloos_lag_at_least_45(self) -> None:
        assert INDICATOR_REGISTRY["DRTSCILM"].publication_lag_days >= 45

    def test_core_pce_lag_at_least_25(self) -> None:
        assert INDICATOR_REGISTRY["PCEPILFE"].publication_lag_days >= 25

    def test_no_negative_lags(self) -> None:
        for sid, meta in INDICATOR_REGISTRY.items():
            assert meta.publication_lag_days >= 0, (
                f"{sid} has negative publication_lag_days"
            )


# ---------------------------------------------------------------
# Test 10 — History start dates allow four-cycle backtest for Tier 1
# ---------------------------------------------------------------

class TestHistoryStartDates:
    """For every Tier 1 indicator, assert history_start <= '1990-01'.
    Exception: T5YIFR starts 2003-01 (TIPS market didn't exist before).
    """

    def test_tier1_history_before_1990(self) -> None:
        # Known exceptions: series whose underlying market/data source
        # did not exist before 1990.
        exceptions = {
            "T5YIFR": "2003-01",       # TIPS market didn't exist before 2003
            "BAMLH0A0HYM2": "1996-12", # ICE BofA HY index starts Dec 1996
        }
        for m in get_by_tier(1):
            if m.series_id in exceptions:
                assert m.history_start == exceptions[m.series_id], (
                    f"{m.series_id} expected history_start="
                    f"'{exceptions[m.series_id]}', got '{m.history_start}'"
                )
                continue
            assert m.history_start <= "1990-01", (
                f"{m.series_id} has history_start='{m.history_start}', "
                f"expected <= '1990-01' for four-cycle backtest"
            )

    def test_t5yifr_exception_flagged(self) -> None:
        """T5YIFR starts 2003-01 — backtest must handle its absence in
        pre-2003 periods."""
        meta = INDICATOR_REGISTRY["T5YIFR"]
        assert meta.history_start == "2003-01"
        assert "2003" in meta.notes or "TIPS" in meta.notes
