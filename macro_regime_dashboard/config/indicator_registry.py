"""Indicator registry — Phase 1 data catalogue.

This module defines the complete metadata registry for every data series the
macroeconomic regime nowcasting dashboard consumes.  Each series is registered
as an :class:`IndicatorMeta` entry inside :data:`INDICATOR_REGISTRY`, keyed by
its ``series_id``.

The registry serves as the translation layer between external data sources
(FRED, CFTC, Yahoo Finance, etc.) and the internal regime classification
engine from Phase 0.  If a series is not in this registry, it does not exist
to the system.

Helper functions provide filtered views by tier, dimension, source, sub-state
role, and data provider.  A :func:`validate_registry` function performs
structural integrity checks.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IndicatorMeta:
    """Metadata for a single economic indicator series.

    Attributes:
        series_id: Primary identifier.  FRED ID for FRED series, custom
            for constructed or external sources.
        name: Human-readable name for dashboard display.
        description: One-liner explaining what this measures and why we care.
        source: Data provider — ``'fred'``, ``'cftc'``, ``'yfinance'``,
            ``'binance'``, ``'coingecko'``, or ``'constructed'``.
        source_detail: API endpoint, URL, ticker symbol, or construction
            formula depending on the source.
        frequency: Publication cadence — ``'daily'``, ``'weekly'``,
            ``'monthly'``, ``'quarterly'``, or ``'8-hourly'``.
        tier: Priority tier.  1 = core (must-have), 2 = confirmation,
            3 = supplementary watchlist.
        regime_dimension: Which regime axis this indicator informs —
            ``'growth'``, ``'inflation'``, ``'liquidity'``, ``'risk'``,
            or ``'multi'`` if cross-dimension.
        sub_state_role: Which sub-state overlay this feeds —
            ``'none'``, ``'fragile'``, or ``'crowded_capitulation'``.
        transform: How the raw value is transformed before threshold
            comparison — ``'level'``, ``'yoy_pct'``, ``'mom_pct'``,
            ``'spread'``, ``'percentile_3y'``, ``'z_score'``,
            ``'vs_200d_ma'``, or ``'4wk_ma'``.
        units: Measurement units — ``'percent'``, ``'basis_points'``,
            ``'index'``, ``'thousands'``, ``'millions'``,
            ``'billions_usd'``, ``'ratio'``, or ``'level'``.
        inverted: If ``True``, higher raw values indicate more
            contractionary / risk-off / tighter conditions.  Critical
            for composite construction — a wrong sign inverts reality.
        seasonally_adjusted: ``True`` if the series is seasonally adjusted.
            NSA series are flagged for the transform layer.
        revision_prone: ``True`` if this series gets materially revised
            (e.g. GDP, payrolls, IP).  Flags need for ALFRED vintages.
        history_start: Earliest reliable data in ``'YYYY-MM'`` format.
            Determines backtest coverage.
        publication_lag_days: Typical delay from reference period to
            release.  0 for real-time market data.
        threshold_entry: The value that triggers a regime signal (from
            Phase 0 threshold config).  ``None`` if not a direct
            threshold indicator.
        threshold_exit: Hysteresis exit value.  ``None`` if same as
            entry or not applicable.
        notes: Anything the regime engine or dashboard developer needs
            to know — quirks, construction details, caveats.
    """

    series_id: str
    name: str
    description: str
    source: str
    source_detail: str
    frequency: str
    tier: int
    regime_dimension: str
    sub_state_role: str
    transform: str
    units: str
    inverted: bool = False
    seasonally_adjusted: bool = True
    revision_prone: bool = False
    history_start: str = ""
    publication_lag_days: int = 0
    threshold_entry: float | None = None
    threshold_exit: float | None = None
    notes: str = ""


# ===================================================================
# INDICATOR_REGISTRY — Complete data catalogue
# ===================================================================
#
# Maps series_id -> IndicatorMeta for every series the system consumes.
# Tier 1 = 15, Tier 2 = 40, Tier 3 = 10.  Total = 65.
# ===================================================================

INDICATOR_REGISTRY: dict[str, IndicatorMeta] = {

    # ===============================================================
    # TIER 1 — Core Regime Indicators (15 series)
    # ===============================================================

    "T10Y3M": IndicatorMeta(
        series_id="T10Y3M",
        name="3M-10Y Spread",
        description="Treasury yield curve spread; best single recession predictor per NY Fed research",
        source="fred",
        source_detail="FRED series T10Y3M; 10-Year Treasury Constant Maturity Minus 3-Month Treasury Constant Maturity",
        frequency="daily",
        tier=1,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1982-01",
        publication_lag_days=0,
        threshold_entry=0.0,
        threshold_exit=0.1,
        notes="Signal fires when spread goes negative for 3+ months then re-steepens. Inverted: negative = recession signal.",
    ),
    "T10Y2Y": IndicatorMeta(
        series_id="T10Y2Y",
        name="2s10s Spread",
        description="Treasury 2Y-10Y yield curve spread; captures curve dynamics T10Y3M misses",
        source="fred",
        source_detail="FRED series T10Y2Y; 10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity",
        frequency="daily",
        tier=1,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1976-06",
        publication_lag_days=0,
        notes="More market-traded than T10Y3M. Inverted: negative = recession signal.",
    ),
    "BAMLH0A0HYM2": IndicatorMeta(
        series_id="BAMLH0A0HYM2",
        name="HY OAS",
        description="ICE BofA High Yield Option-Adjusted Spread; most responsive real-time credit risk indicator",
        source="fred",
        source_detail="FRED series BAMLH0A0HYM2; ICE BofA US High Yield Index Option-Adjusted Spread",
        frequency="daily",
        tier=1,
        regime_dimension="multi",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1996-12",
        publication_lag_days=0,
        threshold_entry=500.0,
        threshold_exit=400.0,
        notes="Maps to both growth and liquidity dimensions. Wider spread = tighter/riskier conditions.",
    ),
    "NFCI": IndicatorMeta(
        series_id="NFCI",
        name="Chicago Fed NFCI",
        description="105-variable financial conditions composite; primary liquidity regime indicator",
        source="fred",
        source_detail="FRED series NFCI; Chicago Fed National Financial Conditions Index",
        frequency="weekly",
        tier=1,
        regime_dimension="liquidity",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1971-01",
        publication_lag_days=3,
        threshold_entry=0.0,
        threshold_exit=-0.2,
        notes="Released Wednesday for prior week. Positive = tight. Also used in growth vote counting. Entry: >0.0 for 4+ weeks. Exit: <-0.2.",
    ),
    "SAHMREALTIME": IndicatorMeta(
        series_id="SAHMREALTIME",
        name="Sahm Rule Indicator",
        description="Real-time recession indicator; triggered every recession since 1970",
        source="fred",
        source_detail="FRED series SAHMREALTIME; Real-time Sahm Rule Recession Indicator",
        frequency="monthly",
        tier=1,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="1959-01",
        publication_lag_days=5,
        threshold_entry=0.5,
        threshold_exit=0.3,
        notes="Entry: >=0.50. Exit: <0.30. Based on 3-month MA of unemployment rate vs trailing 12-month low.",
    ),
    "ICSA": IndicatorMeta(
        series_id="ICSA",
        name="Initial Jobless Claims",
        description="Weekly initial unemployment claims; high-frequency labor market deterioration signal",
        source="fred",
        source_detail="FRED series ICSA; Initial Claims, Seasonally Adjusted",
        frequency="weekly",
        tier=1,
        regime_dimension="growth",
        sub_state_role="none",
        transform="4wk_ma",
        units="thousands",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="1967-01",
        publication_lag_days=5,
        threshold_entry=10.0,
        threshold_exit=5.0,
        notes="Thursday release for prior week. Thresholds are pct-above-trough: 4-wk MA >10% above 6-month low. Exit: <5% above.",
    ),
    "PCEPILFE": IndicatorMeta(
        series_id="PCEPILFE",
        name="Core PCE YoY",
        description="Fed target inflation measure; core Personal Consumption Expenditures price index",
        source="fred",
        source_detail="FRED series PCEPILFE with units=pc1 for YoY; PCE Excluding Food and Energy (Chain-Type Price Index)",
        frequency="monthly",
        tier=1,
        regime_dimension="inflation",
        sub_state_role="none",
        transform="yoy_pct",
        units="percent",
        inverted=False,
        seasonally_adjusted=True,
        revision_prone=True,
        history_start="1959-02",
        publication_lag_days=30,
        notes="Higher = more inflationary (regime state, not directional signal). Modest revisions. Fetch with units=pc1.",
    ),
    "T5YIFR": IndicatorMeta(
        series_id="T5YIFR",
        name="5Y5Y Forward Inflation",
        description="Market long-run inflation expectation; anchoring/unanchoring detection",
        source="fred",
        source_detail="FRED series T5YIFR; 5-Year, 5-Year Forward Inflation Expectation Rate",
        frequency="daily",
        tier=1,
        regime_dimension="inflation",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2003-01",
        publication_lag_days=0,
        notes="TIPS market did not exist before 2003. Backtest must handle absence in pre-2003 periods. Inflationary threshold: >2.5%.",
    ),
    "PERMIT": IndicatorMeta(
        series_id="PERMIT",
        name="Building Permits",
        description="New privately-owned housing units authorized; 12-18 month recession lead indicator",
        source="fred",
        source_detail="FRED series PERMIT; New Privately-Owned Housing Units Authorized in Permit-Issuing Places: Total Units",
        frequency="monthly",
        tier=1,
        regime_dimension="growth",
        sub_state_role="none",
        transform="yoy_pct",
        units="thousands",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=True,
        history_start="1960-01",
        publication_lag_days=18,
        threshold_entry=-20.0,
        threshold_exit=-10.0,
        notes="Signal: YoY < -20%. Exit: YoY > -10%. Declining permits = contractionary.",
    ),
    "GACDFSA066MSFRBPHI": IndicatorMeta(
        series_id="GACDFSA066MSFRBPHI",
        name="Philly Fed Mfg Index",
        description="Philadelphia Fed Manufacturing Business Outlook Survey; best free ISM proxy",
        source="fred",
        source_detail="FRED series GACDFSA066MSFRBPHI; Diffusion Index for Current General Activity: Manufacturing",
        frequency="monthly",
        tier=1,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="1968-05",
        publication_lag_days=15,
        notes="Strongest ISM correlation of all regional Fed surveys. Below 0 = contraction.",
    ),
    "CFNAIMA3": IndicatorMeta(
        series_id="CFNAIMA3",
        name="CFNAI 3-Month MA",
        description="Chicago Fed National Activity Index 3-month moving average; 85-indicator composite",
        source="fred",
        source_detail="FRED series CFNAIMA3; Chicago Fed National Activity Index: Three Month Moving Average",
        frequency="monthly",
        tier=1,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="1967-04",
        publication_lag_days=30,
        threshold_entry=-0.7,
        threshold_exit=-0.3,
        notes="Contraction threshold: < -0.70. Exit: > -0.30. Negative = below trend growth.",
    ),
    "DFF": IndicatorMeta(
        series_id="DFF",
        name="Fed Funds Rate",
        description="Daily effective federal funds rate; monetary policy stance anchor",
        source="fred",
        source_detail="FRED series DFF; Federal Funds Effective Rate",
        frequency="daily",
        tier=1,
        regime_dimension="liquidity",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1954-07",
        publication_lag_days=0,
        notes="Directional, not good/bad. Policy stance anchor for the liquidity dimension.",
    ),
    "M2SL": IndicatorMeta(
        series_id="M2SL",
        name="M2 Money Supply YoY",
        description="Broad money supply growth; monetary impulse indicator for liquidity and inflation",
        source="fred",
        source_detail="FRED series M2SL with units=pc1 for YoY; M2 Money Stock",
        frequency="monthly",
        tier=1,
        regime_dimension="multi",
        sub_state_role="none",
        transform="yoy_pct",
        units="billions_usd",
        inverted=False,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="1959-01",
        publication_lag_days=10,
        notes="Maps to both liquidity and inflation dimensions. Fetch with units=pc1.",
    ),
    "VIXCLS": IndicatorMeta(
        series_id="VIXCLS",
        name="VIX",
        description="CBOE Volatility Index; primary equity market fear gauge",
        source="fred",
        source_detail="FRED series VIXCLS; CBOE Volatility Index: VIX",
        frequency="daily",
        tier=1,
        regime_dimension="risk",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1990-01",
        publication_lag_days=0,
        notes="Risk-on: <20. Risk-off: >25. Crisis: >35. Higher VIX = more fear = risk-off.",
    ),
    "SP500": IndicatorMeta(
        series_id="SP500",
        name="S&P 500",
        description="S&P 500 index level; percent distance from 200-day MA for risk appetite",
        source="fred",
        source_detail="FRED series SP500. Also available via yfinance ^GSPC for intraday or total return.",
        frequency="daily",
        tier=1,
        regime_dimension="risk",
        sub_state_role="none",
        transform="vs_200d_ma",
        units="index",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1957-01",
        publication_lag_days=0,
        notes="Above 200d MA = risk-on. Used in risk appetite composite as pct distance from 200-day MA.",
    ),

    # ===============================================================
    # TIER 2 — Confirmation & Sub-State Detection (40 series)
    # ===============================================================

    # --- Yield Curve & Rates (3 series) ---

    "DFII10": IndicatorMeta(
        series_id="DFII10",
        name="10Y Real Yield (TIPS)",
        description="10-year TIPS yield; real rate proxy for financial conditions",
        source="fred",
        source_detail="FRED series DFII10; Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Inflation-Indexed",
        frequency="daily",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2003-01",
        publication_lag_days=0,
        notes="Higher real yield = tighter real financial conditions.",
    ),
    "T5YIE": IndicatorMeta(
        series_id="T5YIE",
        name="5Y Breakeven Inflation",
        description="5-year breakeven inflation rate; near-term market inflation expectations",
        source="fred",
        source_detail="FRED series T5YIE; 5-Year Breakeven Inflation Rate",
        frequency="daily",
        tier=2,
        regime_dimension="inflation",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2003-01",
        publication_lag_days=0,
        notes="Near-term inflation expectations derived from TIPS market.",
    ),
    "T10YIE": IndicatorMeta(
        series_id="T10YIE",
        name="10Y Breakeven Inflation",
        description="10-year breakeven inflation rate; longer-term market inflation expectations",
        source="fred",
        source_detail="FRED series T10YIE; 10-Year Breakeven Inflation Rate",
        frequency="daily",
        tier=2,
        regime_dimension="inflation",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2003-01",
        publication_lag_days=0,
        notes="Longer-term inflation expectations derived from TIPS market.",
    ),

    # --- Credit & Financial Conditions (4 series) ---

    "BAMLC0A0CM": IndicatorMeta(
        series_id="BAMLC0A0CM",
        name="IG OAS",
        description="ICE BofA Investment Grade corporate OAS; less volatile than HY, catches slow-build stress",
        source="fred",
        source_detail="FRED series BAMLC0A0CM; ICE BofA US Corporate Index Option-Adjusted Spread",
        frequency="daily",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1996-12",
        publication_lag_days=0,
        notes="Investment grade credit spread. Less volatile than HY OAS.",
    ),
    "BAA10Y": IndicatorMeta(
        series_id="BAA10Y",
        name="Moody's BAA-10Y Spread",
        description="Moody BAA corporate bond yield minus 10Y Treasury; classic credit risk spread",
        source="fred",
        source_detail="FRED series BAA10Y; Moody Seasoned Baa Corporate Bond Yield Relative to Yield on 10-Year Treasury",
        frequency="daily",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1986-01",
        publication_lag_days=0,
        notes="Longer history than ICE BofA indices. Classic credit risk spread.",
    ),
    "STLFSI4": IndicatorMeta(
        series_id="STLFSI4",
        name="St. Louis Fed Financial Stress",
        description="St. Louis Fed Financial Stress Index; broad financial stress composite",
        source="fred",
        source_detail="FRED series STLFSI4; St. Louis Fed Financial Stress Index",
        frequency="weekly",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1993-12",
        publication_lag_days=5,
        notes="Crisis threshold: >5.0. Tight: >1.0. Positive = financial stress.",
    ),
    "DRTSCILM": IndicatorMeta(
        series_id="DRTSCILM",
        name="SLOOS C&I Lending (Large Firms)",
        description="Senior Loan Officer Survey net tightening on C&I loans; credit supply signal",
        source="fred",
        source_detail="FRED series DRTSCILM; Net Pct of Domestic Banks Tightening Standards for C&I Loans to Large Firms",
        frequency="quarterly",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1990-01",
        publication_lag_days=60,
        notes=">20% net tightening = Tight signal. Quarterly — forward-fill between releases.",
    ),

    # --- Funding Plumbing / Fragile Sub-State (4 series) ---

    "RRPONTSYD": IndicatorMeta(
        series_id="RRPONTSYD",
        name="ON RRP Balance",
        description="Overnight Reverse Repo facility balance; liquidity buffer depletion indicator for Fragile",
        source="fred",
        source_detail="FRED series RRPONTSYD; Overnight Reverse Repurchase Agreements: Treasury Securities Sold by the Federal Reserve",
        frequency="daily",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="fragile",
        transform="level",
        units="billions_usd",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2013-03",
        publication_lag_days=1,
        threshold_entry=50.0,
        threshold_exit=100.0,
        notes="Fragile threshold: <$50B. Exit: >$100B. Lower = less liquidity buffer. Limited backtest depth.",
    ),
    "SOFR": IndicatorMeta(
        series_id="SOFR",
        name="Secured Overnight Financing Rate",
        description="Secured overnight funding rate; component of SOFR-IORB spread for Fragile detection",
        source="fred",
        source_detail="FRED series SOFR; Secured Overnight Financing Rate",
        frequency="daily",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="fragile",
        transform="level",
        units="percent",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2018-04",
        publication_lag_days=1,
        notes="Component of SOFR-IORB spread. Use DFF as proxy before 2018.",
    ),
    "IORB": IndicatorMeta(
        series_id="IORB",
        name="Interest on Reserve Balances",
        description="Interest rate paid on reserve balances; component of SOFR-IORB spread for Fragile",
        source="fred",
        source_detail="FRED series IORB; Interest Rate on Reserve Balances. Extend backward using IOER from 2008.",
        frequency="daily",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="fragile",
        transform="level",
        units="percent",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2021-07",
        publication_lag_days=0,
        notes="Replaced IOER in July 2021. Extend backward using IOER series from 2008-2021.",
    ),
    "WALCL": IndicatorMeta(
        series_id="WALCL",
        name="Fed Balance Sheet Total Assets",
        description="Federal Reserve total assets (H.4.1); YoY change signals QT/QE for Fragile sub-state",
        source="fred",
        source_detail="FRED series WALCL; Assets: Total Assets (Less Eliminations from Consolidation): Wednesday Level",
        frequency="weekly",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="fragile",
        transform="yoy_pct",
        units="millions",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2002-12",
        publication_lag_days=3,
        threshold_entry=0.0,
        threshold_exit=0.0,
        notes="H.4.1 release Thursday. Fragile condition: YoY < 0% (QT ongoing).",
    ),

    # --- Constructed: SOFR-IORB Spread (1 series) ---

    "SOFR_IORB_SPREAD": IndicatorMeta(
        series_id="SOFR_IORB_SPREAD",
        name="SOFR minus IORB Spread",
        description="SOFR minus IORB spread; single most important plumbing indicator — would have caught Sept 2019",
        source="constructed",
        source_detail="SOFR - IORB (or SOFR - IOER before 2021-07). Use DFF - IOER as proxy before 2018-04.",
        frequency="daily",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="fragile",
        transform="level",
        units="basis_points",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2018-04",
        publication_lag_days=1,
        threshold_entry=0.0,
        threshold_exit=0.0,
        notes="Fragile threshold: >0bp persistent for 5+ days. Exit: <=0bp for 10+ days. Positive = funding stress.",
    ),

    # --- Labor (5 series) ---

    "UNRATE": IndicatorMeta(
        series_id="UNRATE",
        name="Unemployment Rate",
        description="Civilian unemployment rate; lagging indicator that feeds Sahm Rule construction",
        source="fred",
        source_detail="FRED series UNRATE; Unemployment Rate",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=True,
        history_start="1948-01",
        publication_lag_days=5,
        notes="Lagging indicator. Modest revisions. Feeds Sahm Rule construction.",
    ),
    "PAYEMS": IndicatorMeta(
        series_id="PAYEMS",
        name="Nonfarm Payrolls",
        description="Total nonfarm employment; first-Friday release with significant revisions",
        source="fred",
        source_detail="FRED series PAYEMS; All Employees, Total Nonfarm",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="mom_pct",
        units="thousands",
        inverted=False,
        seasonally_adjusted=True,
        revision_prone=True,
        history_start="1939-01",
        publication_lag_days=5,
        notes="First Friday release. ALFRED vintages critical — revisions of 50K+ common. Growth = expansionary.",
    ),
    "AWHMAN": IndicatorMeta(
        series_id="AWHMAN",
        name="Avg Weekly Mfg Hours",
        description="Average weekly hours in manufacturing; one of the oldest leading indicators",
        source="fred",
        source_detail="FRED series AWHMAN; Average Weekly Hours of Production and Nonsupervisory Employees, Manufacturing",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="level",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=True,
        history_start="1939-01",
        publication_lag_days=5,
        notes="Below 40 hrs is a warning. Declining hours = leading recession signal.",
    ),
    "CCSA": IndicatorMeta(
        series_id="CCSA",
        name="Continuing Claims",
        description="Continuing jobless claims; captures duration of unemployment spells",
        source="fred",
        source_detail="FRED series CCSA; Continued Claims (Insured Unemployment)",
        frequency="weekly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="thousands",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="1967-01",
        publication_lag_days=12,
        notes="Lagged vs initial claims but captures unemployment duration. Higher = weaker labor market.",
    ),
    "JTSQUR": IndicatorMeta(
        series_id="JTSQUR",
        name="Quits Rate (JOLTS)",
        description="JOLTS quits rate; declining quits = weakening labor confidence",
        source="fred",
        source_detail="FRED series JTSQUR; Quits: Total Nonfarm, Rate",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=False,
        seasonally_adjusted=True,
        revision_prone=True,
        history_start="2000-12",
        publication_lag_days=40,
        notes="JOLTS release has long lag. Higher quits rate = confident labor market.",
    ),

    # --- Housing (3 series) ---

    "HOUST": IndicatorMeta(
        series_id="HOUST",
        name="Housing Starts",
        description="New privately-owned housing units started; coincident/short-lead housing indicator",
        source="fred",
        source_detail="FRED series HOUST; Housing Starts: Total: New Privately Owned Housing Units Started",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="yoy_pct",
        units="thousands",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=True,
        history_start="1959-01",
        publication_lag_days=18,
        notes="Declining = contractionary. Coincident/short-lead housing indicator.",
    ),
    "MORTGAGE30US": IndicatorMeta(
        series_id="MORTGAGE30US",
        name="30Y Mortgage Rate",
        description="Freddie Mac 30-year fixed mortgage rate; Fed policy to housing transmission mechanism",
        source="fred",
        source_detail="FRED series MORTGAGE30US; 30-Year Fixed Rate Mortgage Average in the United States",
        frequency="weekly",
        tier=2,
        regime_dimension="liquidity",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1971-04",
        publication_lag_days=3,
        notes="Freddie Mac survey. Higher = tighter housing credit conditions.",
    ),
    "HSN1F": IndicatorMeta(
        series_id="HSN1F",
        name="New Home Sales",
        description="New single-family home sales; volatile housing demand indicator",
        source="fred",
        source_detail="FRED series HSN1F; New One Family Houses Sold: United States",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="yoy_pct",
        units="thousands",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=True,
        history_start="1963-01",
        publication_lag_days=30,
        notes="Volatile, heavily revised. Declining = contractionary. Use with caution.",
    ),

    # --- Production (2 series) ---

    "INDPRO": IndicatorMeta(
        series_id="INDPRO",
        name="Industrial Production",
        description="Industrial production index; core coincident indicator used in Harding-Pagan cycle dating",
        source="fred",
        source_detail="FRED series INDPRO; Industrial Production: Total Index",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="yoy_pct",
        units="index",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=True,
        history_start="1919-01",
        publication_lag_days=15,
        notes="Declining YoY = contraction signal. Used in Harding-Pagan cycle dating.",
    ),
    "TCU": IndicatorMeta(
        series_id="TCU",
        name="Capacity Utilisation",
        description="Total industry capacity utilization rate; peak/late-cycle signal when elevated",
        source="fred",
        source_detail="FRED series TCU; Capacity Utilization: Total Industry",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=False,
        seasonally_adjusted=True,
        revision_prone=True,
        history_start="1967-01",
        publication_lag_days=15,
        notes="Peak/Late cycle signal: >82%. High utilization signals late-cycle pressure.",
    ),

    # --- Sentiment (2 series) ---

    "UMCSENT": IndicatorMeta(
        series_id="UMCSENT",
        name="Michigan Consumer Sentiment",
        description="University of Michigan consumer sentiment index; consumer confidence proxy",
        source="fred",
        source_detail="FRED series UMCSENT; University of Michigan: Consumer Sentiment",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1978-01",
        publication_lag_days=1,
        notes="Preliminary mid-month, final end-month. Lower = weaker consumer confidence.",
    ),
    "MICH": IndicatorMeta(
        series_id="MICH",
        name="Michigan Inflation Expectations 1Y",
        description="Michigan survey 1-year ahead inflation expectations; expectations unanchoring detection",
        source="fred",
        source_detail="FRED series MICH; University of Michigan: Inflation Expectation",
        frequency="monthly",
        tier=2,
        regime_dimension="inflation",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1978-01",
        publication_lag_days=1,
        notes="Inflationary threshold: >4.0%. Higher = more inflationary. Used in inflation range voting.",
    ),

    # --- Freight (2 series) ---

    "FRGSHPUSM649NCIS": IndicatorMeta(
        series_id="FRGSHPUSM649NCIS",
        name="Cass Freight Shipments",
        description="Cass Freight Shipments Index; goods-side economic activity proxy",
        source="fred",
        source_detail="FRED series FRGSHPUSM649NCIS; Cass Freight Index: Shipments",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1990-01",
        publication_lag_days=20,
        notes="Signal: declining 3+ consecutive months. Exit: rising 2+ months. Engine uses derived freight_decline_months.",
    ),
    "HTRUCKSSAAR": IndicatorMeta(
        series_id="HTRUCKSSAAR",
        name="Heavy Truck Sales (SAAR)",
        description="Heavy truck sales seasonally adjusted annual rate; capex proxy and goods-side recession lead",
        source="fred",
        source_detail="FRED series HTRUCKSSAAR; Motor Vehicle Retail Sales: Heavy Weight Trucks",
        frequency="monthly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="thousands",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="1967-01",
        publication_lag_days=30,
        notes="Capex proxy. Leading indicator of goods-side recession.",
    ),

    # --- FX & Commodities (4 series) ---

    "DTWEXBGS": IndicatorMeta(
        series_id="DTWEXBGS",
        name="Broad Trade-Weighted Dollar",
        description="Broad trade-weighted US dollar index; stronger dollar signals risk-off conditions",
        source="fred",
        source_detail="FRED series DTWEXBGS; Nominal Broad U.S. Dollar Index",
        frequency="daily",
        tier=2,
        regime_dimension="risk",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2006-01",
        publication_lag_days=1,
        notes="Used in risk appetite composite (inverted). Stronger dollar = risk-off.",
    ),
    "DCOILWTICO": IndicatorMeta(
        series_id="DCOILWTICO",
        name="WTI Crude Oil",
        description="West Texas Intermediate crude oil spot price; commodity/inflation proxy",
        source="fred",
        source_detail="FRED series DCOILWTICO; Crude Oil Prices: West Texas Intermediate (WTI) - Cushing, Oklahoma",
        frequency="daily",
        tier=2,
        regime_dimension="inflation",
        sub_state_role="none",
        transform="level",
        units="level",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1986-01",
        publication_lag_days=0,
        notes="Commodity/inflation proxy. Rising oil prices contribute to inflationary pressure.",
    ),
    "GOLDAMGBD228NLBM": IndicatorMeta(
        series_id="GOLDAMGBD228NLBM",
        name="Gold (London Fix USD)",
        description="Gold price London PM fix in USD; safe haven demand proxy",
        source="fred",
        source_detail="FRED series GOLDAMGBD228NLBM; Gold Fixing Price 10:30 A.M. (London time) in London Bullion Market",
        frequency="daily",
        tier=2,
        regime_dimension="risk",
        sub_state_role="none",
        transform="level",
        units="level",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1968-04",
        publication_lag_days=0,
        notes="Safe haven demand proxy. Rising gold = risk-off haven bid, but not inverted — use contextually.",
    ),
    "HG_F": IndicatorMeta(
        series_id="HG_F",
        name="Copper Futures",
        description="Copper futures price; Dr. Copper growth/demand signal",
        source="yfinance",
        source_detail="HG=F",
        frequency="daily",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="mom_pct",
        units="level",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1988-01",
        publication_lag_days=0,
        notes="Dr. Copper. 3-month momentum used in risk composite. Declining copper = growth concern.",
    ),

    # --- Speculator Positioning / COT (8 series) ---

    "COT_ES": IndicatorMeta(
        series_id="COT_ES",
        name="COT Managed Money Net — E-Mini S&P 500",
        description="CFTC managed money net positioning in E-Mini S&P 500 futures; equity risk appetite",
        source="cftc",
        source_detail="E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE; Asset_Mgr_Positions_Long_All minus Asset_Mgr_Positions_Short_All",
        frequency="weekly",
        tier=2,
        regime_dimension="risk",
        sub_state_role="crowded_capitulation",
        transform="percentile_3y",
        units="ratio",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1986-01",
        publication_lag_days=3,
        notes="Percentile rank vs trailing 156 weeks. Higher net long = more crowded risk-on.",
    ),
    "COT_TY": IndicatorMeta(
        series_id="COT_TY",
        name="COT Managed Money Net — 10Y T-Note",
        description="CFTC managed money net positioning in 10Y Treasury futures; rates positioning",
        source="cftc",
        source_detail="10-YEAR U.S. TREASURY NOTES - CHICAGO BOARD OF TRADE; Asset_Mgr_Positions_Long_All minus Asset_Mgr_Positions_Short_All",
        frequency="weekly",
        tier=2,
        regime_dimension="risk",
        sub_state_role="crowded_capitulation",
        transform="percentile_3y",
        units="ratio",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1986-01",
        publication_lag_days=3,
        notes="Invert for composite: higher net SHORT = more crowded risk-on positioning.",
    ),
    "COT_TU": IndicatorMeta(
        series_id="COT_TU",
        name="COT Managed Money Net — 2Y T-Note",
        description="CFTC managed money net positioning in 2Y Treasury futures; front-end rate expectations",
        source="cftc",
        source_detail="2-YEAR U.S. TREASURY NOTES - CHICAGO BOARD OF TRADE; Asset_Mgr_Positions_Long_All minus Asset_Mgr_Positions_Short_All",
        frequency="weekly",
        tier=2,
        regime_dimension="risk",
        sub_state_role="crowded_capitulation",
        transform="percentile_3y",
        units="ratio",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1990-01",
        publication_lag_days=3,
        notes="Front-end rate expectations positioning. Invert for composite.",
    ),
    "COT_GC": IndicatorMeta(
        series_id="COT_GC",
        name="COT Managed Money Net — Gold",
        description="CFTC managed money net positioning in gold futures; safe-haven positioning",
        source="cftc",
        source_detail="GOLD - COMMODITY EXCHANGE INC.; Asset_Mgr_Positions_Long_All minus Asset_Mgr_Positions_Short_All",
        frequency="weekly",
        tier=2,
        regime_dimension="risk",
        sub_state_role="crowded_capitulation",
        transform="percentile_3y",
        units="ratio",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1986-01",
        publication_lag_days=3,
        notes="Invert for composite: net short gold = risk-on positioning.",
    ),
    "COT_CL": IndicatorMeta(
        series_id="COT_CL",
        name="COT Managed Money Net — Crude Oil",
        description="CFTC managed money net positioning in crude oil futures; growth/inflation expectations",
        source="cftc",
        source_detail="CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE; Asset_Mgr_Positions_Long_All minus Asset_Mgr_Positions_Short_All",
        frequency="weekly",
        tier=2,
        regime_dimension="inflation",
        sub_state_role="none",
        transform="percentile_3y",
        units="ratio",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1986-01",
        publication_lag_days=3,
        notes="Not in risk composite — standalone inflation signal.",
    ),
    "COT_DX": IndicatorMeta(
        series_id="COT_DX",
        name="COT Managed Money Net — Dollar Index",
        description="CFTC managed money net positioning in US Dollar Index futures; dollar positioning",
        source="cftc",
        source_detail="U.S. DOLLAR INDEX - ICE FUTURES U.S.; Asset_Mgr_Positions_Long_All minus Asset_Mgr_Positions_Short_All",
        frequency="weekly",
        tier=2,
        regime_dimension="risk",
        sub_state_role="crowded_capitulation",
        transform="percentile_3y",
        units="ratio",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1986-01",
        publication_lag_days=3,
        notes="Net long dollar = risk-off-ish, but use contextually in composite.",
    ),
    "COT_VX": IndicatorMeta(
        series_id="COT_VX",
        name="COT Managed Money Net — VIX Futures",
        description="CFTC managed money net positioning in VIX futures; sentiment about sentiment",
        source="cftc",
        source_detail="CBOE VOLATILITY INDEX (VX) - CBOE FUTURES EXCHANGE; Asset_Mgr_Positions_Long_All minus Asset_Mgr_Positions_Short_All",
        frequency="weekly",
        tier=2,
        regime_dimension="risk",
        sub_state_role="crowded_capitulation",
        transform="percentile_3y",
        units="ratio",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2004-03",
        publication_lag_days=3,
        notes="Shorter history. Net short VIX = risk-on complacency. Invert for composite.",
    ),
    "COT_HG": IndicatorMeta(
        series_id="COT_HG",
        name="COT Managed Money Net — Copper",
        description="CFTC managed money net positioning in copper futures; Dr. Copper positioning",
        source="cftc",
        source_detail="COPPER- #1 - COMMODITY EXCHANGE INC.; Asset_Mgr_Positions_Long_All minus Asset_Mgr_Positions_Short_All",
        frequency="weekly",
        tier=2,
        regime_dimension="growth",
        sub_state_role="none",
        transform="percentile_3y",
        units="ratio",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1986-01",
        publication_lag_days=3,
        notes="Dr. Copper positioning. Not in core risk composite — standalone growth signal.",
    ),

    # --- Constructed Composites (2 series) ---

    "COT_RISK_COMPOSITE": IndicatorMeta(
        series_id="COT_RISK_COMPOSITE",
        name="COT Positioning Risk Composite",
        description="Mean of percentile-ranked COT positioning across key contracts; crowded/capitulation detector",
        source="constructed",
        source_detail="Mean of percentile-ranked: COT_ES, -COT_TY, -COT_GC, -COT_VX, COT_DX. Range 0-100.",
        frequency="weekly",
        tier=2,
        regime_dimension="risk",
        sub_state_role="crowded_capitulation",
        transform="percentile_3y",
        units="index",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2004-03",
        publication_lag_days=3,
        notes=">80 = Crowded. <20 = Capitulation. History limited by COT_VX start date.",
    ),
    "RISK_APPETITE_INDEX": IndicatorMeta(
        series_id="RISK_APPETITE_INDEX",
        name="Risk Appetite Composite",
        description="Normalised multi-asset risk appetite index; primary input to risk regime classification",
        source="constructed",
        source_detail="Normalised average of: VIXCLS (inverted), BAMLH0A0HYM2 (inverted), SP500 vs 200d MA, DTWEXBGS (inverted), HG_F 3mo momentum. Percentile-ranked.",
        frequency="daily",
        tier=2,
        regime_dimension="risk",
        sub_state_role="none",
        transform="percentile_3y",
        units="index",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2006-01",
        publication_lag_days=1,
        notes=">70th = Risk-on. <30th = Risk-off. History limited by DTWEXBGS start date.",
    ),

    # ===============================================================
    # TIER 3 — Supplementary Watchlist (10 series)
    # ===============================================================

    "GACDISA066MSFRBNY": IndicatorMeta(
        series_id="GACDISA066MSFRBNY",
        name="Empire State Mfg Index",
        description="NY Fed Empire State Manufacturing Survey; regional Fed PMI composite input",
        source="fred",
        source_detail="FRED series GACDISA066MSFRBNY; Empire State Manufacturing Survey: General Business Conditions",
        frequency="monthly",
        tier=3,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="2001-07",
        publication_lag_days=15,
        notes="Regional Fed. PMI composite input (weight: 0.25).",
    ),
    "GACDFSA066MSFRBRIC": IndicatorMeta(
        series_id="GACDFSA066MSFRBRIC",
        name="Richmond Fed Mfg Index",
        description="Richmond Fed Manufacturing Survey; regional Fed PMI composite input",
        source="fred",
        source_detail="FRED series GACDFSA066MSFRBRIC; Fifth District Survey of Manufacturing Activity",
        frequency="monthly",
        tier=3,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="1993-11",
        publication_lag_days=15,
        notes="PMI composite input (weight: 0.20).",
    ),
    "GACDISA066MSFRBDAL": IndicatorMeta(
        series_id="GACDISA066MSFRBDAL",
        name="Dallas Fed Mfg Index",
        description="Dallas Fed Manufacturing Survey; regional Fed PMI composite input",
        source="fred",
        source_detail="FRED series GACDISA066MSFRBDAL; Dallas Fed Manufacturing Outlook Survey",
        frequency="monthly",
        tier=3,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="2004-06",
        publication_lag_days=15,
        notes="PMI composite input (weight: 0.08).",
    ),
    "GACDISA066MSFRBKC": IndicatorMeta(
        series_id="GACDISA066MSFRBKC",
        name="KC Fed Mfg Index",
        description="Kansas City Fed Manufacturing Survey; regional Fed PMI composite input",
        source="fred",
        source_detail="FRED series GACDISA066MSFRBKC; Kansas City Fed Manufacturing Survey: Composite Index",
        frequency="monthly",
        tier=3,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="2001-01",
        publication_lag_days=15,
        notes="PMI composite input (weight: 0.12).",
    ),
    "USALOLITONOSTSAM": IndicatorMeta(
        series_id="USALOLITONOSTSAM",
        name="OECD CLI",
        description="OECD Composite Leading Indicator for the US; cross-check for domestic indicators",
        source="fred",
        source_detail="FRED series USALOLITONOSTSAM; Leading Indicators OECD: CLI: Normalised for the United States",
        frequency="monthly",
        tier=3,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=False,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="1955-01",
        publication_lag_days=60,
        notes="Good cross-check, 2-month publication lag. Below 100 = below trend.",
    ),
    "BDI": IndicatorMeta(
        series_id="BDI",
        name="Baltic Dry Index",
        description="Baltic Exchange Dry Index; global trade and shipping demand health indicator",
        source="yfinance",
        source_detail="^BDI",
        frequency="daily",
        tier=3,
        regime_dimension="growth",
        sub_state_role="none",
        transform="level",
        units="index",
        inverted=True,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="1985-01",
        publication_lag_days=0,
        notes="Global trade health. Noisy. Declining = weaker global demand.",
    ),
    "BTC_USD": IndicatorMeta(
        series_id="BTC_USD",
        name="Bitcoin Price",
        description="Bitcoin price in USD; risk proxy in the post-2017 macro landscape",
        source="coingecko",
        source_detail="coingecko API; coin_id=bitcoin, vs_currency=usd",
        frequency="daily",
        tier=3,
        regime_dimension="risk",
        sub_state_role="none",
        transform="level",
        units="level",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2010-07",
        publication_lag_days=0,
        notes="Risk proxy post-2017 only. Limited macro backtest utility before 2017.",
    ),
    "BTC_FUNDING": IndicatorMeta(
        series_id="BTC_FUNDING",
        name="BTC Perpetual Funding Rate",
        description="Bitcoin perpetual futures funding rate; crypto leverage and sentiment extremes",
        source="binance",
        source_detail="Binance API; symbol=BTCUSDT, endpoint=fundingRate",
        frequency="8-hourly",
        tier=3,
        regime_dimension="risk",
        sub_state_role="none",
        transform="level",
        units="percent",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2019-09",
        publication_lag_days=0,
        notes="Deeply negative (<-0.03%/8hr) = extreme bearish. Deeply positive (>0.05%) = bullish leverage extreme.",
    ),
    "PCTTLR": IndicatorMeta(
        series_id="PCTTLR",
        name="CBOE Equity Put/Call Ratio",
        description="CBOE total equity put/call ratio; options-specific hedging demand proxy",
        source="fred",
        source_detail="FRED series PCTTLR; CBOE Total Put/Call Ratio",
        frequency="daily",
        tier=3,
        regime_dimension="risk",
        sub_state_role="none",
        transform="level",
        units="ratio",
        inverted=False,
        seasonally_adjusted=False,
        revision_prone=False,
        history_start="2006-10",
        publication_lag_days=0,
        notes="Partially redundant with VIX. Options-specific hedging demand.",
    ),
    "CPIAUCSL": IndicatorMeta(
        series_id="CPIAUCSL",
        name="CPI All Urban YoY",
        description="Headline CPI for all urban consumers; used in PCE bridge equation, not in regime classifier",
        source="fred",
        source_detail="FRED series CPIAUCSL with units=pc1 for YoY; Consumer Price Index for All Urban Consumers",
        frequency="monthly",
        tier=3,
        regime_dimension="inflation",
        sub_state_role="none",
        transform="yoy_pct",
        units="index",
        inverted=False,
        seasonally_adjusted=True,
        revision_prone=False,
        history_start="1947-01",
        publication_lag_days=15,
        notes="Headline CPI. Used in PCE bridge equation (Phase 4B), not in regime classifier. Fetch with units=pc1.",
    ),

}



# ===================================================================
# Helper Functions
# ===================================================================


def get_by_tier(tier: int) -> list[IndicatorMeta]:
    """Return all indicators of a given tier.

    Args:
        tier: Priority tier — 1 (core), 2 (confirmation), or
            3 (supplementary).

    Returns:
        List of :class:`IndicatorMeta` entries matching the tier.
    """
    return [v for v in INDICATOR_REGISTRY.values() if v.tier == tier]


def get_by_dimension(dimension: str) -> list[IndicatorMeta]:
    """Return all indicators for a regime dimension.

    Args:
        dimension: One of ``'growth'``, ``'inflation'``,
            ``'liquidity'``, ``'risk'``, or ``'multi'``.

    Returns:
        List of :class:`IndicatorMeta` entries matching the dimension.
    """
    return [v for v in INDICATOR_REGISTRY.values()
            if v.regime_dimension == dimension]


def get_by_source(source: str) -> list[IndicatorMeta]:
    """Return all indicators from a given data source.

    Args:
        source: Data provider key — ``'fred'``, ``'cftc'``,
            ``'yfinance'``, ``'binance'``, ``'coingecko'``,
            or ``'constructed'``.

    Returns:
        List of :class:`IndicatorMeta` entries matching the source.
    """
    return [v for v in INDICATOR_REGISTRY.values() if v.source == source]


def get_by_sub_state(role: str) -> list[IndicatorMeta]:
    """Return all indicators that feed a specific sub-state.

    Supports partial matching: ``'crowded'`` and ``'capitulation'``
    both match entries with ``sub_state_role='crowded_capitulation'``,
    since the same COT positioning data feeds both overlay evaluations.

    Args:
        role: Sub-state role — ``'fragile'``, ``'crowded'``,
            ``'capitulation'``, or ``'crowded_capitulation'``.

    Returns:
        List of :class:`IndicatorMeta` entries feeding the sub-state.
    """
    return [v for v in INDICATOR_REGISTRY.values()
            if v.sub_state_role != "none" and role in v.sub_state_role]


def get_fred_ids() -> dict[str, list[str]]:
    """Return FRED series IDs grouped by frequency.

    Returns:
        Dict mapping frequency strings to sorted lists of FRED
        series IDs, e.g. ``{'daily': ['DFF', 'T10Y3M', ...],
        'weekly': ['ICSA', ...], ...}``.
    """
    groups: dict[str, list[str]] = {}
    for v in INDICATOR_REGISTRY.values():
        if v.source == "fred":
            groups.setdefault(v.frequency, []).append(v.series_id)
    for lst in groups.values():
        lst.sort()
    return groups


def get_constructed_indicators() -> list[IndicatorMeta]:
    """Return indicators with source='constructed'.

    These are computed from other series in the registry, not fetched
    from an external API.  The data pipeline must handle them
    differently — their ``source_detail`` field describes the
    construction formula.

    Returns:
        List of :class:`IndicatorMeta` entries that are constructed.
    """
    return [v for v in INDICATOR_REGISTRY.values()
            if v.source == "constructed"]


def validate_registry() -> list[str]:
    """Run integrity checks on the registry.

    Checks performed:
      1. Every ``series_id`` is unique across all entries.
      2. Every Tier 1 indicator has a ``regime_dimension`` that is not
         ``'none'``.
      3. Every indicator with ``sub_state_role != 'none'`` is Tier 2.
      4. Every ``'constructed'`` indicator has a non-empty
         ``source_detail`` explaining its formula.
      5. Every indicator has a non-empty ``history_start``.
      6. ``frequency`` values are valid.
      7. No Tier 3 indicators have ``sub_state_role`` set (they do not
         feed sub-states).

    Returns:
        List of error message strings.  Empty list means all checks
        pass.
    """
    errors: list[str] = []

    valid_frequencies = {"daily", "weekly", "monthly", "quarterly", "8-hourly"}

    # Check 1: series_id uniqueness
    seen_ids: dict[str, str] = {}
    for key, meta in INDICATOR_REGISTRY.items():
        if meta.series_id in seen_ids:
            errors.append(
                f"Duplicate series_id '{meta.series_id}': "
                f"used by '{seen_ids[meta.series_id]}' and '{key}'"
            )
        seen_ids[meta.series_id] = key

    for key, meta in INDICATOR_REGISTRY.items():
        # Check 2: Tier 1 must have a real dimension
        if meta.tier == 1 and meta.regime_dimension == "none":
            errors.append(
                f"'{key}': Tier 1 indicator has regime_dimension='none'"
            )

        # Check 3: sub_state_role != "none" implies Tier 2
        if meta.sub_state_role != "none" and meta.tier != 2:
            errors.append(
                f"'{key}': sub_state_role='{meta.sub_state_role}' "
                f"but tier={meta.tier} (expected 2)"
            )

        # Check 4: constructed indicators must have source_detail
        if meta.source == "constructed" and not meta.source_detail:
            errors.append(
                f"'{key}': constructed indicator missing source_detail"
            )

        # Check 5: every indicator needs history_start
        if not meta.history_start:
            errors.append(f"'{key}': missing history_start")

        # Check 6: valid frequency
        if meta.frequency not in valid_frequencies:
            errors.append(
                f"'{key}': invalid frequency '{meta.frequency}'"
            )

        # Check 7: Tier 3 must not have sub_state_role
        if meta.tier == 3 and meta.sub_state_role != "none":
            errors.append(
                f"'{key}': Tier 3 indicator has "
                f"sub_state_role='{meta.sub_state_role}'"
            )

    return errors
