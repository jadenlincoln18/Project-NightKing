"""Black-76 for options on futures: price, vega, and implied-vol inversion.

Vectorised over numpy arrays. d1 has no r term (futures are martingales under Q).
Inversion is Newton with a bisection fallback; prices at or below the tick floor
or above the no-arb cap return NaN rather than a number that looks like a vol.
"""

from __future__ import annotations

import numpy as np
from scipy.special import ndtr

SQRT_2PI = float(np.sqrt(2.0 * np.pi))


def _phi(x):
    return np.exp(-0.5 * x * x) / SQRT_2PI


def price(F, K, T, sigma, D=1.0, right="C"):
    """Undiscounted-then-discounted Black-76 price. `right` is 'C', 'P', or an array of them."""
    F = np.asarray(F, dtype=float)
    K = np.asarray(K, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    sT = np.maximum(sigma, 1e-12) * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sT * sT) / sT
    d2 = d1 - sT
    call = D * (F * ndtr(d1) - K * ndtr(d2))
    if isinstance(right, str):
        if right == "C":
            return call
        return call - D * (F - K)
    is_call = np.asarray(right) == "C"
    return np.where(is_call, call, call - D * (F - K))


def vega(F, K, T, sigma, D=1.0):
    sT = np.maximum(np.asarray(sigma, dtype=float), 1e-12) * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sT * sT) / sT
    return D * F * _phi(d1) * np.sqrt(T)


def implied_vol(C, F, K, T, D=1.0, right="C", tol=1e-10, max_iter=60):
    """Invert to sigma. Returns NaN where the price is outside (intrinsic, cap)."""
    C = np.atleast_1d(np.asarray(C, dtype=float))
    K = np.atleast_1d(np.asarray(K, dtype=float)) * np.ones_like(C)
    # F and T may be per-quote arrays (quotes taken at different instants, synth/sync.py)
    F = np.atleast_1d(np.asarray(F, dtype=float)) * np.ones_like(C)
    T = np.atleast_1d(np.asarray(T, dtype=float)) * np.ones_like(C)
    right_arr = np.atleast_1d(np.asarray(right)) if not isinstance(right, str) else np.full(C.shape, right)
    is_call = right_arr == "C"
    # work in calls via parity: C = P + D(F - K)
    Cc = np.where(is_call, C, C + D * (F - K))
    intrinsic = D * np.maximum(F - K, 0.0)
    cap = D * F
    ok = (Cc > intrinsic + 1e-12) & (Cc < cap - 1e-12) & np.isfinite(Cc) & (T > 0)
    out = np.full(C.shape, np.nan)
    if not ok.any():
        return out if out.shape != () else float(out)
    Kk, Ck, F, T = K[ok], Cc[ok], F[ok], T[ok]
    lo = np.full(Kk.shape, 1e-6)
    hi = np.full(Kk.shape, 20.0)
    # bisection to bracket, then Newton polish
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        pm = price(F, Kk, T, mid, D, "C")
        above = pm > Ck
        hi = np.where(above, mid, hi)
        lo = np.where(above, lo, mid)
        if np.max(hi - lo) < 1e-6:
            break
    sig = 0.5 * (lo + hi)
    for _ in range(8):
        pm = price(F, Kk, T, sig, D, "C")
        v = vega(F, Kk, T, sig, D)
        step = np.where(v > 1e-14, (pm - Ck) / np.maximum(v, 1e-14), 0.0)
        new = sig - step
        new = np.where((new > 1e-6) & (new < 20.0), new, sig)
        if np.max(np.abs(new - sig)) < tol:
            sig = new
            break
        sig = new
    out[ok] = sig
    return out if out.shape != () else float(out)
