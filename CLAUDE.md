# CLAUDE.md — Project Conventions

## Project Overview

Macroeconomic regime nowcasting dashboard. Phase 0 (current) implements the regime ontology — the formal taxonomy of macroeconomic states, threshold configurations, and a stateful transition engine.

## Quick Reference

```bash
# Run all tests
python -m pytest tests/test_regime_config.py -v

# Run a single test class
python -m pytest tests/test_regime_config.py::TestSept2019Fragile -v
```

## Architecture

- `macro_regime_dashboard/config/regime_config.py` — Core module containing all enums (`GrowthRegime`, `InflationRegime`, `LiquidityRegime`, `RiskRegime`), threshold dataclasses, the `RegimeTransitionEngine`, and `RegimeState`.
- `macro_regime_dashboard/config/indicator_registry.py` — Phase 1 stub for data source metadata (`IndicatorMeta` dataclass).
- `tests/test_regime_config.py` — 8 acceptance test scenarios using historical episodes.

## Code Conventions

- **Python 3.11+** — uses `X | None` union syntax and modern type hints
- **stdlib only** for Phase 0 — `dataclasses`, `enum`, `datetime`, `typing`
- **`from __future__ import annotations`** in every module for forward references
- **Type hints on every function** — parameters and return types
- **Docstrings on every public class and method** — describe the macro logic, not just the code
- **Frozen dataclasses** for threshold configs — all thresholds are immutable constants
- **No thresholds hardcoded in logic** — all values live in `ThresholdConfig` dataclasses

## Key Design Patterns

### Hysteresis
Entry thresholds differ from exit thresholds to prevent regime whipsaw. Once in a regime, the engine uses stricter exit thresholds before transitioning out.

### Confirmation / Persistence
A candidate regime must persist for N consecutive `step()` calls before the engine transitions. Default is 2 periods for most dimensions.

### Vote Counting (Growth Dimension)
8 recession indicators each vote active/inactive. The vote count maps to a growth regime: 0-2 = Expansion, 3-4 = Peak/Late-Cycle, 5+ = Contraction.

### Sub-State Overlays
Fragile, Crowded, and Capitulation are boolean modifiers on base regimes — they never replace the base enum value. Evaluated independently after base regime classification.

### Stagflation Override
After growth and inflation are evaluated independently, if growth = CONTRACTION and inflation = INFLATIONARY (or PMI < 50 with elevated inflation), inflation is overridden to STAGFLATION.

## Indicator Keys

The `RegimeTransitionEngine.step()` method accepts a `dict[str, float]` of indicator observations. Key indicator names used by the engine:

### Growth Dimension
`t10y3m`, `hy_oas`, `nfci`, `icsa_pct_above_trough`, `sahm_rule`, `cfnaima3`, `permit_yoy`, `freight_decline_months`

### Inflation Dimension
`core_pce`, `t5yifr`, `mich`

### Liquidity Dimension
`nfci` (shared with growth), `hy_oas` (shared with growth), `stlfsi4`, `sloos_ci`

### Risk Dimension
`risk_appetite_pct`, `cot_composite`

### Sub-State Indicators
`on_rrp`, `walcl_yoy`, `sofr_iorb_spread` (Fragile); `cot_composite` (Crowded/Capitulation)
