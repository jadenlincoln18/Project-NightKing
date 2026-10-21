"""Gate 0 driver for the PROTOCOL §9 parametric fitter, and the §9.8 spline arm.

    ../.venv/bin/python -m fitter.gate --arm parametric
    ../.venv/bin/python -m fitter.gate --arm spline --limit-per-family 100

Writes one parquet per family as that family completes, so a crash loses at
most one family. The three bars of §9.12 are evaluated in `verdict()` and
nowhere else.

Scoring helpers (`brier`, `logscore`, `bootstrap_diff`) are imported from
`fitter.gate0` — the §8 driver — rather than rewritten, so both arms are scored
by identical code.
"""
from __future__ import annotations

import argparse
import json
import os
import warnings

import numpy as np
import pandas as pd

from fitter import density, skewnormal as sn, synth
from fitter.gate0 import bootstrap_diff, brier, logscore

SEED = 20261020
N_PER_FAMILY = 300          # §9.9
SPLINE_PER_FAMILY = 100     # §9.8 declared paired subset
BAR2_LO, BAR2_HI = 0.85, 0.95     # §9.12 bar 2
BAR3_RATE = 0.60                  # §9.12 bar 3
UNDERPOWERED_N = 100              # §8.7


# --- workers -----------------------------------------------------------------

def _fit_parametric(args):
    idx, bid, ask, method = args
    warnings.filterwarnings("ignore")
    np.seterr(all="ignore")
    r = sn.fit_ladder(synth.EDGES, bid, ask,
                      np.random.default_rng(SEED + 1000 + idx), method=method)
    return idx, r


def _fit_spline(args):
    """§9.8 comparison arm: the m=24 spline of §8.5, with the §9.5 noise scale."""
    idx, bid, ask, n_samples, n_warmup = args
    warnings.filterwarnings("ignore")
    np.seterr(all="ignore")
    bid, ask = np.asarray(bid, float), np.asarray(ask, float)
    mid = (bid + ask) / 200.0
    s = sn.noise_scale(bid, ask)
    r = density.fit_ladder(synth.EDGES, mid, s, np.random.default_rng(SEED + 1000 + idx),
                           sampler="nuts", n_samples=n_samples, n_warmup=n_warmup)
    # the spline has no §9.7 check of its own; it is scored, not gated
    r["gof_x2"] = float(np.sum(((mid - r["fit_mean"]) / s) ** 2))
    r["gof_threshold"] = 11.3449
    r["untrustworthy"] = bool(r["gof_x2"] > 11.3449)
    r["K"] = int(len(mid))
    return idx, r


def rows_for(ladders, indices, fits):
    recs = []
    for (idx, l, f) in zip(indices, ladders, fits):
        s = sn.noise_scale(l.bid, l.ask)
        for k in range(synth.N_BRACKETS):
            recs.append((idx, l.family, k, l.truth_p[k], l.outcome[k], l.bid[k],
                         l.ask[k], l.quote_mid[k], s[k], f["fit_mean"][k],
                         f["fit_lo"][k], f["fit_hi"][k], f["gof_x2"],
                         bool(f["untrustworthy"]), int(f["K"])))
    df = pd.DataFrame(recs, columns=["ladder", "family", "bracket", "truth_p",
                                     "outcome", "bid", "ask", "quote_mid", "s",
                                     "fit_mean", "fit_lo", "fit_hi", "gof_x2",
                                     "untrustworthy", "K"])
    # §9.10 Reading A decides; Reading B is reported and never decides.
    df["disagree"] = (df["quote_mid"] < df["fit_lo"]) | (df["quote_mid"] > df["fit_hi"])
    df["disagree_exec"] = ((df["ask"] / 100.0 < df["fit_lo"])
                           | (df["bid"] / 100.0 > df["fit_hi"]))
    df["trusted"] = ~df["untrustworthy"]
    return df


# --- scoring -----------------------------------------------------------------

def score_set(df, label, n_boot=0):
    if df.empty:
        return {"set": label, "n": 0}
    d = {"set": label, "n": int(len(df)), "n_ladders": int(df["ladder"].nunique()),
         "brier_fit": brier(df["fit_mean"], df["outcome"]),
         "brier_quote": brier(df["quote_mid"], df["outcome"]),
         "log_fit": logscore(df["fit_mean"], df["outcome"]),
         "log_quote": logscore(df["quote_mid"], df["outcome"]),
         "brier_fit_vs_truth": brier(df["fit_mean"], df["truth_p"]),
         "brier_quote_vs_truth": brier(df["quote_mid"], df["truth_p"])}
    d["brier_diff"] = d["brier_quote"] - d["brier_fit"]
    d["fit_wins"] = bool(d["brier_fit"] < d["brier_quote"])
    if n_boot:
        lo, hi = bootstrap_diff(df, n_boot=n_boot)
        d["boot95_brier_diff"] = [lo, hi]
        d["boot95_excludes_zero"] = bool(lo > 0 or hi < 0)
    return d


