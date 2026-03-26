"""
Walk-forward validation for the strongest current strategy candidates.

Method:
  1. Build daily return series for legacy EVA optimized and current EVT Hybrid v3
  2. Form simple ensemble candidates with weights between the two
  3. Optionally apply a lagged BTC moving-average trend filter
  4. Use a rolling 2-year train window and 6-month test window
  5. Select the best candidate by train Sharpe and score it out-of-sample
"""

import math
import numpy as np
import pandas as pd

from compare_strategies import (
    apply_btc_trend_filter,
    load_prices,
    run_current_robust,
    run_ew_strategy,
)


TRAIN_DAYS = 730
TEST_DAYS = 180
STEP_DAYS = 180
WEIGHT_GRID = (0.0, 0.25, 0.50, 0.75, 1.0)
OUTPUT_CSV = "walkforward_folds.csv"


def performance(rets: pd.Series) -> dict:
    """Annualized performance summary for a daily return series."""
    r = rets.dropna()
    if len(r) < 2:
        return {
            "ann_ret": np.nan,
            "ann_vol": np.nan,
            "sharpe": np.nan,
            "max_dd": np.nan,
        }

    ann_ret = r.mean() * 365
    ann_vol = r.std(ddof=1) * math.sqrt(365)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else np.nan
    cum = (1 + r).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax()
    return {
        "ann_ret": ann_ret,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_dd": dd.min(),
    }


def build_candidates() -> dict[str, pd.Series]:
    """Construct aligned daily return series for all walk-forward candidates."""
    prices = load_prices("crypto_10_data.parquet")
    strat_opt = run_ew_strategy(
        prices, L=504, K=7, q=0.90, rebalance_freq=14, top_n=4, cost_bps=10
    )
    strat_current = run_current_robust(prices)

    start = max(strat_opt.index[0], strat_current.index[0])
    end = min(strat_opt.index[-1], strat_current.index[-1])
    strat_opt = strat_opt[start:end]
    strat_current = strat_current[start:end]
    btc_prices = prices["BTCUSD"].loc[start:end]

    candidates = {
        "opt_only": strat_opt.rename("opt_only"),
        "current_only": strat_current.rename("current_only"),
    }
    for weight in WEIGHT_GRID:
        series = weight * strat_opt + (1.0 - weight) * strat_current
        candidates[f"ensemble_w{weight:.2f}"] = series.rename(f"ensemble_w{weight:.2f}")
        candidates[f"ensemble_w{weight:.2f}_filter"] = apply_btc_trend_filter(
            series, btc_prices, lookback=100
        )

    common_index = strat_opt.index
    for series in candidates.values():
        common_index = common_index.intersection(series.index)
    common_index = common_index.sort_values()
    for key in list(candidates):
        candidates[key] = candidates[key].loc[common_index]
    return candidates


def run_walkforward(candidates: dict[str, pd.Series]) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Run rolling train/test selection and return fold stats plus stitched OOS series."""
    idx = next(iter(candidates.values())).index
    folds = []
    selected_test_rets = []
    fixed50_test_rets = []

    start_pos = 0
    while start_pos + TRAIN_DAYS + TEST_DAYS <= len(idx):
        train_idx = idx[start_pos : start_pos + TRAIN_DAYS]
        test_idx = idx[start_pos + TRAIN_DAYS : start_pos + TRAIN_DAYS + TEST_DAYS]

        best_name = None
        best_train_sharpe = -np.inf
        for name, series in candidates.items():
            train_sharpe = performance(series.loc[train_idx])["sharpe"]
            if pd.notna(train_sharpe) and train_sharpe > best_train_sharpe:
                best_name = name
                best_train_sharpe = train_sharpe

        best_test = candidates[best_name].loc[test_idx]
        fixed_test = candidates["ensemble_w0.50"].loc[test_idx]
        selected_test_rets.append(best_test)
        fixed50_test_rets.append(fixed_test)

        best_test_metrics = performance(best_test)
        fixed_test_metrics = performance(fixed_test)
        folds.append(
            {
                "train_start": str(train_idx[0].date()),
                "train_end": str(train_idx[-1].date()),
                "test_start": str(test_idx[0].date()),
                "test_end": str(test_idx[-1].date()),
                "selected": best_name,
                "train_sharpe": best_train_sharpe,
                "test_sharpe": best_test_metrics["sharpe"],
                "test_ret": best_test_metrics["ann_ret"],
                "fixed50_test_sharpe": fixed_test_metrics["sharpe"],
                "fixed50_test_ret": fixed_test_metrics["ann_ret"],
            }
        )
        start_pos += STEP_DAYS

    return (
        pd.DataFrame(folds),
        pd.concat(selected_test_rets).sort_index(),
        pd.concat(fixed50_test_rets).sort_index(),
    )


if __name__ == "__main__":
    candidates = build_candidates()
    folds, selected_oos, fixed50_oos = run_walkforward(candidates)
    folds.to_csv(OUTPUT_CSV, index=False)

    print("FULL SAMPLE")
    for name in ["opt_only", "current_only", "ensemble_w0.50", "ensemble_w0.50_filter"]:
        stats = performance(candidates[name])
        print(name, {k: round(v, 4) for k, v in stats.items()})

    print("\nWALK-FORWARD OOS SUMMARY")
    for name, series in [
        ("selected_by_train_sharpe", selected_oos),
        ("fixed_50_50_oos_windows", fixed50_oos),
    ]:
        stats = performance(series)
        print(name, {k: round(v, 4) for k, v in stats.items()})

    print("\nFOLDS")
    print(folds.to_string(index=False))
    print(f"\nFold details saved -> {OUTPUT_CSV}")
