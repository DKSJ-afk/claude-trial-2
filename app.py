"""Streamlit dashboard for the Macroeconomic Regime Nowcasting Engine.

Run locally:  streamlit run app.py
Deploy free:  https://share.streamlit.io  (connect your GitHub repo)
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from macro_regime_dashboard.config.regime_config import (
    GrowthRegime,
    InflationRegime,
    LiquidityRegime,
    RiskRegime,
    RegimeState,
    RegimeTransitionEngine,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Macro Regime Dashboard",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Preset scenarios
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict[str, float]] = {
    "Custom (use sliders)": {},
    "Sept 2019 — Fragile (pre-repo spike)": {
        "t10y3m": 0.05, "hy_oas": 380.0, "nfci": -0.60,
        "icsa_pct_above_trough": 2.0, "sahm_rule": 0.10,
        "cfnaima3": 0.15, "permit_yoy": 3.0, "freight_decline_months": 0.0,
        "core_pce": 1.8, "t5yifr": 2.1, "mich": 2.5,
        "stlfsi4": -0.3, "sloos_ci": 5.0,
        "risk_appetite_pct": 55.0, "cot_composite": 50.0,
        "on_rrp": 30.0, "walcl_yoy": -3.0, "sofr_iorb_spread": 5.0,
    },
    "March 2009 — Capitulation + Crisis": {
        "t10y3m": 2.50, "hy_oas": 1800.0, "nfci": 2.50,
        "icsa_pct_above_trough": 80.0, "sahm_rule": 1.20,
        "cfnaima3": -1.50, "permit_yoy": -35.0, "freight_decline_months": 6.0,
        "core_pce": 1.0, "t5yifr": 1.5, "mich": 2.5,
        "stlfsi4": 6.0, "sloos_ci": 80.0,
        "risk_appetite_pct": 5.0, "cot_composite": 5.0,
        "on_rrp": 200.0, "walcl_yoy": 50.0, "sofr_iorb_spread": -10.0,
    },
    "Late 2021 — Crowded Risk-On": {
        "t10y3m": 1.50, "hy_oas": 290.0, "nfci": -0.60,
        "icsa_pct_above_trough": 2.0, "sahm_rule": 0.10,
        "cfnaima3": 0.30, "permit_yoy": 10.0, "freight_decline_months": 0.0,
        "core_pce": 4.5, "t5yifr": 2.4, "mich": 4.2,
        "stlfsi4": -0.5, "sloos_ci": -5.0,
        "risk_appetite_pct": 85.0, "cot_composite": 92.0,
        "on_rrp": 1500.0, "walcl_yoy": 15.0, "sofr_iorb_spread": -5.0,
    },
    "Mid-2023 — Expansion + Inflationary": {
        "t10y3m": -0.50, "hy_oas": 450.0, "nfci": -0.30,
        "icsa_pct_above_trough": 3.0, "sahm_rule": 0.10,
        "cfnaima3": 0.15, "permit_yoy": -5.0, "freight_decline_months": 1.0,
        "core_pce": 4.1, "t5yifr": 2.3, "mich": 4.5,
        "stlfsi4": 0.1, "sloos_ci": 25.0,
        "risk_appetite_pct": 55.0, "cot_composite": 55.0,
        "on_rrp": 2000.0, "walcl_yoy": -5.0, "sofr_iorb_spread": -2.0,
    },
    "Stagflation scenario": {
        "t10y3m": 0.10, "hy_oas": 520.0, "nfci": 0.30,
        "icsa_pct_above_trough": 12.0, "sahm_rule": 0.60,
        "cfnaima3": -0.80, "permit_yoy": -22.0, "freight_decline_months": 4.0,
        "core_pce": 3.5, "t5yifr": 2.6, "mich": 4.2,
        "stlfsi4": 1.5, "sloos_ci": 30.0,
        "risk_appetite_pct": 35.0, "cot_composite": 45.0,
        "on_rrp": 100.0, "walcl_yoy": -2.0, "sofr_iorb_spread": 3.0,
        "pmi_composite": 46.0,
    },
}

# ---------------------------------------------------------------------------
# Regime display colours
# ---------------------------------------------------------------------------

GROWTH_COLOURS = {
    GrowthRegime.EXPANSION: "🟢",
    GrowthRegime.PEAK_LATE_CYCLE: "🟡",
    GrowthRegime.CONTRACTION: "🔴",
    GrowthRegime.TROUGH_EARLY_RECOVERY: "🔵",
}
INFLATION_COLOURS = {
    InflationRegime.DISINFLATION: "🔵",
    InflationRegime.REFLATION: "🟢",
    InflationRegime.INFLATIONARY: "🟠",
    InflationRegime.STAGFLATION: "🔴",
}
LIQUIDITY_COLOURS = {
    LiquidityRegime.LOOSE: "🟢",
    LiquidityRegime.NEUTRAL: "🟡",
    LiquidityRegime.TIGHT: "🟠",
    LiquidityRegime.CRISIS: "🔴",
}
RISK_COLOURS = {
    RiskRegime.RISK_ON: "🟢",
    RiskRegime.RISK_OFF: "🔴",
    RiskRegime.TRANSITIONAL: "🟡",
}

# ---------------------------------------------------------------------------
# Session state: persistent engine
# ---------------------------------------------------------------------------

if "engine" not in st.session_state:
    st.session_state.engine = RegimeTransitionEngine()
    st.session_state.history: list[RegimeState] = []

engine: RegimeTransitionEngine = st.session_state.engine
history: list[RegimeState] = st.session_state.history

# ---------------------------------------------------------------------------
# Sidebar — indicator inputs
# ---------------------------------------------------------------------------

st.sidebar.title("Indicator Inputs")

preset = st.sidebar.selectbox("Load a preset scenario", list(PRESETS.keys()))
preset_vals = PRESETS[preset]

if st.sidebar.button("Reset engine state"):
    engine.reset()
    st.session_state.history = []
    history = st.session_state.history
    st.sidebar.success("Engine reset.")

st.sidebar.markdown("---")
st.sidebar.subheader("Growth Indicators")

def _val(key: str, default: float) -> float:
    return preset_vals.get(key, default) if preset_vals else default

t10y3m = st.sidebar.slider("T10Y3M (yield curve spread)", -2.0, 4.0, _val("t10y3m", 1.5), 0.05)
hy_oas = st.sidebar.slider("HY OAS (bp)", 100.0, 2500.0, _val("hy_oas", 350.0), 10.0)
nfci = st.sidebar.slider("NFCI", -1.5, 4.0, _val("nfci", -0.3), 0.05)
icsa_pct = st.sidebar.slider("Initial Claims (% above trough)", 0.0, 100.0, _val("icsa_pct_above_trough", 2.0), 1.0)
sahm = st.sidebar.slider("Sahm Rule", 0.0, 2.0, _val("sahm_rule", 0.1), 0.05)
cfnaima3 = st.sidebar.slider("CFNAIMA3", -2.0, 1.0, _val("cfnaima3", 0.2), 0.05)
permit_yoy = st.sidebar.slider("Building Permits YoY %", -50.0, 30.0, _val("permit_yoy", 5.0), 1.0)
freight = st.sidebar.slider("Freight decline (months)", 0.0, 12.0, _val("freight_decline_months", 0.0), 1.0)

st.sidebar.markdown("---")
st.sidebar.subheader("Inflation Indicators")
core_pce = st.sidebar.slider("Core PCE YoY %", 0.0, 8.0, _val("core_pce", 2.0), 0.1)
t5yifr = st.sidebar.slider("5Y5Y Forward %", 0.5, 4.0, _val("t5yifr", 2.2), 0.05)
mich = st.sidebar.slider("Michigan Inflation Exp %", 1.0, 7.0, _val("mich", 2.8), 0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("Liquidity Indicators")
stlfsi4 = st.sidebar.slider("STLFSI4", -2.0, 8.0, _val("stlfsi4", 0.1), 0.1)
sloos_ci = st.sidebar.slider("SLOOS C&I net tightening %", -30.0, 100.0, _val("sloos_ci", 5.0), 1.0)

st.sidebar.markdown("---")
st.sidebar.subheader("Risk Indicators")
risk_pct = st.sidebar.slider("Risk appetite percentile", 0.0, 100.0, _val("risk_appetite_pct", 50.0), 1.0)
cot = st.sidebar.slider("COT composite percentile", 0.0, 100.0, _val("cot_composite", 50.0), 1.0)

st.sidebar.markdown("---")
st.sidebar.subheader("Fragile Sub-State Indicators")
on_rrp = st.sidebar.slider("ON RRP balance ($B)", 0.0, 2500.0, _val("on_rrp", 300.0), 10.0)
walcl_yoy = st.sidebar.slider("WALCL YoY %", -10.0, 60.0, _val("walcl_yoy", 5.0), 0.5)
sofr_iorb = st.sidebar.slider("SOFR-IORB spread (bp)", -15.0, 20.0, _val("sofr_iorb_spread", -3.0), 0.5)

# Build indicator dict
indicators: dict[str, float] = {
    "t10y3m": t10y3m,
    "hy_oas": hy_oas,
    "nfci": nfci,
    "icsa_pct_above_trough": icsa_pct,
    "sahm_rule": sahm,
    "cfnaima3": cfnaima3,
    "permit_yoy": permit_yoy,
    "freight_decline_months": freight,
    "core_pce": core_pce,
    "t5yifr": t5yifr,
    "mich": mich,
    "stlfsi4": stlfsi4,
    "sloos_ci": sloos_ci,
    "risk_appetite_pct": risk_pct,
    "cot_composite": cot,
    "on_rrp": on_rrp,
    "walcl_yoy": walcl_yoy,
    "sofr_iorb_spread": sofr_iorb,
}

# Add PMI if present in preset
if "pmi_composite" in preset_vals:
    indicators["pmi_composite"] = preset_vals["pmi_composite"]

# ---------------------------------------------------------------------------
# Main area — step engine and display
# ---------------------------------------------------------------------------

st.title("📊 Macro Regime Nowcasting Dashboard")
st.caption("Phase 0 — Rules-based regime classification with hysteresis and confirmation")

# Auto-step: run engine twice on each render to satisfy confirmation
state = engine.step(indicators, datetime.now())
state = engine.step(indicators, datetime.now())
history.append(state)

# Keep only last 50 in history
if len(history) > 50:
    st.session_state.history = history[-50:]
    history = st.session_state.history

# --- Regime cards ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    icon = GROWTH_COLOURS.get(state.growth, "")
    st.metric("Growth", f"{icon} {state.growth.value.replace('_', ' ').title()}")
    prob = state.growth_probs.get(state.growth, 0)
    st.progress(prob, text=f"Confidence: {prob:.0%}")

with col2:
    icon = INFLATION_COLOURS.get(state.inflation, "")
    st.metric("Inflation", f"{icon} {state.inflation.value.replace('_', ' ').title()}")
    prob = state.inflation_probs.get(state.inflation, 0)
    st.progress(prob, text=f"Confidence: {prob:.0%}")

with col3:
    icon = LIQUIDITY_COLOURS.get(state.liquidity, "")
    st.metric("Liquidity", f"{icon} {state.liquidity.value.replace('_', ' ').title()}")
    prob = state.liquidity_probs.get(state.liquidity, 0)
    st.progress(prob, text=f"Confidence: {prob:.0%}")

with col4:
    icon = RISK_COLOURS.get(state.risk_appetite, "")
    st.metric("Risk Appetite", f"{icon} {state.risk_appetite.value.replace('_', ' ').title()}")
    prob = state.risk_probs.get(state.risk_appetite, 0)
    st.progress(prob, text=f"Confidence: {prob:.0%}")

# --- Sub-state overlays ---
st.markdown("---")
st.subheader("Sub-State Overlays")

sub_col1, sub_col2, sub_col3 = st.columns(3)

with sub_col1:
    if state.fragile:
        st.error(f"**FRAGILE** — Confidence: {state.fragile_confidence:.0%}")
        st.caption("Surface calm but plumbing stressed. Liquidity buffer depleted, reserves draining.")
    else:
        st.success("Fragile: Inactive")

with sub_col2:
    if state.crowded:
        st.warning(f"**CROWDED** — Confidence: {state.crowded_confidence:.0%}")
        st.caption("Extreme consensus long positioning. Trend intact but snap-back risk elevated.")
    else:
        st.success("Crowded: Inactive")

with sub_col3:
    if state.capitulation:
        st.info(f"**CAPITULATION** — Confidence: {state.capitulation_confidence:.0%}")
        st.caption("Extreme short positioning. Historically highest risk-adjusted entry point.")
    else:
        st.success("Capitulation: Inactive")

# --- Alerts ---
if state.alerts:
    st.markdown("---")
    st.subheader("Alerts")
    for alert in state.alerts:
        st.warning(alert)

# --- Probability distributions ---
st.markdown("---")
st.subheader("Probability Distributions")

prob_col1, prob_col2 = st.columns(2)

with prob_col1:
    st.markdown("**Growth**")
    for regime, prob in sorted(state.growth_probs.items(), key=lambda x: -x[1]):
        label = regime.value.replace("_", " ").title()
        st.progress(prob, text=f"{label}: {prob:.0%}")

    st.markdown("**Inflation**")
    for regime, prob in sorted(state.inflation_probs.items(), key=lambda x: -x[1]):
        label = regime.value.replace("_", " ").title()
        st.progress(prob, text=f"{label}: {prob:.0%}")

with prob_col2:
    st.markdown("**Liquidity**")
    for regime, prob in sorted(state.liquidity_probs.items(), key=lambda x: -x[1]):
        label = regime.value.replace("_", " ").title()
        st.progress(prob, text=f"{label}: {prob:.0%}")

    st.markdown("**Risk**")
    for regime, prob in sorted(state.risk_probs.items(), key=lambda x: -x[1]):
        label = regime.value.replace("_", " ").title()
        st.progress(prob, text=f"{label}: {prob:.0%}")

# --- Raw summary ---
with st.expander("Raw RegimeState summary"):
    st.code(state.summary())
    st.json({
        "growth": state.growth.value,
        "inflation": state.inflation.value,
        "liquidity": state.liquidity.value,
        "risk_appetite": state.risk_appetite.value,
        "fragile": state.fragile,
        "fragile_confidence": round(state.fragile_confidence, 3),
        "crowded": state.crowded,
        "crowded_confidence": round(state.crowded_confidence, 3),
        "capitulation": state.capitulation,
        "capitulation_confidence": round(state.capitulation_confidence, 3),
        "model_version": state.model_version,
        "alerts": state.alerts,
    })
