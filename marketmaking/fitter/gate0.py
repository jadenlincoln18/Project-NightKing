"""Gate 0 driver — generate, fit, score. PROTOCOL §8.

Run:
    ../.venv/bin/python -m fitter.gate0 --n-per-family 200 --out reports/gate0

The pass bar (§8.7) is evaluated here and nowhere else:

    PASS  <=>  Brier(fit) < Brier(quote)  on the PRIMARY disagreement set.

Everything else this module prints is reported and does not gate.
"""
from __future__ import annotations

import argparse
import json
import os
import warnings

import numpy as np
import pandas as pd

from fitter import density, synth

SEED = 20261020
ROW_COLUMNS = ("ladder", "family", "bracket", "truth_p", "outcome", "bid", "ask",
               "quote_mid", "fit_mean", "fit_lo", "fit_hi")


# --- fitting -----------------------------------------------------------------

def _fit_one(args):
    """Worker: fit one ladder. Returns (index, dict of arrays, diagnostics)."""
    i, bid, ask, sampler, n_samples, n_warmup, target_accept = args
    warnings.filterwarnings("ignore")
    np.seterr(all="ignore")  # BLAS sets stale FP flags on matmul; results checked finite
    bid, ask = np.asarray(bid, float), np.asarray(ask, float)
    mid = (bid + ask) / 200.0
    hs = np.maximum((ask - bid) / 200.0, density.HS_FLOOR)
    rng = np.random.default_rng(SEED + 1000 + i)
    r = density.fit_ladder(synth.EDGES, mid, hs, rng, sampler=sampler,
                           n_samples=n_samples, n_warmup=n_warmup,
                           target_accept=target_accept)
    return i, r


def fit_all(ladders, sampler="nuts", n_samples=500, n_warmup=500, workers=None,
            target_accept=0.8, indices=None):
    """Fit every ladder. `indices` carries each ladder's ORIGINAL generation index.

    The per-ladder sampler seed is `SEED + 1000 + original_index`, so a run on a
    subset of the ladders reproduces the full run's fits **exactly** on that
    subset. That is what makes the robustness runs paired rather than merely
    comparable.
    """
    from concurrent.futures import ProcessPoolExecutor
    workers = workers or max(1, (os.cpu_count() or 4) - 2)
    indices = list(range(len(ladders))) if indices is None else list(indices)
    jobs = [(idx, l.bid, l.ask, sampler, n_samples, n_warmup, target_accept)
            for idx, l in zip(indices, ladders)]
    pos = {idx: j for j, idx in enumerate(indices)}
    out = [None] * len(ladders)
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, r in ex.map(_fit_one, jobs, chunksize=1):
            out[pos[i]] = r
            done += 1
            if done % 50 == 0:
                print("    fitted %d/%d" % (done, len(ladders)), flush=True)
    return out


def rows(ladders, fits) -> pd.DataFrame:
    recs = []
    for i, (l, f) in enumerate(zip(ladders, fits)):
        for k in range(synth.N_BRACKETS):
            recs.append((i, l.family, k, l.truth_p[k], l.outcome[k], l.bid[k], l.ask[k],
                         l.quote_mid[k], f["fit_mean"][k], f["fit_lo"][k], f["fit_hi"][k]))
    df = pd.DataFrame(recs, columns=list(ROW_COLUMNS))
    # PROTOCOL §8.6 / §1B: asymmetric quantiles, never a symmetric half-width.
    df["disagree"] = (df["quote_mid"] < df["fit_lo"]) | (df["quote_mid"] > df["fit_hi"])
    df["disagree_exec"] = ((df["ask"] / 100.0 < df["fit_lo"])
                           | (df["bid"] / 100.0 > df["fit_hi"]))
    return df


# --- scoring -----------------------------------------------------------------

def brier(f, y) -> float:
    f, y = np.asarray(f, float), np.asarray(y, float)
    return float(np.mean((f - y) ** 2))


def logscore(f, y, eps=1e-6) -> float:
    f, y = np.clip(np.asarray(f, float), eps, 1 - eps), np.asarray(y, float)
    return float(-np.mean(y * np.log(f) + (1 - y) * np.log(1 - f)))


def bootstrap_diff(df, n_boot=2000, seed=SEED):
    """Ladder-clustered 95% CI on Brier(quote) - Brier(fit). Reported, not gating."""
    rng = np.random.default_rng(seed)
    lad = df["ladder"].to_numpy()
    uniq = np.unique(lad)
    by = {u: np.flatnonzero(lad == u) for u in uniq}
    q, f, y = (df["quote_mid"].to_numpy(), df["fit_mean"].to_numpy(),
               df["outcome"].to_numpy())
    diffs = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([by[u] for u in pick])
        diffs[b] = brier(q[idx], y[idx]) - brier(f[idx], y[idx])
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def score_set(df, label) -> dict:
    if df.empty:
        return {"set": label, "n": 0}
    d = {
        "set": label,
        "n": int(len(df)),
        "n_ladders": int(df["ladder"].nunique()),
        "brier_fit": brier(df["fit_mean"], df["outcome"]),
        "brier_quote": brier(df["quote_mid"], df["outcome"]),
        "log_fit": logscore(df["fit_mean"], df["outcome"]),
        "log_quote": logscore(df["quote_mid"], df["outcome"]),
        "brier_fit_vs_truth": brier(df["fit_mean"], df["truth_p"]),
        "brier_quote_vs_truth": brier(df["quote_mid"], df["truth_p"]),
    }
    d["brier_diff"] = d["brier_quote"] - d["brier_fit"]
    d["fit_wins"] = bool(d["brier_fit"] < d["brier_quote"])
    return d


