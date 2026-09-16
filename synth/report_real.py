"""Aggregate the real-chain runs (synth/realchain.py, V2 arms) into FINDINGS_REALCHAIN_V2.md
and plots: every V1 table before/after, per arm, so each of the three changes (forward
source, synchronisation, detector) is attributable.

Descriptive only: no Kalshi price is read, no gap is computed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from . import detector

HERE = Path(__file__).resolve().parent
ARMS = ("base", "fwd", "sync", "sync_m", "real")
ARM_LABEL = {"base": "V1 (parity fwd, raw)", "fwd": "futures fwd, raw", "sync": "V2: futures fwd + sync", "sync_m": "sync (sticky-moneyness)",
             "real": "V3: real intraday path"}
SNAPS = ("T-2d", "T-1d", "T-4h", "T-0")
WINDOWS = (60, 10)


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


def _parity_stats(pm: List[float], z: Optional[List[float]] = None) -> Dict[str, Any]:
    pm = np.array(pm, float)
    d = {"n": int(pm.size), "mean_c": float(pm.mean()), "median_c": float(np.median(pm)), "mad_c": float(np.median(np.abs(pm - np.median(pm)))),
         "rmse_c": float(np.sqrt(np.mean(pm ** 2))), "p10_c": float(np.percentile(pm, 10)), "p90_c": float(np.percentile(pm, 90)),
         "frac_within_10c": float(np.mean(np.abs(pm) < 10)), "frac_within_25c": float(np.mean(np.abs(pm) < 25))}
    if z is not None:
        d["frac_within_3se"] = float(np.mean(np.abs(np.array(z)) < 3))
    return d


# --------------------------------------------------------------------------
# aggregate
# --------------------------------------------------------------------------

def _cell(sub: List[Dict[str, Any]]) -> Dict[str, Any]:
    g = [r for r in sub if r.get("gate0")]
    ext = [r for r in g if "act3_bracket_mean" in r]
    d: Dict[str, Any] = {
        "n": len(sub), "n_gate0": len(g), "n_gate0_pooled": sum(1 for r in sub if r.get("gate0_pooled")), "n_extracted": len(ext),
        "dates_extracted": sorted(r["settle_date"] for r in ext),
        "n_quoted_strikes_median": _q([r.get("n_quoted_strikes") for r in sub], 50),
        "n_otm_strikes_median": _q([r.get("n_strikes") for r in g], 50),
        "two_sided_median": _q([r.get("two_sided_strikes") for r in g], 50),
        "quote_age_median_min": _q([r.get("quote_age_median_min") for r in g], 50),
        "frac_bid_1c_median": _q([r.get("frac_bid_1c") for r in g], 50),
        "hs_median_cents": 100 * (_q([r.get("hs_median") for r in g], 50) or 0),
        "hs_log_ratio_to_model_median": _q([r.get("hs_log_ratio_to_model_median") for r in g], 50),
        "parity_pairs_median": _q([r.get("parity_pairs") for r in g], 50),
        "se_F0_cents_median": 100 * (_q([r.get("se_F0") for r in g], 50) or 0),
        "se_F0_parity_cents_median": 100 * (_q([r.get("se_F0_parity") for r in g], 50) or 0),
        "parity_flagged_frac": _frac([r.get("parity_flagged", 0) > 0 for r in g]),
        "contract_month_match_frac": _frac([r.get("contract_month_match") for r in g]),
        "forward_sources": {k: int(v) for k, v in zip(*np.unique([r.get("forward_source", "—") for r in g], return_counts=True))} if g else {},
    }
    # parity vs futures: raw parity (every arm), synchronised parity (sync arms), and the arm's forward
    pm = [(r["parity_minus_nymex_cents"], r["parity_minus_nymex_cents"] / (100 * max(r["se_F0_parity"], 1e-6))) for r in g
          if r.get("parity_minus_nymex_cents") is not None]
    if pm:
        d["parity_vs_nymex"] = _parity_stats([x[0] for x in pm], [x[1] for x in pm])
    pms = [(r["parity_sync_minus_nymex_cents"], r["parity_sync_minus_nymex_cents"] / (100 * max(r["se_F0_parity_sync"], 1e-6))) for r in g
           if r.get("parity_sync_minus_nymex_cents") is not None]
    if pms:
        d["parity_sync_vs_nymex"] = _parity_stats([x[0] for x in pms], [x[1] for x in pms])
    pmf = [(r["parity_sync_minus_F0_cents"], r["parity_sync_minus_F0_cents"] / (100 * max(r["se_F0_parity_sync"], 1e-6))) for r in g
           if r.get("parity_sync_minus_F0_cents") is not None]
    if pmf:
        d["parity_sync_vs_forward"] = _parity_stats([x[0] for x in pmf], [x[1] for x in pmf])
    pc = [r["parity_check"] for r in g if r.get("parity_check")]
    if pc:
        d["parity_check_flagged_frac"] = _frac([x["flagged"] for x in pc])
        d["parity_check_abs_z_median"] = _q([abs(x["z"]) for x in pc], 50)
    pi = [r.get("parity_minus_ice_cents") for r in g if r.get("parity_minus_ice_cents") is not None]
    if pi:
        d["parity_vs_ice"] = _parity_stats(pi)
    pis = [r.get("parity_sync_minus_ice_cents") for r in g if r.get("parity_sync_minus_ice_cents") is not None]
    if pis:
        d["parity_sync_vs_ice"] = _parity_stats(pis)
    sy = [r["sync"] for r in sub if r.get("sync")]
    if sy:
        d["sync"] = {"n": len(sy), "path_ok_frac": _frac([s["ok"] for s in sy]), "n_informative_median": _q([s.get("n_informative") for s in sy], 50),
                     "path_range_dollars_median": _q([s.get("path_range_dollars") for s in sy], 50), "path_range_dollars_p90": _q([s.get("path_range_dollars") for s in sy], 90),
                     "path_rms_resid_cents_median": 100 * (_q([s.get("path_rms_resid_dollars") for s in sy], 50) or 0),
                     "level_offset_cents_median": _q([s.get("level_offset_cents") for s in sy], 50),
                     "level_offset_abs_cents_median": _q([abs(s["level_offset_cents"]) for s in sy if s.get("level_offset_cents") is not None], 50),
                     "anchor_drift_cents_median": _q([s.get("anchor_drift_cents") for s in sy], 50),
                     "anchor_drift_abs_cents_median": _q([abs(s["anchor_drift_cents"]) for s in sy if s.get("anchor_drift_cents") is not None], 50),
                     "anchor_drift_abs_cents_p90": _q([abs(s["anchor_drift_cents"]) for s in sy if s.get("anchor_drift_cents") is not None], 90),
                     "adj_rms_cents_median": _q([s["adj_rms_cents"] for s in sy], 50), "adj_max_abs_cents_median": _q([s["adj_max_abs_cents"] for s in sy], 50),
                     "adj_theta_rms_cents_median": _q([s["adj_theta_rms_cents"] for s in sy], 50), "adj_delta_rms_cents_median": _q([s["adj_delta_rms_cents"] for s in sy], 50)}
    if ext:
        # the split-half cutoff is applied at report time, with the calibrated value if the calibration has run
        cut = detector.split_z_cutoff()
        for r in ext:
            r["detector"]["fired"] = bool(r["split_half"]["max_abs_z"] > cut)
            r["detector"]["cutoff"] = cut
        det = [r["detector"] for r in ext]
        v1 = [r["detector_v1"] for r in ext]
        sh = [r["split_half"] for r in ext]
        lo = [r["loo"] for r in ext]
        d.update({
            "atm_sigma_median": _q([r["atm_sigma"] for r in ext], 50), "atm_sigma_p10": _q([r["atm_sigma"] for r in ext], 10),
            "atm_sigma_p90": _q([r["atm_sigma"] for r in ext], 90),
            "std_dollars_median": _q([r["act3_std_dollars"] for r in ext], 50),
            "skew_median": _q([r["act3_skew"] for r in ext], 50), "skew_frac_positive": _frac([r["act3_skew"] > 0 for r in ext]),
            "modes_hist": {str(k): int(v) for k, v in zip(*np.unique([r["act3_n_modes"] for r in ext], return_counts=True))},
            "modes_hist_unconstrained": {str(k): int(v) for k, v in zip(*np.unique([r["act3u_n_modes"] for r in ext], return_counts=True))},
            "frac_draws_multimodal_median": _q([r["act3_frac_draws_multimodal"] for r in ext], 50),
            "frac_runs_multimodal_majority": _frac([r["act3_frac_draws_multimodal"] > 0.5 for r in ext]),
            "frac_runs_multimodal_mean": _frac([r["act3_n_modes"] >= 2 for r in ext]),
            # V1 gate (Act II vs Act III)
            "v1_fired_frac": _frac([x["fired"] for x in v1]), "v1_fired_trusted_frac": _frac([x["fired"] for x in v1 if x["trusted"]]),
            "v1_cents_median": _q([x["cents"] for x in v1], 50), "v1_cents_p90": _q([x["cents"] for x in v1], 90),
            "v1_cents_max": max([x["cents"] for x in v1 if x["cents"] is not None] or [0.0]),
            "act2_ok_frac": _frac([r["act2_ok"] for r in ext]),
            # new gate
            "gate4_fired_frac": _frac([x["fired"] for x in det]),
            "split_z_median": _q([s["max_abs_z"] for s in sh], 50), "split_z_p90": _q([s["max_abs_z"] for s in sh], 90), "split_z_max": _q([s["max_abs_z"] for s in sh], 100),
            "split_diff_cents_median": _q([s["max_abs_diff_cents"] for s in sh], 50), "split_diff_cents_p90": _q([s["max_abs_diff_cents"] for s in sh], 90),
            "split_cutoff": cut,
            "split_half_chi2_median": _q([h["chi2_per_strike"] for s in sh for h in s["halves"]], 50),
            "split_half_rhat_median": _q([h["rhat_max"] for s in sh for h in s["halves"]], 50),
            "loo_z_median": _q([x["max_abs_z"] for x in lo], 50), "loo_z_p90": _q([x["max_abs_z"] for x in lo], 90),
            "loo_rms_median": _q([x["rms_z"] for x in lo], 50),
            "loo_flagged_frac": _frac([x["n_flagged"] > 0 for x in lo]), "loo_n_flagged_median": _q([x["n_flagged"] for x in lo], 50),
            "loo_n_flagged_mean": float(np.mean([x["n_flagged"] for x in lo])),
            "checks": {k: _frac([r["checks"].get(k) for r in ext]) for k in ("act2_butterfly_free", "act2_density_nonneg", "act2_normalised",
                                                                             "act2_mean_equals_forward", "act3_normalisation_edge_mass_ok", "act3_chi2_ok",
                                                                             "act3_max_resid_ok", "mean_equals_forward_ok", "sampler_ok", "sampler_bracket_ok")},
            "mean_equals_forward_z_abs_median": _q([abs(r["checks"]["mean_equals_forward_z"]) for r in ext], 50),
            "act3u_mean_minus_F0_cents_median": _q([r["act3u_mean_minus_F0_cents"] for r in ext], 50),
            "act3u_mean_minus_F0_cents_mad": float(np.median(np.abs(np.array([r["act3u_mean_minus_F0_cents"] for r in ext]) - np.median([r["act3u_mean_minus_F0_cents"] for r in ext])))),
            "chi2_per_strike_median": _q([r["act3_chi2_per_strike"] for r in ext], 50), "chi2_per_strike_p90": _q([r["act3_chi2_per_strike"] for r in ext], 90),
            "chi2_per_strike_p10": _q([r["act3_chi2_per_strike"] for r in ext], 10),
            "chi2u_per_strike_median": _q([r["act3u_chi2_per_strike"] for r in ext], 50),
            "max_abs_resid_median": _q([r["act3_max_abs_resid"] for r in ext], 50),
            "tau_median": _q([r["act3_tau_q"][1] for r in ext], 50),
            "edge_mass_median": _q([float(np.max(r["act3_edge_mass"])) for r in ext], 50),
            "sampler": {"rhat_max_median": _q([r["act3_rhat_max"] for r in ext], 50), "rhat_max_p90": _q([r["act3_rhat_max"] for r in ext], 90),
                        "ess_min_median": _q([r["act3_ess_min"] for r in ext], 50), "divergences_median": _q([r["act3_divergences"] for r in ext], 50),
                        "bracket_rhat_max_median": _q([r["act3_bracket_rhat_max"] for r in ext], 50), "bracket_rhat_max_p90": _q([r["act3_bracket_rhat_max"] for r in ext], 90),
                        "bracket_ess_min_median": _q([r["act3_bracket_ess_min"] for r in ext], 50),
                        "frac_bracket_rhat_lt_1_05": _frac([r["act3_bracket_rhat_max"] < 1.05 for r in ext]),
                        "seconds_median": _q([r["act3_seconds"] for r in ext], 50),
                        "split_seconds_median": _q([r.get("split_half_seconds") for r in ext], 50), "loo_seconds_median": _q([r.get("loo_seconds") for r in ext], 50)},
            "width90_body_cents_median": _q([100 * float(np.max(r["act3_bracket_width90"])) for r in ext], 50),
        })
        fired = [r for r in ext if r["detector"]["fired"]]
        quiet = [r for r in ext if not r["detector"]["fired"]]
        d["fired_vs_quiet"] = {
            "n_fired": len(fired), "n_quiet": len(quiet),
            "fired_multimodal_frac": _frac([r["act3_n_modes"] >= 2 for r in fired]), "quiet_multimodal_frac": _frac([r["act3_n_modes"] >= 2 for r in quiet]),
            "fired_chi2_median": _q([r["act3_chi2_per_strike"] for r in fired], 50), "quiet_chi2_median": _q([r["act3_chi2_per_strike"] for r in quiet], 50),
            "fired_age_median": _q([r["quote_age_median_min"] for r in fired], 50), "quiet_age_median": _q([r["quote_age_median_min"] for r in quiet], 50),
            "fired_nstrikes_median": _q([r["n_strikes"] for r in fired], 50), "quiet_nstrikes_median": _q([r["n_strikes"] for r in quiet], 50),
            "fired_loo_median": _q([r["loo"]["max_abs_z"] for r in fired], 50), "quiet_loo_median": _q([r["loo"]["max_abs_z"] for r in quiet], 50),
            "fired_act2_median": _q([r["detector_v1"]["cents"] for r in fired], 50), "quiet_act2_median": _q([r["detector_v1"]["cents"] for r in quiet], 50),
        }
    return d


def aggregate_v2(rs: List[Dict[str, Any]], v1: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    ok = [r for r in rs if r.get("error") is None]
    out: Dict[str, Any] = {"n_runs": len(rs), "n_errors": len(rs) - len(ok), "errors": [r["error"] for r in rs if r.get("error")][:5],
                           "dates": sorted({r["settle_date"] for r in rs}), "synthetic_baseline": _synth_baseline(),
                           "arms": sorted({r.get("arm", "base") for r in rs})}
    by: Dict[str, Dict[str, Any]] = {}
    for arm in ARMS:
        for snap in SNAPS:
            for w in WINDOWS:
                sub = [r for r in ok if r.get("arm", "base") == arm and r["snap"] == snap and r.get("window_min", 60) == w]
                if sub:
                    by["%s_%s_w%d" % (arm, snap, w)] = _cell(sub)
    out["by_cell"] = by
    # paired comparison on the dates every arm extracted
    paired: Dict[str, Any] = {}
    arms_p = ["base", "fwd", "sync"] + (["real"] if any(k.startswith("real_") for k in by) else [])
    out["paired_arms"] = arms_p
    for snap in SNAPS[:3]:
        for w in WINDOWS:
            cells = {a: by.get("%s_%s_w%d" % (a, snap, w)) for a in arms_p}
            if not all(cells.values()):
                continue
            common = set.intersection(*[set(c["dates_extracted"]) for c in cells.values()])
            if not common:
                continue
            row: Dict[str, Any] = {"n_common": len(common)}
            for a in arms_p:
                ext = [r for r in ok if r.get("arm", "base") == a and r["snap"] == snap and r.get("window_min", 60) == w and r["settle_date"] in common
                       and "act3_bracket_mean" in r]
                row[a] = {"chi2_median": _q([r["act3_chi2_per_strike"] for r in ext], 50), "chi2_lt2_frac": _frac([r["act3_chi2_per_strike"] < 2 for r in ext]),
                          "multimodal_majority_frac": _frac([r["act3_frac_draws_multimodal"] > 0.5 for r in ext]),
                          "meanF_z_abs_median": _q([abs(r["checks"]["mean_equals_forward_z"]) for r in ext], 50),
                          "meanF_ok_frac": _frac([r["checks"]["mean_equals_forward_ok"] for r in ext]),
                          "split_z_median": _q([r["split_half"]["max_abs_z"] for r in ext], 50), "gate4_fired_frac": _frac([r["detector"]["fired"] for r in ext]),
                          "v1_fired_frac": _frac([r["detector_v1"]["fired"] for r in ext]), "loo_flagged_frac": _frac([r["loo"]["n_flagged"] > 0 for r in ext]),
                          "width90_body_cents_median": _q([100 * float(np.max(r["act3_bracket_width90"])) for r in ext], 50)}
            paired["%s_w%d" % (snap, w)] = row
    out["paired"] = paired
    # V1 reproduction check: base arm vs the stored V1 runs
    if v1:
        v1k = {(r["settle_date"], r["snap"], r.get("window_min", 60)): r for r in v1 if r.get("error") is None and "act3_chi2_per_strike" in r}
        diffs = []
        for r in ok:
            if r.get("arm", "base") != "base" or "act3_chi2_per_strike" not in r:
                continue
            o = v1k.get((r["settle_date"], r["snap"], r.get("window_min", 60)))
            if o is not None:
                diffs.append((abs(r["act3_chi2_per_strike"] - o["act3_chi2_per_strike"]), float(np.abs(r["act3_bracket_mean"] - o["act3_bracket_mean"]).max()) * 100))
        if diffs:
            out["v1_reproduction"] = {"n": len(diffs), "chi2_abs_diff_max": float(max(x[0] for x in diffs)), "bracket_abs_diff_cents_max": float(max(x[1] for x in diffs))}
    p = HERE / "results_real" / "split_half_null.json"
    if p.exists():
        out["split_half_calibration"] = json.load(open(p))
    # real vs reconstructed path (the `real` arm carries both)
    val: Dict[str, Any] = {}
    for snap in SNAPS:
        for w in WINDOWS:
            sub = [r["real_path"] for r in ok if r.get("arm") == "real" and r["snap"] == snap and r.get("window_min", 60) == w and r.get("real_path")]
            sub = [x for x in sub if x["source"] == "real" and x.get("recon_ok")]
            if not sub:
                continue
            d = np.concatenate([np.asarray(x["diff_shape_dollars"]) for x in sub]) * 100.0
            draw = np.concatenate([np.asarray(x["diff_dollars"]) for x in sub]) * 100.0
            dist = np.concatenate([np.asarray(x["dist_from_anchor_min"]) for x in sub])
            bins = [(0, 5), (5, 15), (15, 30), (30, 45), (45, 61)]
            by_dist = []
            for lo, hi in bins:
                m = (dist >= lo) & (dist < hi)
                if m.any():
                    by_dist.append({"bin": "%d–%d" % (lo, hi - 1 if hi == 61 else hi), "n": int(m.sum()), "rmse_c": float(np.sqrt(np.mean(d[m] ** 2))),
                                    "mad_c": float(np.median(np.abs(d[m] - np.median(d[m])))), "p90_abs_c": float(np.percentile(np.abs(d[m]), 90))})
            anc = np.array([x["real_at_anchor_minus_anchor_cents"] for x in sub])
            atr = np.array([x["real_minus_recon_at_ref_cents"] for x in sub])
            val["%s_w%d" % (snap, w)] = {"n_jobs": len(sub), "coverage_median": float(np.median([x["coverage"] for x in sub])),
                                         "n_from_fallback_mean": float(np.mean([x["n_from_fallback"] for x in sub])),
                                         "level_at_anchor_minus_anchor_c": {"median": float(np.median(anc)), "mad": float(np.median(np.abs(anc - np.median(anc)))),
                                                                            "rmse": float(np.sqrt(np.mean(anc ** 2)))},
                                         "real_minus_recon_at_ref_c": {"median": float(np.median(atr)), "rmse": float(np.sqrt(np.mean(atr ** 2)))},
                                         "shape": {"mean_c": float(d.mean()), "median_c": float(np.median(d)), "mad_c": float(np.median(np.abs(d - np.median(d)))),
                                                   "rmse_c": float(np.sqrt(np.mean(d ** 2))), "p10_c": float(np.percentile(d, 10)), "p90_c": float(np.percentile(d, 90))},
                                         "raw": {"mean_c": float(draw.mean()), "rmse_c": float(np.sqrt(np.mean(draw ** 2)))},
                                         "shape_rmse_per_job_median_c": float(np.median([x["shape_rmse_cents"] for x in sub])),
                                         "shape_max_abs_per_job_median_c": float(np.median([x["shape_max_abs_cents"] for x in sub])),
                                         "by_distance": by_dist}
    out["path_validation"] = val
    out["runs"] = [{k: r.get(k) for k in ("settle_date", "root", "snap", "window_min", "arm", "gate0", "gate0_pooled", "forward_source", "n_quoted_strikes", "n_strikes",
                                          "two_sided_strikes", "quote_age_median_min", "F0", "se_F0", "F0_parity", "F0_parity_sync", "nymex_settle_same_day",
                                          "parity_minus_nymex_cents", "parity_sync_minus_nymex_cents", "parity_check", "atm_sigma", "act3_n_modes", "act3u_n_modes",
                                          "act3_frac_draws_multimodal", "act3_skew", "act3_std_dollars", "act3_chi2_per_strike", "act3_rhat_max", "act3_ess_min",
                                          "act3_bracket_rhat_max", "act3_bracket_ess_min", "act3_divergences", "act3u_mean_minus_F0_cents", "act2_ok", "seconds")}
                   | {"detector": r.get("detector"), "checks": r.get("checks"),
                      "sync": {k: v for k, v in (r.get("sync") or {}).items() if not k.startswith("path_") or k in ("path_range_dollars", "path_rms_resid_dollars")} or None}
                   for r in ok]
    return out


# --------------------------------------------------------------------------
# plots
# --------------------------------------------------------------------------

def plot_run(r: Dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    has_path = bool(r.get("sync") and r["sync"].get("path_values") is not None)
    fig, axes = plt.subplots(3 if has_path else 2, 1, figsize=(9, 11 if has_path else 8),
                             gridspec_kw={"height_ratios": [1.2, 1, 0.6] if has_path else [1.2, 1]})
    a1, a2 = axes[0], axes[1]
    s = r["act3_grid_s"]
    a1.fill_between(s, r["act3_grid_f_q"][0], r["act3_grid_f_q"][1], color="C0", alpha=0.25, label="Act III 90% band (constrained)")
    a1.plot(s, r["act3_grid_f_mean"], "C0", lw=1.5, label="Act III posterior mean")
    a1.plot(r["act3u_grid_s"], r["act3u_grid_f_mean"], "C2--", lw=1.2, label="Act III, no martingale constraint")
    if r.get("act2_ok"):
        g, f = r["act2_grid"]
        a1.plot(g, f, "C3:", lw=1.5, label="Act II (SVI)")
    a1.plot(r["K"], np.zeros_like(r["K"]), "|", color="gray", ms=12, label="OTM strikes (%d)" % r["n_strikes"])
    a1.axvline(r["F0"], color="k", lw=0.8, ls="--", label="forward %.2f (%s)" % (r["F0"], r.get("forward_source", "")))
    if r.get("F0_parity"):
        a1.axvline(r["F0_parity"], color="C4", lw=0.8, ls=":", label="raw parity %.2f" % r["F0_parity"])
    if r.get("nymex_settle_same_day"):
        a1.axvline(r["nymex_settle_same_day"], color="C1", lw=0.8, ls="--", label="NYMEX settle %.2f" % r["nymex_settle_same_day"])
    lo, hi = r["F0"] - 4 * r["act3_std_dollars"], r["F0"] + 4 * r["act3_std_dollars"]
    a1.set_xlim(max(lo, s[0]), min(hi, s[-1]))
    a1.set_ylim(bottom=0)
    a1.set_ylabel("density (per $)")
    det = r["detector"]
    a1.set_title("%s %s %s w%d [%s]: %d strikes, ATM σ %.0f%%, modes %d, χ²/strike %.1f, split-half max|z| %.1f (%s), LOO flags %d"
                 % (r["settle_date"], r["root"], r["snap"], r["window_min"], r["arm"], r["n_strikes"], 100 * r["atm_sigma"], r["act3_n_modes"],
                    r["act3_chi2_per_strike"], det.get("split_max_abs_z") or 0, "FIRED" if det["fired"] else "quiet", det.get("loo_n_flagged") or 0), fontsize=8)
    a1.legend(loc="upper right", fontsize=7)
    e = r["edges"]
    mids = np.concatenate([[e[0] - 0.5], 0.5 * (e[1:] + e[:-1]), [e[-1] + 0.5]])
    q = r["act3_bracket_q"]
    a2.errorbar(mids, 100 * q[1], yerr=100 * np.vstack([q[1] - q[0], q[2] - q[1]]), fmt="o", color="C0", ms=4, capsize=2, label="Act III median, 90% band")
    sh = r.get("split_half")
    if sh:
        a2.plot(mids, 100 * sh["halves"][0]["mean"], "C5^", ms=4, alpha=0.8, label="odd strikes")
        a2.plot(mids, 100 * sh["halves"][1]["mean"], "C6v", ms=4, alpha=0.8, label="even strikes")
    if r.get("act2_ok"):
        a2.plot(mids, 100 * r["act2_bracket"], "C3x", ms=6, label="Act II")
    a2.set_xlabel("$1 bracket around the forward (open tails at the ends)")
    a2.set_ylabel("bracket probability (¢)")
    a2.set_xlim(max(lo, s[0]), min(hi, s[-1]))
    a2.legend(fontsize=8)
    if has_path:
        a3 = axes[2]
        sy = r["sync"]
        a3.plot(-sy["path_knots_min"], sy["path_values"], "C0-", lw=1.2, label="options-implied path (level anchored)")
        a3.axhline(sy["anchor"], color="C1", lw=0.8, ls="--", label="anchor %.2f" % sy["anchor"])
        a3.set_xlabel("minutes before the snapshot")
        a3.set_ylabel("underlying ($)")
        a3.set_title("path range $%.2f, %d informative events, adjustment rms %.1f¢ (theta %.1f¢)" % (
            sy.get("path_range_dollars") or 0, sy.get("n_informative") or 0, sy["adj_rms_cents"], sy["adj_theta_rms_cents"]), fontsize=8)
        a3.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def plots_v2(rs: List[Dict[str, Any]], out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = [r for r in rs if r.get("error") is None]
    ext = [r for r in ok if "act3_bracket_mean" in r]
    for r in ext:
        plot_run(r, out_dir / ("%s_%s_w%d_%s.png" % (r["settle_date"], r["snap"], r["window_min"], r["arm"])))
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.4))
    # 1. chi2 before/after per date
    key = lambda r: (r["settle_date"], r["snap"], r["window_min"])
    base = {key(r): r for r in ext if r["arm"] == "base"}
    for arm, mk, c in (("fwd", "s", "C1"), ("sync", "o", "C2")):
        xs, ys = [], []
        for r in ext:
            if r["arm"] == arm and key(r) in base:
                xs.append(base[key(r)]["act3_chi2_per_strike"])
                ys.append(r["act3_chi2_per_strike"])
        if xs:
            axes[0].scatter(xs, ys, marker=mk, s=22, alpha=0.7, c=c, label="%s (n=%d)" % (ARM_LABEL[arm], len(xs)))
    lim = [0.3, 100]
    axes[0].plot(lim, lim, "k--", lw=0.8)
    axes[0].axhline(2.0, color="gray", lw=0.6, ls=":")
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("χ²/strike, V1 (parity forward, raw window)")
    axes[0].set_ylabel("χ²/strike, after the change")
    axes[0].set_title("Act III fit quality before/after, same date and snapshot")
    axes[0].legend(fontsize=7)
    # 2. parity vs settlement: raw and synchronised
    for arm, k, mk, c, lab in (("base", "parity_minus_nymex_cents", "o", "C0", "raw parity (V1)"), ("sync", "parity_sync_minus_nymex_cents", "s", "C2", "synchronised parity")):
        sub = [r for r in ok if r["arm"] == arm and r.get("gate0") and r.get(k) is not None and r["snap"] in ("T-2d", "T-1d")]
        if sub:
            axes[1].scatter([r["n_strikes"] for r in sub], [r[k] for r in sub], marker=mk, s=22, alpha=0.7, c=c, label="%s (n=%d)" % (lab, len(sub)))
    axes[1].axhline(0, color="k", lw=0.8)
    axes[1].set_xlabel("OTM strikes in the snapshot")
    axes[1].set_ylabel("parity forward − NYMEX settlement (¢)")
    axes[1].set_title("Stage 6 vs the futures, 14:30 snapshots (T-2d, T-1d)")
    axes[1].legend(fontsize=7)
    # 3. split-half z vs chi2, by arm
    for arm, mk, c in (("base", "o", "C0"), ("sync", "s", "C2")):
        sub = [r for r in ext if r["arm"] == arm]
        if sub:
            axes[2].scatter([r["act3_chi2_per_strike"] for r in sub], [r["split_half"]["max_abs_z"] for r in sub], marker=mk, s=22, alpha=0.7, c=c,
                            label="%s" % ARM_LABEL[arm])
    axes[2].axhline(detector.split_z_cutoff(), color="k", ls="--", lw=0.8, label="cutoff %.1f" % detector.split_z_cutoff())
    axes[2].set_xscale("log")
    axes[2].set_yscale("log")
    axes[2].set_xlabel("Act III χ² per strike")
    axes[2].set_ylabel("split-half max |z| over the ladder")
    axes[2].set_title("new Gate 4 vs fit quality")
    axes[2].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "_summary.png", dpi=120)
    plt.close(fig)


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------

def _rows(S: Dict[str, Any], snaps, arms=ARMS):
    for snap in snaps:
        for w in WINDOWS:
            for arm in arms:
                d = S["by_cell"].get("%s_%s_w%d" % (arm, snap, w))
                if d:
                    yield snap, w, arm, d


def render_v2(S: Dict[str, Any], rs: List[Dict[str, Any]], plot_dir: Path) -> str:
    B = S.get("synthetic_baseline", {})
    L: List[str] = []
    v3 = "real" in S.get("arms", [])
    L.append("# FINDINGS_REALCHAIN_V3 — the real intraday path in place of the reconstruction (V1 / V2 / V3 side by side)\n" if v3 else
             "# FINDINGS_REALCHAIN_V2 — forward from the futures, synchronised quotes, split-half gate\n")
    if v3:
        L.append("Response to `NightKing/HANDOFF_actii_and_intraday.md` Task 3. Same 30 dates, snapshots, windows and sampler settings as V1 and V2; the "
                 "`real` arm is V2's `sync` arm with the underlying's path inside each window read from 1-minute CL futures bars of the option's own "
                 "underlying (`db_pull_futures.py`, ohlcv-1m) instead of being reconstructed from the option trade stream. The real level at the "
                 "snapshot instant is the forward on every snapshot, T-4h included (V2 had to use parity there). Where bars are missing for more "
                 "than five minutes the reconstruction fills the hole, shifted to the nearest real minute; the share of such minutes is reported. "
                 "All V2 arms are re-listed unchanged so every table is V1 / V2 / V3 on the same dates.\n")
    L.append("Response to `NightKing/HANDOFF_forward_and_sync_fix.md`. Same 30 dates, snapshots, windows and sampler settings as "
             "`FINDINGS_REALCHAIN.md` (V1). Three changes, run as separate arms so that each is attributable, with the V1 pipeline "
             "re-run as the `base` arm so every number below is before/after on the same dates. **Nothing here is a trade signal**: "
             "no Kalshi price was read and no gap was computed. Generated by `python3 -m synth.realchain`; per-run plots in "
             "`synth/plots_real_v2/`, aggregate in `synth/results_real/summary_v2.json`.\n")
    L.append("| arm | forward | quotes | Gate 4 |\n|---|---|---|---|")
    L.append("| `base` | Stage 6 parity regression on the raw window (V1) | last quote per instrument in the window, as quoted | new (split-half + LOO), V1's Act II gate also reported |")
    L.append("| `fwd` | NYMEX settlement of the option's own underlying at the 14:30 snapshots (T-2d, T-1d, T-0); parity at T-4h, where no futures print exists at 10:30 | as quoted | same |")
    L.append("| `sync` | futures-anchored: the settlement fixes the level at 14:29, the options-implied path carries it to 14:30; parity at T-4h (on the synchronised quotes) | every quote moved to the snapshot instant and level by a sticky-strike Black-76 reprice (`synth/sync.py`) | same |")
    L.append("| `sync_m` | as `sync` | sticky-moneyness reprice (sensitivity; T-1d / 60 min only) | same |")
    L.append("| `real` | the real 1-minute futures level at the snapshot instant, every snapshot | sticky-strike reprice along the real path (reconstruction only in holes > 5 min) | same |\n")
    L.append("Errors: %d of %d jobs. Arms present: %s.\n" % (S["n_errors"], S["n_runs"], ", ".join(S["arms"])))
    if S.get("v1_reproduction"):
        v = S["v1_reproduction"]
        L.append("The `base` arm reproduces V1: over %d extractions, max |Δχ²/strike| = %s and max bracket difference = %s¢ against `synth/results_real/runs.pkl`.\n"
                 % (v["n"], _f(v["chi2_abs_diff_max"], "%.3f"), _f(v["bracket_abs_diff_cents_max"], "%.3f")))

    # ---- 1. headline: chi2 ----
    L.append("## 1. Headline: Act III χ²/strike, before and after\n")
    L.append("Act III's own goodness of fit against the market's own half-spreads, independent of any cross-check. Synthetic "
             "well-specified chains sit at 1.1. `extracted` is the number of dates that reach Act III in that arm (the futures forward "
             "needs no parity pairs, so it extracts more T-2d and 10-minute dates than parity does).\n")
    L.append("| snapshot | window | arm | extracted | χ²/strike med (p10–p90) | χ² < 2 | max resid < 3 | unconstrained χ² med | quote age med (min) |\n|---|---|---|---|---|---|---|---|---|")
    for snap, w, arm, d in _rows(S, SNAPS[:3]):
        if "chi2_per_strike_median" not in d:
            continue
        L.append("| %s | %d | %s | %d | %s (%s–%s) | %s | %s | %s | %s |" % (
            snap, w, ARM_LABEL[arm], d["n_extracted"], _f(d["chi2_per_strike_median"], "%.1f"), _f(d["chi2_per_strike_p10"], "%.1f"), _f(d["chi2_per_strike_p90"], "%.1f"),
            _pct(d["checks"]["act3_chi2_ok"]), _pct(d["checks"]["act3_max_resid_ok"]), _f(d["chi2u_per_strike_median"], "%.1f"), _f(d["quote_age_median_min"], "%.1f")))
    if S.get("paired"):
        L.append("\nPaired on the dates all three arms extracted:\n")
        pa = S.get("paired_arms", ["base", "fwd", "sync"])
        lab = " → ".join({"base": "V1", "fwd": "fwd", "sync": "V2", "real": "V3"}[a] for a in pa)
        L.append("| snapshot | window | n | χ² med: %s | χ² < 2: %s | >50%% draws multimodal: %s | 90%% body width med (¢): %s |\n|---|---|---|---|---|---|---|" % (lab, lab, lab, lab))
        for k, row in S["paired"].items():
            snap, w = k.split("_w")
            L.append("| %s | %s | %d | %s | %s | %s | %s |" % (
                snap, w, row["n_common"], " → ".join(_f(row[a]["chi2_median"], "%.1f") for a in pa), " → ".join(_pct(row[a]["chi2_lt2_frac"]) for a in pa),
                " → ".join(_pct(row[a]["multimodal_majority_frac"]) for a in pa), " → ".join(_f(row[a]["width90_body_cents_median"], "%.1f") for a in pa)))

    # ---- 2. forward ----
    L.append("\n## 2. The forward: parity vs the futures, and the synchronisation itself\n")
    L.append("At 14:30 ET the option quotes and the NYMEX settlement of the option's own underlying contract (from `options_definition.underlying`) "
             "refer to the same two minutes. `raw parity` is Stage 6 on the window as quoted (V1); `synchronised parity` is Stage 6 after every quote "
             "has been moved to the snapshot instant and level. The parity check flags |raw parity − futures| > %.0f se and > %.0f¢.\n" % (2.0 + 1.0, 10.0))
    L.append("| snapshot | window | arm | n | pairs med | parity − NYMEX: median (¢) | MAD | RMSE | within 10¢ | within 25¢ | within 3 se | check flagged |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    for snap, w, arm, d in _rows(S, ("T-2d", "T-1d", "T-0"), ("base", "sync")):
        for key, lab in (("parity_vs_nymex", "raw parity"), ("parity_sync_vs_nymex", "synchronised parity"), ("parity_sync_vs_forward", "synchronised parity vs the path forward")):
            pv = d.get(key)
            if not pv or (arm == "base" and key != "parity_vs_nymex"):
                continue
            L.append("| %s | %d | %s: %s | %d | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                snap, w, ARM_LABEL[arm], lab, pv["n"], _f(d["parity_pairs_median"], "%.0f"), _f(pv["median_c"], "%.1f"), _f(pv["mad_c"], "%.1f"), _f(pv["rmse_c"], "%.1f"),
                _pct(pv["frac_within_10c"]), _pct(pv["frac_within_25c"]), _pct(pv.get("frac_within_3se")), _pct(d.get("parity_check_flagged_frac")) if key == "parity_vs_nymex" else "—"))
    for w in WINDOWS:
        for arm in ("base", "sync"):
            d = S["by_cell"].get("%s_T-0_w%d" % (arm, w), {})
            for key, lab in (("parity_vs_ice", "raw parity"), ("parity_sync_vs_ice", "synchronised parity")):
                pi = d.get(key)
                if pi:
                    L.append("\n- T-0, %d min, %s: %s − ICE settlement: median %.1f¢, RMSE %.1f¢, within 10¢ on %s of %d dates." % (w, ARM_LABEL[arm], lab, pi["median_c"], pi["rmse_c"], _pct(pi["frac_within_10c"]), pi["n"]))
    L.append("\nThe synchronisation (`synth/sync.py`): the underlying's path inside the window is estimated from every option trade in it (the "
             "TBBO stream carries each option's own bid/ask at the trade), on 1-minute knots with a random-walk prior at the ATM vol, and its "
             "level is anchored to the settlement at 14:29 (parity at 10:30). `level offset` is the options-implied level at the anchor minus the "
             "futures — a second measurement of the Stage 6 disagreement that uses every quote; `anchor drift` is the path's last-minute move, "
             "i.e. forward used − settlement. The adjustment splits into a theta part (T_i → T_ref) and a delta part (F(t_i) → F_ref).\n")
    L.append("| snapshot | window | arm | n | path ok | informative events med | path range $ med (p90) | path resid rms (¢) | level offset med (¢) | |offset| med | anchor drift med (¢) | |drift| med (p90) | adjustment rms med (¢) | max |adj| med | theta rms med | delta rms med |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for snap, w, arm, d in _rows(S, SNAPS, ("sync", "sync_m")):
        sy = d.get("sync")
        if not sy:
            continue
        L.append("| %s | %d | %s | %d | %s | %s | %s (%s) | %s | %s | %s | %s | %s (%s) | %s | %s | %s | %s |" % (
            snap, w, ARM_LABEL[arm], sy["n"], _pct(sy["path_ok_frac"]), _f(sy["n_informative_median"], "%.0f"), _f(sy["path_range_dollars_median"]), _f(sy["path_range_dollars_p90"]),
            _f(sy["path_rms_resid_cents_median"], "%.1f"), _f(sy["level_offset_cents_median"], "%.1f"), _f(sy["level_offset_abs_cents_median"], "%.1f"),
            _f(sy["anchor_drift_cents_median"], "%.1f"), _f(sy["anchor_drift_abs_cents_median"], "%.1f"), _f(sy["anchor_drift_abs_cents_p90"], "%.1f"),
            _f(sy["adj_rms_cents_median"], "%.1f"), _f(sy["adj_max_abs_cents_median"], "%.1f"), _f(sy["adj_theta_rms_cents_median"], "%.1f"), _f(sy["adj_delta_rms_cents_median"], "%.1f")))

    if S.get("path_validation"):
        L.append("\n### 2b. The real intraday path against V2's reconstruction\n")
        L.append("From the `real` arm, which carries both paths on every job. `shape` = real − reconstructed after removing the difference at the anchor "
                 "minute (14:29 for the 14:30 snapshots, 10:30 for T-4h): the reconstruction's level came from the settlement/parity and its shape from "
                 "the options, so the shape is what is tested. `raw` includes the level. `real at anchor − anchor` checks the bars against the "
                 "settlement itself. Error by distance from the anchor is the direct test of the T-4h hypothesis.\n")
        L.append("| snapshot | window | jobs | bar coverage med | minutes from fallback (mean) | real@anchor − anchor: median / MAD / RMSE (¢) | real − recon at t_ref: median / RMSE (¢) | shape diff: mean / median / MAD / RMSE / p10–p90 (¢) | per-job shape RMSE med | per-job max shape diff med | raw diff RMSE |\n|---|---|---|---|---|---|---|---|---|---|---|")
        for k, v in S["path_validation"].items():
            snap, w = k.split("_w")
            a, r, sh = v["level_at_anchor_minus_anchor_c"], v["real_minus_recon_at_ref_c"], v["shape"]
            L.append("| %s | %s | %d | %s | %s | %s / %s / %s | %s / %s | %s / %s / %s / %s / %s–%s | %s | %s | %s |" % (
                snap, w, v["n_jobs"], _pct(v["coverage_median"]), _f(v["n_from_fallback_mean"], "%.1f"), _f(a["median"], "%.1f"), _f(a["mad"], "%.1f"), _f(a["rmse"], "%.1f"),
                _f(r["median"], "%.1f"), _f(r["rmse"], "%.1f"), _f(sh["mean_c"], "%.1f"), _f(sh["median_c"], "%.1f"), _f(sh["mad_c"], "%.1f"), _f(sh["rmse_c"], "%.1f"),
                _f(sh["p10_c"], "%.0f"), _f(sh["p90_c"], "%.0f"), _f(v["shape_rmse_per_job_median_c"], "%.1f"), _f(v["shape_max_abs_per_job_median_c"], "%.1f"), _f(v["raw"]["rmse_c"], "%.1f")))
        L.append("\nShape error by distance from the anchor (minutes; RMSE / MAD / p90 of the absolute difference, ¢):\n")
        bins = sorted({b["bin"] for v in S["path_validation"].values() for b in v["by_distance"]}, key=lambda x: int(x.split("–")[0]))
        L.append("| snapshot | window | " + " | ".join(bins) + " |\n|---|---|" + "---|" * len(bins))
        for k, v in S["path_validation"].items():
            snap, w = k.split("_w")
            bd = {b["bin"]: b for b in v["by_distance"]}
            L.append("| %s | %s | " % (snap, w) + " | ".join(("%s / %s / %s (n=%d)" % (_f(bd[b]["rmse_c"], "%.1f"), _f(bd[b]["mad_c"], "%.1f"), _f(bd[b]["p90_abs_c"], "%.1f"), bd[b]["n"])) if b in bd else "—" for b in bins) + " |")

    # ---- 3. gate 0 ----
    L.append("\n## 3. Gate 0 and chain geometry by snapshot and arm\n")
    L.append("| snapshot | window | arm | jobs | Gate 0 (pooled ≥8) | Gate 0 (OTM 8 / 3+3) | extracted | forward source | quoted strikes (med) | OTM strikes (med) | two-sided strikes (med) | quote age med (min) | 1¢ bids | half-spread med (¢) | log(hs/synthetic model) med |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for snap, w, arm, d in _rows(S, SNAPS):
        L.append("| %s | %d | %s | %d | %d | %d | %d | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            snap, w, ARM_LABEL[arm], d["n"], d["n_gate0_pooled"], d["n_gate0"], d["n_extracted"], ", ".join("%s %d" % kv for kv in d["forward_sources"].items()),
            _f(d["n_quoted_strikes_median"], "%.0f"), _f(d["n_otm_strikes_median"], "%.0f"), _f(d["two_sided_median"], "%.0f"), _f(d["quote_age_median_min"], "%.1f"),
            _pct(d["frac_bid_1c_median"]), _f(d["hs_median_cents"], "%.1f"), _f(d["hs_log_ratio_to_model_median"])))

    # ---- 4. shapes ----
    L.append("\n## 4. What shape are real WTI weekly densities?\n")
    L.append("Mode count of the Act III posterior-mean density (constrained / unconstrained), the share of posterior draws that are "
             "multimodal, skew and width. V1 found multimodality that vanished at the 10-minute window; the question is whether it survives synchronisation.\n")
    L.append("| snapshot | window | arm | n | modes (constrained) | modes (unconstrained) | runs where >50% of draws multimodal | ATM σ med (p10–p90) | posterior std $ med | skew med | skew > 0 |\n|---|---|---|---|---|---|---|---|---|---|---|")
    for snap, w, arm, d in _rows(S, SNAPS[:3]):
        if "modes_hist" not in d:
            continue
        L.append("| %s | %d | %s | %d | %s | %s | %s | %s (%s–%s) | %s | %s | %s |" % (
            snap, w, ARM_LABEL[arm], d["n_extracted"], d["modes_hist"], d["modes_hist_unconstrained"], _pct(d["frac_runs_multimodal_majority"]),
            _pct(d["atm_sigma_median"]), _pct(d["atm_sigma_p10"]), _pct(d["atm_sigma_p90"]), _f(d["std_dollars_median"]), _f(d["skew_median"]), _pct(d["skew_frac_positive"])))

    # ---- 5. detector ----
    L.append("\n## 5. Gate 4: the old detector and the new one\n")
    cal = S.get("split_half_calibration")
    if cal:
        L.append("Split-half cutoff calibrated on synthetic chains (`python3 -m synth.realchain --calibrate`, real strike grids, the study's NUTS settings):\n")
        L.append("| planted situation | n | split-half max|z| med | p95 | max | > 3 | LOO max|z| med | LOO > 3 | LOO names the injected strike | Act II − Act III med (¢) | Act II > 2.5¢ | χ²/strike med | posterior vs truth max|z| med |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for kind, lab in (("null", "crude-skew truth, calibrated noise (null)"), ("stale", "one stale quote (data inconsistency)"), ("bimodal", "bimodal truth (prior mis-specification)")):
            c = cal.get(kind)
            if not c:
                continue
            L.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                lab, c["n"], _f(c["split_max_abs_z_median"]), _f(c["split_max_abs_z_p95"]), _f(c["split_max_abs_z_max"]), _pct(c["split_frac_gt3"]),
                _f(c["loo_max_abs_z_median"]), _pct(c["loo_frac_gt3"]), _pct(c.get("loo_localised_frac")), _f(c.get("act2_cents_median")), _pct(c.get("act2_frac_gt_cutoff")),
                _f(c["chi2_median"]), _f(c["truth_max_abs_z_median"])))
        L.append("\nCutoff in use: max|z| > %.2f (the null p95).\n" % cal.get("cutoff_p95", detector.split_z_cutoff()))
    L.append("**V1 gate** (max |Act II − Act III| over the ladder, cutoff %.1f¢) and **new gate** (split-half: Act III fitted to the odd- and to the "
             "even-indexed strikes, posteriors compared bracket by bracket, z = Δmean / √(v₁+v₂), statistic max|z|; LOO: each strike dropped and "
             "predicted from the rest, |z| > 3 flags it) on every arm:\n" % detector.CUTOFF_CENTS)
    L.append("| snapshot | window | arm | n | V1 fired | V1 max|Δ| med (¢) | p90 | **new Gate 4 fired** | split max|z| med | p90 | max | split max|Δ| med (¢) | LOO max|z| med | p90 | chains with a LOO flag | LOO flags per chain (mean) |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for snap, w, arm, d in _rows(S, SNAPS[:3]):
        if "gate4_fired_frac" not in d:
            continue
        L.append("| %s | %d | %s | %d | %s | %s | %s | **%s** | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            snap, w, ARM_LABEL[arm], d["n_extracted"], _pct(d["v1_fired_frac"]), _f(d["v1_cents_median"]), _f(d["v1_cents_p90"]), _pct(d["gate4_fired_frac"]),
            _f(d["split_z_median"]), _f(d["split_z_p90"]), _f(d["split_z_max"]), _f(d["split_diff_cents_median"]), _f(d["loo_z_median"]), _f(d["loo_z_p90"]),
            _pct(d["loo_flagged_frac"]), _f(d["loo_n_flagged_mean"], "%.1f")))
    L.append("\nWhat the new gate fires on (fired vs quiet chains):\n")
    L.append("| snapshot | window | arm | fired / quiet | multimodal: fired / quiet | χ²/strike med: fired / quiet | quote age med: fired / quiet | strikes med: fired / quiet | LOO max|z| med: fired / quiet | Act II Δ med (¢): fired / quiet |\n|---|---|---|---|---|---|---|---|---|---|")
    for snap, w, arm, d in _rows(S, SNAPS[:3]):
        fv = d.get("fired_vs_quiet")
        if not fv:
            continue
        L.append("| %s | %d | %s | %d / %d | %s / %s | %s / %s | %s / %s | %s / %s | %s / %s | %s / %s |" % (
            snap, w, ARM_LABEL[arm], fv["n_fired"], fv["n_quiet"], _pct(fv["fired_multimodal_frac"]), _pct(fv["quiet_multimodal_frac"]), _f(fv["fired_chi2_median"], "%.1f"),
            _f(fv["quiet_chi2_median"], "%.1f"), _f(fv["fired_age_median"], "%.1f"), _f(fv["quiet_age_median"], "%.1f"), _f(fv["fired_nstrikes_median"], "%.0f"),
            _f(fv["quiet_nstrikes_median"], "%.0f"), _f(fv["fired_loo_median"], "%.1f"), _f(fv["quiet_loo_median"], "%.1f"), _f(fv["fired_act2_median"], "%.1f"), _f(fv["quiet_act2_median"], "%.1f")))

    # ---- 6. checks ----
    L.append("\n## 6. The three checks on real data\n")
    L.append("Convexity = Act II g(k) ≥ 0 on the used range and density ≥ 0 (Act III is positive by construction). Normalisation = Act II mass "
             "within 1% of 1 and Act III mass in the outer 2.5% of the grid < 1%. Mean = forward: Act II density mean within 15¢ of the forward; "
             "Act III *unconstrained* posterior mean within 3 posterior sd of it (the Stage 14 diagnostic on real data; synthetic |z| median 0.74).\n")
    L.append("| snapshot | window | arm | n | Act II butterfly-free | Act II density ≥ 0 | Act II normalised | Act II mean = F0 | Act III edge mass ok | unconstrained mean = F0 (3 sd) | |z| med | mean − F0 med (¢) ± MAD | τ med |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for snap, w, arm, d in _rows(S, SNAPS[:3]):
        if "checks" not in d:
            continue
        c = d["checks"]
        L.append("| %s | %d | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s ± %s | %s |" % (
            snap, w, ARM_LABEL[arm], d["n_extracted"], _pct(c["act2_butterfly_free"]), _pct(c["act2_density_nonneg"]), _pct(c["act2_normalised"]), _pct(c["act2_mean_equals_forward"]),
            _pct(c["act3_normalisation_edge_mass_ok"]), _pct(c["mean_equals_forward_ok"]), _f(d["mean_equals_forward_z_abs_median"], "%.1f"),
            _f(d["act3u_mean_minus_F0_cents_median"], "%.0f"), _f(d["act3u_mean_minus_F0_cents_mad"], "%.0f"), _f(d["tau_median"], "%.1f")))

    # ---- 7. sampler ----
    L.append("\n## 7. Sampler health\n")
    bs = B.get("sampler", {})
    L.append("| chain set | R̂ max med (p90), raw | min ESS med, raw | divergences med | bracket R̂ max med (p90) | bracket min ESS med | runs with bracket R̂ < 1.05 | seconds / Act III run | split-half s | LOO s |\n|---|---|---|---|---|---|---|---|---|---|")
    if bs:
        L.append("| synthetic A_crude_full (n=120) | %s (%s) | %s | %s | %s (%s) | %s | — | %s | — | — |" % (
            _f(bs.get("rhat_max_median"), "%.3f"), _f(bs.get("rhat_max_p90"), "%.3f"), _f(bs.get("ess_min_median"), "%.0f"), _f(bs.get("divergences_median"), "%.0f"),
            _f(bs.get("bracket_rhat_max_median"), "%.3f"), _f(bs.get("bracket_rhat_max_p90"), "%.3f"), _f(bs.get("bracket_ess_min_median"), "%.0f"), _f(B.get("seconds_per_run"), "%.0f")))
    for snap, w, arm, d in _rows(S, SNAPS[:3]):
        sm = d.get("sampler")
        if not sm:
            continue
        L.append("| %s, %d min, %s (n=%d) | %s (%s) | %s | %s | %s (%s) | %s | %s | %s | %s | %s |" % (
            snap, w, ARM_LABEL[arm], d["n_extracted"], _f(sm["rhat_max_median"], "%.3f"), _f(sm["rhat_max_p90"], "%.3f"), _f(sm["ess_min_median"], "%.0f"), _f(sm["divergences_median"], "%.0f"),
            _f(sm["bracket_rhat_max_median"], "%.3f"), _f(sm["bracket_rhat_max_p90"], "%.3f"), _f(sm["bracket_ess_min_median"], "%.0f"), _pct(sm["frac_bracket_rhat_lt_1_05"]),
            _f(sm["seconds_median"], "%.0f"), _f(sm["split_seconds_median"], "%.0f"), _f(sm["loo_seconds_median"], "%.0f")))
    L.append("\n## 8. Verdicts\n")
    L.append("_(written by hand after the numbers; see the end of this file.)_\n")
    L.append("Plots: `synth/plots_real_v2/_summary.png` and one `<date>_<snap>_w<window>_<arm>.png` per extraction (the sync arms add the estimated path).\n")
    return "\n".join(L) + "\n"
