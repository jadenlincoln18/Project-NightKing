"""Aggregate the real-chain runs (synth/realchain.py) into FINDINGS_REALCHAIN.md and plots.

Descriptive only: shapes, detector firing, the three checks, sampler health, the parity
forward against CME settlement, and where real chains differ from the synthetic ones.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from . import detector

HERE = Path(__file__).resolve().parent


def _q(xs, q) -> Optional[float]:
    xs = [x for x in xs if x is not None and np.isfinite(x)]
    return float(np.percentile(xs, q)) if xs else None


def _frac(xs) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def _pct(x) -> str:
    return "—" if x is None else "%.0f%%" % (100 * x)


def _f(x, fmt="%.2f") -> str:
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else fmt % x


def _synth_baseline() -> Dict[str, Any]:
    p = HERE / "results" / "summary.json"
    if not p.exists():
        return {}
    S = json.load(open(p))
    A = S.get("A_crude_full", {})
    return {"sampler": A.get("sampler", {}), "checks": A.get("checks", {}), "act2": A.get("act2", {}),
            "seconds_per_run": A.get("seconds_per_run"), "forward": A.get("forward", {})}


# --------------------------------------------------------------------------
# aggregate
# --------------------------------------------------------------------------

def aggregate(rs: List[Dict[str, Any]]) -> Dict[str, Any]:
    ok = [r for r in rs if r.get("error") is None]
    out: Dict[str, Any] = {"n_runs": len(rs), "n_errors": len(rs) - len(ok), "errors": [r["error"] for r in rs if r.get("error")][:5],
                           "dates": sorted({r["settle_date"] for r in rs}), "synthetic_baseline": _synth_baseline()}
    by_key: Dict[str, Dict[str, Any]] = {}
    for snap in ("T-2d", "T-1d", "T-4h", "T-0"):
        for w in (60, 10):
            sub = [r for r in ok if r["snap"] == snap and r.get("window_min", 60) == w]
            g = [r for r in sub if r.get("gate0")]
            ext = [r for r in g if "act3_bracket_mean" in r]
            key = "%s_w%d" % (snap, w)
            d: Dict[str, Any] = {
                "n": len(sub), "n_gate0": len(g), "n_gate0_pooled": sum(1 for r in sub if r.get("gate0_pooled")), "n_extracted": len(ext),
                "n_quoted_strikes_median": _q([r.get("n_quoted_strikes") for r in sub], 50),
                "n_otm_strikes_median": _q([r.get("n_strikes") for r in g], 50),
                "two_sided_median": _q([r.get("two_sided_strikes") for r in g], 50),
                "quote_age_median_min": _q([r.get("quote_age_median_min") for r in g], 50),
                "frac_bid_1c_median": _q([r.get("frac_bid_1c") for r in g], 50),
                "hs_median_cents": 100 * (_q([r.get("hs_median") for r in g], 50) or 0),
                "hs_log_ratio_to_model_median": _q([r.get("hs_log_ratio_to_model_median") for r in g], 50),
                "parity_pairs_median": _q([r.get("parity_pairs") for r in g], 50),
                "se_F0_cents_median": 100 * (_q([r.get("se_F0") for r in g], 50) or 0),
                "parity_flagged_frac": _frac([r.get("parity_flagged", 0) > 0 for r in g]),
                "contract_month_match_frac": _frac([r.get("contract_month_match") for r in g]),
            }
            pm = [r.get("parity_minus_nymex_cents") for r in g if r.get("parity_minus_nymex_cents") is not None]
            if pm:
                z = [r["parity_minus_nymex_cents"] / (100 * max(r["se_F0"], 1e-6)) for r in g if r.get("parity_minus_nymex_cents") is not None]
                d["parity_vs_nymex"] = {"n": len(pm), "mean_c": float(np.mean(pm)), "median_c": float(np.median(pm)), "mad_c": float(np.median(np.abs(np.array(pm) - np.median(pm)))),
                                        "rmse_c": float(np.sqrt(np.mean(np.square(pm)))), "p10_c": float(np.percentile(pm, 10)), "p90_c": float(np.percentile(pm, 90)),
                                        "frac_within_3se": float(np.mean(np.abs(z) < 3)), "frac_within_10c": float(np.mean(np.abs(pm) < 10)),
                                        "frac_within_25c": float(np.mean(np.abs(pm) < 25))}
            pi = [r.get("parity_minus_ice_cents") for r in g if r.get("parity_minus_ice_cents") is not None]
            if pi:
                d["parity_vs_ice"] = {"n": len(pi), "mean_c": float(np.mean(pi)), "rmse_c": float(np.sqrt(np.mean(np.square(pi)))),
                                      "frac_within_10c": float(np.mean(np.abs(np.array(pi)) < 10))}
            if ext:
                det = [r["detector"] for r in ext]
                d.update({
                    "atm_sigma_median": _q([r["atm_sigma"] for r in ext], 50), "atm_sigma_p10": _q([r["atm_sigma"] for r in ext], 10),
                    "atm_sigma_p90": _q([r["atm_sigma"] for r in ext], 90),
                    "std_dollars_median": _q([r["act3_std_dollars"] for r in ext], 50),
                    "skew_median": _q([r["act3_skew"] for r in ext], 50), "skew_frac_positive": _frac([r["act3_skew"] > 0 for r in ext]),
                    "modes_hist": {str(k): int(v) for k, v in zip(*np.unique([r["act3_n_modes"] for r in ext], return_counts=True))},
                    "modes_hist_unconstrained": {str(k): int(v) for k, v in zip(*np.unique([r["act3u_n_modes"] for r in ext], return_counts=True))},
                    "frac_draws_multimodal_median": _q([r["act3_frac_draws_multimodal"] for r in ext], 50),
                    "frac_runs_multimodal_majority": _frac([r["act3_frac_draws_multimodal"] > 0.5 for r in ext]),
                    "detector_fired_frac": _frac([x["fired"] for x in det]), "detector_fired_trusted_frac": _frac([x["fired"] for x in det if x["trusted"]]),
                    "detector_cents_median": _q([x["cents"] for x in det], 50), "detector_cents_p90": _q([x["cents"] for x in det], 90),
                    "detector_cents_max": max([x["cents"] for x in det if x["cents"] is not None] or [0.0]),
                    "act2_ok_frac": _frac([r["act2_ok"] for r in ext]),
                    "checks": {k: _frac([r["checks"].get(k) for r in ext]) for k in ("act2_butterfly_free", "act2_density_nonneg", "act2_normalised",
                                                                                     "act2_mean_equals_forward", "act3_normalisation_edge_mass_ok", "act3_chi2_ok",
                                                                                     "act3_max_resid_ok", "mean_equals_forward_ok", "sampler_ok", "sampler_bracket_ok")},
                    "mean_equals_forward_z_abs_median": _q([abs(r["checks"]["mean_equals_forward_z"]) for r in ext], 50),
                    "act3u_mean_minus_F0_cents_median": _q([r["act3u_mean_minus_F0_cents"] for r in ext], 50),
                    "act3u_mean_minus_F0_cents_mad": float(np.median(np.abs(np.array([r["act3u_mean_minus_F0_cents"] for r in ext]) - np.median([r["act3u_mean_minus_F0_cents"] for r in ext])))),
                    "chi2_per_strike_median": _q([r["act3_chi2_per_strike"] for r in ext], 50), "chi2_per_strike_p90": _q([r["act3_chi2_per_strike"] for r in ext], 90),
                    "max_abs_resid_median": _q([r["act3_max_abs_resid"] for r in ext], 50),
                    "tau_median": _q([r["act3_tau_q"][1] for r in ext], 50),
                    "edge_mass_median": _q([float(np.max(r["act3_edge_mass"])) for r in ext], 50),
                    "sampler": {"rhat_max_median": _q([r["act3_rhat_max"] for r in ext], 50), "rhat_max_p90": _q([r["act3_rhat_max"] for r in ext], 90),
                                "ess_min_median": _q([r["act3_ess_min"] for r in ext], 50), "divergences_median": _q([r["act3_divergences"] for r in ext], 50),
                                "bracket_rhat_max_median": _q([r["act3_bracket_rhat_max"] for r in ext], 50), "bracket_rhat_max_p90": _q([r["act3_bracket_rhat_max"] for r in ext], 90),
                                "bracket_ess_min_median": _q([r["act3_bracket_ess_min"] for r in ext], 50),
                                "frac_bracket_rhat_lt_1_05": _frac([r["act3_bracket_rhat_max"] < 1.05 for r in ext]),
                                "seconds_median": _q([r["act3_seconds"] for r in ext], 50)},
                    "width90_body_cents_median": _q([100 * float(np.max(r["act3_bracket_width90"])) for r in ext], 50),
                })
                # what the detector fires on
                fired = [r for r in ext if r["detector"]["fired"]]
                quiet = [r for r in ext if not r["detector"]["fired"]]
                d["fired_vs_quiet"] = {
                    "n_fired": len(fired), "n_quiet": len(quiet),
                    "fired_multimodal_frac": _frac([r["act3_n_modes"] >= 2 for r in fired]), "quiet_multimodal_frac": _frac([r["act3_n_modes"] >= 2 for r in quiet]),
                    "fired_chi2_median": _q([r["act3_chi2_per_strike"] for r in fired], 50), "quiet_chi2_median": _q([r["act3_chi2_per_strike"] for r in quiet], 50),
                    "fired_age_median": _q([r["quote_age_median_min"] for r in fired], 50), "quiet_age_median": _q([r["quote_age_median_min"] for r in quiet], 50),
                    "fired_nstrikes_median": _q([r["n_strikes"] for r in fired], 50), "quiet_nstrikes_median": _q([r["n_strikes"] for r in quiet], 50),
                    "fired_sigma_median": _q([r["atm_sigma"] for r in fired], 50), "quiet_sigma_median": _q([r["atm_sigma"] for r in quiet], 50),
                    "fired_act2_butterfly_free_frac": _frac([r["checks"]["act2_butterfly_free"] for r in fired]),
                }
            by_key[key] = d
    out["by_snapshot"] = by_key
    # per-run table for the appendix
    out["runs"] = [{k: r.get(k) for k in ("settle_date", "root", "snap", "window_min", "gate0", "gate0_pooled", "n_quoted_strikes", "n_strikes", "n_below", "n_above",
                                          "two_sided_strikes", "quote_age_median_min", "F0_parity", "se_F0", "nymex_settle_same_day", "parity_minus_nymex_cents",
                                          "parity_minus_ice_cents", "contract_month_match", "atm_sigma", "act3_n_modes", "act3u_n_modes", "act3_frac_draws_multimodal",
                                          "act3_skew", "act3_std_dollars", "act3_chi2_per_strike", "act3_rhat_max", "act3_ess_min", "act3_bracket_rhat_max",
                                          "act3_bracket_ess_min", "act3_divergences", "act3u_mean_minus_F0_cents", "act2_ok", "seconds")}
                   | {"detector_cents": (r.get("detector") or {}).get("cents"), "detector_fired": (r.get("detector") or {}).get("fired"),
                      "checks": r.get("checks")} for r in ok]
    return out


# --------------------------------------------------------------------------
# plots
# --------------------------------------------------------------------------

def plot_run(r: Dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 8), gridspec_kw={"height_ratios": [1.2, 1]})
    s = r["act3_grid_s"]
    a1.fill_between(s, r["act3_grid_f_q"][0], r["act3_grid_f_q"][1], color="C0", alpha=0.25, label="Act III 90% band (constrained)")
    a1.plot(s, r["act3_grid_f_mean"], "C0", lw=1.5, label="Act III posterior mean")
    a1.plot(r["act3u_grid_s"], r["act3u_grid_f_mean"], "C2--", lw=1.2, label="Act III, no martingale constraint")
    if r.get("act2_ok"):
        g, f = r["act2_grid"]
        a1.plot(g, f, "C3:", lw=1.5, label="Act II (SVI)")
    a1.plot(r["K"], np.zeros_like(r["K"]), "|", color="gray", ms=12, label="OTM strikes (%d)" % r["n_strikes"])
    a1.axvline(r["F0_parity"], color="k", lw=0.8, ls="--", label="parity forward %.2f" % r["F0_parity"])
    if r.get("nymex_settle_same_day"):
        a1.axvline(r["nymex_settle_same_day"], color="C1", lw=0.8, ls="--", label="NYMEX settle %.2f" % r["nymex_settle_same_day"])
    lo, hi = r["F0_parity"] - 4 * r["act3_std_dollars"], r["F0_parity"] + 4 * r["act3_std_dollars"]
    a1.set_xlim(max(lo, s[0]), min(hi, s[-1]))
    a1.set_ylim(bottom=0)
    a1.set_ylabel("density (per $)")
    det = r["detector"]
    a1.set_title("%s %s %s (window %d min): %d strikes, ATM σ %.0f%%, modes %d, detector %s (%.1f¢), χ²/strike %.1f"
                 % (r["settle_date"], r["root"], r["snap"], r["window_min"], r["n_strikes"], 100 * r["atm_sigma"], r["act3_n_modes"],
                    "FIRED" if det["fired"] else "quiet", det["cents"] or 0, r["act3_chi2_per_strike"]), fontsize=9)
    a1.legend(loc="upper right", fontsize=7)
    e = r["edges"]
    mids = np.concatenate([[e[0] - 0.5], 0.5 * (e[1:] + e[:-1]), [e[-1] + 0.5]])
    q = r["act3_bracket_q"]
    a2.errorbar(mids, 100 * q[1], yerr=100 * np.vstack([q[1] - q[0], q[2] - q[1]]), fmt="o", color="C0", ms=4, capsize=2, label="Act III median, 90% band")
    if r.get("act2_ok"):
        a2.plot(mids, 100 * r["act2_bracket"], "C3x", ms=6, label="Act II")
    a2.set_xlabel("$1 bracket around the parity forward (open tails at the ends)")
    a2.set_ylabel("bracket probability (¢)")
    a2.set_xlim(max(lo, s[0]), min(hi, s[-1]))
    a2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def plots(rs: List[Dict[str, Any]], out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = [r for r in rs if r.get("error") is None and "act3_bracket_mean" in r]
    for r in ext:
        plot_run(r, out_dir / ("%s_%s_w%d.png" % (r["settle_date"], r["snap"], r["window_min"])))
    # summary: detector vs chi2, coloured by modes; parity vs settle
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for w, mk in ((60, "o"), (10, "s")):
        sub = [r for r in ext if r["window_min"] == w]
        if not sub:
            continue
        c = ["C3" if r["act3_n_modes"] >= 2 else "C0" for r in sub]
        axes[0].scatter([r["act3_chi2_per_strike"] for r in sub], [r["detector"]["cents"] for r in sub], c=c, marker=mk, s=28, alpha=0.8,
                        label="window %d min" % w)
    axes[0].axhline(detector.CUTOFF_CENTS, color="k", ls="--", lw=0.8, label="cutoff %.1f¢" % detector.CUTOFF_CENTS)
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Act III χ² per strike")
    axes[0].set_ylabel("Act II vs Act III max |Δ| (¢)")
    axes[0].set_title("detector vs fit quality (red = multimodal posterior mean)")
    axes[0].legend(fontsize=7)
    for w, mk in ((60, "o"), (10, "s")):
        sub = [r for r in rs if r.get("error") is None and r.get("gate0") and r.get("parity_minus_nymex_cents") is not None and r["window_min"] == w]
        if sub:
            axes[1].scatter([r["n_strikes"] for r in sub], [r["parity_minus_nymex_cents"] for r in sub], marker=mk, s=24, alpha=0.7, label="window %d min" % w)
    axes[1].axhline(0, color="k", lw=0.8)
    axes[1].set_xlabel("OTM strikes in the snapshot")
    axes[1].set_ylabel("parity forward − NYMEX settlement (¢)")
    axes[1].set_title("Stage 6 vs CME settlement, 14:30 snapshots")
    axes[1].legend(fontsize=7)
    for w, mk in ((60, "o"), (10, "s")):
        sub = [r for r in ext if r["window_min"] == w]
        if sub:
            axes[2].scatter([r["quote_age_median_min"] for r in sub], [r["act3_chi2_per_strike"] for r in sub], marker=mk, s=24, alpha=0.7, label="window %d min" % w)
    axes[2].set_yscale("log")
    axes[2].set_xlabel("median quote age in the snapshot (min)")
    axes[2].set_ylabel("Act III χ² per strike")
    axes[2].set_title("staleness vs fit quality")
    axes[2].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "_summary.png", dpi=120)
    plt.close(fig)


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------

def render(S: Dict[str, Any], rs: List[Dict[str, Any]], plot_dir: Path) -> str:
    B = S.get("synthetic_baseline", {})
    L: List[str] = []
    L.append("# FINDINGS_REALCHAIN — the extractor on real KXWTIW chains, descriptively\n")
    L.append("Step 2 of the build order. **Nothing here is a trade signal**: no Kalshi price was read and no gap was "
             "computed. The pipeline has a known blind spot (FINDINGS_SYNTHETIC.md) and this run only characterises what "
             "real WTI weekly chains look like to it. Generated by `python3 -m synth.realchain`; per-run plots in "
             "`synth/plots_real/`, aggregate in `synth/results_real/summary.json`.\n")
    L.append("## 1. What was run\n")
    L.append("- Dates: the %d KXWTIW settlement dates that clear Gate 0 in `data_cme/parquet/chain_density` (same-day weekly "
             "expiry, ≥8 strikes with 3+ per wing in the final hour), %s to %s. Roots LO1–LO5." % (len(S["dates"]), S["dates"][0], S["dates"][-1]))
    L.append("- Snapshots: T-2d and T-1d (14:30 ET, the NYMEX settlement window), T-4h (10:30 ET on settlement day), T-0 "
             "(14:30 ET on settlement day, parity only). Each at two quote windows: **60 min** (Gate 0's own definition) and "
             "**10 min** (near-synchronous — the underlying moves $1+ in an hour in this regime).")
    L.append("- Per snapshot: last two-sided quote per instrument → Stage 6 parity regression on strikes quoting both sides "
             "(MAD outlier flags; D fixed at e^{-0.04T} — the chain cannot identify D at T ≤ 2 days, it returned 0.947 at "
             "expiry) → OTM side per strike → Gate 0 re-checked on the OTM chain → Act II (hardened: Lee bound 2, g(k) "
             "verified on the used range) → Act III with the martingale constraint (deliverable) and without (the "
             "mean-equals-forward check) → Gate 4 detector (`synth/detector.py`, cutoff %.1f¢) → checks. Sampler settings "
             "identical to the synthetic study (4 × (400 + 400) NUTS)." % detector.CUTOFF_CENTS)
    L.append("- Errors: %d of %d jobs.\n" % (S["n_errors"], S["n_runs"]))

    def row(key, label):
        d = S["by_snapshot"].get(key, {})
        return d, label
    L.append("## 2. Gate 0 and chain geometry by snapshot\n")
    L.append("| snapshot | window | jobs | Gate 0 (pooled ≥8) | Gate 0 (OTM 8 / 3+3) | extracted | quoted strikes (med) | OTM strikes (med) | two-sided strikes (med) | quote age med (min) | 1¢ bids | half-spread med (¢) | log(hs/synthetic model) med |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for snap in ("T-2d", "T-1d", "T-4h", "T-0"):
        for w in (60, 10):
            d = S["by_snapshot"].get("%s_w%d" % (snap, w), {})
            if not d:
                continue
            L.append("| %s | %d | %d | %d | %d | %d | %s | %s | %s | %s | %s | %s | %s |" % (
                snap, w, d["n"], d["n_gate0_pooled"], d["n_gate0"], d["n_extracted"], _f(d["n_quoted_strikes_median"], "%.0f"), _f(d["n_otm_strikes_median"], "%.0f"),
                _f(d["two_sided_median"], "%.0f"), _f(d["quote_age_median_min"], "%.1f"), _pct(d["frac_bid_1c_median"]), _f(d["hs_median_cents"], "%.1f"),
                _f(d["hs_log_ratio_to_model_median"])))
    L.append("\n## 3. What shape are real WTI weekly densities?\n")
    L.append("Mode count of the Act III posterior-mean density (constrained / unconstrained), the share of posterior draws "
             "that are multimodal, skew and width. Multimodality here is *what the extractor reports*, which the synthetic "
             "study showed it does reliably when the humps are real and far apart, and which stale quotes can also manufacture (§7).\n")
    L.append("| snapshot | window | n | modes (constrained) | modes (unconstrained) | runs where >50% of draws multimodal | ATM σ med (p10–p90) | posterior std $ med | skew med | skew > 0 |\n|---|---|---|---|---|---|---|---|---|---|")
    for snap in ("T-2d", "T-1d", "T-4h"):
        for w in (60, 10):
            d = S["by_snapshot"].get("%s_w%d" % (snap, w), {})
            if not d or "modes_hist" not in d:
                continue
            L.append("| %s | %d | %d | %s | %s | %s | %s (%s–%s) | %s | %s | %s |" % (
                snap, w, d["n_extracted"], d["modes_hist"], d["modes_hist_unconstrained"], _pct(d["frac_runs_multimodal_majority"]),
                _pct(d["atm_sigma_median"]), _pct(d["atm_sigma_p10"]), _pct(d["atm_sigma_p90"]), _f(d["std_dollars_median"]), _f(d["skew_median"]), _pct(d["skew_frac_positive"])))
    L.append("\n## 4. The detector (headline)\n")
    L.append("Gate 4: max |Act II − Act III| over the $1 ladder, cutoff %.1f¢ (synthetic: p95 of well-specified chains with "
             "≥12 strikes; bimodal chains sat at 8–12¢). Not trusted below 12 strikes.\n" % detector.CUTOFF_CENTS)
    L.append("| snapshot | window | n | fired | fired (trusted chains only) | max|Δ| med (¢) | p90 | max | Act II fit ok |\n|---|---|---|---|---|---|---|---|---|")
    for snap in ("T-2d", "T-1d", "T-4h"):
        for w in (60, 10):
            d = S["by_snapshot"].get("%s_w%d" % (snap, w), {})
            if not d or "detector_fired_frac" not in d:
                continue
            L.append("| %s | %d | %d | %s | %s | %s | %s | %s | %s |" % (snap, w, d["n_extracted"], _pct(d["detector_fired_frac"]), _pct(d["detector_fired_trusted_frac"]),
                                                                    _f(d["detector_cents_median"]), _f(d["detector_cents_p90"]), _f(d["detector_cents_max"]), _pct(d["act2_ok_frac"])))
    L.append("\nWhat it fires on (fired vs quiet chains):\n")
    L.append("| snapshot | window | fired / quiet | multimodal: fired / quiet | χ²/strike med: fired / quiet | quote age med: fired / quiet | strikes med: fired / quiet | ATM σ med: fired / quiet | Act II butterfly-free among fired |\n|---|---|---|---|---|---|---|---|---|")
    for snap in ("T-2d", "T-1d", "T-4h"):
        for w in (60, 10):
            d = S["by_snapshot"].get("%s_w%d" % (snap, w), {})
            fv = d.get("fired_vs_quiet")
            if not fv:
                continue
            L.append("| %s | %d | %d / %d | %s / %s | %s / %s | %s / %s | %s / %s | %s / %s | %s |" % (
                snap, w, fv["n_fired"], fv["n_quiet"], _pct(fv["fired_multimodal_frac"]), _pct(fv["quiet_multimodal_frac"]), _f(fv["fired_chi2_median"], "%.1f"), _f(fv["quiet_chi2_median"], "%.1f"),
                _f(fv["fired_age_median"], "%.1f"), _f(fv["quiet_age_median"], "%.1f"), _f(fv["fired_nstrikes_median"], "%.0f"), _f(fv["quiet_nstrikes_median"], "%.0f"),
                _pct(fv["fired_sigma_median"]), _pct(fv["quiet_sigma_median"]), _pct(fv["fired_act2_butterfly_free_frac"])))
    L.append("\n## 5. The three checks on real data\n")
    L.append("Convexity = Act II g(k) ≥ 0 on the used range and density ≥ 0 (Act III is positive by construction). "
             "Normalisation = Act II mass within 1% of 1 and Act III mass in the outer 2.5% of the grid < 1%. "
             "Mean = forward: Act II density mean within 15¢ of the parity forward; Act III *unconstrained* posterior mean "
             "within 3 posterior sd of it (the Stage 14 diagnostic on real data). Also the fit-quality checks the "
             "synthetic study used as fault detectors.\n")
    L.append("| snapshot | window | n | Act II butterfly-free | Act II density ≥ 0 | Act II normalised | Act II mean = F0 | Act III edge mass ok | Act III χ²/strike < 2 | max resid < 3 | unconstrained mean = F0 (3 sd) | |z| med | mean − F0 med (¢) ± MAD | χ²/strike med (p90) | τ med |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for snap in ("T-2d", "T-1d", "T-4h"):
        for w in (60, 10):
            d = S["by_snapshot"].get("%s_w%d" % (snap, w), {})
            if not d or "checks" not in d:
                continue
            c = d["checks"]
            L.append("| %s | %d | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s ± %s | %s (%s) | %s |" % (
                snap, w, d["n_extracted"], _pct(c["act2_butterfly_free"]), _pct(c["act2_density_nonneg"]), _pct(c["act2_normalised"]), _pct(c["act2_mean_equals_forward"]),
                _pct(c["act3_normalisation_edge_mass_ok"]), _pct(c["act3_chi2_ok"]), _pct(c["act3_max_resid_ok"]), _pct(c["mean_equals_forward_ok"]),
                _f(d["mean_equals_forward_z_abs_median"], "%.1f"), _f(d["act3u_mean_minus_F0_cents_median"], "%.0f"), _f(d["act3u_mean_minus_F0_cents_mad"], "%.0f"),
                _f(d["chi2_per_strike_median"], "%.1f"), _f(d["chi2_per_strike_p90"], "%.1f"), _f(d["tau_median"], "%.1f")))
    L.append("\n## 6. Sampler health: real chains vs synthetic\n")
    bs = B.get("sampler", {})
    L.append("| chain set | R̂ max med (p90), raw | min ESS med, raw | divergences med | bracket R̂ max med (p90) | bracket min ESS med | runs with bracket R̂ < 1.05 | seconds / Act III run |\n|---|---|---|---|---|---|---|---|")
    if bs:
        L.append("| synthetic A_crude_full (n=120) | %s (%s) | %s | %s | %s (%s) | %s | — | %s |" % (
            _f(bs.get("rhat_max_median"), "%.3f"), _f(bs.get("rhat_max_p90"), "%.3f"), _f(bs.get("ess_min_median"), "%.0f"), _f(bs.get("divergences_median"), "%.0f"),
            _f(bs.get("bracket_rhat_max_median"), "%.3f"), _f(bs.get("bracket_rhat_max_p90"), "%.3f"), _f(bs.get("bracket_ess_min_median"), "%.0f"), _f(B.get("seconds_per_run"), "%.0f")))
    for snap in ("T-2d", "T-1d", "T-4h"):
        for w in (60, 10):
            d = S["by_snapshot"].get("%s_w%d" % (snap, w), {})
            sm = d.get("sampler")
            if not sm:
                continue
            L.append("| real %s, %d min (n=%d) | %s (%s) | %s | %s | %s (%s) | %s | %s | %s |" % (
                snap, w, d["n_extracted"], _f(sm["rhat_max_median"], "%.3f"), _f(sm["rhat_max_p90"], "%.3f"), _f(sm["ess_min_median"], "%.0f"), _f(sm["divergences_median"], "%.0f"),
                _f(sm["bracket_rhat_max_median"], "%.3f"), _f(sm["bracket_rhat_max_p90"], "%.3f"), _f(sm["bracket_ess_min_median"], "%.0f"), _pct(sm["frac_bracket_rhat_lt_1_05"]), _f(sm["seconds_median"], "%.0f")))
    L.append("\n## 7. Stage 6 parity forward vs CME settlement\n")
    L.append("At 14:30 ET the option quotes and the NYMEX settlement of the option's own underlying contract (from "
             "`options_definition.underlying`, e.g. LO2 expiring 2026-03-13 → CLJ6) refer to the same instant. At T-0 the "
             "ICE settlement Kalshi uses (`expiration_value`) is compared as well.\n")
    L.append("| snapshot | window | n | pairs med | se med (¢) | parity − NYMEX: mean (¢) | median | MAD | RMSE | p10–p90 | within 3 se | within 10¢ | within 25¢ | underlying = Kalshi contract |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for snap in ("T-2d", "T-1d", "T-0"):
        for w in (60, 10):
            d = S["by_snapshot"].get("%s_w%d" % (snap, w), {})
            pv = d.get("parity_vs_nymex")
            if not pv:
                continue
            L.append("| %s | %d | %d | %s | %s | %s | %s | %s | %s | %s–%s | %s | %s | %s | %s |" % (
                snap, w, pv["n"], _f(d["parity_pairs_median"], "%.0f"), _f(d["se_F0_cents_median"], "%.1f"), _f(pv["mean_c"], "%.1f"), _f(pv["median_c"], "%.1f"), _f(pv["mad_c"], "%.1f"),
                _f(pv["rmse_c"], "%.1f"), _f(pv["p10_c"], "%.0f"), _f(pv["p90_c"], "%.0f"), _pct(pv["frac_within_3se"]), _pct(pv["frac_within_10c"]), _pct(pv["frac_within_25c"]),
                _pct(d["contract_month_match_frac"])))
    for w in (60, 10):
        d = S["by_snapshot"].get("T-0_w%d" % w, {})
        pi = d.get("parity_vs_ice")
        if pi:
            L.append("\n- T-0, %d min: parity − ICE settlement: mean %.1f¢, RMSE %.1f¢, within 10¢ in %s of %d dates." % (w, pi["mean_c"], pi["rmse_c"], _pct(pi["frac_within_10c"]), pi["n"]))
    L.append("\n## 8. Where real chains differ from the synthetic ones\n")
    L.append("_(filled in §9 after the numbers; the per-run appendix is `synth/results_real/summary.json`.)_\n")
    L.append("Plots: `synth/plots_real/_summary.png` and one `<date>_<snap>_w<window>.png` per extraction.\n")
    return "\n".join(L) + "\n"
