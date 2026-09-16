"""Calibrate the split-half statistic on synthetic chains where the answer is known.

Three planted situations on real strike grids with the study's NUTS settings:
    null      crude-skew truth, calibrated noise: max|z| here is the null distribution; its p95
              is the Gate 4 cutoff written to synth/results_real/split_half_null.json
    stale     the same with one stale quote (a mid pushed 15c below its neighbours two strikes
              from the money): a data inconsistency that split-half and LOO should catch
    bimodal   two humps 2.6 vol-scales apart: a prior mis-specification that split-half is
              NOT expected to catch (both halves share the smooth prior); Act II is the
              signal there (FINDINGS_SYNTHETIC.md §7, §11)

    python3 -m synth.realchain --calibrate       (about 10 minutes with 7 workers)
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results_real"
NUTS = {"n_chains": 4, "n_warmup": 400, "n_samples": 400}
N_NULL, N_STALE, N_BIMODAL = 24, 8, 8


def one(job: Dict[str, Any]) -> Dict[str, Any]:
    from . import act2, act3, densities, detector, geometry, noise
    kind, seed = job["kind"], job["seed"]
    geo = geometry.load()
    rng = np.random.default_rng(seed)
    snaps = geometry.snapshots(geo)
    snap = snaps[int(rng.integers(len(snaps)))]
    F0, T = float(snap["forward"]), float(snap["T_years"])
    sigma = float(np.clip(snap["atm_iv"] or 0.6, 0.2, 2.0))
    K = np.array(snap["strikes"], float)
    R = np.array(snap["rights"])
    hs_obs = np.array(snap["half_spreads"], float)
    fam = "bimodal" if kind == "bimodal" else "crude_skew"
    pl = densities.Planted(fam, F0, sigma, T)
    edges = densities.kalshi_edges(F0)
    C = pl.price(K, R)
    hs = noise.half_spreads(rng, C, geo["half_spread_model"], 1.0, observed=hs_obs)
    _, _, mid, hsq = noise.quotes(rng, C, hs, "gaussian")
    inj = None
    if kind == "stale":
        calls = np.where(R == "C")[0]
        i = int(calls[min(2, len(calls) - 1)])
        mid[i] = max(mid[i] - 0.15, 0.005)
        inj = float(K[i])
    out: Dict[str, Any] = {"kind": kind, "seed": seed, "n_strikes": int(len(K)), "F0": F0, "T": T, "sigma": sigma, "injected_strike": inj}
    t0 = time.time()
    try:
        asig = act3.atm_sigma(K, R, mid, F0, pl.D, T)
        se = 0.02
        model = act3.Model(K, R, mid, hsq, F0, pl.D, T, asig, se_F0=se, martingale=True)
        res = act3.sample(model, np.random.default_rng(seed + 100), sampler="nuts", **NUTS)
        summ = model.summarise(res["thetas"], edges)
        br_mean = summ["bracket"].mean(axis=0)
        out["chi2_per_strike"] = float(summ["chi2"].mean() / len(K))
        split = detector.split_half(K, R, mid, hsq, F0, pl.D, T, asig, se, edges, NUTS, seed=seed + 200, cutoff=3.0)
        out["split_max_abs_z"] = split["max_abs_z"]
        out["split_max_abs_diff_cents"] = split["max_abs_diff_cents"]
        lo = detector.loo(K, R, mid, hsq, F0, pl.D, T, asig, se, psi_warm=res["psi_map"])
        out["loo_max_abs_z"] = lo["max_abs_z"]
        out["loo_n_flagged"] = lo["n_flagged"]
        out["loo_worst_strike"] = lo["worst_strike"]
        out["loo_localised"] = bool(inj is not None and abs(lo["worst_strike"] - inj) < 1e-9)
        try:
            a2 = act2.run(K, R, mid, hsq, F0, pl.D, T, edges, rng=np.random.default_rng(0))
            out["act2_cents"] = detector.disagreement_cents(a2["bracket_probs"], br_mean) if a2.get("ok") else None
        except Exception:
            out["act2_cents"] = None
        # truth check: is the full posterior right at the brackets?
        p_true = pl.bracket_probs(edges)
        z_truth = (br_mean - p_true) / np.sqrt(summ["bracket"].var(axis=0, ddof=1) + 1e-12)
        out["truth_max_abs_z"] = float(np.abs(z_truth).max())
    except Exception as exc:
        import traceback
        out["error"] = repr(exc)
        out["traceback"] = traceback.format_exc()
    out["seconds"] = time.time() - t0
    return out


def summarise(rs: List[Dict[str, Any]]) -> Dict[str, Any]:
    S: Dict[str, Any] = {}
    for kind in ("null", "stale", "bimodal"):
        sub = [r for r in rs if r["kind"] == kind and not r.get("error")]
        if not sub:
            continue
        sz = np.array([r["split_max_abs_z"] for r in sub])
        lz = np.array([r["loo_max_abs_z"] for r in sub])
        a2 = np.array([r["act2_cents"] for r in sub if r.get("act2_cents") is not None])
        S[kind] = {"n": len(sub), "split_max_abs_z_median": float(np.median(sz)), "split_max_abs_z_p95": float(np.percentile(sz, 95)),
                   "split_max_abs_z_max": float(sz.max()), "split_frac_gt3": float(np.mean(sz > 3.0)),
                   "loo_max_abs_z_median": float(np.median(lz)), "loo_frac_gt3": float(np.mean(lz > 3.0)),
                   "loo_localised_frac": float(np.mean([r["loo_localised"] for r in sub])) if kind == "stale" else None,
                   "act2_cents_median": float(np.median(a2)) if a2.size else None,
                   "act2_frac_gt_cutoff": float(np.mean(a2 > 2.5)) if a2.size else None,
                   "chi2_median": float(np.median([r["chi2_per_strike"] for r in sub])),
                   "truth_max_abs_z_median": float(np.median([r["truth_max_abs_z"] for r in sub])),
                   "n_strikes_median": float(np.median([r["n_strikes"] for r in sub]))}
    if "null" in S:
        S["cutoff_p95"] = S["null"]["split_max_abs_z_p95"]
    S["n_errors"] = sum(1 for r in rs if r.get("error"))
    return S


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=7)
    a = ap.parse_args(argv)
    RESULTS.mkdir(parents=True, exist_ok=True)
    jobs = ([{"kind": "null", "seed": s} for s in range(N_NULL)] + [{"kind": "stale", "seed": 1000 + s} for s in range(N_STALE)]
            + [{"kind": "bimodal", "seed": 2000 + s} for s in range(N_BIMODAL)])
    ctx = mp.get_context("fork")
    t0 = time.time()
    rs = []
    with ctx.Pool(a.workers) as pool:
        for i, r in enumerate(pool.imap_unordered(one, jobs), 1):
            rs.append(r)
            print("  %2d/%d %-8s seed %4d n=%2d split max|z| %s loo max|z| %s act2 %s %5.0fs" % (
                i, len(jobs), r["kind"], r["seed"], r["n_strikes"], "%.2f" % r["split_max_abs_z"] if "split_max_abs_z" in r else "ERR",
                "%.2f" % r["loo_max_abs_z"] if "loo_max_abs_z" in r else "-", "%.2f" % r["act2_cents"] if r.get("act2_cents") is not None else "-",
                time.time() - t0), flush=True)
            if r.get("error"):
                print("     " + r["error"][:200], flush=True)
    pickle.dump(rs, open(RESULTS / "split_half_calibration.pkl", "wb"))
    S = summarise(rs)
    json.dump(S, open(RESULTS / "split_half_null.json", "w"), indent=1)
    print(json.dumps(S, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
