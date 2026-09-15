"""Aggregate synthetic runs into coverage tables, plots, and FINDINGS_SYNTHETIC.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from . import runner

LEVELS = (50, 80, 90, 95)
Z = {50: 0.674, 80: 1.282, 90: 1.645, 95: 1.960}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _ok(name: str) -> List[Dict[str, Any]]:
    return [r for r in runner.load_results(name) if r.get("error") is None]


def bracket_region(p_true: np.ndarray) -> np.ndarray:
    """'body' >= 10c, 'tail' 1-10c (the 5-20c brackets the strategy wants), 'far' < 1c; the two
    open-ended brackets ('below'/'above' the ladder) are their own region."""
    reg = np.where(p_true >= 0.10, "body", np.where(p_true >= 0.01, "tail", "far")).astype(object)
    reg[0] = "open"
    reg[-1] = "open"
    return reg


def density_region(s_eval: np.ndarray, F0: float, std: float) -> np.ndarray:
    d = np.abs(s_eval - F0) / std
    return np.where(d <= 1.0, "body", np.where(d <= 2.5, "shoulder", "wing"))


def _cov_table(rs: List[Dict[str, Any]], key_cov: str, key_true: str, region_fn) -> Dict[str, Dict[str, float]]:
    """Pooled empirical coverage by region and level."""
    acc: Dict[str, Dict[int, List[bool]]] = {}
    for r in rs:
        cov = r[key_cov]
        if key_true == "p_true":
            reg = region_fn(r["p_true"])
        else:
            reg = region_fn(r["s_eval"], r["F0"], r["std_true"])
        for L in LEVELS:
            for g in ("all", "body", "tail", "far", "open", "shoulder", "wing"):
                mask = np.ones(len(reg), bool) if g == "all" else (reg == g)
                if not mask.any():
                    continue
                acc.setdefault(g, {}).setdefault(L, []).extend(list(cov[L][mask]))
    out: Dict[str, Dict[str, float]] = {}
    for g, d in acc.items():
        out[g] = {str(L): float(np.mean(v)) for L, v in d.items()}
        out[g]["n"] = int(len(next(iter(d.values()))))
    return out


def _err_table(rs: List[Dict[str, Any]], est_key: str) -> Dict[str, Dict[str, float]]:
    """Bias / RMSE / mean 90% width of bracket probabilities in cents, by region."""
    acc: Dict[str, Dict[str, List[float]]] = {}
    for r in rs:
        if est_key not in r:
            continue
        err = 100.0 * (np.asarray(r[est_key]) - r["p_true"])
        reg = bracket_region(r["p_true"])
        w = 100.0 * r["act3_bracket_width90"] if "act3_bracket_width90" in r else np.full(len(err), np.nan)
        for g in ("all", "body", "tail", "far", "open"):
            mask = np.ones(len(reg), bool) if g == "all" else (reg == g)
            if not mask.any():
                continue
            a = acc.setdefault(g, {"err": [], "w": [], "ptrue": []})
            a["err"].extend(err[mask].tolist())
            a["w"].extend(w[mask].tolist())
            a["ptrue"].extend((100 * r["p_true"][mask]).tolist())
    out = {}
    for g, a in acc.items():
        e = np.asarray(a["err"])
        out[g] = {"bias_c": float(e.mean()), "rmse_c": float(np.sqrt(np.mean(e ** 2))), "mae_c": float(np.abs(e).mean()),
                  "width90_c": float(np.nanmean(a["w"])), "mean_ptrue_c": float(np.mean(a["ptrue"])), "n": int(e.size)}
    return out


def _density_err(rs: List[Dict[str, Any]], est_key: str = "act3_density_mean") -> Dict[str, Dict[str, float]]:
    acc: Dict[str, List[float]] = {}
    for r in rs:
        if est_key not in r:
            continue
        reg = density_region(r["s_eval"], r["F0"], r["std_true"])
        f_true = r["f_true"]
        rel = (np.asarray(r[est_key]) - f_true) / max(f_true.max(), 1e-12)  # relative to the peak
        for g in ("all", "body", "shoulder", "wing"):
            mask = np.ones(len(reg), bool) if g == "all" else (reg == g)
            if mask.any():
                acc.setdefault(g, []).extend(rel[mask].tolist())
    return {g: {"bias_rel_peak": float(np.mean(v)), "rmse_rel_peak": float(np.sqrt(np.mean(np.square(v)))), "n": len(v)}
            for g, v in acc.items()}


def _frac(xs) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def _q(xs, q) -> Optional[float]:
    xs = [x for x in xs if x is not None and np.isfinite(x)]
    return float(np.percentile(xs, q)) if xs else None


# --------------------------------------------------------------------------
# aggregate
# --------------------------------------------------------------------------

def summarise_config(name: str) -> Dict[str, Any]:
    all_rs = runner.load_results(name)
    rs = [r for r in all_rs if r.get("error") is None]
    out: Dict[str, Any] = {"n_runs": len(rs), "n_errors": len(all_rs) - len(rs),
                           "errors": [r["error"] for r in all_rs if r.get("error")][:3]}
    if not rs:
        return out
    cfg = rs[0]["cfg"]
    out["cfg"] = {k: v for k, v in cfg.items() if k in ("family", "lookback", "n_strikes", "hs_source", "error", "noise_scale",
                                                        "martingale", "forward_offset", "extent_sd", "inject", "sampler",
                                                        "n_chains", "n_warmup", "n_samples", "hs_floor")}
    out["n_strikes"] = {"median": _q([r["n_strikes"] for r in rs], 50), "min": min(r["n_strikes"] for r in rs),
                        "max": max(r["n_strikes"] for r in rs)}
    out["seconds_per_run"] = _q([r["seconds"] for r in rs], 50)
    out["sampler"] = {
        "frac_converged": _frac([r["act3_converged"] for r in rs]),
        "rhat_max_median": _q([r["act3_rhat_max"] for r in rs], 50), "rhat_max_p90": _q([r["act3_rhat_max"] for r in rs], 90),
        "ess_min_median": _q([r["act3_ess_min"] for r in rs], 50), "ess_min_p10": _q([r["act3_ess_min"] for r in rs], 10),
        "divergences_median": _q([r["act3_divergences"] for r in rs], 50),
        "divergences_frac_runs_gt0": _frac([r["act3_divergences"] > 0 for r in rs]),
        "frac_rhat_gt_1_05": _frac([r["act3_rhat_max"] > 1.05 for r in rs]),
        # convergence of the delivered quantities
        "bracket_rhat_max_median": _q([r.get("act3_bracket_rhat_max") for r in rs], 50),
        "bracket_rhat_max_p90": _q([r.get("act3_bracket_rhat_max") for r in rs], 90),
        "bracket_ess_min_median": _q([r.get("act3_bracket_ess_min") for r in rs], 50),
        "bracket_ess_min_p10": _q([r.get("act3_bracket_ess_min") for r in rs], 10),
        "frac_bracket_rhat_lt_1_01": _frac([r.get("act3_bracket_rhat_max", 9) < 1.01 for r in rs]),
        "frac_bracket_ess_ge_400": _frac([r.get("act3_bracket_ess_min", 0) >= 400 for r in rs]),
        "meanF_ess_median": _q([r.get("act3_meanF_ess") for r in rs], 50),
    }
    out["coverage_bracket"] = _cov_table(rs, "act3_bracket_cov", "p_true", bracket_region)
    out["coverage_density"] = _cov_table(rs, "act3_density_cov", "f_true", density_region)
    out["coverage_forward_stage6"] = {str(L): _frac([r["forward_cov"][L] for r in rs]) for L in LEVELS}
    out["coverage_meanF_posterior"] = {str(L): _frac([bool(r["act3_meanF_cov"][L][0]) for r in rs]) for L in LEVELS}
    out["forward"] = {
        "err_cents_mean": float(np.mean([r["forward_err_cents"] for r in rs])),
        "err_cents_rmse": float(np.sqrt(np.mean([r["forward_err_cents"] ** 2 for r in rs]))),
        "se_cents_median": 100 * _q([r["se_F0"] for r in rs], 50),
        "D_err_median": _q([abs(r["D_hat"] - r["D_true"]) for r in rs], 50),
        "posterior_mean_minus_true_cents_mean": float(np.mean([r["checks"]["mean_vs_true_F_cents"] for r in rs])),
        "posterior_mean_minus_true_cents_sd": float(np.std([r["checks"]["mean_vs_true_F_cents"] for r in rs])),
        "posterior_sd_cents_median": 100 * _q([r["act3_meanF_sd"] for r in rs], 50),
        "z_vs_true_abs_median": _q([abs(r["checks"]["mean_vs_true_F_cents"] / 100.0 / max(r["act3_meanF_sd"], 1e-9)) for r in rs], 50),
        "z_vs_true_abs_p90": _q([abs(r["checks"]["mean_vs_true_F_cents"] / 100.0 / max(r["act3_meanF_sd"], 1e-9)) for r in rs], 90),
        "z_vs_used_abs_median": _q([abs(r["checks"]["mean_equals_forward_z"]) for r in rs], 50),
        "frac_z_vs_used_gt3": _frac([abs(r["checks"]["mean_equals_forward_z"]) > 3 for r in rs]),
        "frac_parity_vs_used_gt3se": _frac([abs(r["F0_used"] - r["F0_hat"]) > 3 * r["se_F0"] for r in rs]),
    }
    out["errors_act3"] = _err_table(rs, "act3_bracket_mean")
    out["errors_act2"] = _err_table(rs, "act2_bracket")
    out["density_err_act3"] = _density_err(rs, "act3_density_mean")
    out["density_err_act2"] = _density_err(rs, "act2_density_at")
    a2 = [r for r in rs if r.get("act2_ok")]
    out["act2"] = {
        "frac_ok": len(a2) / len(rs),
        "vs_act3_max_abs_cents_median": 100 * _q([r["act2_vs_act3_max_abs"] for r in a2], 50),
        "vs_act3_max_abs_cents_p90": 100 * _q([r["act2_vs_act3_max_abs"] for r in a2], 90),
        "frac_inside_act3_90": _frac([r["act2_inside_act3_90"] for r in a2]),
        "frac_density_nonneg": _frac([r["act2_checks"]["density_nonneg"] for r in a2]),
        "frac_normalised": _frac([r["act2_checks"]["normalised"] for r in a2]),
        "frac_min_g_neg": _frac([r["act2_svi"]["min_g"] < 0 for r in a2]),
        "mean_err_cents": float(np.mean([r["act2_mean"] - r["F0"] for r in a2]) * 100) if a2 else None,
    }
    out["checks"] = {
        "chi2_per_strike_median": _q([r["checks"]["chi2_per_strike"] for r in rs], 50),
        "chi2_per_strike_p90": _q([r["checks"]["chi2_per_strike"] for r in rs], 90),
        "chi2_map_per_strike_median": _q([r["checks"].get("chi2_map_per_strike") for r in rs], 50),
        "frac_chi2_gt2": _frac([r["checks"]["chi2_per_strike"] > 2.0 for r in rs]),
        "frac_max_resid_gt3": _frac([r["checks"]["max_abs_resid"] > 3.0 for r in rs]),
        "frac_edge_mass_fail": _frac([not r["checks"]["normalisation_edge_mass_ok"] for r in rs]),
        "edge_mass_median": _q([max(r["act3_edge_mass"]) for r in rs], 50),
        "edge_mass_p90": _q([max(r["act3_edge_mass"]) for r in rs], 90),
        "frac_sampler_flagged": _frac([not r["checks"]["sampler_ok"] for r in rs]),
        "parity_flagged_mean": float(np.mean([r["parity_flagged"] for r in rs])),
        "frac_inject_flagged_by_parity": _frac([r.get("inject_flagged_by_parity") for r in rs]),
        "frac_inject_resid_gt3": _frac([abs(r["inject_resid_z"]) > 3 for r in rs if r.get("inject_resid_z") is not None]) if any(r.get("inject_resid_z") is not None for r in rs) else None,
        "tau_median": _q([r["act3_tau_q"][1] for r in rs], 50),
    }
    out["modes"] = {
        "true": int(rs[0]["true_n_modes"]),
        "frac_recovered": _frac([r["act3_n_modes"] == r["true_n_modes"] for r in rs]),
        "post_modes_hist": {str(k): int(v) for k, v in zip(*np.unique([r["act3_n_modes"] for r in rs], return_counts=True))},
    }
    # bimodal trough: z-score of the truth at the brackets between the two humps
    if cfg["family"].startswith("bimodal"):
        zs, widths, covs = [], [], []
        for r in rs:
            p, q = r["p_true"], r["act3_bracket_q"]
            lo, hi = q[4], q[5]  # 90% pair (levels order 50,80,90,95 -> index 4,5)
            med = r["act3_bracket_median"]
            # trough brackets: between the two highest local maxima of p_true
            pk = [i for i in range(1, len(p) - 1) if p[i] > p[i - 1] and p[i] >= p[i + 1]]
            if len(pk) >= 2:
                i0, i1 = sorted(sorted(pk, key=lambda i: -p[i])[:2])
                tr = np.arange(i0 + 1, i1)
                if tr.size:
                    j = tr[np.argmin(p[tr])]
                    zs.append((med[j] - p[j]) / max((hi[j] - lo[j]) / 3.29, 1e-9))
                    widths.append(100 * (hi[j] - lo[j]))
                    covs.append(bool(lo[j] <= p[j] <= hi[j]))
        out["bimodal_trough"] = {"z_median": _q(zs, 50), "z_p90_abs": _q(np.abs(zs), 90), "width90_c_median": _q(widths, 50),
                                 "coverage90": _frac(covs), "n": len(zs)}
    return out


def aggregate(names: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {n: summarise_config(n) for n in names}
    # forward-offset sensitivity: pair each X_fwd config with the matching baseline by seed
    sens = {}
    base = {r["seed"]: r for r in _ok("A_crude_full")}
    base_nm = {r["seed"]: r for r in _ok("M_crude_nomart")}
    for n in names:
        if not n.startswith("X_fwd"):
            continue
        ref = base_nm if n.endswith("nomart") else base
        rs = _ok(n)
        if not rs:
            continue
        off = rs[0]["cfg"]["forward_offset"]
        d_all, d_max, analytic = [], [], []
        for r in rs:
            b = ref.get(r["seed"])
            if b is None:
                continue
            dp = 100.0 * (r["act3_bracket_mean"] - b["act3_bracket_mean"]) / off  # cents of bracket per cent of forward
            d_all.append(dp)
            d_max.append(np.abs(dp).max())
            # analytic location-shift sensitivity: f(a) - f(b) per bracket, in cents per cent
            e = r["edges"]
            f_e = np.interp(e, r["act3_grid_s"], r["true_grid_f"], left=0.0, right=0.0)
            an = np.concatenate([[-f_e[0]], f_e[:-1] - f_e[1:], [f_e[-1]]])
            analytic.append(np.abs(an).max())
        if d_all:
            d_all = np.array(d_all)
            sens[n] = {"offset_cents": off, "n_pairs": len(d_max), "max_abs_cents_per_cent_median": _q(d_max, 50),
                       "mean_abs_cents_per_cent": float(np.abs(d_all).mean()),
                       "analytic_max_cents_per_cent_median": _q(analytic, 50),
                       "chi2_per_strike_median": out[n]["checks"]["chi2_per_strike_median"],
                       "baseline_chi2_per_strike_median": out["A_crude_full"]["checks"]["chi2_per_strike_median"] if "A_crude_full" in out else None}
    out["_forward_sensitivity"] = sens
    # unconverged: band widths versus the converged baseline on the same seeds
    if "X_unconverged" in names and base:
        ratios = []
        for r in _ok("X_unconverged"):
            b = base.get(r["seed"])
            if b is not None:
                ratios.append(float(np.mean(r["act3_bracket_width90"]) / max(np.mean(b["act3_bracket_width90"]), 1e-12)))
        out["_unconverged_width_ratio"] = {"median": _q(ratios, 50), "p10": _q(ratios, 10), "p90": _q(ratios, 90), "n": len(ratios)}
    return out


# --------------------------------------------------------------------------
# plots
# --------------------------------------------------------------------------

def _pick_example(rs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The run whose 90% bracket coverage is closest to the config median (a typical run)."""
    covs = np.array([r["act3_bracket_cov"][90].mean() for r in rs])
    return rs[int(np.argmin(np.abs(covs - np.median(covs))))]


