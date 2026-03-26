"""
Extreme Value Analysis - Tail Risk Alpha Strategy
Based on: "Extreme Value Analysis for Finite, Multivariate and Correlated Systems
           with Finance as an Example" (Köhler, Heckens, Guhr, 2026)

Core idea:
  1. Decompose crypto returns into uncorrelated market/sector modes via PCA
  2. Measure how "dangerous" each mode is using Peaks-Over-Threshold (GPD tail shape γ)
  3. Rank assets by their exposure to the most dangerous modes
  4. Long assets with low tail-risk exposure, short assets with high exposure
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Optional, Sequence
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────
# 1. DATA
# ─────────────────────────────────────────────────────────────

def load_prices(path: str) -> pd.DataFrame:
    """Load parquet, return wide DataFrame: index=date, columns=ticker."""
    df = pd.read_parquet(path)
    prices = df.pivot(index="time", columns="ticker", values="close").sort_index()
    return prices


# ─────────────────────────────────────────────────────────────
# 2. GPD TAIL FITTING
# ─────────────────────────────────────────────────────────────

def fit_gpd(exceedances: np.ndarray) -> dict:
    """
    Fit Generalised Pareto Distribution to exceedances via MLE.
    Returns fit diagnostics including tail shape γ.
    γ > 0  → Fréchet domain (heavy tail, power law)
    γ = 0  → Gumbel domain  (exponential tail)
    γ < 0  → Weibull domain (bounded tail)
    """
    exceedances = np.asarray(exceedances, dtype=float)
    n = len(exceedances)
    if n < 3:
        return {
            "success": False,
            "gamma": np.nan,
            "sigma": np.nan,
            "n_exceed": n,
            "nll": np.nan,
        }

    def neg_log_likelihood(params):
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

    # Moment-based initial guess
    m1 = np.mean(exceedances)
    m2 = np.mean(exceedances ** 2)
    gamma0 = 0.5 * (1.0 - m1 ** 2 / (m2 - m1 ** 2)) if m2 > m1 ** 2 else 0.1
    gamma0 = np.clip(gamma0, -0.4, 1.5)
    sigma0 = max(m1 * (1.0 - gamma0), 1e-8)

    result = minimize(
        neg_log_likelihood,
        x0=[gamma0, sigma0],
        bounds=[(-0.49, 2.0), (1e-8, None)],
        method="L-BFGS-B",
    )

    if not result.success:
        return {
            "success": False,
            "gamma": np.nan,
            "sigma": np.nan,
            "n_exceed": n,
            "nll": np.nan,
        }

    return {
        "success": True,
        "gamma": float(result.x[0]),
        "sigma": float(result.x[1]),
        "n_exceed": n,
        "nll": float(result.fun),
    }


def gpd_quantile(probabilities: np.ndarray, gamma: float, sigma: float) -> np.ndarray:
    """Quantile function of the GPD for probabilities in (0, 1)."""
    probabilities = np.clip(np.asarray(probabilities, dtype=float), 1e-8, 1 - 1e-8)
    if abs(gamma) < 1e-8:
        return -sigma * np.log1p(-probabilities)
    return sigma / gamma * ((1.0 - probabilities) ** (-gamma) - 1.0)


def gpd_nrmsd(exceedances: np.ndarray, gamma: float, sigma: float) -> float:
    """NRMSD of a GPD fit using theoretical vs empirical quantiles."""
    x = np.sort(np.asarray(exceedances, dtype=float))
    if len(x) < 3:
        return np.inf
    span = x[-1] - x[0]
    if span < 1e-12:
        return 0.0
    probs = (np.arange(1, len(x) + 1) - 0.5) / len(x)
    theo = gpd_quantile(probs, gamma, sigma)
    return float(np.sqrt(np.mean((theo - x) ** 2)) / span)


def select_tail_fit(
    tail_samples: np.ndarray,
    q_grid: Sequence[float],
    min_exceed: int,
) -> dict:
    """Search candidate thresholds and pick the most stable good fit."""
    tail_samples = np.asarray(tail_samples, dtype=float)
    if len(tail_samples) < min_exceed:
        return {
            "success": False,
            "gamma": 0.0,
            "sigma": np.nan,
            "threshold": np.nan,
            "q": np.nan,
            "nrmsd": np.inf,
            "n_exceed": 0,
        }

    candidates = []
    for q in q_grid:
        threshold = np.quantile(tail_samples, q)
        exceedances = tail_samples[tail_samples > threshold] - threshold
        if len(exceedances) < min_exceed:
            continue
        fit = fit_gpd(exceedances)
        if not fit["success"]:
            continue
        nrmsd = gpd_nrmsd(exceedances, fit["gamma"], fit["sigma"])
        candidate = {
            "success": True,
            "gamma": float(fit["gamma"]),
            "sigma": float(fit["sigma"]),
            "threshold": float(threshold),
            "q": float(q),
            "nrmsd": float(nrmsd),
            "n_exceed": int(fit["n_exceed"]),
        }
        candidates.append(candidate)

    if not candidates:
        return {
            "success": False,
            "gamma": 0.0,
            "sigma": np.nan,
            "threshold": np.nan,
            "q": np.nan,
            "nrmsd": np.inf,
            "n_exceed": 0,
        }

    median_gamma = float(np.median([c["gamma"] for c in candidates]))
    for candidate in candidates:
        stability_penalty = abs(candidate["gamma"] - median_gamma)
        candidate["selection_score"] = candidate["nrmsd"] + 0.25 * stability_penalty

    return min(
        candidates,
        key=lambda c: (c["selection_score"], c["nrmsd"], -c["n_exceed"]),
    )


def choose_mode_count(
    eigvals: np.ndarray,
    variance_target: float = 0.80,
    max_modes: Optional[int] = None,
    min_modes: int = 2,
) -> int:
    """Choose the number of PCA modes from explained variance."""
    eigvals = np.maximum(np.asarray(eigvals, dtype=float), 0.0)
    if eigvals.sum() < 1e-12:
        return min_modes
    if max_modes is None:
        max_modes = len(eigvals)
    max_modes = max(1, min(int(max_modes), len(eigvals)))
    min_modes = max(1, min(int(min_modes), max_modes))
    cum_ratio = np.cumsum(eigvals) / eigvals.sum()
    k = int(np.searchsorted(cum_ratio, variance_target, side="left") + 1)
    return max(min_modes, min(k, max_modes))


def signal_to_weights(
    signals: np.ndarray,
    gross_leverage: float = 1.0,
    max_asset_weight: float = 0.30,
) -> np.ndarray:
    """Convert cross-sectional signals into net-neutral continuous weights."""
    centered = np.asarray(signals, dtype=float) - np.mean(signals)
    gross = np.abs(centered).sum()
    if gross < 1e-12:
        return np.zeros_like(centered)

    weights = centered / gross * gross_leverage
    if max_asset_weight is not None:
        weights = np.clip(weights, -max_asset_weight, max_asset_weight)
        weights = weights - weights.mean()
        gross = np.abs(weights).sum()
        if gross < 1e-12:
            return np.zeros_like(centered)
        weights = weights / gross * gross_leverage
    return weights


# ─────────────────────────────────────────────────────────────
# 3. SIGNAL FOR ONE WINDOW
# ─────────────────────────────────────────────────────────────

def compute_tail_risk_signal(
    returns_window: np.ndarray,   # shape (N_assets, L_days)
    max_modes: int = 4,
    variance_target: float = 0.80,
    q_grid: Sequence[float] = (0.90, 0.95, 0.975),
    min_exceed: int = 12,
    downside_weight: float = 0.70,
    upside_weight: float = 0.30,
    risk_mode: str = "dual",
) -> tuple[np.ndarray, dict]:
    """
    Returns cross-sectional signal for N assets.
    Positive signal → safer (lower tail-risk exposure) → long candidate
    Negative signal → more dangerous (higher tail-risk exposure) → short candidate
    """
    N, L = returns_window.shape

    # --- Step 1: Normalize each asset to zero mean, unit variance ---
    mu = returns_window.mean(axis=1, keepdims=True)
    sigma = returns_window.std(axis=1, keepdims=True, ddof=1)
    sigma[sigma < 1e-10] = 1e-10
    M = (returns_window - mu) / sigma  # (N, L)

    # --- Step 2: Sample correlation matrix ---
    C = (1.0 / (L - 1)) * (M @ M.T)
    C = (C + C.T) / 2.0  # enforce symmetry

    # --- Step 3: Eigendecomposition, sort descending ---
    eigvals, eigvecs = np.linalg.eigh(C)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]  # columns = eigenvectors

    K = choose_mode_count(
        eigvals,
        variance_target=variance_target,
        max_modes=min(max_modes, N),
    )
    eigvals_k = np.maximum(eigvals[:K], 1e-10)
    eigvecs_k = eigvecs[:, :K]  # (N, K)

    # --- Step 4: Rotate returns into uncorrelated mode space ---
    # R[k, t] is the return of mode k on day t, variance-normalised
    Lambda_inv_sqrt = np.diag(1.0 / np.sqrt(eigvals_k))
    R = Lambda_inv_sqrt @ (eigvecs_k.T @ M)  # (K, L)

    # --- Step 5: Fit GPD to both tails of each mode ---
    mode_risk = np.zeros(K)
    mode_diag = []
    for k in range(K):
        pos = R[k][R[k] > 0]
        neg = -R[k][R[k] < 0]

        pos_fit = select_tail_fit(pos, q_grid=q_grid, min_exceed=min_exceed)
        neg_fit = select_tail_fit(neg, q_grid=q_grid, min_exceed=min_exceed)

        pos_gamma = max(pos_fit["gamma"], 0.0) if pos_fit["success"] else 0.0
        neg_gamma = max(neg_fit["gamma"], 0.0) if neg_fit["success"] else 0.0
        pos_quality = 1.0 / (1.0 + pos_fit["nrmsd"]) if pos_fit["success"] else 0.0
        neg_quality = 1.0 / (1.0 + neg_fit["nrmsd"]) if neg_fit["success"] else 0.0

        upside_risk = pos_gamma * pos_quality
        downside_risk = neg_gamma * neg_quality
        if risk_mode == "pos":
            mode_risk[k] = upside_risk
        elif risk_mode == "neg":
            mode_risk[k] = downside_risk
        elif risk_mode == "max":
            mode_risk[k] = max(upside_risk, downside_risk)
        elif risk_mode == "dual":
            mode_risk[k] = upside_weight * upside_risk + downside_weight * downside_risk
        else:
            raise ValueError(f"Unknown risk_mode: {risk_mode}")

        mode_diag.append(
            {
                "mode": k + 1,
                "eigval": float(eigvals_k[k]),
                "gamma_pos": pos_gamma,
                "gamma_neg": neg_gamma,
                "nrmsd_pos": float(pos_fit["nrmsd"]),
                "nrmsd_neg": float(neg_fit["nrmsd"]),
                "q_pos": float(pos_fit["q"]),
                "q_neg": float(neg_fit["q"]),
                "n_pos": int(pos_fit["n_exceed"]),
                "n_neg": int(neg_fit["n_exceed"]),
                "mode_risk": float(mode_risk[k]),
            }
        )

    # --- Step 6: Score each asset by its exposure to dangerous modes ---
    scores = np.abs(eigvecs_k) @ mode_risk  # (N,)

    # --- Step 7: Negate z-score (low score = safe = positive signal) ---
    std_s = scores.std(ddof=1)
    if std_s < 1e-10:
        signals = np.zeros(N)
    else:
        signals = -(scores - scores.mean()) / std_s

    diagnostics = {
        "active_modes": K,
        "explained_variance": float(eigvals_k.sum() / np.maximum(eigvals.sum(), 1e-10)),
        "avg_mode_risk": float(mode_risk.mean()) if K > 0 else 0.0,
        "avg_gamma_pos": float(np.mean([d["gamma_pos"] for d in mode_diag])) if mode_diag else 0.0,
        "avg_gamma_neg": float(np.mean([d["gamma_neg"] for d in mode_diag])) if mode_diag else 0.0,
        "signal_dispersion": float(std_s) if std_s >= 1e-10 else 0.0,
        "mode_details": mode_diag,
    }
    return signals, diagnostics


# ─────────────────────────────────────────────────────────────
# 4. BACKTEST ENGINE
# ─────────────────────────────────────────────────────────────

def run_backtest(
    prices: pd.DataFrame,
    L: int = 504,          # lookback window (days)
    max_modes: int = 2,    # cap on number of PCA modes
    variance_target: float = 0.80,
    q_grid: Sequence[float] = (0.90,),
    rebalance_freq: int = 21,  # days between rebalancing
    min_exceed: int = 12,
    cost_bps: float = 10,  # round-trip transaction cost in bps
    gross_leverage: float = 1.0,
    max_asset_weight: float = 0.30,
    signal_direction: int = -1,
    risk_mode: str = "pos",
    weighting_style: str = "top_n",
    top_n: int = 4,
) -> pd.DataFrame:
    """
    Trade the EVT signal with configurable portfolio construction.
    signal_direction = +1  → long safer assets, short riskier assets
    signal_direction = -1  → long riskier assets, short safer assets
    risk_mode controls how positive/negative tails are aggregated into mode risk.
    weighting_style can be "continuous" or "top_n".
    Rebalances every rebalance_freq days.
    Returns daily returns and lightweight diagnostics.
    """
    one_way_cost = cost_bps / 2 / 10_000  # bps → decimal, one-way

    log_ret = np.log(prices / prices.shift(1)).dropna()
    dates = log_ret.index
    ret_arr = log_ret.values  # (T, N)
    N = ret_arr.shape[1]
    T = len(dates)

    strategy_rets = []
    bench_rets = []
    turnover_hist = []
    active_modes_hist = []
    explained_var_hist = []
    avg_mode_risk_hist = []
    avg_gamma_pos_hist = []
    avg_gamma_neg_hist = []
    signal_dispersion_hist = []
    weights = np.zeros(N)
    latest_diag = {
        "active_modes": 0,
        "explained_variance": 0.0,
        "avg_mode_risk": 0.0,
        "avg_gamma_pos": 0.0,
        "avg_gamma_neg": 0.0,
        "signal_dispersion": 0.0,
    }

    for t in range(L, T):
        window = ret_arr[t - L : t].T  # (N, L)

        # Recompute signal on rebalance days
        if (t - L) % rebalance_freq == 0:
            signals, latest_diag = compute_tail_risk_signal(
                window,
                max_modes=max_modes,
                variance_target=variance_target,
                q_grid=q_grid,
                min_exceed=min_exceed,
                risk_mode=risk_mode,
            )
            adjusted_signals = signal_direction * signals
            if weighting_style == "continuous":
                new_weights = signal_to_weights(
                    adjusted_signals,
                    gross_leverage=gross_leverage,
                    max_asset_weight=max_asset_weight,
                )
            elif weighting_style == "top_n":
                ranked = np.argsort(adjusted_signals)[::-1]
                n_select = min(top_n, N // 2)
                new_weights = np.zeros(N)
                new_weights[ranked[:n_select]] = 1.0 / n_select
                new_weights[ranked[-n_select:]] = -1.0 / n_select
            else:
                raise ValueError(f"Unknown weighting_style: {weighting_style}")

            turnover = np.abs(new_weights - weights).sum()
            tc = turnover * one_way_cost
            weights = new_weights
        else:
            turnover = 0.0
            tc = 0.0

        daily = ret_arr[t]
        strategy_rets.append(np.dot(weights, daily) - tc)
        bench_rets.append(daily.mean())  # equal-weight benchmark
        turnover_hist.append(turnover)
        active_modes_hist.append(latest_diag["active_modes"])
        explained_var_hist.append(latest_diag["explained_variance"])
        avg_mode_risk_hist.append(latest_diag["avg_mode_risk"])
        avg_gamma_pos_hist.append(latest_diag["avg_gamma_pos"])
        avg_gamma_neg_hist.append(latest_diag["avg_gamma_neg"])
        signal_dispersion_hist.append(latest_diag["signal_dispersion"])

    result_dates = dates[L:]
    return pd.DataFrame(
        {
            "strategy": strategy_rets,
            "benchmark": bench_rets,
            "turnover": turnover_hist,
            "active_modes": active_modes_hist,
            "explained_variance": explained_var_hist,
            "avg_mode_risk": avg_mode_risk_hist,
            "avg_gamma_pos": avg_gamma_pos_hist,
            "avg_gamma_neg": avg_gamma_neg_hist,
            "signal_dispersion": signal_dispersion_hist,
        },
        index=result_dates,
    )


# ─────────────────────────────────────────────────────────────
# 5. PERFORMANCE METRICS
# ─────────────────────────────────────────────────────────────

def performance_metrics(rets: pd.Series, label: str = "") -> dict:
    """Annualised metrics (crypto = 365 days/year)."""
    r = rets.dropna()
    ann = 365
    ann_ret = r.mean() * ann
    ann_vol = r.std() * np.sqrt(ann)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0

    cum = (1 + r).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax()
    max_dd = dd.min()

    # Calmar ratio
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0.0

    # Win rate
    win_rate = (r > 0).mean()

    return {
        "Label": label,
        "Ann. Return": f"{ann_ret:+.1%}",
        "Ann. Volatility": f"{ann_vol:.1%}",
        "Sharpe Ratio": f"{sharpe:.2f}",
        "Max Drawdown": f"{max_dd:.1%}",
        "Calmar Ratio": f"{calmar:.2f}",
        "Win Rate": f"{win_rate:.1%}",
    }


# ─────────────────────────────────────────────────────────────
# 6. PLOTS
# ─────────────────────────────────────────────────────────────

def plot_results(results: pd.DataFrame, save_path: str = "backtest_results.png"):
    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    fig.suptitle(
        "EVA Tail Risk Strategy — Crypto Portfolio Backtest",
        fontsize=14, fontweight="bold", y=0.98,
    )

    cum_s = (1 + results["strategy"]).cumprod()
    cum_b = (1 + results["benchmark"]).cumprod()

    # Panel 1: Cumulative returns
    axes[0].plot(cum_s, label="EVA Strategy", color="steelblue", linewidth=1.8)
    axes[0].plot(cum_b, label="Equal-Weight Benchmark", color="dimgray",
                 linewidth=1.5, linestyle="--", alpha=0.8)
    axes[0].set_ylabel("Cumulative Return (log scale)")
    axes[0].set_yscale("log")
    axes[0].legend(loc="upper left", fontsize=9)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title("Cumulative Performance", fontsize=11)

    # Panel 2: Rolling Sharpe (90-day)
    roll_sharpe = (
        results["strategy"].rolling(90).mean()
        / results["strategy"].rolling(90).std()
        * np.sqrt(365)
    )
    axes[1].plot(roll_sharpe, color="steelblue", linewidth=1.2)
    axes[1].axhline(0, color="black", linewidth=0.8, linestyle="--")
    axes[1].set_ylabel("Rolling Sharpe (90d)")
    axes[1].grid(True, alpha=0.3)
    axes[1].set_title("Rolling 90-Day Sharpe Ratio", fontsize=11)

    # Panel 3: Drawdown
    dd_s = (cum_s - cum_s.cummax()) / cum_s.cummax()
    dd_b = (cum_b - cum_b.cummax()) / cum_b.cummax()
    axes[2].fill_between(dd_s.index, dd_s * 100, 0,
                          color="steelblue", alpha=0.5, label="Strategy")
    axes[2].fill_between(dd_b.index, dd_b * 100, 0,
                          color="dimgray", alpha=0.3, label="Benchmark")
    axes[2].set_ylabel("Drawdown (%)")
    axes[2].legend(loc="lower left", fontsize=9)
    axes[2].grid(True, alpha=0.3)
    axes[2].set_title("Drawdown", fontsize=11)
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Plot saved → {save_path}")


# ─────────────────────────────────────────────────────────────
# 7. MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    DATA_PATH = "crypto_10_data.parquet"

    print("=" * 55)
    print("  EVA Tail Risk Alpha — Crypto Backtest")
    print("=" * 55)

    print("\n[1/3] Loading data ...")
    prices = load_prices(DATA_PATH)
    print(f"      {prices.shape[1]} assets  |  "
          f"{prices.index[0].date()} → {prices.index[-1].date()}  |  "
          f"{len(prices)} days")

    print("\n[2/3] Running backtest (this may take a few minutes) ...")
    results = run_backtest(
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
    print(f"      Backtest period: {results.index[0].date()} → {results.index[-1].date()}")
    print("      Signal direction: long higher tail-risk exposure, short lower tail-risk exposure")
    print("      Signal construction: positive-tail mode risk with top-4 long/short portfolio")
    print(
        "      Avg active modes: "
        f"{results['active_modes'].mean():.2f}  |  "
        f"Avg explained variance: {results['explained_variance'].mean():.1%}"
    )
    print(
        "      Avg rebalance turnover: "
        f"{results['turnover'].mean():.2%}  |  "
        f"Avg downside gamma: {results['avg_gamma_neg'].mean():.3f}"
    )

    print("\n[3/3] Results")
    print("-" * 55)
    for m in [
        performance_metrics(results["strategy"], "EVA Strategy"),
        performance_metrics(results["benchmark"], "Equal-Weight Benchmark"),
    ]:
        print(f"\n  {m.pop('Label')}")
        for k, v in m.items():
            print(f"    {k:<20} {v}")

    print("\n" + "-" * 55)
    plot_results(results)
    print("\nDone.")
