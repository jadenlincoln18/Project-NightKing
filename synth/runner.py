"""Run the synthetic study and aggregate it.

    python3 -m synth.runner                 # run every config (resumable), then report
    python3 -m synth.runner --only A,B      # a subset
    python3 -m synth.runner --report        # aggregate what is on disk, write FINDINGS + plots
    python3 -m synth.runner --quick         # 6 runs per config, laplace sampler (smoke)

Per-config results go to synth/results/<name>.pkl (gitignored: ~4 MB each); the
aggregate goes to synth/results/summary.json, the plots to synth/plots/, and the
verdict to FINDINGS_SYNTHETIC.md.
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

# pin BLAS threads before numpy is imported anywhere in the workers
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
PLOTS = HERE / "plots"

NUTS = {"sampler": "nuts", "n_chains": 4, "n_warmup": 400, "n_samples": 400}
BASE = dict(NUTS, family="crude_skew", lookback=1, m_coef=24)   # FINDINGS_SYNTHETIC.md was run at 24 knots; the default is now 48
                                                                  # (FINDINGS_PRIOR.md) - a full re-run at 48 is the next study, not this one

# name -> (cfg, n_runs). Seeds are fixed per config so a re-run reproduces the file.
CONFIGS: Dict[str, Any] = {
    # primary coverage study, full real grids
    "A_crude_full": (dict(BASE), 120),
    "B_lognormal_full": (dict(BASE, family="lognormal"), 120),
    "C_bimodal_full": (dict(BASE, family="bimodal"), 120),
    # strike-count sweep (gate is 8 with 3+ per wing; median settlement-day chain is 23)
    "S08_crude": (dict(BASE, n_strikes=8), 60),
    "S12_crude": (dict(BASE, n_strikes=12), 60),
    "S16_crude": (dict(BASE, n_strikes=16), 60),
    "S23_crude": (dict(BASE, n_strikes=23), 60),
    # noise model sweep
    "N05_crude": (dict(BASE, noise_scale=0.5), 60),
    "N20_crude": (dict(BASE, noise_scale=2.0), 60),
    "NU_crude_uniform": (dict(BASE, error="uniform"), 60),
    "NO_crude_observed_hs": (dict(BASE, hs_source="observed"), 60),
    "NF_crude_tickfloor": (dict(BASE, hs_floor=0.01), 60),
    "L2_crude_2day": (dict(BASE, lookback=2), 60),
    # other planted shapes
    "D_heavy_both": (dict(BASE, family="heavy_both"), 60),
    "E_sharp_peak": (dict(BASE, family="sharp_peak"), 60),
    "F_bimodal_close": (dict(BASE, family="bimodal_close"), 60),
    "G_spike_outside_prior": (dict(BASE, family="spike"), 50),
    "C05_bimodal_halfnoise": (dict(BASE, family="bimodal", noise_scale=0.5), 40),
    # Stage 14 diagnostic: sampler without the martingale constraint
    "M_crude_nomart": (dict(BASE, martingale=False), 60),
    "M_lognormal_nomart": (dict(BASE, family="lognormal", martingale=False), 50),
    # injected failure modes
    "X_fwd05": (dict(BASE, forward_offset=5), 50),
    "X_fwd15": (dict(BASE, forward_offset=15), 50),
    "X_fwd50": (dict(BASE, forward_offset=50), 50),
    "X_fwd05_nomart": (dict(BASE, forward_offset=5, martingale=False), 50),
    "X_fwd15_nomart": (dict(BASE, forward_offset=15, martingale=False), 50),
    "X_fwd50_nomart": (dict(BASE, forward_offset=50, martingale=False), 50),
    "X_truncated_grid": (dict(BASE, extent_sd=1.5), 50),
    "X_convexity": (dict(BASE, inject="convexity"), 50),
    "X_stale": (dict(BASE, inject="stale"), 50),
    "X_unconverged": (dict(BASE, inject="unconverged"), 50),
}


def _work(args):
    name, cfg, seed = args
    from . import harness
    try:
        r = harness.run_one(cfg, seed)
        r["error"] = None
    except Exception as exc:  # keep going; a crash is a result too
        import traceback
        r = {"seed": seed, "cfg": cfg, "error": repr(exc), "traceback": traceback.format_exc()}
    r["config"] = name
    return r


def _dump(results, out: Path) -> None:
    tmp = out.with_name(out.name + ".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump(results, fh)
    os.replace(tmp, out)   # atomic: a kill mid-dump leaves the previous checkpoint intact


def run_config(name: str, cfg: Dict[str, Any], n_runs: int, workers: int, quick: bool = False) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / ("%s.pkl" % name)
    if out.exists():
        with open(out, "rb") as fh:
            have = pickle.load(fh)
        # a seed whose run raised is re-done; a seed absent was never attempted; an ok seed is never re-run
        have = [r for r in have if r.get("error") is None]
        if len(have) >= n_runs:
            print("  %-26s cached (%d runs)" % (name, len(have)))
            return out
    else:
        have = []
    done_seeds = {r["seed"] for r in have}
    seeds = [s for s in range(1000, 1000 + n_runs) if s not in done_seeds]
    if quick:
        cfg = dict(cfg, sampler="laplace")
        if cfg.get("inject") == "unconverged":
            cfg = dict(cfg)
    t0 = time.time()
    ctx = mp.get_context("fork") if sys.platform != "win32" else mp.get_context("spawn")
    results = list(have)
    with ctx.Pool(workers) as pool:
        for i, r in enumerate(pool.imap_unordered(_work, [(name, cfg, s) for s in seeds]), 1):
            results.append(r)
            _dump(results, out)   # one checkpoint per completed job
            if i % max(1, len(seeds) // 8) == 0 or i == len(seeds):
                el = time.time() - t0
                print("  %s %-26s %3d/%d  %5.0fs  eta %5.0fs%s" % (time.strftime("%H:%M:%S"), name, i, len(seeds), el, el / i * (len(seeds) - i),
                                                                  "  ERR" if r.get("error") else ""), flush=True)
    _dump(results, out)
    return out


def load_results(name: str) -> List[Dict[str, Any]]:
    p = RESULTS / ("%s.pkl" % name)
    if not p.exists():
        return []
    with open(p, "rb") as fh:
        return [r for r in pickle.load(fh)]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="comma-separated config names")
    ap.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2))))
    ap.add_argument("--report", action="store_true", help="aggregate only")
    ap.add_argument("--quick", action="store_true", help="6 runs per config with the laplace sampler")
    ap.add_argument("--runs", type=int, default=None, help="override runs per config")
    ap.add_argument("--m-coef", type=int, default=None, help="knot count for every config (the study behind FINDINGS_SYNTHETIC.md ran 24)")
    ap.add_argument("--hs-floor", type=float, default=None, help="tick floor on the likelihood tolerance, dollars (FINDINGS_TICKFLOOR.md)")
    ap.add_argument("--hs-floor-mode", default=None, choices=["max", "quad"])
    ap.add_argument("--results-dir", default=None, help="write/read results here instead of synth/results (e.g. synth/results48)")
    ap.add_argument("--findings", default=None, help="write the findings here instead of FINDINGS_SYNTHETIC.md")
    a = ap.parse_args(argv)
    global RESULTS, PLOTS
    if a.results_dir:
        RESULTS = Path(a.results_dir) if Path(a.results_dir).is_absolute() else HERE.parent / a.results_dir
        PLOTS = RESULTS.parent / (RESULTS.name.replace("results", "plots"))
    override = {k: v for k, v in (("m_coef", a.m_coef), ("hs_floor", a.hs_floor), ("hs_floor_mode", a.hs_floor_mode)) if v is not None}
    names = list(CONFIGS) if not a.only else [n.strip() for n in a.only.split(",")]
    if not a.report:
        for n in names:
            cfg, n_runs = CONFIGS[n]
            cfg = dict(cfg, **override)
            n_runs = 6 if a.quick else (a.runs or n_runs)
            run_config(n, cfg, n_runs, a.workers, quick=a.quick)
    from . import report
    summary = report.aggregate(names)
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "summary.json", "w") as fh:
        json.dump(summary, fh, indent=1, default=_json_default)
    report.plots(names, PLOTS)
    text = report.render(summary, PLOTS)
    findings = HERE.parent / (a.findings or "FINDINGS_SYNTHETIC.md")
    tmp = findings.with_suffix(".tmp")
    tmp.write_text(text)
    tmp.replace(findings)
    print("wrote", findings)
    return 0


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


if __name__ == "__main__":
    sys.exit(main())
