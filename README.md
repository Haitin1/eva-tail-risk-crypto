# EVA Tail Risk Strategy — SimicX Internship Project

> **极值尾部风险策略** · 应用于加密货币市场的动态风险管理量化策略

Applying **Extreme Value Analysis (EVA)** from Köhler, Heckens & Guhr (2026) to a 10-asset crypto portfolio. The strategy uses PCA decomposition and Generalized Pareto Distribution (GPD) fitting to dynamically identify and avoid tail risk.

将 Köhler、Heckens 与 Guhr（2026）提出的**极值分析（EVA）**方法应用于10个加密资产组合。策略通过 PCA 分解和广义帕累托分布（GPD）拟合，动态识别并规避尾部风险。

---

## Deliverables · 三个交付物

| # | File · 文件 | Description · 说明 |
|---|---|---|
| 1 | `EVA_Pitch_Deck.pptx` | Pitch deck for non-quant investors (9 slides) · 面向非量化投资人的路演幻灯片（9页） |
| 2 | `strategy.py` · `compare_strategies.py` · `plot_defensive.py` | Source code · 策略源代码 |
| 3 | `output.html` | Backtest & validation report · 回测与验证报告 |

Supporting · 辅助文档: `glossary.html`（术语手册）· `teaching.html`（策略逐步讲解）

---

## Strategy Overview · 策略简介

**Ensemble = 50% EVA Optimized + 50% EVT Hybrid v3**

The core idea: decompose 10 correlated crypto assets into independent market modes via PCA, measure the tail risk (γ) of each mode using EVT/GPD, then dynamically tilt positions away from high-risk exposures.

核心思路：通过 PCA 将10个高度相关的加密资产分解为相互独立的市场驱动力，用 EVT/GPD 测量每个驱动力的尾部风险（γ），再动态调整仓位以规避高风险暴露。

| Sub-Strategy · 子策略 | signal_direction | Logic · 逻辑 |
|---|---|---|
| EVA Optimized | +1 | Long safest 4, short most dangerous 4 · 做多最安全4个，做空最危险4个（防守型） |
| EVT Hybrid v3 | −1 | Long highest positive tail-risk (momentum) · 做多正尾部风险最高的资产（动量型） |

### Key Parameters · 关键参数

| Parameter | Value | Rationale · 依据 |
|---|---|---|
| `L` | 504 (2 years) | Balances GPD sample size and regime relevance · 平衡GPD样本量与信息时效 |
| `K` | 7 PCA modes | Captures ≥ 80% variance · 解释≥80%方差 |
| `q` | 0.90 | ~50 exceedances per mode, GPD stable · 每mode约50个超阈值点，GPD估计稳定 |
| Rebalance | 14d / 21d | EVA Opt / v3 |
| Transaction cost | 10 bps one-way · 单边 |

---

## Results · 回测结果（2018–2026）

| Metric · 指标 | EVA Strategy · 本策略 | BTC B&H | Equal-Weight B&H · 等权基准 |
|---|---|---|---|
| Arithmetic Ann. Return · 算术年化收益 | **+31.0%** | +33.6% | +28.4% |
| CAGR · 复合年化增长率 | **+27.9%** | +28.9% | +22.1% |
| Sharpe Ratio · 夏普比率 | **1.11** | 0.54 | 0.36 |
| Max Drawdown · 最大回撤 | **−33%** | −84% | −89% |
| Calmar Ratio · 卡玛比率 | **0.94** | 0.40 | 0.25 |
| 2022 Annual Return · 2022年收益 | **+4.0%** | −71.1% | — |
| OOS Sharpe (30% holdout) · 样本外夏普 | **1.08** | — | — |

> **Key takeaway · 核心结论**：Strategy CAGR is comparable to BTC, but MaxDD is compressed from −84% to −33%, and Sharpe improves from 0.54 to 1.11. The value lies in survivability through bear markets, not outright return maximization.
>
> 策略 CAGR 与 BTC 接近，但最大回撤从 −84% 压缩至 −33%，Sharpe 从 0.54 提升至 1.11。价值在于穿越熊市的生存能力，而非追求最高绝对收益。

---

## File Structure · 文件结构

```
.
├── strategy.py                # 核心策略：PCA + GPD + 信号 + 回测引擎
├── compare_strategies.py      # 多策略对比运行器
├── plot_defensive.py          # 生成 defensive_strategy.png（3面板图表）
├── walkforward_validation.py  # 样本外滚动验证
├── make_pitch.js              # PPT 生成脚本（pptxgenjs）
├── package.json
├── output.html                # Task 3：回测与验证报告（含11个交互图表）
├── glossary.html              # 专业术语手册（中文）
├── teaching.html              # 策略逐步讲解（交互式）
├── crypto_10_data.parquet     # 价格数据（10个加密资产，日频）
├── defensive_strategy.png     # 主回测图（净值 / 回撤 / 尾部风险信号）
└── comparison_results.png     # 多策略对比图
```

---

## How to Run · 运行方法

```bash
# Install Python dependencies · 安装 Python 依赖
pip install numpy pandas scipy matplotlib pptxgenjs

# Run full backtest + generate chart · 运行回测并生成图表
python strategy.py

# Compare all strategy variants · 对比所有策略变体
python compare_strategies.py

# Generate pitch deck · 生成路演幻灯片
npm install
node make_pitch.js
```

---

## Validation · 有效性验证

- **No look-ahead bias** · 无前视偏差：Signal uses only `[t−L, t−1]` data; trades execute at close on day `t`
- **Transaction costs included** · 含交易成本：10 bps one-way on all rebalances
- **Fair benchmark** · 公平基准：Equal-weight 10-crypto B&H (same universe, no strategy)
- **Mechanical bear regime** · 机械定义熊市：BTC drawdown > 40% from rolling 180-day high (no manual selection)
- **Out-of-sample test** · 样本外测试：70/30 time-series split, Sharpe 1.12 → 1.08 (−3.6% degradation)

---

## Reference · 参考文献

Köhler, Heckens, Guhr (2026). *Extreme Value Analysis of Financial Markets*. arXiv: 2603.xxxxx

---

*SimicX Quantitative Research Internship · March 2026*
