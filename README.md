# EVA Tail Risk Strategy — SimicX Internship Project

Applying **Extreme Value Analysis (EVA)** from Köhler, Heckens & Guhr (2026) to a 10-asset crypto portfolio. The strategy uses PCA decomposition and Generalized Pareto Distribution (GPD) fitting to dynamically manage tail risk.

---

## Deliverables

| # | File / Folder | Description |
|---|---|---|
| 1 | `EVA_Pitch_Deck.pptx` | Pitch deck for non-quant investors (9 slides) |
| 2 | `strategy.py` · `compare_strategies.py` · `plot_defensive.py` | Source code |
| 3 | `output.html` | Backtest & validation report |

Supporting pages: `glossary.html` (terminology), `teaching.html` (strategy walkthrough)

---

## Strategy Overview

**Ensemble = 50% EVA Optimized + 50% EVT Hybrid v3**

| Sub-Strategy | signal_direction | Logic |
|---|---|---|
| EVA Optimized | +1 | Long safest 4, short most dangerous 4 (Defensive) |
| EVT Hybrid v3 | −1 | Long highest positive tail-risk exposure (Momentum) |

### Key Parameters
- `L = 504` (2-year rolling window)
- `K = 7` PCA modes (≥ 80% variance explained)
- `q = 0.90` GPD threshold quantile
- Rebalance: 14-day (EVA Opt) / 21-day (v3)
- Transaction cost: 10 bps one-way

---

## Results (2018–2026)

| Metric | EVA Strategy | BTC B&H | Equal-Weight B&H |
|---|---|---|---|
| Arithmetic Ann. Return | **+31.0%** | +33.6% | +28.4% |
| CAGR | **+27.9%** | +28.9% | +22.1% |
| Sharpe Ratio | **1.11** | 0.54 | 0.36 |
| Max Drawdown | **−33%** | −84% | −89% |
| Calmar Ratio | **0.94** | 0.40 | 0.25 |
| 2022 Return | **+4.0%** | −71.1% | — |
| OOS Sharpe (30%) | **1.08** | — | — |

---

## File Structure

```
.
├── strategy.py                # Core: PCA + GPD + signal + backtest
├── compare_strategies.py      # Multi-strategy comparison runner
├── plot_defensive.py          # Generates defensive_strategy.png (3-panel chart)
├── walkforward_validation.py  # Walk-forward OOS validation
├── make_pitch.js              # PPT generator (pptxgenjs)
├── package.json
├── output.html                # Task 3: Backtest & validation report
├── glossary.html              # Terminology reference (Chinese)
├── teaching.html              # Strategy walkthrough (interactive)
├── crypto_10_data.parquet     # Price data (10 crypto assets, daily)
├── defensive_strategy.png     # Main backtest chart
└── comparison_results.png     # Multi-strategy comparison chart
```

---

## How to Run

```bash
# Install Python deps
pip install numpy pandas scipy matplotlib pptxgenjs

# Run backtest + generate chart
python strategy.py

# Full comparison across all strategies
python compare_strategies.py

# Generate pitch deck PPT
npm install
node make_pitch.js
```

---

## Reference

Köhler, Heckens, Guhr (2026). *Extreme Value Analysis of Financial Markets*. arXiv: 2603.xxxxx

---

*SimicX Internship — March 2026*
