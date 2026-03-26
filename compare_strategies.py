"""
Comprehensive comparison:
  1. BTC Buy-and-Hold
  2. Equal-Weight Buy-and-Hold (all 10 coins)
  3. Our Strategy — default params  (L=504, K=5, q=0.95, top_n=3, reb=7)
  4. Our Strategy — optimized params (L=504, K=7, q=0.90, top_n=4, reb=14)
  5. SimicX pseudocode — signal-proportional vol-scaled weights (L=504, K=5, q=0.95, reb=5)
  6. Current EVT hybrid v3 from strategy.py
  7. Equal-weight ensemble of EVA Optimized + Current EVT Hybrid v3
  8. BTC-trend-filtered ensemble
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
from strategy import run_backtest as run_current_backtest
warnings.filterwarnings("ignore")

# ── reuse core functions from strategy.py ──────────────────────────────────

def load_prices(path):
    df = pd.read_parquet(path)
    return df.pivot(index="time", columns="ticker", values="close").sort_index()

def fit_gpd_gamma(exceedances):
    n = len(exceedances)
    if n < 10:
        return 0.0
    def neg_ll(params):
        gamma, sigma = params
        if sigma <= 0:
            return 1e10
        y = exceedances / sigma
        if gamma == 0:
            return n * np.log(sigma) + np.sum(y)
        z = 1.0 + gamma * y
        if np.any(z <= 0):
            return 1e10
        return n * np.log(sigma) + (1.0 + 1.0 / gamma) * np.sum(np.log(z))
    m1 = np.mean(exceedances)
    m2 = np.mean(exceedances ** 2)
    g0 = np.clip(0.5 * (1.0 - m1**2 / (m2 - m1**2)) if m2 > m1**2 else 0.1, -0.4, 1.5)
    s0 = max(m1 * (1.0 - g0), 1e-8)
    res = minimize(neg_ll, [g0, s0], bounds=[(-0.49, 2.0), (1e-8, None)], method="L-BFGS-B")
    return float(res.x[0]) if res.success else 0.0

def compute_signal(returns_window, K=5, q=0.95, min_exceed=10):
    N, L = returns_window.shape
    mu = returns_window.mean(axis=1, keepdims=True)
    sigma = returns_window.std(axis=1, keepdims=True, ddof=1)
    sigma[sigma < 1e-10] = 1e-10
    M = (returns_window - mu) / sigma
    C = (1.0 / (L - 1)) * (M @ M.T)
    C = (C + C.T) / 2.0
    eigvals, eigvecs = np.linalg.eigh(C)
    order = np.argsort(eigvals)[::-1]
    eigvals, eigvecs = eigvals[order], eigvecs[:, order]
    K = min(K, N)
    eigvals_k = np.maximum(eigvals[:K], 1e-10)
    eigvecs_k = eigvecs[:, :K]
    R = np.diag(1.0 / np.sqrt(eigvals_k)) @ (eigvecs_k.T @ M)
    gamma_k = np.zeros(K)
    for k in range(K):
        pos = R[k][R[k] > 0]
        if len(pos) < min_exceed:
            continue
        thresh = np.quantile(pos, q)
        exc = pos[pos > thresh] - thresh
        if len(exc) < min_exceed:
            continue
        gamma_k[k] = fit_gpd_gamma(exc)
    scores = np.abs(eigvecs_k) @ gamma_k
    std_s = scores.std(ddof=1)
    if std_s < 1e-10:
        return np.zeros(N), eigvecs_k
    return -(scores - scores.mean()) / std_s, eigvecs_k

# ── Strategy 1: our equal-weight long/short top_n ──────────────────────────

def run_ew_strategy(prices, L=504, K=5, q=0.95, rebalance_freq=7, top_n=3, cost_bps=10):
    one_way = cost_bps / 2 / 10_000
    log_ret = np.log(prices / prices.shift(1)).dropna()
    ret_arr = log_ret.values
    N, T = ret_arr.shape[1], len(log_ret)
    strategy_rets, weights = [], np.zeros(N)
    for t in range(L, T):
        window = ret_arr[t - L:t].T
        if (t - L) % rebalance_freq == 0:
            sig, _ = compute_signal(window, K=K, q=q)
            ranked = np.argsort(sig)[::-1]
            new_w = np.zeros(N)
            new_w[ranked[:top_n]] = 1.0 / top_n
            new_w[ranked[-top_n:]] = -1.0 / top_n
            tc = np.abs(new_w - weights).sum() * one_way
            weights = new_w
        else:
            tc = 0.0
        strategy_rets.append(np.dot(weights, ret_arr[t]) - tc)
    return pd.Series(strategy_rets, index=log_ret.index[L:], name="strategy")

# ── Strategy 2: SimicX signal-proportional + vol-scaled (dollar-neutral) ───

def run_simicx_style(prices, L=504, K=5, q=0.95, rebalance_freq=5,
                     vol_target=0.15, max_weight=0.5, cost_bps=10):
    """
    Mimics SimicX pseudocode position sizing:
      w_i = signal_i / Σ|signal_j|
      then scale by vol_target / (σ_i_daily * sqrt(365))
      normalize to dollar-neutral (Σ|w_i'| = 1)
    """
    one_way = cost_bps / 2 / 10_000
    log_ret = np.log(prices / prices.shift(1)).dropna()
    ret_arr = log_ret.values
    N, T = ret_arr.shape[1], len(log_ret)
    strategy_rets, weights = [], np.zeros(N)
    for t in range(L, T):
        window = ret_arr[t - L:t].T  # (N, L)
        if (t - L) % rebalance_freq == 0:
            sig, _ = compute_signal(window, K=K, q=q)
            sig_sum = np.abs(sig).sum()
            if sig_sum < 1e-10:
                new_w = np.zeros(N)
            else:
                # Signal-proportional weights
                w_prop = sig / sig_sum
                # Vol-scale each position
                daily_vol = window.std(axis=1, ddof=1)
                daily_vol = np.maximum(daily_vol, 1e-8)
                ann_vol = daily_vol * np.sqrt(365)
                w_scaled = w_prop / ann_vol * vol_target
                # Clip to max individual weight
                w_scaled = np.clip(w_scaled, -max_weight, max_weight)
                # Normalize to dollar-neutral (sum of abs = 1)
                total = np.abs(w_scaled).sum()
                new_w = w_scaled / total if total > 1e-10 else np.zeros(N)
            tc = np.abs(new_w - weights).sum() * one_way
            weights = new_w
        else:
            tc = 0.0
        strategy_rets.append(np.dot(weights, ret_arr[t]) - tc)
    return pd.Series(strategy_rets, index=log_ret.index[L:], name="simicx_style")


def run_current_robust(prices):
    """Run the current robust EVT implementation from strategy.py."""
    results = run_current_backtest(
        prices,
        L=504,
        max_modes=2,
        variance_target=0.80,
        q_grid=(0.90,),
        rebalance_freq=21,
        min_exceed=12,
        cost_bps=10,
        gross_leverage=1.0,
        max_asset_weight=0.30,
        signal_direction=-1,
        risk_mode="pos",
        weighting_style="top_n",
        top_n=4,
    )
    return results["strategy"].rename("current_robust")


def apply_btc_trend_filter(rets, btc_prices, lookback=100):
    """Keep exposure only when BTC is above its lagged moving average."""
    ma = btc_prices.rolling(lookback).mean()
    regime_on = (btc_prices > ma).shift(1).fillna(False).astype(float)
    aligned = rets.index.intersection(regime_on.index)
    filtered = rets.loc[aligned] * regime_on.loc[aligned]
    return filtered.rename(f"{rets.name}_btc_filter")

# ── Performance metrics ─────────────────────────────────────────────────────

def metrics(rets, label=""):
    r = rets.dropna()
    ann = 365
    ann_ret = r.mean() * ann
    ann_vol = r.std() * np.sqrt(ann)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
    cum = (1 + r).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax()
    max_dd = dd.min()
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0.0
    win_rate = (r > 0).mean()
    return {
        "Label": label,
        "Ann. Return": ann_ret,
        "Ann. Vol": ann_vol,
        "Sharpe": sharpe,
        "Max DD": max_dd,
        "Calmar": calmar,
        "Win Rate": win_rate,
    }

# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    DATA = "crypto_10_data.parquet"
    prices = load_prices(DATA)
    log_ret = np.log(prices / prices.shift(1)).dropna()

    print("Running backtests… (takes ~3-5 min)")

    # 1. BTC buy-and-hold
    btc_rets = log_ret["BTCUSD"].iloc[504:]
    print("  [1/8] BTC B&H done")

    # 2. Equal-weight buy-and-hold
    ew_rets = log_ret.mean(axis=1).iloc[504:]
    print("  [2/8] EW B&H done")

    # 3. Our default params
    strat_default = run_ew_strategy(prices, L=504, K=5, q=0.95,
                                    rebalance_freq=7, top_n=3, cost_bps=10)
    print("  [3/8] Our default done")

    # 4. Our optimized params
    strat_opt = run_ew_strategy(prices, L=504, K=7, q=0.90,
                                rebalance_freq=14, top_n=4, cost_bps=10)
    print("  [4/8] Our optimized done")

    # 5. SimicX pseudocode style
    strat_simicx = run_simicx_style(prices, L=504, K=5, q=0.95,
                                    rebalance_freq=5, cost_bps=10)
    print("  [5/8] SimicX style done")

    # 6. Current robust EVT strategy
    strat_current = run_current_robust(prices)
    print("  [6/8] Current EVT hybrid v3 done")

    # 7. Equal-weight ensemble of strongest legacy and current hybrid
    strat_ensemble = (0.5 * strat_opt + 0.5 * strat_current).rename("ensemble")
    print("  [7/8] Ensemble done")

    # 8. BTC trend filtered ensemble
    strat_ensemble_filtered = apply_btc_trend_filter(
        strat_ensemble,
        prices["BTCUSD"],
        lookback=100,
    )
    print("  [8/8] BTC trend-filtered ensemble done")

    # Align all series to same dates
    start = max(btc_rets.index[0], ew_rets.index[0],
                strat_default.index[0], strat_opt.index[0], strat_simicx.index[0],
                strat_current.index[0], strat_ensemble.index[0],
                strat_ensemble_filtered.index[0])
    end = min(btc_rets.index[-1], ew_rets.index[-1],
              strat_default.index[-1], strat_opt.index[-1], strat_simicx.index[-1],
              strat_current.index[-1], strat_ensemble.index[-1],
              strat_ensemble_filtered.index[-1])

    btc_rets    = btc_rets[start:end]
    ew_rets     = ew_rets[start:end]
    strat_default = strat_default[start:end]
    strat_opt   = strat_opt[start:end]
    strat_simicx = strat_simicx[start:end]
    strat_current = strat_current[start:end]
    strat_ensemble = strat_ensemble[start:end]
    strat_ensemble_filtered = strat_ensemble_filtered[start:end]

    # ── Print metrics table ─────────────────────────────────────────────────
    all_series = [
        (btc_rets,      "BTC Buy & Hold"),
        (ew_rets,       "EW Buy & Hold"),
        (strat_default, "EVA Default (K=5,q=.95,reb=7,n=3)"),
        (strat_simicx,  "SimicX Style (vol-scaled,reb=5)"),
        (strat_opt,     "EVA Optimized (K=7,q=.90,reb=14,n=4)"),
        (strat_current, "Current EVT Hybrid v3"),
        (strat_ensemble, "Ensemble (50/50 Opt + Hybrid v3)"),
        (strat_ensemble_filtered, "Ensemble + BTC Trend Filter"),
    ]

    print("\n" + "=" * 80)
    print(f"  {'Strategy':<38} {'Ret':>7} {'Vol':>7} {'Sharpe':>7} {'MaxDD':>7} {'Calmar':>7}")
    print("=" * 80)
    all_metrics = []
    for rets, label in all_series:
        m = metrics(rets, label)
        all_metrics.append(m)
        print(f"  {label:<38} "
              f"{m['Ann. Return']:>+7.1%} "
              f"{m['Ann. Vol']:>7.1%} "
              f"{m['Sharpe']:>7.2f} "
              f"{m['Max DD']:>7.1%} "
              f"{m['Calmar']:>7.2f}")
    print("=" * 80)

    # ── Plot ────────────────────────────────────────────────────────────────
    colors = {
        "BTC Buy & Hold":       "#94A3B8",   # gray
        "EW Buy & Hold":        "#64748B",   # darker gray
        "EVA Default (K=5,q=.95,reb=7,n=3)": "#F59E0B",  # amber
        "SimicX Style (vol-scaled,reb=5)": "#6366F1",  # indigo
        "EVA Optimized (K=7,q=.90,reb=14,n=4)": "#00C9A7",  # teal
        "Current EVT Hybrid v3": "#EF4444",  # red
        "Ensemble (50/50 Opt + Hybrid v3)": "#22C55E",  # green
        "Ensemble + BTC Trend Filter": "#A855F7",  # violet
    }
    lstyles = {
        "BTC Buy & Hold":       "--",
        "EW Buy & Hold":        ":",
        "EVA Default (K=5,q=.95,reb=7,n=3)": "-.",
        "SimicX Style (vol-scaled,reb=5)": "-",
        "EVA Optimized (K=7,q=.90,reb=14,n=4)": "-",
        "Current EVT Hybrid v3": "-",
        "Ensemble (50/50 Opt + Hybrid v3)": "-",
        "Ensemble + BTC Trend Filter": "--",
    }
    lwidths = {
        "BTC Buy & Hold":       1.5,
        "EW Buy & Hold":        1.5,
        "EVA Default (K=5,q=.95,reb=7,n=3)": 1.8,
        "SimicX Style (vol-scaled,reb=5)": 2.0,
        "EVA Optimized (K=7,q=.90,reb=14,n=4)": 2.5,
        "Current EVT Hybrid v3": 2.2,
        "Ensemble (50/50 Opt + Hybrid v3)": 2.4,
        "Ensemble + BTC Trend Filter": 2.4,
    }

    fig = plt.figure(figsize=(16, 14))
    gs = fig.add_gridspec(3, 2, hspace=0.45, wspace=0.35)
    ax_cum  = fig.add_subplot(gs[0, :])   # top full-width: cumulative return
    ax_dd   = fig.add_subplot(gs[1, :])   # middle full-width: drawdown
    ax_bar  = fig.add_subplot(gs[2, 0])   # bottom-left: bar chart metrics
    ax_roll = fig.add_subplot(gs[2, 1])   # bottom-right: rolling Sharpe (opt vs SimicX)

    fig.suptitle("EVA Tail Risk Strategy — Full Comparison",
                 fontsize=15, fontweight="bold", y=0.98)

    # ── Panel 1: Cumulative returns ─────────────────────────────────────────
    for rets, label in all_series:
        cum = (1 + rets).cumprod()
        ax_cum.plot(cum, label=label, color=colors[label],
                    linestyle=lstyles[label], linewidth=lwidths[label])
    ax_cum.set_yscale("log")
    ax_cum.set_ylabel("Cumulative Return (log scale)")
    ax_cum.set_title("Cumulative Performance (2019–2026, log scale)", fontsize=11)
    ax_cum.legend(fontsize=8, loc="upper left")
    ax_cum.grid(True, alpha=0.25)
    ax_cum.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # ── Panel 2: Drawdown ───────────────────────────────────────────────────
    for rets, label in all_series:
        cum = (1 + rets).cumprod()
        dd = (cum - cum.cummax()) / cum.cummax() * 100
        ax_dd.plot(dd, label=label, color=colors[label],
                   linestyle=lstyles[label], linewidth=lwidths[label], alpha=0.85)
    ax_dd.set_ylabel("Drawdown (%)")
    ax_dd.set_title("Drawdown Comparison", fontsize=11)
    ax_dd.legend(fontsize=8, loc="lower left")
    ax_dd.grid(True, alpha=0.25)
    ax_dd.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # ── Panel 3: Bar chart — key metrics ───────────────────────────────────
    labels_short = [
        "BTC\nB&H",
        "EW\nB&H",
        "EVA\nDefault",
        "SimicX\nStyle",
        "EVA\nOptimized",
        "Current\nHybrid",
        "50/50\nEnsemble",
        "Ensemble\n+ Trend",
    ]
    sharpes = [m["Sharpe"] for m in all_metrics]
    bar_colors = [colors[m["Label"]] for m in all_metrics]
    bars = ax_bar.bar(labels_short, sharpes, color=bar_colors, edgecolor="white", linewidth=0.8)
    for bar, val in zip(bars, sharpes):
        ax_bar.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f"{val:.2f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax_bar.set_ylabel("Sharpe Ratio")
    ax_bar.set_title("Sharpe Ratio by Strategy", fontsize=11)
    ax_bar.grid(True, alpha=0.25, axis="y")
    ax_bar.axhline(0, color="black", linewidth=0.8)

    # Add second y-axis for Ann. Return on same chart (twin axis)
    ax_bar2 = ax_bar.twinx()
    returns_pct = [m["Ann. Return"] * 100 for m in all_metrics]
    x_pos = range(len(labels_short))
    ax_bar2.scatter(x_pos, returns_pct, color="white", edgecolor=bar_colors,
                    linewidth=2, zorder=5, s=60, marker="D")
    ax_bar2.set_ylabel("Ann. Return (%)", color="gray")
    ax_bar2.tick_params(axis="y", colors="gray")

    # ── Panel 4: Rolling 90-day Sharpe (major strategy variants) ───────────
    for rets, label in [(strat_opt, "EVA Optimized (K=7,q=.90,reb=14,n=4)"),
                        (strat_current, "Current EVT Hybrid v3"),
                        (strat_ensemble, "Ensemble (50/50 Opt + Hybrid v3)"),
                        (strat_ensemble_filtered, "Ensemble + BTC Trend Filter")]:
        roll = (rets.rolling(90).mean() / rets.rolling(90).std() * np.sqrt(365))
        ax_roll.plot(roll, label=label.split("(")[0].strip(),
                     color=colors[label], linestyle=lstyles[label],
                     linewidth=lwidths[label])
    ax_roll.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax_roll.set_ylabel("Rolling Sharpe (90d)")
    ax_roll.set_title("Rolling 90-Day Sharpe: Strategy Variants", fontsize=11)
    ax_roll.legend(fontsize=8)
    ax_roll.grid(True, alpha=0.25)
    ax_roll.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.savefig("comparison_results.png", dpi=150, bbox_inches="tight",
                facecolor="#0D1B2A")
    print("\nPlot saved → comparison_results.png")

    # ── Also save a clean metrics table as CSV for PPT reference ───────────
    rows = []
    for m in all_metrics:
        rows.append({
            "Strategy": m["Label"],
            "Ann. Return": f"{m['Ann. Return']:+.1%}",
            "Ann. Vol": f"{m['Ann. Vol']:.1%}",
            "Sharpe": f"{m['Sharpe']:.2f}",
            "Max DD": f"{m['Max DD']:.1%}",
            "Calmar": f"{m['Calmar']:.2f}",
            "Win Rate": f"{m['Win Rate']:.1%}",
        })
    pd.DataFrame(rows).to_csv("comparison_metrics.csv", index=False)
    print("Metrics saved → comparison_metrics.csv")
