# Macro Regime Dashboard

A macroeconomic regime nowcasting dashboard that classifies current economic conditions across four dimensions: Growth, Inflation, Liquidity, and Risk Appetite.

## Phase 0 — Regime Ontology

Phase 0 defines the formal taxonomy of macroeconomic states that all downstream phases consume.

### Project Structure

```
macro_regime_dashboard/
    __init__.py
    config/
        __init__.py
        regime_config.py          # Enums, thresholds, RegimeTransitionEngine
        indicator_registry.py     # Stub for Phase 1 data pipeline
tests/
    __init__.py
    test_regime_config.py         # 8 historical scenario acceptance tests
```

### Regime Dimensions

| Dimension | States | Primary Indicators |
|-----------|--------|--------------------|
| **Growth** | Expansion, Peak/Late-Cycle, Contraction, Trough/Early-Recovery | Sahm Rule, CFNAI, yield curve, claims, HY OAS, NFCI, permits, freight |
| **Inflation** | Disinflation, Reflation, Inflationary, Stagflation | Core PCE YoY, 5Y5Y Forward, Michigan Expectations |
| **Liquidity** | Loose, Neutral, Tight, Crisis | NFCI, HY OAS, STLFSI4, SLOOS C&I |
| **Risk** | Risk-On, Transitional, Risk-Off | Composite percentile (VIX, OAS, S&P vs 200d, DXY, copper) |

### Sub-State Overlays

- **Fragile**: Surface conditions appear loose, but funding plumbing is stressed (Sept 2019 scenario)
- **Crowded Risk-On**: Extreme consensus long positioning creates snap-back risk
- **Capitulation**: Extreme short positioning — historically highest risk-adjusted entry points

### Running the Dashboard

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens an interactive web dashboard where you can:
- Adjust indicator sliders to explore regime classifications in real time
- Load preset scenarios (Sept 2019, March 2009, Late 2021, Mid-2023, Stagflation)
- See probability distributions across all regime states
- Monitor sub-state overlays (Fragile, Crowded, Capitulation)

### Free Hosting on Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub and click **New app**
4. Select this repo, branch, and `app.py` as the main file
5. Click **Deploy** — your dashboard will be live at a public URL

### Running Tests

```bash
python -m pytest tests/test_regime_config.py -v
```

### Phase Roadmap

| Phase | Description |
|-------|-------------|
| **0** | Regime ontology — enums, thresholds, transition engine (this phase) |
| **1** | Data pipeline — FRED/CFTC/Yahoo Finance ingestion, transforms, caching |
| **2** | Dashboard — Streamlit/Dash frontend with regime visualisation |
| **3** | Alerting — Regime transition notifications |
| **4A** | HMM posteriors — Replace rules-based probability with Hidden Markov Model |
| **4B** | Backtesting — Historical regime classification validation |

### Requirements

- Python 3.11+
- `streamlit` for the dashboard (see `requirements.txt`)
- pytest for running tests
