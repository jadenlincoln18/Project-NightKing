"""Gate 4: is this chain internally consistent enough to trust its posterior?

Three signals, in order of standing.

1. Split-half consistency (the gate). Act III is fitted twice, to the odd-indexed and to
   the even-indexed strikes of the OTM chain (interleaved, so both halves span the whole
   strike range), with the same forward, grid, prior and sampler as the deliverable. The
   two posteriors are compared bracket by bracket over the Kalshi ladder:
       z_j = (m1_j - m2_j) / sqrt(v1_j + v2_j)
   with m, v the posterior mean and variance of bracket j in each half. The halves see
   disjoint quotes, so under a consistent chain m1 - m2 has variance v1 + v2 and z is a
   standard normal (up to the posteriors being non-Gaussian). The statistic is
   max_j |z_j| over the ladder; the cutoff is calibrated on synthetic well-specified chains
   (`python3 -m synth.realchain --calibrate`, stored in `synth/results_real/split_half_null.json`)
   and falls back to 3.0. Same machinery on both sides, so disagreement points at the data,
   not at one method's numerics - which is exactly what asynchronous quotes produce.
   What it cannot see: a smooth-prior bias that both halves share (the bimodal blind spot
   of FINDINGS_SYNTHETIC.md §7). That remains Act II's job below.

2. Leave-one-out predictive residuals (the localiser). Each strike is dropped in turn, the
   model is refitted without it (Laplace: MAP warm-started from the full fit + Gauss-Newton
   covariance - NUTS per strike would cost 25x the whole run), the dropped price is
   predicted, and the miss is standardised by sqrt(half-spread^2 + predictive variance):
       r_i = (mid_i - E[C_i | rest]) / sqrt(hs_i^2 + Var[C_i | rest]).
   |r_i| > 3 names the strike that the rest of the chain cannot explain. Reported per
   strike; the count and the worst strike are summarised.

3. Act II vs Act III (reported, not gating). max |Act II - Act III| over the ladder in
   cents, with the synthetic cutoff (FINDINGS_SYNTHETIC.md §11: p95 of well-specified
   chains with >= 12 strikes). Act II differentiates the fitted call curve and Act III
   integrates, so on a chain whose quotes disagree with each other the two diverge faster
   than either's own error; on the synthetic study it was nevertheless the only signal that
   fired on the bimodal truth, so it stays in the report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from . import act3

CUTOFF_CENTS = 2.5      # Act II vs Act III, see FINDINGS_SYNTHETIC.md §11
MIN_STRIKES_TRUSTED = 12
SPLIT_Z_CUTOFF_DEFAULT = 3.0
LOO_Z_CUTOFF = 3.0
NULL_PATH = Path(__file__).resolve().parent / "results_real" / "split_half_null.json"


def split_z_cutoff() -> float:
    """p95 of max|z| on synthetic well-specified chains, if the calibration has been run."""
    if NULL_PATH.exists():
        try:
            return float(json.load(open(NULL_PATH))["cutoff_p95"])
        except Exception:
            pass
    return SPLIT_Z_CUTOFF_DEFAULT


# --------------------------------------------------------------------------
# 1. split-half
# --------------------------------------------------------------------------

def _posterior_bracket(model: act3.Model, res: Dict[str, Any], edges: np.ndarray) -> Dict[str, Any]:
    summ = model.summarise(res["thetas"], edges)
    br = summ["bracket"]
    n_ch = res.get("n_chains", 1)
    chains_br = br.reshape(n_ch, -1, br.shape[1]) if n_ch > 1 else br[None]
    keep = chains_br.std(axis=(0, 1)) > 1e-12
    return {"mean": br.mean(axis=0), "var": br.var(axis=0, ddof=1), "q": np.percentile(br, [5, 50, 95], axis=0),
            "chi2_per_strike": float(summ["chi2"].mean() / len(model.K)), "rhat_max": res["rhat_max"], "ess_min": res["ess_min"],
            "divergences": res["divergences"], "n_strikes": int(len(model.K)),
            "bracket_rhat_max": float(act3.split_rhat(chains_br[:, :, keep]).max()) if (keep.any() and n_ch > 1) else 1.0,
            "seconds": res["seconds"]}


def split_half(K, right, mid, hs, F0: float, D: float, T: float, atm_sigma: float, se_F0: float, edges: np.ndarray,
               nuts: Dict[str, int], seed: int = 3, sampler: str = "nuts", cutoff: Optional[float] = None) -> Dict[str, Any]:
    K = np.asarray(K, float)
    right = np.asarray(right)
    mid = np.asarray(mid, float)
    hs = np.asarray(hs, float)
    order = np.argsort(K)
    halves = [order[0::2], order[1::2]]
    fits = []
    for h, idx in enumerate(halves):
        model = act3.Model(K[idx], right[idx], mid[idx], hs[idx], F0, D, T, atm_sigma, se_F0=se_F0, martingale=True)
        res = act3.sample(model, np.random.default_rng(seed + h), sampler=sampler, **nuts)
        fits.append(_posterior_bracket(model, res, edges))
    a, b = fits
    z = (a["mean"] - b["mean"]) / np.sqrt(a["var"] + b["var"] + 1e-12)
    diff_c = 100.0 * (a["mean"] - b["mean"])
    cut = split_z_cutoff() if cutoff is None else cutoff
    # brackets with no posterior mass in either half say nothing; ignore z where both sds < 1e-4
    live = np.sqrt(a["var"] + b["var"]) > 1e-4
    zmax = float(np.abs(z[live]).max()) if live.any() else 0.0
    return {"z": z, "diff_cents": diff_c, "max_abs_z": zmax, "max_abs_diff_cents": float(np.abs(diff_c).max()),
            "argmax_bracket": int(np.argmax(np.where(live, np.abs(z), -1.0))), "cutoff": cut, "fired": bool(zmax > cut),
            "halves": [{k: v for k, v in f.items() if k not in ("mean", "var")} | {"mean": f["mean"]} for f in fits],
            "n_per_half": [int(len(h)) for h in halves], "n_live_brackets": int(live.sum())}


# --------------------------------------------------------------------------
# 2. leave-one-out predictive
# --------------------------------------------------------------------------

def loo(K, right, mid, hs, F0: float, D: float, T: float, atm_sigma: float, se_F0: float,
        psi_warm: Optional[np.ndarray] = None, cutoff: float = LOO_Z_CUTOFF) -> Dict[str, Any]:
    """Laplace leave-one-out: for each strike, refit the MAP without it (warm start), predict its
    price with the Gauss-Newton posterior covariance, standardise the miss."""
    K = np.asarray(K, float)
    right = np.asarray(right)
    mid = np.asarray(mid, float)
    hs = np.asarray(hs, float)
    n = K.size
    full = act3.Model(K, right, mid, hs, F0, D, T, atm_sigma, se_F0=se_F0, martingale=True)
    psi0 = act3.map_estimate(full) if psi_warm is None else np.asarray(psi_warm, float)
    pred = np.empty(n)
    pred_sd = np.empty(n)
    for i in range(n):
        keep = np.ones(n, bool)
        keep[i] = False
        m = act3.Model(K[keep], right[keep], mid[keep], hs[keep], F0, D, T, atm_sigma, se_F0=se_F0, martingale=True)
        psi = act3.map_estimate(m, psi0=psi0, maxiter=500)
        H = m.gauss_newton(psi)
        H = 0.5 * (H + H.T) + 1e-8 * np.eye(m.dim)
        theta = m.QV @ psi
        p, _ = m.density(theta)
        pay = np.maximum(m.s - K[i], 0.0) if right[i] == "C" else np.maximum(K[i] - m.s, 0.0)
        g = D * pay
        Chat = float(g @ p)
        J_theta = (g * p) @ m.B - Chat * (p @ m.B)   # dChat/dtheta
        J = m.QV.T @ J_theta                          # dChat/dpsi
        try:
            var = float(J @ np.linalg.solve(H, J))
        except np.linalg.LinAlgError:
            var = 0.0
        pred[i] = Chat
        pred_sd[i] = np.sqrt(max(var, 0.0))
    r = (mid - pred) / np.sqrt(hs ** 2 + pred_sd ** 2)
    worst = int(np.argmax(np.abs(r)))
    return {"pred": pred, "pred_sd": pred_sd, "z": r, "max_abs_z": float(np.abs(r).max()), "worst_strike": float(K[worst]),
            "worst_right": str(right[worst]), "n_flagged": int((np.abs(r) > cutoff).sum()),
            "flagged_strikes": [float(k) for k in K[np.abs(r) > cutoff]], "rms_z": float(np.sqrt(np.mean(r ** 2))), "cutoff": cutoff}


# --------------------------------------------------------------------------
# 3. Act II vs Act III (reported)
# --------------------------------------------------------------------------

def disagreement_cents(act2_bracket: np.ndarray, act3_bracket_mean: np.ndarray) -> float:
    return float(100.0 * np.max(np.abs(np.asarray(act2_bracket) - np.asarray(act3_bracket_mean))))


def act2_signal(act2_bracket: Optional[np.ndarray], act3_bracket_mean: np.ndarray, n_strikes: int,
                cutoff: float = CUTOFF_CENTS) -> Dict[str, object]:
    if act2_bracket is None:
        return {"fired": True, "trusted": True, "cents": None, "reason": "Act II did not produce a usable fit"}
    d = disagreement_cents(act2_bracket, act3_bracket_mean)
    trusted = n_strikes >= MIN_STRIKES_TRUSTED
    fired = d > cutoff
    reason = ("Act II and Act III disagree by %.2fc on a bracket (cutoff %.1fc)" % (d, cutoff)) if fired else "agree"
    if not trusted:
        reason += "; %d strikes < %d, not trusted on thin chains" % (n_strikes, MIN_STRIKES_TRUSTED)
    return {"fired": bool(fired), "trusted": bool(trusted), "cents": d, "reason": reason}


# --------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------

def gate(split: Optional[Dict[str, Any]], loo_res: Optional[Dict[str, Any]], act2: Dict[str, object]) -> Dict[str, object]:
    """Gate 4 = split-half consistency. LOO and Act II are reported alongside."""
    if split is None:
        return {"fired": True, "reason": "split-half did not run", "split_max_abs_z": None, "loo_max_abs_z": None,
                "loo_n_flagged": None, "act2_cents": act2.get("cents"), "act2_fired": act2.get("fired")}
    reason = ("split-half posteriors disagree: max |z| %.1f on a bracket (%.1fc; cutoff %.1f)" % (
        split["max_abs_z"], split["diff_cents"][split["argmax_bracket"]], split["cutoff"])) if split["fired"] else "split halves agree"
    if loo_res is not None and loo_res["n_flagged"]:
        reason += "; LOO flags %d strike(s), worst %.2f%s at |z| %.1f" % (loo_res["n_flagged"], loo_res["worst_strike"], loo_res["worst_right"], loo_res["max_abs_z"])
    return {"fired": bool(split["fired"]), "reason": reason, "split_max_abs_z": split["max_abs_z"],
            "split_max_abs_diff_cents": split["max_abs_diff_cents"],
            "loo_max_abs_z": None if loo_res is None else loo_res["max_abs_z"],
            "loo_n_flagged": None if loo_res is None else loo_res["n_flagged"],
            "act2_cents": act2.get("cents"), "act2_fired": act2.get("fired"), "act2_trusted": act2.get("trusted")}
