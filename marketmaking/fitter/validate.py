"""PROTOCOL §9.6 inference validation, on the declared subsample.

    ../.venv/bin/python -m fitter.validate

The subsample is fixed by §9.6: **the first 15 ladders of each family, 60
ladders, 360 bracket observations**, from the §9.9 generator. Three posteriors
are computed on identical data:

  laplace      the §9.6 primary candidate
  quadrature   the §9.6 reference: sinh-stretched 3-D grid, adaptively widened
               until boundary mass < 1e-4, with a node-count stability check
  mcmc         an independent adaptive random-walk Metropolis, 4 x 20,000

§9.6's licence condition for Laplace, fixed before this was run:
    mean |d posterior mean| < 0.005  AND  mean |d band endpoint| < 0.010.
On a miss, the primary run uses the quadrature posterior and says so.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from fitter import skewnormal as sn, synth

SEED = 20261020
N_VALIDATE_PER_FAMILY = 15      # §9.6
TOL_MEAN = 0.005
TOL_BAND = 0.010


def _diffs(a, b):
    dm = np.abs(a["fit_mean"] - b["fit_mean"])
    db = np.abs(np.concatenate([a["fit_lo"] - b["fit_lo"], a["fit_hi"] - b["fit_hi"]]))
    return dm, db


def main(out_dir="reports/gate0_parametric", n_per_family=300, mcmc_every=5):
    np.seterr(all="ignore")
    os.makedirs(out_dir, exist_ok=True)
    pool = synth.SpreadPool(pd.read_parquet("reports/gate0/spread_sample.parquet"))
    rng = np.random.default_rng(SEED)
    ladders = synth.generate(n_per_family, pool, rng)

    seen, sub = {}, []
    for i, l in enumerate(ladders):
        seen[l.family] = seen.get(l.family, 0) + 1
        if seen[l.family] <= N_VALIDATE_PER_FAMILY:
            sub.append((i, l))

    rec = {"laplace_vs_quad": {"mean": [], "band": []},
           "mcmc_vs_quad": {"mean": [], "band": []},
           "grid_stability": {"mean": [], "band": []},
           "boundary_mass": [], "grid_extent": [],
           "mcmc_rhat": [], "mcmc_ess": [], "per_family": {}}

    for n, (idx, l) in enumerate(sub):
        q = sn.fit_ladder(synth.EDGES, l.bid, l.ask, None, method="quadrature")
        lp = sn.fit_ladder(synth.EDGES, l.bid, l.ask,
                           np.random.default_rng(SEED + 1000 + idx))
        dm, db = _diffs(lp, q)
        rec["laplace_vs_quad"]["mean"] += dm.tolist()
        rec["laplace_vs_quad"]["band"] += db.tolist()
        rec["boundary_mass"].append(q["boundary_mass"])
        rec["grid_extent"].append(q["grid_sd_extent"])
        f = rec["per_family"].setdefault(l.family, {"mean": [], "band": []})
        f["mean"] += dm.tolist()
        f["band"] += db.tolist()

        q2 = sn.fit_ladder(synth.EDGES, l.bid, l.ask, None, method="quadrature",
                           n_axis=121)
        dm2, db2 = _diffs(q, q2)
        rec["grid_stability"]["mean"] += dm2.tolist()
        rec["grid_stability"]["band"] += db2.tolist()

        if n % mcmc_every == 0:
            mc = sn.fit_ladder(synth.EDGES, l.bid, l.ask,
                               np.random.default_rng(SEED + 7 + idx), method="mcmc")
            dm3, db3 = _diffs(mc, q)
            rec["mcmc_vs_quad"]["mean"] += dm3.tolist()
            rec["mcmc_vs_quad"]["band"] += db3.tolist()
            rec["mcmc_rhat"].append(mc["mcmc_rhat_max"])
            rec["mcmc_ess"].append(mc["mcmc_ess_min"])
        print("  validated %d/%d" % (n + 1, len(sub)), flush=True)

    def summ(d):
        return {"mean_abs_mean": float(np.mean(d["mean"])),
                "max_abs_mean": float(np.max(d["mean"])),
                "mean_abs_band": float(np.mean(d["band"])),
                "max_abs_band": float(np.max(d["band"])),
                "n_obs": int(len(d["mean"]))}

    out = {
        "subsample": {"n_ladders": len(sub), "per_family": N_VALIDATE_PER_FAMILY,
                      "n_bracket_obs": 6 * len(sub)},
        "tolerances": {"mean_abs_mean": TOL_MEAN, "mean_abs_band": TOL_BAND},
        "laplace_vs_quadrature": summ(rec["laplace_vs_quad"]),
        "mcmc_vs_quadrature": summ(rec["mcmc_vs_quad"]),
        "quadrature_grid_stability_81_vs_121": summ(rec["grid_stability"]),
        "quadrature_boundary_mass": {
            "max": float(np.max(rec["boundary_mass"])),
            "median": float(np.median(rec["boundary_mass"])),
            "n_above_1e-4": int(np.sum(np.array(rec["boundary_mass"]) > 1e-4)),
            "max_sd_extent": float(np.max(rec["grid_extent"]))},
        "mcmc_diagnostics": {"rhat_max": float(np.max(rec["mcmc_rhat"])),
                             "ess_min": float(np.min(rec["mcmc_ess"])),
                             "n_ladders": len(rec["mcmc_rhat"])},
        "laplace_by_family": {k: summ(v) for k, v in rec["per_family"].items()},
    }
    lv = out["laplace_vs_quadrature"]
    out["LAPLACE_LICENSED"] = bool(lv["mean_abs_mean"] < TOL_MEAN
                                   and lv["mean_abs_band"] < TOL_BAND)
    out["PRIMARY_INFERENCE"] = "laplace" if out["LAPLACE_LICENSED"] else "quadrature"
    with open(os.path.join(out_dir, "validation.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    main()
