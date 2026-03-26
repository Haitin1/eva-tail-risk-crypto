"""
生成 defensive_strategy.png  (V2)
3 面板图：集成策略 vs BTC vs 等权基准
- Panel 1: 累积收益（对数坐标）
- Panel 2: 回撤对比（策略 / BTC / 等权基准）
- Panel 3: 滚动尾部厚度 γ（市场压力雷达）

熊市阴影：机械定义 ── BTC 从过去 180 日最高点回撤 > 40% 时标红
"""

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from scipy.optimize import minimize
import warnings
warnings.filterwarnings("ignore")

# ── 中文字体：优先从系统路径直接加载 ─────────────────────────────────────────
def _setup_chinese_font():
    import os, glob
    candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode MS.ttf",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                fm.fontManager.addfont(path)
                prop = fm.FontProperties(fname=path)
                name = prop.get_name()
                matplotlib.rcParams['font.sans-serif'] = [name, 'DejaVu Sans']
                matplotlib.rcParams['axes.unicode_minus'] = False
                return name
            except Exception:
                continue
    # fallback: 用英文
    matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False
    return None

_setup_chinese_font()

# ── 复用核心函数 ──────────────────────────────────────────────────────────────

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
        return np.zeros(N), gamma_k
    return -(scores - scores.mean()) / std_s, gamma_k


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


def run_current_robust(prices):
    from strategy import run_backtest as run_current_backtest
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


def compute_rolling_gamma(log_ret, L=504, K=7, q=0.90, step=21):
    ret_arr = log_ret.values.T   # (N, T)
    dates = log_ret.index
    T = len(dates)
    gammas, idx = [], []
    for t in range(L, T, step):
        window = ret_arr[:, t - L:t]
        _, gamma_k = compute_signal(window, K=K, q=q)
        gammas.append(float(gamma_k.mean()))
        idx.append(dates[t])
    return pd.Series(gammas, index=idx, name="avg_gamma")


def mechanical_bear_mask(btc_prices, window=180, threshold=0.40):
    """
    Returns a boolean Series: True when BTC has fallen > threshold
    from its rolling window-day high (mechanical definition, no human selection).
    """
    rolling_high = btc_prices.rolling(window, min_periods=1).max()
    dd = (btc_prices - rolling_high) / rolling_high
    return dd < -threshold


def shade_bears(ax, mask, color="#FF4444", alpha=0.13):
    """Shade contiguous True regions in mask."""
    in_stress = False
    t0 = None
    for date, val in mask.items():
        if val and not in_stress:
            t0 = date
            in_stress = True
        elif not val and in_stress:
            ax.axvspan(t0, date, alpha=alpha, color=color, zorder=0)
            in_stress = False
    if in_stress:
        ax.axvspan(t0, mask.index[-1], alpha=alpha, color=color, zorder=0)


# ── 数据加载 ──────────────────────────────────────────────────────────────────

def load_prices(path):
    df = pd.read_parquet(path)
    return df.pivot(index="time", columns="ticker", values="close").sort_index()