def plot_example(r: Dict[str, Any], path: Path, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 8), gridspec_kw={"height_ratios": [1.2, 1]})
    s = r["act3_grid_s"]
    a1.fill_between(s, r["act3_grid_f_q"][0], r["act3_grid_f_q"][1], color="C0", alpha=0.25, label="Act III 90% band")
    a1.plot(s, r["act3_grid_f_mean"], "C0", lw=1.5, label="Act III posterior mean")
    a1.plot(s, r["true_grid_f"], "k--", lw=1.5, label="planted truth")
    if r.get("act2_ok"):
        a1.plot(r["s_eval"], r["act2_density_at"], "C3.", ms=5, label="Act II (SVI)")
    a1.plot(r["K"], np.zeros_like(r["K"]), "|", color="gray", ms=12, label="strikes (%d)" % r["n_strikes"])
    lo = max(s[0], r["F0"] - 5 * r["std_true"])
    hi = min(s[-1], r["F0"] + 5 * r["std_true"])
    a1.set_xlim(lo, hi)
    a1.set_ylim(bottom=0)
    a1.set_ylabel("density (per $)")
    a1.set_title(title)
    a1.legend(loc="upper right", fontsize=8)
    mids = np.concatenate([[r["edges"][0] - 0.5], 0.5 * (r["edges"][1:] + r["edges"][:-1]), [r["edges"][-1] + 0.5]])
    q = r["act3_bracket_q"]
    a2.errorbar(mids, 100 * r["act3_bracket_median"], yerr=100 * np.vstack([r["act3_bracket_median"] - q[4], q[5] - r["act3_bracket_median"]]),
                fmt="o", color="C0", ms=4, capsize=2, label="Act III median, 90% band")
    a2.plot(mids, 100 * r["p_true"], "k_", ms=14, mew=2, label="truth")
    if r.get("act2_ok"):
        a2.plot(mids, 100 * r["act2_bracket"], "C3x", ms=6, label="Act II")
    a2.set_xlabel("Kalshi $1 bracket (open tails at the ends)")
    a2.set_ylabel("bracket probability (¢)")
    a2.legend(fontsize=8)
    a2.set_xlim(lo, hi)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plots(names: List[str], out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out_dir.mkdir(parents=True, exist_ok=True)
    have = {n: _ok(n) for n in names}
    have = {n: rs for n, rs in have.items() if rs}
    # 1. planted vs recovered examples
    for n in ("A_crude_full", "B_lognormal_full", "C_bimodal_full", "D_heavy_both", "E_sharp_peak", "F_bimodal_close",
              "G_spike_outside_prior", "S08_crude", "C05_bimodal_halfnoise"):
        if n in have:
            r = _pick_example(have[n])
            plot_example(r, out_dir / ("example_%s.png" % n),
                         "%s: %s, %s %s, %d strikes, F0=%.2f" % (n, r["cfg"]["family"], r["snapshot"]["root"], r["snapshot"]["settle_date"],
                                                                r["n_strikes"], r["F0"]))
    # 2. coverage curves
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, (key, ttl) in zip(axes, [("act3_bracket_cov", "bracket probabilities"), ("act3_density_cov", "density at grid points"),
                                    ("act3_meanF_cov", "posterior mean = forward")]):
        for n in ("A_crude_full", "B_lognormal_full", "C_bimodal_full", "S08_crude", "S23_crude", "NF_crude_tickfloor"):
            if n not in have:
                continue
            emp = [np.mean([np.mean(r[key][L]) for r in have[n]]) for L in LEVELS]
            ax.plot(LEVELS, [100 * e for e in emp], "o-", label=n)
        ax.plot([50, 95], [50, 95], "k--", lw=1)
        ax.set_xlabel("nominal (%)")
        ax.set_ylabel("empirical (%)")
        ax.set_title(ttl)
        ax.set_ylim(0, 100)
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "coverage_curves.png", dpi=120)
    plt.close(fig)
    # 3. error by bracket position
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for n in ("A_crude_full", "B_lognormal_full", "C_bimodal_full"):
        if n not in have:
            continue
        pos, err, w = [], [], []
        for r in have[n]:
            mids = np.concatenate([[r["edges"][0] - 0.5], 0.5 * (r["edges"][1:] + r["edges"][:-1]), [r["edges"][-1] + 0.5]])
            pos.extend(((mids - r["F0"]) / r["std_true"]).tolist())
            err.extend((100 * (r["act3_bracket_mean"] - r["p_true"])).tolist())
            w.extend((100 * r["act3_bracket_width90"]).tolist())
        pos, err, w = np.array(pos), np.array(err), np.array(w)
        bins = np.arange(-4.5, 4.6, 0.5)
        idx = np.digitize(pos, bins)
        c = 0.5 * (bins[1:] + bins[:-1])
        rmse = [np.sqrt(np.mean(err[idx == i] ** 2)) if np.any(idx == i) else np.nan for i in range(1, len(bins))]
        bias = [np.mean(err[idx == i]) if np.any(idx == i) else np.nan for i in range(1, len(bins))]
        ww = [np.mean(w[idx == i]) if np.any(idx == i) else np.nan for i in range(1, len(bins))]
        axes[0].plot(c, rmse, "o-", label="%s RMSE" % n)
        axes[0].plot(c, bias, "x--", alpha=0.6, label="%s bias" % n)
        axes[1].plot(c, ww, "o-", label=n)
    axes[0].axhline(0, color="k", lw=0.5)
    axes[0].set_xlabel("bracket midpoint − F0, in planted std units")
    axes[0].set_ylabel("bracket probability error (¢)")
    axes[0].set_title("Act III error by position")
    axes[0].legend(fontsize=7)
    axes[1].set_xlabel("bracket midpoint − F0, in planted std units")
    axes[1].set_ylabel("mean 90% band width (¢)")
    axes[1].set_title("band width by position")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "error_by_region.png", dpi=120)
    plt.close(fig)
    # 4. coverage / error vs strike count and vs noise
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    xs, cov90, rm, wd = [], [], [], []
    for n in ("S08_crude", "S12_crude", "S16_crude", "S23_crude", "A_crude_full"):
        if n in have:
            xs.append(np.median([r["n_strikes"] for r in have[n]]))
            cov90.append(100 * np.mean([np.mean(r["act3_bracket_cov"][90]) for r in have[n]]))
            rm.append(np.sqrt(np.mean([np.mean((100 * (r["act3_bracket_mean"] - r["p_true"])) ** 2) for r in have[n]])))
            wd.append(np.mean([np.mean(100 * r["act3_bracket_width90"]) for r in have[n]]))
    if xs:
        axes[0].plot(xs, cov90, "o-", label="90% bracket coverage (%)")
        axes[0].plot(xs, rm, "s-", label="bracket RMSE (¢)")
        axes[0].plot(xs, wd, "^-", label="mean 90% width (¢)")
        axes[0].axhline(90, color="k", ls="--", lw=0.8)
        axes[0].set_xlabel("strikes in chain (median of config)")
        axes[0].set_title("thinning toward the 8-strike gate")
        axes[0].legend(fontsize=8)
    xs, cov90, rm, wd = [], [], [], []
    for n in ("N05_crude", "A_crude_full", "N20_crude"):
        if n in have:
            xs.append(have[n][0]["cfg"]["noise_scale"])
            cov90.append(100 * np.mean([np.mean(r["act3_bracket_cov"][90]) for r in have[n]]))
            rm.append(np.sqrt(np.mean([np.mean((100 * (r["act3_bracket_mean"] - r["p_true"])) ** 2) for r in have[n]])))
            wd.append(np.mean([np.mean(100 * r["act3_bracket_width90"]) for r in have[n]]))
    if xs:
        axes[1].plot(xs, cov90, "o-", label="90% bracket coverage (%)")
        axes[1].plot(xs, rm, "s-", label="bracket RMSE (¢)")
        axes[1].plot(xs, wd, "^-", label="mean 90% width (¢)")
        axes[1].axhline(90, color="k", ls="--", lw=0.8)
        axes[1].set_xscale("log")
        axes[1].set_xlabel("half-spread multiplier")
        axes[1].set_title("noise scaling")
        axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "coverage_vs_strikes_and_noise.png", dpi=120)
    plt.close(fig)
    # 5. Stage 14 diagnostic histogram
    fig, ax = plt.subplots(figsize=(7, 4))
    for n in ("M_crude_nomart", "M_lognormal_nomart"):
        if n in have:
            z = [r["checks"]["mean_vs_true_F_cents"] / 100.0 / max(r["act3_meanF_sd"], 1e-9) for r in have[n]]
            ax.hist(z, bins=25, alpha=0.5, label="%s (n=%d)" % (n, len(z)))
    ax.set_xlabel("(posterior mean of E[F_T] − planted F0) / posterior sd, martingale constraint OFF")
    ax.set_title("Stage 14 diagnostic: does the mean land on F0 unaided?")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "stage14_diagnostic.png", dpi=120)
    plt.close(fig)
    # 6. forward-offset sensitivity
    base = {r["seed"]: r for r in have.get("A_crude_full", [])}
    fig, ax = plt.subplots(figsize=(8, 4))
    for n in ("X_fwd05", "X_fwd15", "X_fwd50"):
        if n not in have or not base:
            continue
        pos, dp = [], []
        for r in have[n]:
            b = base.get(r["seed"])
            if b is None:
                continue
            mids = np.concatenate([[r["edges"][0] - 0.5], 0.5 * (r["edges"][1:] + r["edges"][:-1]), [r["edges"][-1] + 0.5]])
            pos.extend(((mids - r["F0"]) / r["std_true"]).tolist())
            dp.extend((100 * (r["act3_bracket_mean"] - b["act3_bracket_mean"]) / r["cfg"]["forward_offset"]).tolist())
        ax.plot(pos, dp, ".", ms=3, alpha=0.4, label="%s: offset %d¢" % (n, have[n][0]["cfg"]["forward_offset"]))
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("bracket midpoint − F0 (planted std units)")
    ax.set_ylabel("Δ bracket price per ¢ of forward error (¢/¢)")
    ax.set_title("bracket sensitivity to a mis-specified forward (martingale constraint ON)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "forward_sensitivity.png", dpi=120)
    plt.close(fig)
    # 7. unconverged vs converged band widths
    if "X_unconverged" in have and base:
        fig, ax = plt.subplots(figsize=(7, 4))
        wu, wc = [], []
        for r in have["X_unconverged"]:
            b = base.get(r["seed"])
            if b is not None:
                wu.append(np.mean(100 * r["act3_bracket_width90"]))
                wc.append(np.mean(100 * b["act3_bracket_width90"]))
        ax.plot(wc, wu, "o", ms=4)
        m = max(max(wc, default=1), max(wu, default=1))
        ax.plot([0, m], [0, m], "k--", lw=1)
        ax.set_xlabel("mean 90% band width, converged (¢)")
        ax.set_ylabel("mean 90% band width, 5-iteration warmup (¢)")
        ax.set_title("unconverged chain: what the bands would have looked like")
        fig.tight_layout()
        fig.savefig(out_dir / "unconverged_bands.png", dpi=120)
        plt.close(fig)


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------

def _pct(x) -> str:
    return "—" if x is None else "%.0f%%" % (100 * x)


def _f(x, fmt="%.2f") -> str:
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else fmt % x


def cov_row(name: str, tab: Dict[str, Any], region: str) -> str:
    t = tab.get(region)
    if not t:
        return "| %s | %s | — | — | — | — | — |" % (name, region)
    return "| %s | %s | %s | %s | %s | %s | %d |" % (name, region, _pct(t.get("50")), _pct(t.get("80")), _pct(t.get("90")),
                                                    _pct(t.get("95")), t["n"])


def verdict(S: Dict[str, Any]) -> Dict[str, Any]:
    """Mechanical part of the verdict; the prose interprets it."""
    A = S.get("A_crude_full", {})
    B = S.get("B_lognormal_full", {})
    C = S.get("C_bimodal_full", {})
    M = S.get("M_crude_nomart", {})
    crit = {}

    def cov90(cfg, region="all"):
        return (cfg.get("coverage_bracket", {}).get(region, {}) or {}).get("90")
    for nm, cfg in (("A", A), ("B", B)):
        for reg in ("all", "body", "tail"):
            c = cov90(cfg, reg)
            crit["%s_bracket90_%s" % (nm, reg)] = (c, None if c is None else (0.85 <= c <= 0.97))
    if M.get("forward"):
        z = M["forward"]["z_vs_true_abs_median"]
        bias = M["forward"]["posterior_mean_minus_true_cents_mean"]
        crit["stage14_mean_lands_on_F0"] = ((bias, z), z is not None and z < 2.0 and abs(bias) < 2.0)
    for n in ("X_fwd05", "X_fwd15", "X_fwd50"):
        if n in S and S[n].get("forward"):
            f = S[n]["forward"]
            caught = (f["frac_parity_vs_used_gt3se"] or 0) > 0.9
            crit["caught_%s_by_parity" % n] = (f["frac_parity_vs_used_gt3se"], caught)
    for n in ("X_fwd05_nomart", "X_fwd15_nomart", "X_fwd50_nomart"):
        if n in S and S[n].get("forward"):
            f = S[n]["forward"]
            crit["caught_%s_by_meanF" % n] = (f["frac_z_vs_used_gt3"], (f["frac_z_vs_used_gt3"] or 0) > 0.9)
    if "X_truncated_grid" in S and S["X_truncated_grid"].get("checks"):
        v = S["X_truncated_grid"]["checks"]["frac_edge_mass_fail"]
        crit["caught_truncated_grid"] = (v, (v or 0) > 0.9)
    for n in ("X_convexity", "X_stale"):
        if n in S and S[n].get("checks"):
            ch = S[n]["checks"]
            v = max(ch["frac_inject_flagged_by_parity"] or 0, ch["frac_inject_resid_gt3"] or 0, ch["frac_chi2_gt2"] or 0)
            crit["caught_%s" % n] = ((ch["frac_inject_flagged_by_parity"], ch["frac_inject_resid_gt3"], ch["frac_chi2_gt2"]), v > 0.9)
    if "X_unconverged" in S and S["X_unconverged"].get("checks"):
        v = S["X_unconverged"]["checks"]["frac_sampler_flagged"]
        crit["caught_unconverged"] = (v, (v or 0) > 0.9)
    if C.get("bimodal_trough"):
        bt = C["bimodal_trough"]
        crit["bimodal_trough_covered90"] = (bt["coverage90"], (bt["coverage90"] or 0) >= 0.8)
        crit["bimodal_modes_recovered"] = (C["modes"]["frac_recovered"], (C["modes"]["frac_recovered"] or 0) >= 0.8)
    fails = [k for k, (v, ok) in crit.items() if ok is False]
    core = [k for k in fails if k.startswith(("A_bracket90", "B_bracket90", "stage14", "caught_"))]
    if not fails:
        v = "PASS"
    elif not core:
        v = "PASS WITH CAVEATS"
    else:
        # under-coverage or a missed failure mode in the core set
        v = "FAIL" if any(k.startswith(("caught_", "stage14")) for k in core) else "PASS WITH CAVEATS"
    return {"criteria": crit, "failed": fails, "verdict": v}


def render(S: Dict[str, Any], plot_dir: Path) -> str:
    V = verdict(S)
    rel = lambda p: str(Path(plot_dir).relative_to(Path(plot_dir).parent.parent) / p)  # noqa: E731
    L: List[str] = []
    L.append("# FINDINGS_SYNTHETIC — synthetic validation of the density extractor\n")
    L.append("**Verdict: %s** (mechanical criteria below; interpretation in §9).\n" % V["verdict"])
    L.append("Generated by `python3 -m synth.runner`. Every number below is computed from the run pickles in "
             "`synth/results/` (`summary.json` holds the aggregate). Truth is planted; the pipeline never sees it.\n")
    # setup
    A = S.get("A_crude_full", {})
    L.append("## 1. Setup\n")
    L.append("- Strike grids: real CME chains from `data_cme/` — for every weekly/monthly expiry that matched a Kalshi "
             "settlement date, the strikes with a fresh quote in the 60 minutes before 14:30 ET one (and two) business "
             "day(s) before expiry, OTM side only, forward from put-call parity on that snapshot (`synth/geometry.py`, "
             "cached in `synth/geometry.json`).")
    L.append("- Noise: half-spreads drawn from a power law in the option's own price fitted on every OTM quote in those "
             "snapshots (log hs = α + β log mid + ε), floored at the half-tick, then bid/ask rounded to $0.01 with a 1¢ "
             "bid floor exactly as the tape shows. Mid error ~ N(0, hs²) unless stated (\"uniform\" = truth inside the spread).")
    L.append("- Planted densities: crude-like skew with a fat upper tail (3-component lognormal mixture), Black-76 lognormal, "
             "bimodal (humps 2.6 vol-scales apart), close bimodal (1.6), Student-t (ν=3) in log space, Laplace (kink at "
             "the mode), and lognormal + narrow spike (truth outside the prior). Mean re-centred to F0 exactly.")
    L.append("- Vol scale per run = the real snapshot's ATM IV clipped to [0.25, 1.0]; T = 1 business day (or 2).")
    L.append("- Pipeline: Stage 6 parity regression (F0, D, se(F0), MAD outlier flags) → Stage 8 OTM → Stage 7 Black-76 IV → "
             "Act II SVI (vega²/hs² weights, Lee bound, g(k) check, $0.01 even grid, second difference) and Act III "
             "(24-coefficient cubic B-spline log-density, P-spline roughness prior with τ integrated out under a "
             "lognormal hyperprior, integrate-forward Gaussian likelihood with sd = half-spread, Stage 14 soft "
             "martingale constraint with sd = se(F0), NUTS with a dense metric). Brackets: $1-wide Kalshi ladder "
             "(`T79.99`-style edges) ±12 around F0 plus the two open tails.")
    if A:
        sm = A["sampler"]
        L.append("- Sampler per run: %d chains × (%d warmup + %d) NUTS; median %.0f s per run (7 processes in parallel). "
                 "Raw sampler coordinates: R̂ max median %.3f (p90 %.3f), min ESS median %.0f, divergences in %s of runs (median %s per run). "
                 "Delivered quantities (the %d bracket probabilities): R̂ max median %s (p90 %s), min ESS median %s (p10 %s); "
                 "runs with every bracket at R̂<1.01: %s, ESS≥400: %s.\n"
                 % (A["cfg"]["n_chains"], A["cfg"]["n_warmup"], A["cfg"]["n_samples"], A["seconds_per_run"] or 0,
                    sm["rhat_max_median"] or 0, sm["rhat_max_p90"] or 0, sm["ess_min_median"] or 0, _pct(sm["divergences_frac_runs_gt0"]),
                    _f(sm["divergences_median"], "%.0f"), 26, _f(sm["bracket_rhat_max_median"], "%.3f"), _f(sm["bracket_rhat_max_p90"], "%.3f"),
                    _f(sm["bracket_ess_min_median"], "%.0f"), _f(sm["bracket_ess_min_p10"], "%.0f"), _pct(sm["frac_bracket_rhat_lt_1_01"]),
                    _pct(sm["frac_bracket_ess_ge_400"])))
    # coverage tables
    L.append("## 2. Coverage (primary test)\n")
    L.append("Empirical frequency with which the central credible interval contains the planted value, pooled over runs "
             "and brackets/points. Bracket regions by true probability: body ≥10¢, tail 1–10¢, far <1¢. Density regions by "
             "distance from F0 in planted-std units: body ≤1, shoulder 1–2.5, wing >2.5.\n")
    L.append("### 2.1 Bracket probabilities (Act III)\n")
    L.append("| config | region | 50% | 80% | 90% | 95% | n |\n|---|---|---|---|---|---|---|")
    for n in ("A_crude_full", "B_lognormal_full", "C_bimodal_full", "D_heavy_both", "E_sharp_peak", "F_bimodal_close",
              "G_spike_outside_prior", "S08_crude", "S12_crude", "S16_crude", "S23_crude", "N05_crude", "N20_crude",
              "NU_crude_uniform", "NO_crude_observed_hs", "NF_crude_tickfloor", "L2_crude_2day", "M_crude_nomart"):
        if n in S and S[n].get("coverage_bracket"):
            for reg in ("all", "body", "tail", "far", "open"):
                L.append(cov_row(n, S[n]["coverage_bracket"], reg))
    L.append("\n### 2.2 Density at grid points (Act III)\n")
    L.append("| config | region | 50% | 80% | 90% | 95% | n |\n|---|---|---|---|---|---|---|")
    for n in ("A_crude_full", "B_lognormal_full", "C_bimodal_full", "S08_crude", "S23_crude", "N20_crude"):
        if n in S and S[n].get("coverage_density"):
            for reg in ("all", "body", "shoulder", "wing"):
                L.append(cov_row(n, S[n]["coverage_density"], reg))
    L.append("\n### 2.3 Forward\n")
    L.append("Stage 6: frequentist interval F̂0 ± z·se from the parity regression. Act III: central posterior interval of "
             "E[F_T] (with the martingale constraint on, this is dominated by the constraint; the honest test is the "
             "M_* rows, constraint off).\n")
    L.append("| config | quantity | 50% | 80% | 90% | 95% | err mean (¢) | err RMSE (¢) | se or sd (¢) |\n|---|---|---|---|---|---|---|---|---|")
    for n in ("A_crude_full", "B_lognormal_full", "C_bimodal_full", "S08_crude", "M_crude_nomart", "M_lognormal_nomart"):
        if n in S and S[n].get("forward"):
            f, c6, cp = S[n]["forward"], S[n]["coverage_forward_stage6"], S[n]["coverage_meanF_posterior"]
            L.append("| %s | Stage 6 F̂0 | %s | %s | %s | %s | %s | %s | %s |" % (n, _pct(c6["50"]), _pct(c6["80"]), _pct(c6["90"]), _pct(c6["95"]),
                                                                              _f(f["err_cents_mean"]), _f(f["err_cents_rmse"]), _f(f["se_cents_median"])))
            L.append("| %s | Act III E[F_T] | %s | %s | %s | %s | %s | %s | %s |" % (n, _pct(cp["50"]), _pct(cp["80"]), _pct(cp["90"]), _pct(cp["95"]),
                                                                                 _f(f["posterior_mean_minus_true_cents_mean"]), _f(f["posterior_mean_minus_true_cents_sd"]),
                                                                                 _f(f["posterior_sd_cents_median"])))
    # errors
    L.append("\n## 3. Bias and RMSE by region\n")
    L.append("Bracket probability error = estimate − truth, in cents of Kalshi price (1¢ = 0.01 probability). Width = mean 90% band.\n")
    L.append("| config | route | region | bias (¢) | RMSE (¢) | MAE (¢) | 90% width (¢) | mean true (¢) | n |\n|---|---|---|---|---|---|---|---|---|")
    for n in ("A_crude_full", "B_lognormal_full", "C_bimodal_full", "D_heavy_both", "E_sharp_peak", "S08_crude", "S23_crude",
              "N05_crude", "N20_crude", "NU_crude_uniform", "NF_crude_tickfloor", "L2_crude_2day"):
        if n not in S or not S[n].get("errors_act3"):
            continue
        for route, key in (("Act III", "errors_act3"), ("Act II", "errors_act2")):
            for reg in ("body", "tail", "far", "open"):
                t = S[n][key].get(reg)
                if t:
                    L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %d |" % (n, route, reg, _f(t["bias_c"]), _f(t["rmse_c"]), _f(t["mae_c"]),
                                                                            _f(t["width90_c"]) if route == "Act III" else "—", _f(t["mean_ptrue_c"], "%.1f"), t["n"]))
    L.append("\nDensity error relative to the peak of the planted density (posterior mean − truth) / max f:\n")
    L.append("| config | route | body | shoulder | wing |\n|---|---|---|---|---|")
    for n in ("A_crude_full", "B_lognormal_full", "C_bimodal_full", "S08_crude"):
        if n in S and S[n].get("density_err_act3"):
            for route, key in (("Act III", "density_err_act3"), ("Act II", "density_err_act2")):
                d = S[n][key]
                L.append("| %s | %s | %s | %s | %s |" % (n, route, *["bias %s / RMSE %s" % (_f(d[g]["bias_rel_peak"], "%.3f"), _f(d[g]["rmse_rel_peak"], "%.3f")) if g in d else "—"
                                                               for g in ("body", "shoulder", "wing")]))
    # stage 14
    L.append("\n## 4. Stage 14 diagnostic — does the posterior mean land on F0 unaided?\n")
    for n in ("M_crude_nomart", "M_lognormal_nomart"):
        if n in S and S[n].get("forward"):
            f = S[n]["forward"]
            L.append("- **%s** (n=%d): posterior mean of E[F_T] − planted F0 = %.2f ¢ on average (sd across runs %.2f ¢); "
                     "posterior sd of E[F_T] median %.2f ¢; |z| median %.2f, p90 %.2f; Stage 6 F̂0 error RMSE %.2f ¢ (se median %.2f ¢)."
                     % (n, S[n]["n_runs"], f["posterior_mean_minus_true_cents_mean"], f["posterior_mean_minus_true_cents_sd"],
                        f["posterior_sd_cents_median"], f["z_vs_true_abs_median"], f["z_vs_true_abs_p90"], f["err_cents_rmse"], f["se_cents_median"]))
    c = V["criteria"].get("stage14_mean_lands_on_F0")
    if c:
        L.append("\n**Result: %s** — criterion |bias| < 2¢ and median |z| < 2 %s. Plot: `%s`.\n"
                 % ("YES, the mean lands on F0 without the constraint" if c[1] else "NO", "met" if c[1] else "not met", rel("stage14_diagnostic.png")))
    # act II vs III
    L.append("## 5. Act II (SVI) vs Act III (Bayesian)\n")
    L.append("| config | Act II fits | max |Δ bracket| median (¢) | p90 (¢) | Act II inside Act III 90% band | Act II density ≥0 | SVI g(k)<0 | Act II RMSE body/tail (¢) | Act III RMSE body/tail (¢) |\n|---|---|---|---|---|---|---|---|---|")
    for n in ("A_crude_full", "B_lognormal_full", "C_bimodal_full", "D_heavy_both", "E_sharp_peak", "S08_crude", "S23_crude", "N20_crude"):
        if n in S and S[n].get("act2"):
            a, e2, e3 = S[n]["act2"], S[n]["errors_act2"], S[n]["errors_act3"]
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s / %s | %s / %s |" % (
                n, _pct(a["frac_ok"]), _f(a["vs_act3_max_abs_cents_median"]), _f(a["vs_act3_max_abs_cents_p90"]), _pct(a["frac_inside_act3_90"]),
                _pct(a["frac_density_nonneg"]), _pct(a["frac_min_g_neg"]),
                _f(e2.get("body", {}).get("rmse_c")), _f(e2.get("tail", {}).get("rmse_c")),
                _f(e3.get("body", {}).get("rmse_c")), _f(e3.get("tail", {}).get("rmse_c"))))
    # failure modes
    L.append("\n## 6. Injected failure modes\n")
    L.append("| failure mode | config | detector | fired in | caught? |\n|---|---|---|---|---|")
    sens = S.get("_forward_sensitivity", {})
    for n in ("X_fwd05", "X_fwd15", "X_fwd50"):
        if n in S and S[n].get("forward"):
            f, ch = S[n]["forward"], S[n]["checks"]
            L.append("| forward offset %d¢ (constraint ON) | %s | parity F̂0 vs supplied F0 > 3 se | %s | %s |" % (
                S[n]["cfg"]["forward_offset"], n, _pct(f["frac_parity_vs_used_gt3se"]), "yes" if (f["frac_parity_vs_used_gt3se"] or 0) > 0.9 else "NO"))
            L.append("| | | χ²/strike > 2 (constraint fights the quotes) | %s (median χ²/strike %s vs baseline %s) | %s |" % (
                _pct(ch["frac_chi2_gt2"]), _f(ch["chi2_per_strike_median"]), _f((S.get("A_crude_full", {}).get("checks") or {}).get("chi2_per_strike_median")),
                "yes" if (ch["frac_chi2_gt2"] or 0) > 0.9 else "no"))
    for n in ("X_fwd05_nomart", "X_fwd15_nomart", "X_fwd50_nomart"):
        if n in S and S[n].get("forward"):
            f = S[n]["forward"]
            L.append("| forward offset %d¢ (constraint OFF) | %s | mean-equals-forward: |E[F_T] − supplied F0| > 3 posterior sd | %s (median |z| %s) | %s |" % (
                S[n]["cfg"]["forward_offset"], n, _pct(f["frac_z_vs_used_gt3"]), _f(f["z_vs_used_abs_median"], "%.1f"), "yes" if (f["frac_z_vs_used_gt3"] or 0) > 0.9 else "NO"))
    if "X_truncated_grid" in S and S["X_truncated_grid"].get("checks"):
        ch = S["X_truncated_grid"]["checks"]
        L.append("| truncated integration grid (±1.5 vol-scales) | X_truncated_grid | mass in outer 2.5%% of grid > 1%% | %s (median edge mass %s; baseline %s) | %s |" % (
            _pct(ch["frac_edge_mass_fail"]), _f(ch["edge_mass_median"], "%.3f"), _f((S.get("A_crude_full", {}).get("checks") or {}).get("edge_mass_median"), "%.5f"),
            "yes" if (ch["frac_edge_mass_fail"] or 0) > 0.9 else "NO"))
        L.append("| | | χ²/strike > 2 | %s | %s |" % (_pct(ch["frac_chi2_gt2"]), "yes" if (ch["frac_chi2_gt2"] or 0) > 0.9 else "no"))
    for n, label in (("X_convexity", "convexity violation (one call quote pushed above its neighbours)"), ("X_stale", "stale quote (one call quote left far below)")):
        if n in S and S[n].get("checks"):
            ch = S[n]["checks"]
            L.append("| %s | %s | Stage 6 parity residual (MAD z > 4) | %s | %s |" % (label, n, _pct(ch["frac_inject_flagged_by_parity"]), "yes" if (ch["frac_inject_flagged_by_parity"] or 0) > 0.9 else "no"))
            L.append("| | | Act III posterior-predictive residual at that strike > 3 sd | %s | %s |" % (_pct(ch["frac_inject_resid_gt3"]), "yes" if (ch["frac_inject_resid_gt3"] or 0) > 0.9 else "no"))
            L.append("| | | χ²/strike > 2 | %s | %s |" % (_pct(ch["frac_chi2_gt2"]), "yes" if (ch["frac_chi2_gt2"] or 0) > 0.9 else "no"))
            if S[n].get("act2"):
                L.append("| | | Act II vs Act III max |Δ| (median) | %s ¢ (baseline %s ¢) | — |" % (
                    _f(S[n]["act2"]["vs_act3_max_abs_cents_median"]), _f((S.get("A_crude_full", {}).get("act2") or {}).get("vs_act3_max_abs_cents_median"))))
    if "X_unconverged" in S and S["X_unconverged"].get("checks"):
        ch, sm = S["X_unconverged"]["checks"], S["X_unconverged"]["sampler"]
        wr = S.get("_unconverged_width_ratio", {})
        L.append("| unconverged chain (2 chains, 5 warmup, 40 draws) | X_unconverged | R̂ ≥ 1.01 or ESS < 400 or divergences | %s (R̂ max median %s, ESS min median %s) | %s |" % (
            _pct(ch["frac_sampler_flagged"]), _f(sm["rhat_max_median"], "%.3f"), _f(sm["ess_min_median"], "%.0f"), "yes" if (ch["frac_sampler_flagged"] or 0) > 0.9 else "NO"))
        if wr:
            L.append("| | | band width vs converged run on the same seeds | median ratio %s (p10 %s, p90 %s) | — |" % (_f(wr["median"]), _f(wr["p10"]), _f(wr["p90"])))
    if "G_spike_outside_prior" in S and S["G_spike_outside_prior"].get("checks"):
        ch = S["G_spike_outside_prior"]["checks"]
        cb = S["G_spike_outside_prior"]["coverage_bracket"].get("all", {})
        L.append("| truth outside the prior (20%% mass in a spike 0.05 vol-scales wide) | G_spike_outside_prior | χ²/strike > 2 | %s (median %s) | %s |" % (
            _pct(ch["frac_chi2_gt2"]), _f(ch["chi2_per_strike_median"]), "yes" if (ch["frac_chi2_gt2"] or 0) > 0.9 else "no"))
        L.append("| | | 90%% bracket coverage | %s | — |" % _pct(cb.get("90")))
    # bimodal
    L.append("\n## 7. The bimodal test\n")
    for n in ("C_bimodal_full", "F_bimodal_close", "C05_bimodal_halfnoise"):
        if n in S and S[n].get("bimodal_trough"):
            bt, md, cb = S[n]["bimodal_trough"], S[n]["modes"], S[n]["coverage_bracket"]
            L.append("- **%s** (n=%d, noise ×%s): posterior mean density shows two humps in %s of runs (histogram of mode counts %s). "
                     "At the trough bracket the posterior median overstates the truth by z = %s (median; p90 |z| %s), the 90%% band is %s ¢ wide "
                     "and contains the truth in %s of runs. Overall 90%% bracket coverage %s (body %s, tail %s). χ²/strike median %s — the fit is "
                     "consistent with the quotes."
                     % (n, S[n]["n_runs"], S[n]["cfg"]["noise_scale"], _pct(md["frac_recovered"]), md["post_modes_hist"], _f(bt["z_median"], "%+.1f"),
                        _f(bt["z_p90_abs"], "%.1f"), _f(bt["width90_c_median"]), _pct(bt["coverage90"]), _pct(cb.get("all", {}).get("90")),
                        _pct(cb.get("body", {}).get("90")), _pct(cb.get("tail", {}).get("90")), _f(S[n]["checks"]["chi2_per_strike_median"])))
    # sensitivity
    L.append("\n## 8. Sensitivity of bracket probabilities to forward error\n")
    L.append("Paired by seed with the unshifted run. ¢/¢ = change in a bracket's price in cents per cent of forward error. "
             "The analytic location-shift value is f(a) − f(b) for edges a, b (per dollar, which is the same number in ¢/¢).\n")
    L.append("| config | offset (¢) | max over brackets, median run (¢/¢) | mean |Δ| over brackets (¢/¢) | analytic max f(a)−f(b) | χ²/strike (median) |\n|---|---|---|---|---|---|")
    for n, s in sens.items():
        L.append("| %s | %d | %s | %s | %s | %s (baseline %s) |" % (n, s["offset_cents"], _f(s["max_abs_cents_per_cent_median"], "%.3f"), _f(s["mean_abs_cents_per_cent"], "%.3f"),
                                                                 _f(s["analytic_max_cents_per_cent_median"], "%.3f"), _f(s["chi2_per_strike_median"]), _f(s["baseline_chi2_per_strike_median"])))
    L.append("\n## 9. Verdict: %s\n" % V["verdict"])
    L.append("Mechanical criteria (value, met):\n")
    for k, (v, ok) in V["criteria"].items():
        L.append("- `%s`: %s → %s" % (k, _fmt_val(v), "met" if ok else ("NOT met" if ok is False else "n/a")))
    L.append("\nPlots: " + ", ".join("`%s`" % rel(p.name) for p in sorted(Path(plot_dir).glob("*.png"))) + "\n")
    return "\n".join(L) + "\n"


def _fmt_val(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, (tuple, list)):
        return "(" + ", ".join(_fmt_val(x) for x in v) + ")"
    if isinstance(v, (float, np.floating)):
        return "%.3f" % v
    return str(v)