def verdict(df, n_boot=2000):
    """The §9.12 bars. Evaluated here and nowhere else."""
    prim = df[df["disagree"] & df["trusted"]]
    union = df[df["disagree"]]
    trusted = df[df["trusted"]]

    cover = lambda d: (float(((d["truth_p"] >= d["fit_lo"])
                              & (d["truth_p"] <= d["fit_hi"])).mean())
                       if len(d) else float("nan"))

    by_lad = df.groupby("ladder").agg(family=("family", "first"),
                                      untrust=("untrustworthy", "first"))
    fire = by_lad.groupby("family")["untrust"].mean().to_dict()
    n_lad_fam = by_lad.groupby("family")["untrust"].size().to_dict()
    wellspec = by_lad[by_lad["family"].isin(["unimodal", "skewed"])]["untrust"]

    out = {
        "primary_disagreement": score_set(prim, "primary_disagreement(trusted)", n_boot),
        "union_disagreement": score_set(union, "disagreement(trusted+untrustworthy)",
                                        n_boot),
        "secondary_executable": score_set(
            df[df["disagree_exec"] & df["trusted"]], "secondary_executable"),
        "all": score_set(df, "all"),
        "by_family_primary": {f: score_set(prim[prim["family"] == f],
                                           "primary/%s" % f) for f in synth.FAMILIES},
        "by_family_all": {f: score_set(df[df["family"] == f], "all/%s" % f)
                          for f in synth.FAMILIES},
        "untrustworthy": {
            "n_ladders_flagged": int(by_lad["untrust"].sum()),
            "n_ladders": int(len(by_lad)),
            "rate": float(by_lad["untrust"].mean()),
            "n_obs_excluded_from_primary": int(len(union) - len(prim)),
            "fire_rate_by_family": {k: float(v) for k, v in fire.items()},
            "n_ladders_by_family": {k: int(v) for k, v in n_lad_fam.items()},
            "false_fire_rate_wellspecified_U_K": float(wellspec.mean()) if len(wellspec) else None,
            "gof_threshold": 11.3449,
        },
        "bands": {
            "coverage_trusted": cover(trusted),
            "coverage_all": cover(df),
            "coverage_by_family_trusted": {
                f: cover(trusted[trusted["family"] == f]) for f in synth.FAMILIES},
            "width_mean_trusted": float((trusted["fit_hi"] - trusted["fit_lo"]).mean()),
            "asymmetry_mean_trusted": float(
                ((trusted["fit_hi"] - trusted["fit_mean"])
                 - (trusted["fit_mean"] - trusted["fit_lo"])).mean()),
        },
        "disagreement_rate_primary": float((df["disagree"] & df["trusted"]).mean()),
        "disagreement_rate_exec": float(df["disagree_exec"].mean()),
    }

    p = out["primary_disagreement"]
    bar1 = {"bar": "Brier(fit) < Brier(quote), strict, on the PRIMARY disagreement "
                   "set, AND the ladder-clustered 95% CI excludes zero",
            "n": p.get("n", 0),
            "brier_fit": p.get("brier_fit"), "brier_quote": p.get("brier_quote"),
            "brier_diff": p.get("brier_diff"),
            "boot95": p.get("boot95_brier_diff"),
            "fit_wins": bool(p.get("fit_wins", False)),
            "ci_excludes_zero": bool(p.get("boot95_excludes_zero", False)),
            "underpowered": bool(p.get("n", 0) < UNDERPOWERED_N)}
    bar1["PASS"] = bool(bar1["fit_wins"] and bar1["ci_excludes_zero"])

    u = out["union_disagreement"]
    bar1["union_set_check"] = {
        "n": u.get("n", 0), "brier_fit": u.get("brier_fit"),
        "brier_quote": u.get("brier_quote"), "fit_wins": bool(u.get("fit_wins", False)),
        "note": ("bar 1 passes on the primary set but FAILS on the union of trusted "
                 "and untrustworthy observations -- the exclusion did the work"
                 if bar1["PASS"] and not u.get("fit_wins", False) else
                 "bar 1's outcome is the same on the union set")}

    cov = out["bands"]["coverage_trusted"]
    bar2 = {"bar": "90%% band contains the truth on %.0f-%.0f%% of trusted "
                   "observations (fails in BOTH directions)" % (100 * BAR2_LO, 100 * BAR2_HI),
            "coverage_trusted": cov, "lo": BAR2_LO, "hi": BAR2_HI,
            "direction": ("too narrow / overconfident" if cov < BAR2_LO else
                          "too wide / padded" if cov > BAR2_HI else "in band"),
            "PASS": bool(BAR2_LO <= cov <= BAR2_HI)}

    bfire = float(fire.get("bimodal", float("nan")))
    bar3 = {"bar": "GoF fires on >= %.0f%% of bimodal truths" % (100 * BAR3_RATE),
            "fire_rate_bimodal": bfire, "required": BAR3_RATE,
            "false_fire_rate_U_K": out["untrustworthy"]["false_fire_rate_wellspecified_U_K"],
            "PASS": bool(bfire >= BAR3_RATE)}

    out["BAR1"], out["BAR2"], out["BAR3"] = bar1, bar2, bar3
    out["VERDICT"] = {"bar1": bar1["PASS"], "bar2": bar2["PASS"], "bar3": bar3["PASS"],
                      "PASS": bool(bar1["PASS"] and bar2["PASS"] and bar3["PASS"])}
    return out


