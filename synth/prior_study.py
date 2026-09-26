"""Part A of NightKing/HANDOFF_prior_fix.md: candidate priors on the log-density's second
differences, judged on the synthetic harness against the current Gaussian prior on the same
planted densities and the same seeds.

    candidates   t3   Student-t increments, nu = 3   (tau integrated by quadrature; no extra parameters)
                 t1   Student-t increments, nu = 1   (Cauchy; the heaviest tail)
                 hs   horseshoe: explicit local scales lambda_j ~ C+(0, 0.5), sampled non-centred
                      (the route the act3 docstring history warns about; run on a small subset so its
                      sampler diagnostics are on record)
    baseline     the Gaussian prior's runs already on disk (synth/results/<config>.pkl), restricted
                 to the seeds the candidates ran

Per-candidate results go to synth/results_prior/<cand>/<config>.pkl, checkpointed after every
job (atomic write) and resumed by default: a seed with status ok is never re-run, a seed whose
run raised is re-run, a seed absent was never attempted. Nothing here needs the network.

    python3 -m synth.prior_study                    # run every candidate (resumable), then report
    python3 -m synth.prior_study --cands t3         # one candidate
    python3 -m synth.prior_study --report           # aggregate what is on disk -> FINDINGS_PRIOR.md
    python3 -m synth.prior_study --quick            # 3 runs per config, laplace sampler (smoke)
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
from typing import Any, Dict, List, Optional, Tuple

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from . import runner  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = HERE / "results_prior"
PLOTS = HERE / "plots_prior"

CANDIDATES: Dict[str, Tuple[str, float, int]] = {"t3": ("student", 3.0, 24), "t1": ("student", 1.0, 24), "hs": ("horseshoe", 3.0, 24),
                                                 "m36": ("gauss", 3.0, 36), "m48": ("gauss", 3.0, 48), "m48t3": ("student", 3.0, 48),
                                                 "m64": ("gauss", 3.0, 64)}
CAND_LABEL = {"base": "Gaussian, 24 knots (current)", "t3": "Student-t ν=3, 24 knots", "t1": "Student-t ν=1, 24 knots", "hs": "horseshoe, 24 knots",
              "m36": "Gaussian, 36 knots", "m48": "Gaussian, 48 knots", "m48t3": "Student-t ν=3, 48 knots", "m64": "Gaussian, 64 knots"}
# configs and runs per config (the first n seeds of each; the baseline has >= these)
CONFIGS: Dict[str, int] = {
    "A_crude_full": 40, "B_lognormal_full": 40, "C_bimodal_full": 40, "C05_bimodal_halfnoise": 30, "F_bimodal_close": 30,
    "E_sharp_peak": 30, "G_spike_outside_prior": 30, "D_heavy_both": 30, "S08_crude": 30, "M_crude_nomart": 30,
    "X_fwd15": 30, "X_stale": 30, "X_convexity": 30, "X_truncated_grid": 30, "X_unconverged": 30,
}
CONFIGS_HS: Dict[str, int] = {"A_crude_full": 20, "C_bimodal_full": 20, "F_bimodal_close": 20, "S08_crude": 20}
CONFIGS_SMALL: Dict[str, int] = {"A_crude_full": 30, "B_lognormal_full": 30, "C_bimodal_full": 30, "C05_bimodal_halfnoise": 20, "F_bimodal_close": 20,
                                 "E_sharp_peak": 20, "G_spike_outside_prior": 20, "D_heavy_both": 20, "S08_crude": 20, "M_crude_nomart": 20,
                                 "X_fwd15": 20, "X_stale": 20, "X_convexity": 20, "X_truncated_grid": 20, "X_unconverged": 20}
CONFIGS_BLIND: Dict[str, int] = {"A_crude_full": 20, "C_bimodal_full": 20, "C05_bimodal_halfnoise": 20, "E_sharp_peak": 20, "G_spike_outside_prior": 20, "S08_crude": 20}
CONFIGS_BY_CAND = {"hs": CONFIGS_HS, "t1": CONFIGS_HS, "m36": CONFIGS_SMALL, "m48": CONFIGS_SMALL, "m48t3": CONFIGS_BLIND, "m64": CONFIGS_BLIND}
NOT_REGRESS = ["A_crude_full", "B_lognormal_full", "S08_crude", "M_crude_nomart", "X_fwd15", "X_stale", "X_convexity", "X_truncated_grid", "X_unconverged"]
MUST_IMPROVE = ["C_bimodal_full", "C05_bimodal_halfnoise", "G_spike_outside_prior", "E_sharp_peak"]


def _work(args):
    cand, name, cfg, seed = args
    from . import harness
    try:
        r = harness.run_one(cfg, seed)
        r["error"] = None
    except Exception as exc:
        import traceback
        r = {"seed": seed, "cfg": cfg, "error": repr(exc), "traceback": traceback.format_exc()}
    r["config"] = name
    r["candidate"] = cand
    return r


def _load(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "rb") as fh:
        return pickle.load(fh)


def _dump(rs: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump(rs, fh)
    os.replace(tmp, path)


def run_candidate(cand: str, workers: int, quick: bool = False, only: Optional[List[str]] = None) -> None:
    kind, nu, m = CANDIDATES[cand]
    configs = CONFIGS_BY_CAND.get(cand, CONFIGS)
    for name, n_runs in configs.items():
        if only and name not in only:
            continue
        cfg, _ = runner.CONFIGS[name]
        cfg = dict(cfg, prior=kind, nu=nu, m_coef=m)   # every candidate pins its own knot count; the baseline pickles were made at 24
        if quick:
            cfg = dict(cfg, sampler="laplace")
            n_runs = 3
        out = RESULTS / cand / ("%s.pkl" % name)
        have = _load(out)
        ok_seeds = {r["seed"] for r in have if r.get("error") is None}
        seeds = [s for s in range(1000, 1000 + n_runs) if s not in ok_seeds]
        if not seeds:
            print("  %-4s %-24s cached (%d ok)" % (cand, name, len(ok_seeds)), flush=True)
            continue
        results = [r for r in have if r.get("error") is None]
        t0 = time.time()
        ctx = mp.get_context("fork")
        with ctx.Pool(workers) as pool:
            for i, r in enumerate(pool.imap_unordered(_work, [(cand, name, cfg, s) for s in seeds]), 1):
                results.append(r)
                _dump(results, out)   # one checkpoint per completed job
                el = time.time() - t0
                print("  %s %-4s %-24s %3d/%d seed %d %s %5.0fs eta %5.0fs" % (
                    time.strftime("%H:%M:%S"), cand, name, i, len(seeds), r["seed"], "ERR" if r.get("error") else "ok", el, el / i * (len(seeds) - i)), flush=True)
                if r.get("error"):
                    print("      " + r["error"][:160], flush=True)


# --------------------------------------------------------------------------
# aggregate
# --------------------------------------------------------------------------

def _summ(rs: List[Dict[str, Any]]) -> Dict[str, Any]:
    from . import report
    return report.summarise_runs(rs)


def _metrics(S: Dict[str, Any], name: str) -> Dict[str, Any]:
    cb = S.get("coverage_bracket", {})
    ea = S.get("errors_act3", {})
    sm = S.get("sampler", {})
    ck = S.get("checks", {})
    fw = S.get("forward", {})
    g = lambda d, k: (d.get(k) if d else None)
    out = {
        "n": S.get("n_runs", 0), "n_errors": S.get("n_errors", 0),
        "cov90_all": g(cb.get("all"), "90"), "cov90_body": g(cb.get("body"), "90"), "cov90_tail": g(cb.get("tail"), "90"), "cov90_far": g(cb.get("far"), "90"),
        "cov50_all": g(cb.get("all"), "50"), "cov95_all": g(cb.get("all"), "95"),
        "rmse_body": g(ea.get("body"), "rmse_c"), "rmse_tail": g(ea.get("tail"), "rmse_c"), "bias_body": g(ea.get("body"), "bias_c"),
        "width_body": g(ea.get("body"), "width90_c"), "width_tail": g(ea.get("tail"), "width90_c"),
        "rhat_med": sm.get("rhat_max_median"), "rhat_p90": sm.get("rhat_max_p90"), "ess_med": sm.get("ess_min_median"), "ess_p10": sm.get("ess_min_p10"),
        "div_med": sm.get("divergences_median"), "brhat_med": sm.get("bracket_rhat_max_median"), "brhat_p90": sm.get("bracket_rhat_max_p90"),
        "bess_med": sm.get("bracket_ess_min_median"), "bess_p10": sm.get("bracket_ess_min_p10"),
        "chi2_med": ck.get("chi2_per_strike_median"), "frac_chi2_gt2": ck.get("frac_chi2_gt2"), "tau_med": ck.get("tau_median"),
        "seconds": S.get("seconds_per_run"),
        "modes_recovered": (S.get("modes") or {}).get("frac_recovered"), "modes_hist": (S.get("modes") or {}).get("post_modes_hist"),
        "stage14_bias": fw.get("posterior_mean_minus_true_cents_mean"), "stage14_z": fw.get("z_vs_true_abs_median"),
        "stage14_zused": fw.get("z_vs_used_abs_median"), "meanF_cov90": (S.get("coverage_meanF_posterior") or {}).get("90"),
        "fault_parity": fw.get("frac_parity_vs_used_gt3se"), "fault_zused": fw.get("frac_z_vs_used_gt3"),
        "fault_resid": ck.get("frac_inject_resid_gt3"), "fault_chi2": ck.get("frac_chi2_gt2"), "fault_edge": ck.get("frac_edge_mass_fail"),
        "fault_sampler": ck.get("frac_sampler_flagged"),
        "dens_body_rmse": ((S.get("density_err_act3") or {}).get("body") or {}).get("rmse_rel_peak"),
        "act2_disagree": (S.get("act2") or {}).get("vs_act3_max_abs_cents_median"),
    }
    bt = S.get("bimodal_trough")
    if bt:
        out.update({"trough_z": bt.get("z_median"), "trough_cov": bt.get("coverage90"), "trough_width": bt.get("width90_c_median")})
    return out


def aggregate(cands: List[str]) -> Dict[str, Any]:
    base_dir = runner.RESULTS
    out: Dict[str, Any] = {"cands": cands, "configs": {}, "unconverged_width_ratio": {}}
    for name in CONFIGS:
        cell: Dict[str, Any] = {}
        seeds_by_cand = {}
        for c in cands:
            rs = _load(RESULTS / c / ("%s.pkl" % name))
            if not rs:
                continue
            seeds_by_cand[c] = {r["seed"] for r in rs}
            cell[c] = _metrics(_summ(rs), name)
        if not cell:
            continue
        base_all = _load(base_dir / ("%s.pkl" % name))
        seeds = set.union(*seeds_by_cand.values()) if seeds_by_cand else set()
        base_rs = [r for r in base_all if r["seed"] in seeds]
        cell["base"] = _metrics(_summ(base_rs), name) if base_rs else {"n": 0}
        cell["base_full"] = _metrics(_summ(base_all), name) if base_all else {"n": 0}
        out["configs"][name] = cell
    # X_unconverged: band width relative to the converged run on the same seeds, per candidate
    for c in ["base"] + cands:
        conv = _load(RESULTS / c / "A_crude_full.pkl") if c != "base" else _load(base_dir / "A_crude_full.pkl")
        unc = _load(RESULTS / c / "X_unconverged.pkl") if c != "base" else _load(base_dir / "X_unconverged.pkl")
        cv = {r["seed"]: r for r in conv if r.get("error") is None}
        ratios = [float(np.mean(r["act3_bracket_width90"]) / max(np.mean(cv[r["seed"]]["act3_bracket_width90"]), 1e-12))
                  for r in unc if r.get("error") is None and r["seed"] in cv]
        if ratios:
            out["unconverged_width_ratio"][c] = float(np.median(ratios))
    # checklist per candidate
    out["checklist"] = {c: checklist(out, c) for c in cands}
    return out


def checklist(A: Dict[str, Any], c: str) -> Dict[str, Any]:
    C = A["configs"]
    g = lambda name, cand, k: (C.get(name, {}).get(cand, {}) or {}).get(k)
    items: Dict[str, Any] = {}

    def item(key, value, ok, ref=None):
        items[key] = {"value": value, "ok": None if value is None else bool(ok), "ref": ref}
    # must not regress (against the baseline on the same seeds; tolerance 3 points of coverage, 0.1c RMSE)
    item("A_cov90_all", g("A_crude_full", c, "cov90_all"), (g("A_crude_full", c, "cov90_all") or 0) >= (g("A_crude_full", "base", "cov90_all") or 0) - 0.03, g("A_crude_full", "base", "cov90_all"))
    item("A_cov90_body", g("A_crude_full", c, "cov90_body"), (g("A_crude_full", c, "cov90_body") or 0) >= (g("A_crude_full", "base", "cov90_body") or 0) - 0.03, g("A_crude_full", "base", "cov90_body"))
    item("A_cov90_tail", g("A_crude_full", c, "cov90_tail"), (g("A_crude_full", c, "cov90_tail") or 0) >= (g("A_crude_full", "base", "cov90_tail") or 0) - 0.03, g("A_crude_full", "base", "cov90_tail"))
    item("A_rmse_body", g("A_crude_full", c, "rmse_body"), (g("A_crude_full", c, "rmse_body") or 9) <= (g("A_crude_full", "base", "rmse_body") or 0) + 0.10, g("A_crude_full", "base", "rmse_body"))
    item("A_rmse_tail", g("A_crude_full", c, "rmse_tail"), (g("A_crude_full", c, "rmse_tail") or 9) <= (g("A_crude_full", "base", "rmse_tail") or 0) + 0.10, g("A_crude_full", "base", "rmse_tail"))
    item("B_cov90_all", g("B_lognormal_full", c, "cov90_all"), (g("B_lognormal_full", c, "cov90_all") or 0) >= (g("B_lognormal_full", "base", "cov90_all") or 0) - 0.03, g("B_lognormal_full", "base", "cov90_all"))
    item("S08_cov90_all", g("S08_crude", c, "cov90_all"), (g("S08_crude", c, "cov90_all") or 0) >= (g("S08_crude", "base", "cov90_all") or 0) - 0.03, g("S08_crude", "base", "cov90_all"))
    item("M_stage14_z", g("M_crude_nomart", c, "stage14_z"), (g("M_crude_nomart", c, "stage14_z") or 9) <= 1.5, g("M_crude_nomart", "base", "stage14_z"))
    item("X_fwd15_caught_parity", g("X_fwd15", c, "fault_parity"), (g("X_fwd15", c, "fault_parity") or 0) >= 0.95, g("X_fwd15", "base", "fault_parity"))
    item("X_stale_caught_resid", g("X_stale", c, "fault_resid"), (g("X_stale", c, "fault_resid") or 0) >= 0.90, g("X_stale", "base", "fault_resid"))
    item("X_convexity_caught_resid", g("X_convexity", c, "fault_resid"), (g("X_convexity", c, "fault_resid") or 0) >= 0.85, g("X_convexity", "base", "fault_resid"))
    item("X_truncated_caught_edge", g("X_truncated_grid", c, "fault_edge"), (g("X_truncated_grid", c, "fault_edge") or 0) >= 0.95, g("X_truncated_grid", "base", "fault_edge"))
    item("X_unconverged_caught", g("X_unconverged", c, "fault_sampler"), (g("X_unconverged", c, "fault_sampler") or 0) >= 0.95, g("X_unconverged", "base", "fault_sampler"))
    # sampler health gate: bracket R-hat median <= 1.03 and bracket ESS median >= 150 on the crude chains, divergences not worse than 2x
    item("A_bracket_rhat", g("A_crude_full", c, "brhat_med"), (g("A_crude_full", c, "brhat_med") or 9) <= max(1.03, (g("A_crude_full", "base", "brhat_med") or 1) + 0.01), g("A_crude_full", "base", "brhat_med"))
    item("A_bracket_ess", g("A_crude_full", c, "bess_med"), (g("A_crude_full", c, "bess_med") or 0) >= min(150.0, 0.75 * (g("A_crude_full", "base", "bess_med") or 0)), g("A_crude_full", "base", "bess_med"))
    # must improve
    item("C_trough_cov90", g("C_bimodal_full", c, "trough_cov"), (g("C_bimodal_full", c, "trough_cov") or 0) >= 0.80, g("C_bimodal_full", "base", "trough_cov"))
    item("C_trough_absz", None if g("C_bimodal_full", c, "trough_z") is None else abs(g("C_bimodal_full", c, "trough_z")),
         abs(g("C_bimodal_full", c, "trough_z") or 9) <= 2.0, g("C_bimodal_full", "base", "trough_z"))
    item("C_cov90_all", g("C_bimodal_full", c, "cov90_all"), (g("C_bimodal_full", c, "cov90_all") or 0) >= 0.80, g("C_bimodal_full", "base", "cov90_all"))
    item("G_cov90_all", g("G_spike_outside_prior", c, "cov90_all"), (g("G_spike_outside_prior", c, "cov90_all") or 0) >= 0.80, g("G_spike_outside_prior", "base", "cov90_all"))
    item("E_cov90_body", g("E_sharp_peak", c, "cov90_body"), (g("E_sharp_peak", c, "cov90_body") or 0) >= 0.80, g("E_sharp_peak", "base", "cov90_body"))
    regress = [k for k, v in items.items() if not k.startswith(("C_", "G_", "E_")) and v["ok"] is False]
    improve = [k for k, v in items.items() if k.startswith(("C_", "G_", "E_")) and v["ok"] is True]
    items["_summary"] = {"regressions": regress, "improvements": improve,
                         "verdict": ("REJECTED (regresses: %s)" % ", ".join(regress)) if regress else
                                    ("PASS" if len(improve) >= 4 else ("PARTIAL (%d of 5 improve targets met)" % len(improve) if improve else "NO IMPROVEMENT"))}
    return items


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------

def _pct(x):
    return "—" if x is None else "%.0f%%" % (100 * x)


def _f(x, fmt="%.2f"):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else fmt % x


def render(A: Dict[str, Any]) -> str:
    cands = ["base"] + A["cands"]
    C = A["configs"]
    L: List[str] = []
    L.append("# FINDINGS_PRIOR — locally adaptive priors on the log-density's second differences\n")
    L.append("Part A of `NightKing/HANDOFF_prior_fix.md`. Every candidate runs through the synthetic harness (`synth/prior_study.py`) on the same "
             "planted densities, real strike grids, noise model and seeds as `FINDINGS_SYNTHETIC.md`; the baseline row is the current Gaussian "
             "prior's runs on disk restricted to the same seeds, so every comparison is paired. Sampler: 4 × (400 + 400) NUTS, unchanged.\n")
    L.append("| candidate | prior on d = D2·θ | extra parameters | how τ is handled |\n|---|---|---|---|")
    L.append("| `base` | d_j ~ N(0, τ²) | none | integrated out (1-d quadrature) |")
    L.append("| `t3` | d_j ~ τ·t₃ (Gaussian with inverse-gamma local scale, integrated per increment) | none | integrated out (quadrature over a product of t densities) |")
    L.append("| `t1` | d_j ~ τ·t₁ (Cauchy increments) | none | as `t3` |")
    L.append("| `hs` | d_j = λ_j z_j, z_j ~ N(0,1), λ_j ~ C⁺(0, 0.5), non-centred | 22 log-scales | none (a global τ with local λ_j ran down the flat τ→0, λ→∞ ridge) |")
    L.append("| `m36` / `m48` | as `base` with 36 / 48 knots (0.47 / 0.35 vol-scales between knots instead of 0.7) | +12 / +24 coefficients | as `base` |")
    L.append("| `m48t3` | Student-t ν=3 increments on 48 knots | +24 coefficients | as `t3` |")
    L.append("| `m64` | as `base` with 64 knots (0.22 vol-scales between knots) | +40 coefficients | as `base` |\n")
    L.append("**VERDICT_PLACEHOLDER**\n")
    L.append("## 1. Checklist, per candidate\n")
    L.append("Must-not-regress items are judged against the baseline on the same seeds (coverage within 3 points, RMSE within 0.1¢, sampler within the "
             "stated gate); must-improve items against the fixed targets (coverage ≥ 80%, trough |z| ≤ 2). Tolerances were fixed before the runs.\n")
    keys = [k for k in next(iter(A["checklist"].values())).keys() if not k.startswith("_")] if A["checklist"] else []
    L.append("| item | baseline | " + " | ".join(CAND_LABEL[c] for c in A["cands"]) + " |\n|---|---|" + "---|" * len(A["cands"]))
    for k in keys:
        ref = next(iter(A["checklist"].values()))[k]["ref"]
        fmt = "%.2f" if any(s in k for s in ("rmse", "z", "rhat")) else ("%.0f" if "ess" in k else None)
        cell = lambda v: "—" if v is None else ((fmt % v) if fmt else _pct(v))
        row = [cell(ref)]
        for c in A["cands"]:
            it = A["checklist"][c][k]
            row.append("%s %s" % (cell(it["value"]), "" if it["ok"] is None else ("✓" if it["ok"] else "✗")))
        L.append("| %s | %s |" % (k, " | ".join(row)))
    L.append("| **verdict** | | " + " | ".join("**%s**" % A["checklist"][c]["_summary"]["verdict"] for c in A["cands"]) + " |")
    L.append("\n## 2. Bracket coverage and error, by planted density\n")
    L.append("90% bracket coverage (all / body ≥10¢ / tail 1–10¢), bracket RMSE (¢) body / tail, mean 90% band width (¢) body / tail, bias body (¢).\n")
    L.append("| config | candidate | n | cov90 all | body | tail | far | RMSE body | tail | width body | tail | bias body |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, cell in C.items():
        for c in cands:
            m = cell.get(c)
            if not m or not m.get("n"):
                continue
            L.append("| %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                name, CAND_LABEL[c], m["n"], _pct(m["cov90_all"]), _pct(m["cov90_body"]), _pct(m["cov90_tail"]), _pct(m["cov90_far"]), _f(m["rmse_body"]), _f(m["rmse_tail"]),
                _f(m["width_body"]), _f(m["width_tail"]), _f(m["bias_body"], "%+.2f")))
    L.append("\n## 3. The blind spot: bimodal, spiked and kinked truths\n")
    L.append("Trough = the bracket between the two humps where the truth is lowest: z of the posterior median against the truth (in units of the 90% "
             "band / 3.29), the band's width and whether it contains the truth. Modes = posterior-mean mode count matches the truth.\n")
    L.append("| config | candidate | n | trough z med | trough 90% width (¢) | trough coverage | cov90 all | cov90 body | modes recovered | posterior modes | density RMSE body (rel. peak) | τ med | χ²/strike med |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name in MUST_IMPROVE + ["F_bimodal_close", "D_heavy_both"]:
        cell = C.get(name, {})
        for c in cands:
            m = cell.get(c)
            if not m or not m.get("n"):
                continue
            L.append("| %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                name, CAND_LABEL[c], m["n"], _f(m.get("trough_z"), "%+.1f"), _f(m.get("trough_width")), _pct(m.get("trough_cov")), _pct(m["cov90_all"]), _pct(m["cov90_body"]),
                _pct(m["modes_recovered"]), m["modes_hist"], _f(m["dens_body_rmse"], "%.3f"), _f(m["tau_med"]), _f(m["chi2_med"])))
    L.append("\n## 4. Sampler health (the acceptance gate)\n")
    L.append("| config | candidate | n | R̂ max med (p90), raw | min ESS med (p10) | divergences med | bracket R̂ med (p90) | bracket ESS med (p10) | s / run |\n|---|---|---|---|---|---|---|---|---|")
    for name, cell in C.items():
        for c in cands:
            m = cell.get(c)
            if not m or not m.get("n"):
                continue
            L.append("| %s | %s | %d | %s (%s) | %s (%s) | %s | %s (%s) | %s (%s) | %s |" % (
                name, CAND_LABEL[c], m["n"], _f(m["rhat_med"], "%.3f"), _f(m["rhat_p90"], "%.3f"), _f(m["ess_med"], "%.0f"), _f(m["ess_p10"], "%.0f"), _f(m["div_med"], "%.0f"),
                _f(m["brhat_med"], "%.3f"), _f(m["brhat_p90"], "%.3f"), _f(m["bess_med"], "%.0f"), _f(m["bess_p10"], "%.0f"), _f(m["seconds"], "%.0f")))
    if A.get("unconverged_width_ratio"):
        L.append("\nX_unconverged band width relative to the converged run on the same seeds (median): " + ", ".join("%s %s" % (CAND_LABEL[c], _f(v)) for c, v in A["unconverged_width_ratio"].items()) + ".\n")
    L.append("\n## 5. Stage 14 and the injected faults\n")
    L.append("| config | candidate | n | Stage 14 bias (¢) | \\|z\\| vs truth med | E[F] 90% cov | parity flags the forward | z(used) > 3 | injected strike resid > 3 | χ² > 2 | edge-mass fails | sampler flagged |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name in ["M_crude_nomart", "X_fwd15", "X_stale", "X_convexity", "X_truncated_grid", "X_unconverged"]:
        cell = C.get(name, {})
        for c in cands:
            m = cell.get(c)
            if not m or not m.get("n"):
                continue
            L.append("| %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                name, CAND_LABEL[c], m["n"], _f(m["stage14_bias"], "%+.2f"), _f(m["stage14_z"]), _pct(m["meanF_cov90"]), _pct(m["fault_parity"]), _pct(m["fault_zused"]),
                _pct(m["fault_resid"]), _pct(m["fault_chi2"]), _pct(m["fault_edge"]), _pct(m["fault_sampler"])))
    L.append("\n## 6. Reading\n")
    L.append("READING_PLACEHOLDER\n")
    L.append("Plots: `synth/plots_prior/` — the planted bimodal, spike and kinked chains under each prior (same seed).\n")
    return "\n".join(L) + "\n"


def plots(cands: List[str]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    PLOTS.mkdir(parents=True, exist_ok=True)
    for name in ["C_bimodal_full", "G_spike_outside_prior", "E_sharp_peak", "A_crude_full", "F_bimodal_close"]:
        rows = {"base": [r for r in _load(runner.RESULTS / ("%s.pkl" % name)) if r.get("error") is None]}
        for c in cands:
            rows[c] = [r for r in _load(RESULTS / c / ("%s.pkl" % name)) if r.get("error") is None]
        seeds = set.intersection(*[{r["seed"] for r in v} for v in rows.values() if v]) if any(rows.values()) else set()
        if not seeds:
            continue
        seed = sorted(seeds)[0]
        n = len([c for c in rows if rows[c]])
        fig, axes = plt.subplots(1, n, figsize=(5.2 * n, 4), sharey=True)
        axes = np.atleast_1d(axes)
        i = 0
        for c in ["base"] + cands:
            rs = [r for r in rows.get(c, []) if r["seed"] == seed]
            if not rs:
                continue
            r = rs[0]
            ax = axes[i]
            i += 1
            s = r["act3_grid_s"]
            ax.fill_between(s, r["act3_grid_f_q"][0], r["act3_grid_f_q"][1], color="C0", alpha=0.25)
            ax.plot(s, r["act3_grid_f_mean"], "C0", lw=1.4, label="posterior mean, 90% band")
            ax.plot(s, r["true_grid_f"], "k--", lw=1.2, label="truth")
            ax.plot(r["K"], np.zeros_like(r["K"]), "|", color="gray", ms=10)
            ax.set_xlim(r["F0"] - 4 * r["std_true"], r["F0"] + 4 * r["std_true"])
            ax.set_title("%s — %s\nχ²/strike %.2f, R̂ %.3f, ESS %.0f, τ %.2f" % (name, CAND_LABEL[c], r["checks"]["chi2_per_strike"], r["act3_rhat_max"], r["act3_ess_min"], r["act3_tau_q"][1]), fontsize=8)
            ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(PLOTS / ("%s_seed%d.png" % (name, seed)), dpi=110)
        plt.close(fig)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cands", default=",".join(CANDIDATES))
    ap.add_argument("--only", default=None, help="comma-separated config names")
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    cands = [c.strip() for c in a.cands.split(",")]
    if not a.report:
        for c in cands:
            print("=== candidate %s (%s) %s" % (c, CAND_LABEL[c], time.strftime("%Y-%m-%d %H:%M:%S")), flush=True)
            run_candidate(c, a.workers, quick=a.quick, only=[x.strip() for x in a.only.split(",")] if a.only else None)
    all_c = [c for c in CANDIDATES if (RESULTS / c).exists()]
    A = aggregate(all_c)
    RESULTS.mkdir(parents=True, exist_ok=True)
    json.dump(A, open(RESULTS / "summary.json", "w"), indent=1, default=str)
    plots(all_c)
    text = render(A)
    p = ROOT / "FINDINGS_PRIOR.md"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(text)
    tmp.replace(p)
    print("wrote", p)
    for c in all_c:
        print(c, A["checklist"][c]["_summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
