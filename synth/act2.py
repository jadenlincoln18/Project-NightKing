"""Act II: OTM selection (Stage 8) -> Black-76 IV (Stage 7) -> weighted SVI fit (Stage 9)
-> arbitrage check + fine even grid + second difference (Stage 10) -> bracket probabilities.

Weights are inverse-variance in total variance: sd(w_i) ~ 2*sigma_i*T*hs_i/vega_i.

Raw SVI: w(k) = a + b*(rho*(k - m) + sqrt((k - m)^2 + s^2)).
Bounds enforced in the optimiser: b >= 0, |rho| < 1, s > 0, a + b*s*sqrt(1 - rho^2) >= 0
(w > 0), and Lee's moment bound on the wing slopes b*(1 + |rho|) <= 2. NOTE: the
writeup quotes the bound as 4/sqrt(T) and says it makes a negative density impossible.
Neither is right for raw SVI in total variance: Lee's bound is 2, and Gatheral-Jacquier
(2014) show the slope bound alone does not exclude butterfly arbitrage - their g(k)
function must be checked. We enforce the bound, penalise g(k) < 0 during the fit, and
report min g / min density afterwards. Stage 10 is therefore "enforce, then verify".
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
from scipy.optimize import minimize

from . import black76

FINE_STEP = 0.01  # dollars; even in K so the second difference has no off-centre bias


def svi_w(k, a, b, rho, m, s):
    d = k - m
    return a + b * (rho * d + np.sqrt(d * d + s * s))


def svi_g(k, a, b, rho, m, s):
    """Gatheral-Jacquier g(k); density >= 0 iff g >= 0 (for w > 0)."""
    d = k - m
    R = np.sqrt(d * d + s * s)
    w = a + b * (rho * d + R)
    w1 = b * (rho + d / R)
    w2 = b * s * s / (R ** 3)
    w = np.maximum(w, 1e-12)
    return (1.0 - k * w1 / (2.0 * w)) ** 2 - 0.25 * w1 * w1 * (1.0 / w + 0.25) + 0.5 * w2


def fit_svi(k: np.ndarray, w_obs: np.ndarray, weights: np.ndarray, T: float, k_check: Optional[np.ndarray] = None,
            n_starts: int = 6, rng: Optional[np.random.Generator] = None) -> Dict[str, object]:
    rng = rng or np.random.default_rng(0)
    k = np.asarray(k, float)
    w_obs = np.asarray(w_obs, float)
    wt = np.asarray(weights, float)
    wt = wt / wt.mean()
    kc = k_check if k_check is not None else np.linspace(k.min() - 0.3, k.max() + 0.3, 400)
    scale = float(np.median(w_obs))

    def unpack(p):
        a = p[0] * scale
        rho = np.tanh(p[2])
        b = (2.0 / (1.0 + abs(rho))) / (1.0 + np.exp(-p[1]))  # 0 < b < 2/(1+|rho|): Lee's bound
        m = p[3]
        s = np.exp(p[4])
        return a, b, rho, m, s

    def loss(p):
        with np.errstate(all="ignore"):  # L-BFGS probes extreme parameters; NaN losses are simply rejected
            return _loss(p)

    def _loss(p):
        a, b, rho, m, s = unpack(p)
        if not np.all(np.isfinite([a, b, rho, m, s])):
            return 1e30
        pred = svi_w(k, a, b, rho, m, s)
        L = float(np.sum(wt * (pred - w_obs) ** 2)) / scale ** 2
        # positivity of w and of the g function (butterfly) as smooth penalties
        wmin = a + b * s * np.sqrt(1.0 - rho * rho)
        L += 1e3 * min(wmin / scale, 0.0) ** 2
        g = svi_g(kc, a, b, rho, m, s)
        L += 1e2 * float(np.sum(np.minimum(g, 0.0) ** 2))
        return L

    best = None
    for i in range(n_starts):
        p0 = np.array([0.8 + 0.4 * rng.uniform(), rng.normal(0, 1), rng.normal(0, 0.5), rng.normal(0, 0.05),
                       np.log(0.05 + 0.1 * rng.uniform())])
        if i == 0:
            p0 = np.array([0.9, 0.0, 0.0, 0.0, np.log(0.1)])
        try:
            res = minimize(loss, p0, method="L-BFGS-B")
        except Exception:
            continue
        if best is None or res.fun < best.fun:
            best = res
    a, b, rho, m, s = unpack(best.x)
    g = svi_g(kc, a, b, rho, m, s)
    return {"a": a, "b": b, "rho": rho, "m": m, "s": s, "loss": float(best.fun), "min_g": float(g.min()),
            "lee_slope": float(b * (1 + abs(rho))), "converged": bool(best.success)}


def run(K: np.ndarray, right: np.ndarray, mid: np.ndarray, hs: np.ndarray, F0: float, D: float, T: float,
        edges: np.ndarray, s_eval: Optional[np.ndarray] = None, rng: Optional[np.random.Generator] = None) -> Dict[str, object]:
    """Full Act II on an OTM chain. Returns density on a fine even grid, bracket probs, checks."""
    K = np.asarray(K, float)
    mid = np.asarray(mid, float)
    hs = np.asarray(hs, float)
    right = np.asarray(right)
    out: Dict[str, object] = {"ok": False}
    # Stage 7: IV of OTM mids; drop strikes whose mid cannot be inverted (below the floor)
    iv = black76.implied_vol(np.maximum(mid, 0.0), F0, K, T, D, right)
    good = np.isfinite(iv) & (iv > 0.01) & (iv < 5.0)
    out["n_used"] = int(good.sum())
    out["n_dropped"] = int((~good).sum())
    if good.sum() < 5:
        out["reason"] = "fewer than 5 invertible strikes"
        return out
    Kg, ivg, hsg = K[good], iv[good], hs[good]
    k = np.log(Kg / F0)
    vega = black76.vega(F0, Kg, T, ivg, D)
    sd_iv = hsg / np.maximum(vega, 1e-9)
    sd_w = 2.0 * ivg * T * sd_iv
    weights = 1.0 / np.maximum(sd_w, 1e-12) ** 2
    weights = np.minimum(weights, np.percentile(weights, 99) * 1.0)  # one super-tight quote must not own the fit
    w_obs = ivg * ivg * T
    fit = fit_svi(k, w_obs, weights, T, rng=rng)
    out["svi"] = fit
    # Stage 10: reprice on a fine even grid in K, then second difference
    v0 = float(np.sqrt(max(svi_w(0.0, fit["a"], fit["b"], fit["rho"], fit["m"], fit["s"]), 1e-6)))
    s_lo = min(F0 * np.exp(-8 * v0 - 0.05), edges[0] - 5.0, Kg.min() - 5.0)
    s_hi = max(F0 * np.exp(8 * v0 + 0.05), edges[-1] + 5.0, Kg.max() + 5.0)
    s_lo = max(s_lo, 0.05 * F0)
    grid = np.arange(s_lo, s_hi + FINE_STEP, FINE_STEP)
    kk = np.log(grid / F0)
    w = svi_w(kk, fit["a"], fit["b"], fit["rho"], fit["m"], fit["s"])
    sig = np.sqrt(np.maximum(w, 1e-12) / T)
    C = black76.price(F0, grid, T, sig, D, "C")
    dC = np.gradient(C, FINE_STEP)  # central first difference
    surv = np.clip(-dC / D, 0.0, 1.0)  # Q(F_T > K) = -e^{rT} C'(K)
    f = np.gradient(dC, FINE_STEP) / D  # e^{rT} C''(K)
    out.update({"grid": grid, "density": f, "survival": surv, "F0": F0, "D": D,
                "min_density": float(f.min()), "mass": float(np.trapz(np.maximum(f, 0), grid)),
                "mean": float(np.trapz(grid * np.maximum(f, 0), grid))})
    cdf_e = 1.0 - np.interp(edges, grid, surv)
    out["bracket_probs"] = np.concatenate([[cdf_e[0]], np.diff(cdf_e), [1.0 - cdf_e[-1]]])
    if s_eval is not None:
        out["density_at"] = np.interp(s_eval, grid, f, left=0.0, right=0.0)
    # verification (Stage 10 as check): non-negativity, normalisation, Lee bound
    out["checks"] = {"density_nonneg": bool(f.min() > -1e-6), "normalised": bool(abs(out["mass"] - 1.0) < 0.01),
                     "min_g": fit["min_g"], "lee_slope_ok": bool(fit["lee_slope"] <= 2.0 + 1e-9)}
    out["ok"] = True
    return out