# --- driver ------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("parametric", "spline"), default="parametric")
    ap.add_argument("--method", default="quadrature",
                    help="parametric inference: quadrature (the §9.6 primary after "
                         "validation) or laplace")
    ap.add_argument("--n-per-family", type=int, default=N_PER_FAMILY)
    ap.add_argument("--limit-per-family", type=int, default=None)
    ap.add_argument("--out", default="reports/gate0_parametric")
    ap.add_argument("--n-samples", type=int, default=500)
    ap.add_argument("--n-warmup", type=int, default=500)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--spread-sample", default="reports/gate0/spread_sample.parquet")
    a = ap.parse_args(argv)
    np.seterr(all="ignore")

    from concurrent.futures import ProcessPoolExecutor
    os.makedirs(a.out, exist_ok=True)
    workers = a.workers or max(1, (os.cpu_count() or 4) - 2)
    pool = synth.SpreadPool(pd.read_parquet(a.spread_sample))
    rng = np.random.default_rng(SEED)
    ladders = synth.generate(a.n_per_family, pool, rng)
    print("generated %d ladders, %d per family, families=%s"
          % (len(ladders), a.n_per_family, list(synth.FAMILIES)), flush=True)

    parts = []
    for fam in synth.FAMILIES:
        sel = [(i, l) for i, l in enumerate(ladders) if l.family == fam]
        if a.limit_per_family:
            sel = sel[:a.limit_per_family]
        idxs = [i for i, _ in sel]
        lads = [l for _, l in sel]
        if a.arm == "parametric":
            jobs = [(i, l.bid, l.ask, a.method) for i, l in sel]
            fn = _fit_parametric
        else:
            jobs = [(i, l.bid, l.ask, a.n_samples, a.n_warmup) for i, l in sel]
            fn = _fit_spline
        res = {}
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for n, (i, r) in enumerate(ex.map(fn, jobs, chunksize=1)):
                res[i] = r
                if (n + 1) % 25 == 0:
                    print("    %s %s %d/%d" % (a.arm, fam, n + 1, len(jobs)), flush=True)
        df = rows_for(lads, idxs, [res[i] for i in idxs])
        path = os.path.join(a.out, "rows_%s_%s.parquet" % (a.arm, fam))
        df.to_parquet(path)
        print("  wrote %s  (%d rows, %d ladders)" % (path, len(df), df["ladder"].nunique()),
              flush=True)
        parts.append(df)

    full = pd.concat(parts, ignore_index=True)
    full.to_parquet(os.path.join(a.out, "rows_%s_all.parquet" % a.arm))
    rep = verdict(full, n_boot=a.n_boot)
    rep["config"] = {"arm": a.arm, "method": a.method, "n_per_family": a.n_per_family,
                     "limit_per_family": a.limit_per_family, "seed": SEED,
                     "families": list(synth.FAMILIES), "sigma_q": sn.SIGMA_Q,
                     "h_bar": sn.H_BAR, "n_ladders": int(full["ladder"].nunique()),
                     "n_obs": int(len(full))}
    with open(os.path.join(a.out, "report_%s.json" % a.arm), "w") as fh:
        json.dump(rep, fh, indent=1, default=float)
    print(json.dumps(rep["VERDICT"], indent=1, default=float), flush=True)
    return rep


if __name__ == "__main__":
    main()