# ── 主程序 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    DATA = "crypto_10_data.parquet"
    prices = load_prices(DATA)
    log_ret = np.log(prices / prices.shift(1)).dropna()

    print("运行策略回测中…（约3-5分钟）")

    btc_rets = log_ret["BTCUSD"].iloc[504:]
    ew_rets  = log_ret.mean(axis=1).iloc[504:]

    strat_opt = run_ew_strategy(prices, L=504, K=7, q=0.90,
                                rebalance_freq=14, top_n=4, cost_bps=10)
    print("  [1/3] EVA 优化版完成")

    strat_current = run_current_robust(prices)
    print("  [2/3] EVT 混合 v3 完成")

    strat_ensemble = (0.5 * strat_opt + 0.5 * strat_current).rename("ensemble")
    print("  [3/3] 集成策略完成")

    # ── 对齐时间序列 ─────────────────────────────────────────────────────────
    start = max(btc_rets.index[0], strat_ensemble.index[0])
    end   = min(btc_rets.index[-1], strat_ensemble.index[-1])
    btc_rets       = btc_rets[start:end]
    ew_rets        = ew_rets[start:end]
    strat_ensemble = strat_ensemble[start:end]

    # ── 机械熊市判断 ─────────────────────────────────────────────────────────
    btc_bear_mask = mechanical_bear_mask(
        prices["BTCUSD"].loc[start:end], window=180, threshold=0.40
    )
    print("  机械熊市区间定义：BTC 从过去 180 日高点回撤 > 40%")

    # ── 滚动 γ ───────────────────────────────────────────────────────────────
    print("  计算滚动 γ…（约1分钟）")
    log_ret_aligned = log_ret.loc[start:end]
    gamma_series = compute_rolling_gamma(log_ret_aligned, L=504, K=7, q=0.90, step=21)

    # ── 颜色方案 ─────────────────────────────────────────────────────────────
    TEAL   = "#00C9A7"
    ORANGE = "#F59E0B"
    GRAY   = "#94A3B8"
    DGRAY  = "#475569"
    BG     = "#0D1B2A"
    TEXT   = "#E2E8F0"
    BEAR   = "#FF4444"
    GRID   = "#1E3040"

    # ── 绘图：3 面板 ─────────────────────────────────────────────────────────
    fig, axes = plt.subplots(
        3, 1, figsize=(14, 11), sharex=True,
        gridspec_kw={"height_ratios": [3, 2, 2], "hspace": 0.38}
    )
    fig.patch.set_facecolor(BG)
    for ax in axes:
        ax.set_facecolor(BG)
        ax.tick_params(colors=TEXT, labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID)

    fig.suptitle(
        "EVA Tail Risk Strategy — 8-Year Performance vs Benchmarks",
        fontsize=13, fontweight="bold", color=TEXT, y=0.995
    )

    # ── Panel 1: 累积收益 ─────────────────────────────────────────────────────
    ax = axes[0]
    cum_ens = (1 + strat_ensemble).cumprod()
    cum_btc = (1 + btc_rets).cumprod()
    cum_ew  = (1 + ew_rets).cumprod()

    ax.plot(cum_ens, color=TEAL,   linewidth=2.4, label="EVA Strategy", zorder=3)
    ax.plot(cum_btc, color=GRAY,   linewidth=1.6, label="BTC Buy & Hold",
            linestyle="--", zorder=1)
    ax.plot(cum_ew,  color=DGRAY,  linewidth=1.4, label="Equal-Weight 10-Crypto",
            linestyle=":",  zorder=1, alpha=0.85)
    ax.set_yscale("log")
    ax.set_ylabel("累积收益（对数坐标）", color=TEXT, fontsize=10)
    ax.set_title("累积收益对比  /  Cumulative Return (log scale)", color=TEXT,
                 fontsize=11, pad=6)
    ax.legend(fontsize=9.5, loc="upper left", facecolor="#152030",
              labelcolor=TEXT, framealpha=0.85, edgecolor=GRID)
    ax.grid(True, alpha=0.18, color=GRID)
    shade_bears(ax, btc_bear_mask)

    # ── Panel 2: 回撤 ─────────────────────────────────────────────────────────
    ax = axes[1]
    dd_ens = (cum_ens - cum_ens.cummax()) / cum_ens.cummax() * 100
    dd_btc = (cum_btc - cum_btc.cummax()) / cum_btc.cummax() * 100
    dd_ew  = (cum_ew  - cum_ew.cummax())  / cum_ew.cummax()  * 100

    ax.fill_between(dd_ens.index, dd_ens, 0, alpha=0.55, color=TEAL,  label="EVA Strategy")
    ax.fill_between(dd_btc.index, dd_btc, 0, alpha=0.25, color=GRAY,  label="BTC Buy & Hold")
    ax.plot(dd_ew, color=DGRAY, linewidth=1.2, linestyle=":", alpha=0.75,
            label="Equal-Weight 10-Crypto")
    ax.set_ylabel("回撤（%）", color=TEXT, fontsize=10)
    ax.set_title("回撤对比  /  Drawdown Comparison", color=TEXT, fontsize=11, pad=6)
    ax.legend(fontsize=9.5, loc="lower left", facecolor="#152030",
              labelcolor=TEXT, framealpha=0.85, edgecolor=GRID)
    ax.grid(True, alpha=0.18, color=GRID)
    shade_bears(ax, btc_bear_mask)

    # ── Panel 3: 滚动 γ ───────────────────────────────────────────────────────
    ax = axes[2]
    ax.plot(gamma_series, color="#F87171", linewidth=1.5, label="avg γ  (tail shape)")
    ax.axhline(0, color=TEXT, linewidth=0.7, linestyle="--", alpha=0.4)
    ax.fill_between(gamma_series.index, gamma_series, 0,
                    where=gamma_series > 0, alpha=0.22, color="#F87171")
    ax.set_ylabel("尾部形态参数 γ", color=TEXT, fontsize=10)
    ax.set_title("尾部风险雷达  /  Rolling Tail Risk Signal  (γ > 0 = fat tail rising)",
                 color=TEXT, fontsize=11, pad=6)
    ax.legend(fontsize=9.5, loc="upper left", facecolor="#152030",
              labelcolor=TEXT, framealpha=0.85, edgecolor=GRID)
    ax.grid(True, alpha=0.18, color=GRID)
    shade_bears(ax, btc_bear_mask)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # ── 底部注释（机械定义说明） ─────────────────────────────────────────────
    fig.text(
        0.5, 0.005,
        "Red shading = Bear regime defined mechanically: "
        "BTC drawdown > 40% from rolling 180-day high  |  No manual period selection",
        ha="center", va="bottom", fontsize=8.5, color="#64748B",
        style="italic"
    )

    plt.savefig("defensive_strategy.png", dpi=150, bbox_inches="tight",
                facecolor=BG)
    print("\n✓ 图表已保存 → defensive_strategy.png")

    # ── 打印 Stress vs Normal 统计（供 Slide 9 参考） ─────────────────────────
    stress = btc_bear_mask.reindex(strat_ensemble.index).fillna(False)
    normal = ~stress

    def period_stats(rets, mask):
        r = rets[mask].dropna()
        if len(r) == 0:
            return dict(ann_ret=0, max_dd=0)
        cum = (1 + r).cumprod()
        dd = (cum - cum.cummax()) / cum.cummax()
        return dict(
            ann_ret=r.mean() * 365,
            max_dd=dd.min() * 100
        )

    print("\n── Stress vs Normal Regime 统计 ────────────────────────────────")
    print(f"{'':30s}  {'熊市压力期':>12}  {'正常市场':>12}")
    for label, rets in [("EVA Strategy", strat_ensemble),
                         ("BTC Buy & Hold", btc_rets)]:
        s = period_stats(rets, stress)
        n = period_stats(rets, normal)
        print(f"  {label:<28}  "
              f"年化{s['ann_ret']:>+6.1%} / MaxDD{s['max_dd']:>6.1f}%   "
              f"年化{n['ann_ret']:>+6.1%} / MaxDD{n['max_dd']:>6.1f}%")
    print("────────────────────────────────────────────────────────────────")
