"""One synthetic run: plant -> exact prices on a real strike grid -> calibrated quotes ->
Stage 6 -> Act II and Act III -> compare with the planted truth.

`run_one(cfg, seed)` returns a flat dict of arrays and scalars; the runner aggregates
hundreds of them into coverage tables. Failure-mode injections are switches in the cfg
so the same code path is exercised with and without the fault.

cfg keys (all optional, defaults in DEFAULTS)
  family          planted density family (synth.densities.FAMILIES)
  lookback        1 or 2 business days before settlement (which real snapshots to draw)
  n_strikes       thin the real grid to this many strikes (>= 3 per wing kept); None = all
  hs_source       "model" | "observed"          (see synth.noise)
  error           "gaussian" | "uniform" | "none"
  noise_scale     multiplies every half-spread
  martingale      Stage 14 on/off
  forward_offset  cents added to the Stage 6 forward before it is used downstream
  extent_sd       Act III grid half-width in vol-scales (7 normal; 1.5 = truncated grid)
  inject          None | "convexity" | "unconverged" | "stale"
  sampler         "slice" | "nuts" | "laplace"
  n_chains, n_warmup, n_samples
  levels          nominal coverage levels
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np

from . import act2, act3, densities, geometry, noise, stage6

DEFAULTS: Dict[str, Any] = {
    "family": "crude_skew", "lookback": 1, "n_strikes": None, "hs_source": "model", "error": "gaussian",
    "noise_scale": 1.0, "martingale": True, "forward_offset": 0.0, "extent_sd": 7.0, "inject": None,
    "sampler": "slice", "n_chains": 4, "n_warmup": 300, "n_samples": 500, "levels": (50, 80, 90, 95),
    "sigma_clip": (0.25, 1.0), "m_coef": 24, "n_grid": 400, "snapshot": None, "fixed_D": None, "hs_floor": 0.0,
}
EDGE_MASS_MAX = 0.01  # posterior mass in the outer 2.5% of the grid at either end
_GEO: Optional[Dict[str, Any]] = None


def _geo() -> Dict[str, Any]:
    global _GEO
    if _GEO is None:
        _GEO = geometry.load()
    return _GEO


def thin_strikes(rng: np.random.Generator, K: np.ndarray, right: np.ndarray, F0: float, n: int, min_wing: int = 3):
    """Random subset of n strikes keeping at least min_wing on each side of F0."""
    below = np.where(K < F0)[0]
    above = np.where(K >= F0)[0]
    n = min(n, len(K))
    nb = max(min_wing, int(round(n * len(below) / len(K))))
    na = max(min_wing, n - nb)
    nb = min(nb, len(below))
    na = min(na, len(above))
    idx = np.concatenate([rng.choice(below, nb, replace=False), rng.choice(above, na, replace=False)])
    idx.sort()
    return K[idx], right[idx]


def quantile_pairs(levels) -> List[float]:
    q: List[float] = []
    for L in levels:
        q += [50 - L / 2.0, 50 + L / 2.0]
    return q


def covered(truth: np.ndarray, samples: np.ndarray, levels) -> Dict[int, np.ndarray]:
    """Per-level boolean array: truth inside the central credible interval of the samples."""
    out = {}
    for L in levels:
        lo, hi = np.percentile(samples, [50 - L / 2.0, 50 + L / 2.0], axis=0)
        out[L] = (truth >= lo) & (truth <= hi)
    return out


def run_one(cfg: Dict[str, Any], seed: int) -> Dict[str, Any]:
    c = dict(DEFAULTS)
    c.update(cfg or {})
    geo = _geo()
    rng = np.random.default_rng(seed)
    t_start = time.time()
    snaps = geometry.snapshots(geo, lookback=c["lookback"])
    snap = snaps[c["snapshot"] if c["snapshot"] is not None else int(rng.integers(len(snaps)))]
    F0 = float(snap["forward"])
    T = float(snap["T_years"])
    sigma = float(np.clip(snap["atm_iv"] or 0.6, *c["sigma_clip"]))
    K_all = np.array(snap["strikes"], float)
    R_all = np.array(snap["rights"])
    hs_obs_all = np.array(snap["half_spreads"], float)
    if c["n_strikes"] is not None and c["n_strikes"] < len(K_all):
        K, R = thin_strikes(rng, K_all, R_all, F0, int(c["n_strikes"]))
        hs_obs = hs_obs_all[np.searchsorted(K_all, K)]
    else:
        K, R, hs_obs = K_all, R_all, hs_obs_all

    # --- plant and price -------------------------------------------------------
    pl = densities.Planted(c["family"], F0, sigma, T)
    edges = densities.kalshi_edges(F0)
    p_true = pl.bracket_probs(edges)
    s_eval = F0 + np.arange(-12.0, 12.01, 0.5)
    f_true = pl.pdf(s_eval)
    C_true = pl.price(K, R)
    hsm = geo["half_spread_model"]
    hs = noise.half_spreads(rng, C_true, hsm, c["noise_scale"], observed=hs_obs if c["hs_source"] == "observed" else None)
    bid, ask, mid, hsq = noise.quotes(rng, C_true, hs, c["error"])

    # parity pairs: both sides quoted within 2 vol-scales of the forward
    near = np.abs(np.log(K / F0)) < 2.0 * pl.v
    Kp = K[near] if near.sum() >= 3 else K
    Cc, Pp = pl.price(Kp, "C"), pl.price(Kp, "P")
    hc = noise.half_spreads(rng, Cc, hsm, c["noise_scale"])
    hp = noise.half_spreads(rng, Pp, hsm, c["noise_scale"])
    _, _, cm, hcq = noise.quotes(rng, Cc, hc, c["error"])
    _, _, pm, hpq = noise.quotes(rng, Pp, hp, c["error"])

    # --- injections on the quotes -----------------------------------------------
    inject = c["inject"]
    inj_idx = None
    if inject in ("convexity", "stale"):
        # a bad quote 2 strikes from the money on the call side: either pushed far above its
        # neighbours (local concavity of the call curve) or left stale (far below)
        calls = np.where((R == "C"))[0]
        if len(calls) >= 3:
            inj_idx = int(calls[min(2, len(calls) - 1)])
            neigh = np.abs(mid[max(inj_idx - 1, 0)] - mid[min(inj_idx + 1, len(mid) - 1)])
            bump = max(0.15, 3 * neigh)
            mid[inj_idx] = mid[inj_idx] + bump if inject == "convexity" else max(mid[inj_idx] - bump, 0.005)
            # also break its parity pair so Stage 6 sees it
            j = np.where(np.isclose(Kp, K[inj_idx]))[0]
            if j.size:
                cm[j[0]] = cm[j[0]] + (bump if inject == "convexity" else -bump)

    # --- Stage 6 ----------------------------------------------------------------
    st6 = stage6.parity_forward(Kp, cm, pm, weights=1.0 / (hcq ** 2 + hpq ** 2), fixed_D=c["fixed_D"])
    F0_hat = float(st6["F0"]) if st6["ok"] else F0
    D_hat = float(st6["D"]) if st6["ok"] else pl.D
    se_F0 = float(st6["se_F0"]) if st6["ok"] else 0.05
    F0_used = F0_hat + c["forward_offset"] / 100.0

    out: Dict[str, Any] = {
        "seed": seed, "cfg": c, "snapshot": {"root": snap["root"], "settle_date": snap["settle_date"],
                                             "lookback_days": snap["lookback_days"], "atm_iv": snap["atm_iv"]},
        "F0": F0, "T": T, "sigma": sigma, "v": pl.v, "std_true": pl.std, "n_strikes": int(len(K)),
        "n_below": int((K < F0).sum()), "n_above": int((K >= F0).sum()), "K": K, "right": R, "mid": mid, "hs": hsq,
        "C_true": C_true, "edges": edges, "p_true": p_true, "s_eval": s_eval, "f_true": f_true,
        "F0_hat": F0_hat, "se_F0": se_F0, "D_hat": D_hat, "D_true": pl.D, "F0_used": F0_used,
        "parity_flagged": int(np.sum(st6["flagged"])), "parity_resid_sd": st6.get("resid_sd", np.nan),
        "parity_n": st6["n_pairs"], "inject": inject, "inject_strike": float(K[inj_idx]) if inj_idx is not None else None,
    }
    if inj_idx is not None:
        out["inject_flagged_by_parity"] = bool(st6["flagged"][np.where(np.isclose(Kp, K[inj_idx]))[0][0]]) \
            if np.any(np.isclose(Kp, K[inj_idx])) else False
    levels = tuple(c["levels"])
    # frequentist coverage of the Stage 6 forward: |F0_hat - F0| <= z * se
    from scipy.stats import norm
    out["forward_cov"] = {L: bool(abs(F0_hat - F0) <= norm.ppf(0.5 + L / 200.0) * se_F0) for L in levels}
    out["forward_err_cents"] = 100.0 * (F0_hat - F0)

    # --- Act II -----------------------------------------------------------------
    try:
        a2 = act2.run(K, R, mid, hsq, F0_used, D_hat, T, edges, s_eval=s_eval, rng=rng)
    except Exception as exc:  # a failed fit is a result, not a crash
        a2 = {"ok": False, "reason": repr(exc)}
    out["act2_ok"] = bool(a2.get("ok"))
    if a2.get("ok"):
        out["act2_bracket"] = a2["bracket_probs"]
        out["act2_density_at"] = a2["density_at"]
        out["act2_mean"] = a2["mean"]
        out["act2_mass"] = a2["mass"]
        out["act2_min_density"] = a2["min_density"]
        out["act2_checks"] = a2["checks"]
        out["act2_svi"] = {k: float(v) if isinstance(v, (float, int, np.floating)) else v for k, v in a2["svi"].items()}
        out["act2_n_used"] = a2["n_used"]
    else:
        out["act2_reason"] = a2.get("reason")

    # --- Act III ------------------------------------------------------------------
    asig = act3.atm_sigma(K, R, mid, F0_used, D_hat, T)
    model = act3.Model(K, R, mid, hsq, F0_used, D_hat, T, asig, se_F0=se_F0, m=c["m_coef"], n_grid=c["n_grid"],
                       extent_sd=c["extent_sd"], martingale=c["martingale"], hs_floor=c["hs_floor"])
    n_warmup, n_samples, n_chains = c["n_warmup"], c["n_samples"], c["n_chains"]
    sampler = c["sampler"]
    if inject == "unconverged":
        sampler, n_warmup, n_samples, n_chains = "nuts", 5, 40, 2
    res = act3.sample(model, rng, sampler=sampler, n_chains=n_chains, n_warmup=n_warmup, n_samples=n_samples)
    summ = model.summarise(res["thetas"], edges, s_eval=s_eval)
    br = summ["bracket"]
    # convergence of the quantities that are actually delivered (bracket probabilities, E[F_T]),
    # not just of the raw sampler coordinates
    n_ch = int(res.get("n_chains", n_chains)) if res["sampler"] != "laplace" else 1
    if n_ch > 1 and br.shape[0] % n_ch == 0:
        chains_br = br.reshape(n_ch, -1, br.shape[1])
        keep = chains_br.std(axis=(0, 1)) > 1e-12
        out["act3_bracket_rhat_max"] = float(act3.split_rhat(chains_br[:, :, keep]).max()) if keep.any() else 1.0
        out["act3_bracket_ess_min"] = float(act3.ess(chains_br[:, :, keep]).min()) if keep.any() else float(br.shape[0])
        mf = summ["mean_F"].reshape(n_ch, -1, 1)
        out["act3_meanF_rhat"] = float(act3.split_rhat(mf)[0])
        out["act3_meanF_ess"] = float(act3.ess(mf)[0])
    else:
        out["act3_bracket_rhat_max"] = 1.0
        out["act3_bracket_ess_min"] = float(br.shape[0])
        out["act3_meanF_rhat"] = 1.0
        out["act3_meanF_ess"] = float(br.shape[0])
    out.update({
        "act3_bracket_mean": br.mean(axis=0), "act3_bracket_median": np.median(br, axis=0),
        "act3_bracket_q": np.percentile(br, quantile_pairs(levels), axis=0),
        "act3_bracket_cov": covered(p_true, br, levels),
        "act3_bracket_width90": np.diff(np.percentile(br, [5, 95], axis=0), axis=0)[0],
        "act3_density_mean": summ["density_at"].mean(axis=0),
        "act3_density_q": np.percentile(summ["density_at"], quantile_pairs(levels), axis=0),
        "act3_density_cov": covered(f_true, summ["density_at"], levels),
        "act3_meanF": summ["mean_F"], "act3_meanF_cov": covered(np.array([F0]), summ["mean_F"][:, None], levels),
        "act3_meanF_mean": float(summ["mean_F"].mean()), "act3_meanF_sd": float(summ["mean_F"].std()),
        "act3_chi2_mean": float(summ["chi2"].mean()), "act3_resid_mean": summ["resid"].mean(axis=0),
        "act3_edge_mass": summ["edge_mass"].mean(axis=0), "act3_tau_q": np.percentile(res["taus"], [5, 50, 95]),
        "act3_rhat_max": res["rhat_max"], "act3_ess_min": res["ess_min"], "act3_divergences": res["divergences"],
        "act3_converged": res["converged"], "act3_sampler": res["sampler"], "act3_seconds": res["seconds"],
        "act3_grid": (float(model.s[0]), float(model.s[-1])), "act3_atm_sigma": asig,
    })
    # posterior mean density on the model grid (for plots) and modality
    p_mean = np.mean([model.density(th)[1] for th in res["thetas"][:: max(1, len(res["thetas"]) // 200)]], axis=0)
    out["act3_grid_s"] = model.s
    out["act3_grid_f_mean"] = p_mean
    out["act3_grid_f_q"] = np.percentile(np.array([model.density(th)[1] for th in res["thetas"][:: max(1, len(res["thetas"]) // 400)]]),
                                         [5, 95], axis=0)
    out["true_grid_f"] = pl.pdf(model.s)
    out["act3_n_modes"] = count_modes(model.s, p_mean)
    out["true_n_modes"] = count_modes(pl.s, pl.f)
    # checks
    out["checks"] = {
        "mean_equals_forward_z": float((summ["mean_F"].mean() - F0_used) / max(summ["mean_F"].std(), 1e-9)),
        "mean_vs_true_F_cents": float(100.0 * (summ["mean_F"].mean() - F0)),
        "normalisation_edge_mass_ok": bool(summ["edge_mass"].mean(axis=0).max() < EDGE_MASS_MAX),
        "chi2_map_per_strike": float(model.chi2(model.theta_from(res["psi_map"])[0])[0] / len(K)),
        "chi2_per_strike": float(summ["chi2"].mean() / len(K)),
        "max_abs_resid": float(np.abs(summ["resid"].mean(axis=0)).max()),
        "worst_resid_strike": float(K[int(np.argmax(np.abs(summ["resid"].mean(axis=0))))]),
        "sampler_ok": bool(res["converged"]),
    }
    if inj_idx is not None:
        out["inject_resid_z"] = float(summ["resid"].mean(axis=0)[inj_idx])
    if a2.get("ok"):
        out["act2_vs_act3_max_abs"] = float(np.abs(a2["bracket_probs"] - br.mean(axis=0)).max())
        lo, hi = np.percentile(br, [5, 95], axis=0)
        out["act2_inside_act3_90"] = float(np.mean((a2["bracket_probs"] >= lo) & (a2["bracket_probs"] <= hi)))
    out["seconds"] = time.time() - t_start
    return out


def count_modes(s: np.ndarray, f: np.ndarray, rel_trough: float = 0.2, floor_frac: float = 0.02) -> int:
    """Number of distinct humps: local maxima above floor_frac*max(f) separated by a trough at
    least rel_trough below the lower of the two peaks."""
    f = np.asarray(f, float)
    fmax = f.max()
    if fmax <= 0:
        return 0
    peaks = [i for i in range(1, len(f) - 1) if f[i] > f[i - 1] and f[i] >= f[i + 1] and f[i] > floor_frac * fmax]
    if not peaks:
        return 0
    kept = [peaks[0]]
    for i in peaks[1:]:
        j = kept[-1]
        trough = f[j:i + 1].min()
        if trough < (1.0 - rel_trough) * min(f[i], f[j]):
            kept.append(i)
        elif f[i] > f[j]:
            kept[-1] = i
    return len(kept)
