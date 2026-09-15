"""Stage 6: forward and discount factor from put-call parity, by regression.

C - P = D*F0 - D*K, linear in K. Regress y = C - P on (K - Kbar): slope = -D,
intercept = D*(F0 - Kbar). Residuals beyond `outlier_z` standard errors are flagged
and dropped once (the free bad-quote detector). The standard error of F0 is the
tolerance the Stage 14 martingale constraint uses.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np


def parity_forward(K: np.ndarray, call_mid: np.ndarray, put_mid: np.ndarray, weights: Optional[np.ndarray] = None,
                   outlier_z: float = 4.0, fixed_D: Optional[float] = None) -> Dict[str, object]:
    K = np.asarray(K, float)
    y = np.asarray(call_mid, float) - np.asarray(put_mid, float)
    w = np.ones_like(K) if weights is None else np.asarray(weights, float)
    keep = np.isfinite(y) & np.isfinite(K) & (w > 0)
    flagged = np.zeros(K.shape, bool)
    for _pass in range(2):
        Kk, yk, wk = K[keep], y[keep], w[keep]
        if Kk.size < 2:
            return {"F0": np.nan, "D": np.nan, "se_F0": np.nan, "n_pairs": int(Kk.size), "flagged": flagged,
                    "resid": np.full(K.shape, np.nan), "ok": False}
        Kbar = np.average(Kk, weights=wk)
        xc = Kk - Kbar
        if fixed_D is None:
            A = np.vstack([np.ones_like(xc), xc]).T
            W = np.sqrt(wk)
            coef, *_ = np.linalg.lstsq(A * W[:, None], yk * W, rcond=None)
            a, b = coef
            D = float(np.clip(-b, 0.9, 1.0))
            resid = yk - (a + b * xc)
            dof = max(Kk.size - 2, 1)
        else:
            D = float(fixed_D)
            a = float(np.average(yk + D * xc, weights=wk))
            resid = yk - (a - D * xc)
            dof = max(Kk.size - 1, 1)
        s2 = float(np.sum(wk * resid ** 2) / dof)
        se_a = float(np.sqrt(s2 / np.sum(wk)))
        # outlier scale from the MAD of the standardised residuals: one bad quote must not
        # inflate the very scale it is judged against
        zs = resid * np.sqrt(np.maximum(wk, 1e-12))
        mad = 1.4826 * float(np.median(np.abs(zs - np.median(zs))))
        z = zs / max(mad, 1e-9)
        new_flags = np.abs(z) > outlier_z
        if _pass == 0 and new_flags.any() and Kk.size - new_flags.sum() >= 3:
            idx = np.where(keep)[0][new_flags]
            flagged[idx] = True
            keep[idx] = False
            continue
        break
    F0 = float(Kbar + a / D)
    full_resid = np.full(K.shape, np.nan)
    full_resid[keep] = resid
    return {"F0": F0, "D": D, "se_F0": float(se_a / D), "n_pairs": int(keep.sum()), "flagged": flagged,
            "resid": full_resid, "resid_sd": float(np.sqrt(s2)), "ok": True}