def report(df, n_boot=2000) -> dict:
    prim = df[df["disagree"]]
    out = {
        "all": score_set(df, "all"),
        "primary_disagreement": score_set(prim, "primary_disagreement"),
        "secondary_executable": score_set(df[df["disagree_exec"]], "secondary_executable"),
        "by_family": {fam: score_set(prim[prim["family"] == fam],
                                     "primary_disagreement/%s" % fam)
                      for fam in synth.FAMILIES},
        "by_family_all": {fam: score_set(df[df["family"] == fam], "all/%s" % fam)
                          for fam in synth.FAMILIES},
        "disagreement_rate": float(df["disagree"].mean()),
        "disagreement_rate_exec": float(df["disagree_exec"].mean()),
        "band_width_mean": float((df["fit_hi"] - df["fit_lo"]).mean()),
        "band_asymmetry_mean": float((((df["fit_hi"] - df["fit_mean"])
                                       - (df["fit_mean"] - df["fit_lo"]))).mean()),
        "band_covers_truth": float(((df["truth_p"] >= df["fit_lo"])
                                    & (df["truth_p"] <= df["fit_hi"])).mean()),
    }
    if len(prim):
        lo, hi = bootstrap_diff(prim, n_boot=n_boot)
        out["primary_disagreement"]["boot95_brier_diff"] = [lo, hi]
        out["primary_disagreement"]["boot95_excludes_zero"] = bool(lo > 0 or hi < 0)
    # §8.7: the bar, evaluated here and nowhere else.
    out["VERDICT"] = {
        "bar": "Brier(fit) < Brier(quote) on the PRIMARY disagreement set",
        "brier_fit": out["primary_disagreement"].get("brier_fit"),
        "brier_quote": out["primary_disagreement"].get("brier_quote"),
        "n": out["primary_disagreement"].get("n", 0),
        "underpowered": bool(out["primary_disagreement"].get("n", 0) < 100),
        "PASS": bool(out["primary_disagreement"].get("fit_wins", False)),
    }
    return out


# --- driver ------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-family", type=int, default=200)
    ap.add_argument("--out", default="reports/gate0")
    ap.add_argument("--tag", default="primary")
    ap.add_argument("--overround", type=float, default=synth.OVERROUND)
    ap.add_argument("--sampler", default="nuts")
    ap.add_argument("--n-samples", type=int, default=500)
    ap.add_argument("--n-warmup", type=int, default=500)
    ap.add_argument("--target-accept", type=float, default=0.8,
                    help="NUTS dual-averaging target; 0.8 is the extractor's default "
                         "and the pre-registered primary. Raising it is a sampler "
                         "setting, not a model change: the target distribution is "
                         "identical. Reported separately, never as the primary.")
    ap.add_argument("--limit-per-family", type=int, default=None,
                    help="fit only the first K ladders of each family, keeping their "
                         "ORIGINAL indices so the fits are paired with the full run")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--spread-sample", default="reports/gate0/spread_sample.parquet")
    a = ap.parse_args(argv)

    os.makedirs(a.out, exist_ok=True)
    pool = synth.SpreadPool(pd.read_parquet(a.spread_sample))
    print("spread pool: %d tight of %d measured bracket-minutes (%.1f%%)"
          % (pool.n_tight, round(pool.n_tight / max(pool.frac_tight, 1e-9)),
             100 * pool.frac_tight), flush=True)

    rng = np.random.default_rng(SEED)
    ladders = synth.generate(a.n_per_family, pool, rng, overround=a.overround)
    print("generated %d ladders (%d per family), overround=%.4f"
          % (len(ladders), a.n_per_family, a.overround), flush=True)
    indices = list(range(len(ladders)))
    if a.limit_per_family:
        seen, keep = {}, []
        for i, l in enumerate(ladders):
            seen[l.family] = seen.get(l.family, 0) + 1
            if seen[l.family] <= a.limit_per_family:
                keep.append(i)
        ladders = [ladders[i] for i in keep]
        indices = keep
        print("    fitting a paired subset: %d ladders" % len(ladders), flush=True)

    fits = fit_all(ladders, sampler=a.sampler, n_samples=a.n_samples,
                   n_warmup=a.n_warmup, workers=a.workers,
                   target_accept=a.target_accept, indices=indices)
    df = rows(ladders, fits)
    df["ladder"] = np.repeat(indices, synth.N_BRACKETS)
    diag = {
        "converged_frac": float(np.mean([f["converged"] for f in fits])),
        "rhat_max": float(np.max([f["rhat_max"] for f in fits])),
        "ess_min": float(np.min([f["ess_min"] for f in fits])),
        "divergences_mean": float(np.mean([f["divergences"] for f in fits])),
        "divergence_free_frac": float(np.mean([f["divergences"] == 0 for f in fits])),
        "seconds_mean": float(np.mean([f["seconds"] for f in fits])),
    }
    rep = report(df)
    rep["sampler_diagnostics"] = diag
    rep["config"] = {"n_per_family": a.n_per_family, "overround": a.overround,
                     "sampler": a.sampler, "n_samples": a.n_samples,
                     "n_warmup": a.n_warmup, "target_accept": a.target_accept,
                     "limit_per_family": a.limit_per_family, "seed": SEED,
                     "sigma_q": synth.SIGMA_Q, "edges": synth.EDGES.tolist(),
                     "n_brackets": synth.N_BRACKETS}

    df.to_parquet(os.path.join(a.out, "rows_%s.parquet" % a.tag))
    with open(os.path.join(a.out, "report_%s.json" % a.tag), "w") as fh:
        json.dump(rep, fh, indent=1, default=float)
    print(json.dumps(rep, indent=1, default=float))
    return rep


if __name__ == "__main__":
    main()
