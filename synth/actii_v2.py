"""Task 1 of NightKing/HANDOFF_actii_and_intraday.md: Act II's firing rate on the synchronised
chains of the V2 run, and whether Act II and the split-half gate fire on the same chains.

Reads synth/results_real/runs_v2.pkl (no re-running) and writes FINDINGS_ACTII_V2.md.

    python3 -m synth.actii_v2
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from . import detector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SNAPS = ("T-2d", "T-1d", "T-4h")
WINDOWS = (60, 10)
ARMS = ("base", "sync")
LABEL = {"base": "V1 raw", "sync": "V2 synchronised"}


def _q(xs, q):
    xs = [x for x in xs if x is not None and np.isfinite(x)]
    return float(np.percentile(xs, q)) if xs else None


def _frac(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def _pct(x):
    return "—" if x is None else "%.0f%%" % (100 * x)


def _f(x, fmt="%.2f"):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else fmt % x


def fisher_exact(a, b, c, d) -> Optional[float]:
    try:
        from scipy.stats import fisher_exact as fe
        return float(fe([[a, b], [c, d]])[1])
    except Exception:
        return None


def phi(a, b, c, d) -> Optional[float]:
    den = (a + b) * (c + d) * (a + c) * (b + d)
    return float((a * d - b * c) / np.sqrt(den)) if den > 0 else None


def classify(r: Dict[str, Any], cut: float) -> str:
    a2 = bool(r["act2_signal"]["fired"])
    sh = bool(r["split_half"]["max_abs_z"] > cut)
    return {(True, True): "both", (True, False): "act2_only", (False, True): "split_only", (False, False): "neither"}[(a2, sh)]


def profile(rs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rs:
        return {"n": 0}
    return {
        "n": len(rs),
        "multimodal_mean_frac": _frac([r["act3_n_modes"] >= 2 for r in rs]),
        "draws_multimodal_median": _q([r["act3_frac_draws_multimodal"] for r in rs], 50),
        "tau_median": _q([r["act3_tau_q"][1] for r in rs], 50),
        "width90_median_cents": _q([100 * float(np.max(r["act3_bracket_width90"])) for r in rs], 50),
        "n_strikes_median": _q([r["n_strikes"] for r in rs], 50),
        "chi2_median": _q([r["act3_chi2_per_strike"] for r in rs], 50),
        "loo_flags_mean": float(np.mean([r["loo"]["n_flagged"] for r in rs])),
        "act2_cents_median": _q([r["act2_signal"]["cents"] for r in rs], 50),
        "split_z_median": _q([r["split_half"]["max_abs_z"] for r in rs], 50),
        "act2_min_g_median": _q([r["act2_svi"]["min_g"] for r in rs if r.get("act2_ok")], 50),
        "act2_mean_drift_abs_median": _q([abs(r["act2_checks"]["mean_minus_F0_cents"]) for r in rs if r.get("act2_ok")], 50),
        "act2_lee_slope_median": _q([r["act2_svi"]["lee_slope"] for r in rs if r.get("act2_ok")], 50),
        "act2_rho_abs_median": _q([abs(r["act2_svi"]["rho"]) for r in rs if r.get("act2_ok")], 50),
        "atm_sigma_median": _q([r["atm_sigma"] for r in rs], 50),
        "skew_median": _q([r["act3_skew"] for r in rs], 50),
        "age_median": _q([r["quote_age_median_min"] for r in rs], 50),
        "act2_inside_band_frac": _frac([bool(np.all((r["act2_bracket"] >= r["act3_bracket_q"][0]) & (r["act2_bracket"] <= r["act3_bracket_q"][2])))
                                        for r in rs if r.get("act2_ok")]),
    }


def analyse(rs: List[Dict[str, Any]]) -> Dict[str, Any]:
    cut = detector.split_z_cutoff()
    ext = [r for r in rs if r.get("error") is None and "act3_bracket_mean" in r and r.get("arm") in ARMS]
    for r in ext:
        r["_class"] = classify(r, cut)
    out: Dict[str, Any] = {"cutoff": cut, "cells": {}, "pooled": {}, "act2_only_runs": []}
    for arm in ARMS:
        for snap in SNAPS:
            for w in WINDOWS:
                sub = [r for r in ext if r["arm"] == arm and r["snap"] == snap and r["window_min"] == w]
                if not sub:
                    continue
                sig = [r["act2_signal"] for r in sub]
                cls = [r["_class"] for r in sub]
                a = sum(c == "both" for c in cls)
                b = sum(c == "act2_only" for c in cls)
                c_ = sum(c == "split_only" for c in cls)
                d = sum(c == "neither" for c in cls)
                out["cells"]["%s_%s_w%d" % (arm, snap, w)] = {
                    "n": len(sub), "act2_fired": _frac([s["fired"] for s in sig]), "act2_fired_trusted": _frac([s["fired"] for s in sig if s["trusted"]]),
                    "n_trusted": sum(1 for s in sig if s["trusted"]),
                    "cents_median": _q([s["cents"] for s in sig], 50), "cents_p90": _q([s["cents"] for s in sig], 90), "cents_max": _q([s["cents"] for s in sig], 100),
                    "act2_ok": _frac([r["act2_ok"] for r in sub]),
                    "butterfly_free": _frac([r["act2_svi"]["butterfly_free"] for r in sub if r.get("act2_ok")]),
                    "density_nonneg": _frac([r["act2_checks"]["density_nonneg"] for r in sub if r.get("act2_ok")]),
                    "normalised": _frac([r["act2_checks"]["normalised"] for r in sub if r.get("act2_ok")]),
                    "mean_eq_fwd": _frac([r["act2_checks"]["mean_equals_forward"] for r in sub if r.get("act2_ok")]),
                    "mean_drift_abs_median": _q([abs(r["act2_checks"]["mean_minus_F0_cents"]) for r in sub if r.get("act2_ok")], 50),
                    "mean_drift_abs_p90": _q([abs(r["act2_checks"]["mean_minus_F0_cents"]) for r in sub if r.get("act2_ok")], 90),
                    "n_used_median": _q([r["act2_n_used"] for r in sub if r.get("act2_ok")], 50),
                    "n_dropped_median": _q([r["act2_n_dropped"] for r in sub if r.get("act2_ok")], 50),
                    "lee_slope_median": _q([r["act2_svi"]["lee_slope"] for r in sub if r.get("act2_ok")], 50),
                    "inside_band": _frac([bool(np.all((r["act2_bracket"] >= r["act3_bracket_q"][0]) & (r["act2_bracket"] <= r["act3_bracket_q"][2])))
                                          for r in sub if r.get("act2_ok")]),
                    "split_fired": _frac([r["split_half"]["max_abs_z"] > cut for r in sub]),
                    "both": a, "act2_only": b, "split_only": c_, "neither": d,
                    "phi": phi(a, b, c_, d), "fisher_p": fisher_exact(a, b, c_, d),
                    "jaccard": (a / (a + b + c_)) if (a + b + c_) else None,
                }
        sub = [r for r in ext if r["arm"] == arm]
        cls = [r["_class"] for r in sub]
        a, b, c_, d = (sum(c == k for c in cls) for k in ("both", "act2_only", "split_only", "neither"))
        out["pooled"][arm] = {"n": len(sub), "both": a, "act2_only": b, "split_only": c_, "neither": d, "phi": phi(a, b, c_, d),
                              "fisher_p": fisher_exact(a, b, c_, d), "jaccard": (a / (a + b + c_)) if (a + b + c_) else None,
                              "act2_fired": _frac([r["act2_signal"]["fired"] for r in sub]), "split_fired": _frac([r["split_half"]["max_abs_z"] > cut for r in sub]),
                              "profiles": {k: profile([r for r in sub if r["_class"] == k]) for k in ("both", "act2_only", "split_only", "neither")}}
    for r in sorted([r for r in ext if r["arm"] == "sync" and r["_class"] == "act2_only"], key=lambda r: -r["act2_signal"]["cents"]):
        out["act2_only_runs"].append({
            "date": r["settle_date"], "snap": r["snap"], "w": r["window_min"], "n": r["n_strikes"], "cents": r["act2_signal"]["cents"],
            "split_z": r["split_half"]["max_abs_z"], "chi2": r["act3_chi2_per_strike"], "modes": r["act3_n_modes"], "draws_mm": r["act3_frac_draws_multimodal"],
            "tau": r["act3_tau_q"][1], "width90": 100 * float(np.max(r["act3_bracket_width90"])), "loo": r["loo"]["n_flagged"],
            "act2_ok": r["act2_ok"], "min_g": r["act2_svi"]["min_g"] if r.get("act2_ok") else None,
            "drift": r["act2_checks"]["mean_minus_F0_cents"] if r.get("act2_ok") else None, "rho": r["act2_svi"]["rho"] if r.get("act2_ok") else None,
            "sigma": r["atm_sigma"], "skew": r["act3_skew"], "trusted": r["act2_signal"]["trusted"], "reason": r["act2_signal"].get("reason", "")})
    p = HERE / "results_real" / "split_half_null.json"
    out["calibration"] = json.load(open(p)) if p.exists() else {}
    return out


VERDICT = (
    "**Verdict: Act II is quiet where the synchronisation is clean — 7% at T-1d/60 against 68% in V1 and a 0% calibrated "
    "false-positive rate — but still fires on 53% of T-4h/60 chains, and on synchronised chains its fires are two things: three "
    "genuinely multimodal T-4h posteriors (the prior-mismatch signature, τ 7–17) and a larger set where Act II itself is broken "
    "(wings that run away by $16–24, ρ pinned at ±0.99, or chains under 12 strikes). So split-half and Act II do cover different "
    "failure modes (fully disjoint at T-1d; pooled φ = 0.28, Jaccard 0.26), the prior can stay untouched for now, Act II must stay "
    "a report line rather than a gate until its wings are pinned, and T-4h — the snapshot nearest decision time — is where Task 2 "
    "has to look: it is the only snapshot where both Act II and Act III's multimodality survived synchronisation.**\n")

READING = """
## 5. Reading

**Firing rate.** Synchronisation took Act II from 67% to 27% of chains pooled, and to **7%** at T-1d/60 — two chains, both with
χ²/strike ≈ 1 and Act II's disagreement at 3.9¢ and 5.9¢ (against a 2.5¢ cutoff that is the p95 of well-specified synthetic
chains). That is the calibrated behaviour: the confound the handoff named (Act II differentiating the asynchrony) is gone, and the
old 68% was that confound. The 10-minute windows behave the same way (0% among trusted chains at T-1d/10). T-2d/60 sits at 31%
and **T-4h/60 at 53%**; those two are where the rest of this document lives.

**Same chains or different ones?** Pooled over synchronised chains the two gates are positively associated (φ = 0.28, Fisher p =
0.004) but far from identical: 11 chains fire both, 22 fire Act II only, 9 fire split-half only, Jaccard 0.26. The association is
carried entirely by T-4h/60 (φ = 0.42, five chains fire both — and those are the worst chains in the study, χ²/strike 5.2 median,
5.8 LOO flags per chain, 45% with a multimodal posterior mean). At T-1d/60 the two gates are **disjoint**: no chain fires both, two
fire Act II only, five fire split-half only. So the answer to "one phenomenon or two" is two, with a third category where a chain is
bad enough that both see it.

**What the Act II-only chains are.** Twenty-two chains, listed in §4. They sort into four groups:

1. *Genuinely multimodal Act III posteriors* — 2026-05-01, 2026-05-29 and 2026-03-06, all T-4h/60: 2–4 modes in the posterior
   mean, 96–100% of draws multimodal, τ 6.7–17 (the roughness scale the sampler is pushed to when the data want structure the
   prior dislikes; a well-behaved chain sits at τ ≈ 0.7–1.0), χ²/strike 3.6–5.2, 6–7 LOO flags each, Act II disagreement 5–21¢.
   These are the chains the bimodal calibration case describes: split-half cannot see them because both halves carry the same
   posterior, and Act II does. Whether they are real or a reconstruction artifact of the path (T-4h is furthest from the 14:29
   anchor) is exactly Task 2's question.
2. *Act II broken, not the chain* — 2026-08-21 T-4h (Act II density mean $23.71 above the forward), 2026-07-10 T-4h ($16.62),
   2026-05-29 T-4h again ($1.90), and the fits with |ρ| pinned at the 0.99 bound (2026-07-31 T-2d, 2026-05-01 T-1d/10, 2026-07-10
   T-4h at −0.94). On these the SVI wings ran away or the fit sits on a constraint; the chain itself has χ²/strike 0.7–3.4 and
   passes split-half easily. The disagreement is Act II's error, not Act III's.
3. *Thin chains Act II is not trusted on* — 2026-08-28 T-2d (9 strikes, 10.4¢), 2026-07-10 T-1d/10, 2026-07-24 T-1d/10,
   2026-03-13 T-2d/10, 2026-02-13 T-1d/10, 2026-05-01 T-1d/10 (9–11 strikes). The detector already reports these as untrusted.
4. *Marginal fires on clean chains* — 2.5–4¢ on chains with χ²/strike ≈ 1, one mode, τ ≈ 1 (2026-03-20, 2026-03-27, 2026-01-09,
   2026-08-21 T-1d, 2026-08-28 T-4h, 2026-01-16). Six of 82 clean-looking chains at or just above a p95 cutoff is the expected
   false-positive rate.

**Act II fit health is the problem for using it as a gate.** On synchronised chains g(k) ≥ 0 holds on 93–100% of fits and the
density is non-negative on the used range on 95–100%, so the Stage 10 hardening works. But the density *mean* lands within 15¢ of
the forward on only 52–73% of chains, and the p90 of |mean − F0| is $1.8–$20: the SVI wings extrapolate beyond the last strike
and, when they run away, carry the mean with them (V1's "~$0.50 mean drift on synthetic" is the mild version of this). Act II's
bracket probabilities sit inside Act III's 90% band on every bracket on only 0–15% of chains. The gate compares a bracket vector
from a fit whose tails are unconstrained to a posterior whose tails are prior-dominated; where the two disagree by 3¢ on a
shoulder bracket that is not evidence of anything about the chain. A usable Act II gate needs (a) the wing slope pinned or the
mean constrained to the forward — the Stage 14 idea applied to Act II — and (b) the comparison restricted to brackets inside the
strike range. Neither was done here, because this task was to read the number, not change the method.

**What this says about the prior.** The three chains in group 1 are the only evidence in 124 synchronised extractions that real
WTI densities sit outside the roughness prior's comfort zone, and all three are at T-4h/60 — the snapshot with the weakest path
reconstruction, 21% one-cent bids and a window that is a fifth of the option's remaining life. At T-1d and T-2d there is no such
chain. The prior's form is therefore not at the front of the queue on this evidence; it moves there only if Task 2 shows those
three (and the 23% T-4h multimodality of V2 §8) survive a real intraday path.

**Consequence for T-2d.** Act II fires on 31% of T-2d/60 chains, but 3 of the 8 fires are untrusted 9–12-strike chains and the
five that fire both gates have χ²/strike well above 2. T-2d is kept: the futures forward extracts it on 26 of 30 dates and the
split-half gate handles it like any other snapshot.
"""


def render(A: Dict[str, Any]) -> str:
    L: List[str] = []
    cells, pooled = A["cells"], A["pooled"]
    s = pooled.get("sync", {})
    b = pooled.get("base", {})
    L.append("# FINDINGS_ACTII_V2 — Act II's firing rate on synchronised chains, and whether it sees what split-half sees\n")
    L.append("Task 1 of `NightKing/HANDOFF_actii_and_intraday.md`. Read entirely from the V2 run on disk (`synth/results_real/runs_v2.pkl`, "
             "`python3 -m synth.actii_v2`); nothing re-run, no Kalshi price read. Act II gate = max |Act II − Act III| over the ladder > "
             "%.1f¢ (the V1 cutoff); split-half gate = max |z| > %.2f (the V2 calibrated cutoff).\n" % (detector.CUTOFF_CENTS, A["cutoff"]))
    L.append(VERDICT)
    L.append("## 1. Act II firing rate, V1 raw chains vs V2 synchronised chains\n")
    L.append("| snapshot | window | chains | n (trusted ≥12 strikes) | Act II fired: V1 raw → V2 sync | trusted only | max\\|Δ\\| median (¢): V1 → V2 | p90 | max | Act II inside Act III's 90% band on every bracket |\n|---|---|---|---|---|---|---|---|---|---|")
    for snap in SNAPS:
        for w in WINDOWS:
            cb, cs = cells.get("base_%s_w%d" % (snap, w)), cells.get("sync_%s_w%d" % (snap, w))
            if not cs:
                continue
            g = lambda c, k, fmt="%.2f": _f(c[k], fmt) if c else "—"
            gp = lambda c, k: _pct(c[k]) if c else "—"
            L.append("| %s | %d | %s → %d | %s → %d | %s → **%s** | %s → %s | %s → %s | %s → %s | %s → %s | %s → %s |" % (
                snap, w, cb["n"] if cb else "—", cs["n"], cb["n_trusted"] if cb else "—", cs["n_trusted"], gp(cb, "act2_fired"), _pct(cs["act2_fired"]),
                gp(cb, "act2_fired_trusted"), _pct(cs["act2_fired_trusted"]), g(cb, "cents_median"), _f(cs["cents_median"]), g(cb, "cents_p90"), _f(cs["cents_p90"]),
                g(cb, "cents_max"), _f(cs["cents_max"]), gp(cb, "inside_band"), _pct(cs["inside_band"])))
    L.append("\nPooled over the three snapshots and both windows: Act II fires on %s of V1 raw chains (n=%d) and **%s** of V2 synchronised chains (n=%d). "
             "On the calibration chains (`synth/results_real/split_half_null.json`) the same gate fires on %s of well-specified synthetic chains "
             "and %s of bimodal ones.\n" % (_pct(b.get("act2_fired")), b.get("n", 0), _pct(s.get("act2_fired")), s.get("n", 0),
                                              _pct(A["calibration"].get("null", {}).get("act2_frac_gt_cutoff")), _pct(A["calibration"].get("bimodal", {}).get("act2_frac_gt_cutoff"))))
    L.append("## 2. Do Act II and split-half fire on the same chains?\n")
    L.append("Confusion matrix per cell (both / Act II only / split-half only / neither), the phi coefficient between the two indicators (0 = independent, "
             "1 = identical), Fisher's exact p for association, and the Jaccard overlap of the two fired sets (fired by both ÷ fired by either).\n")
    L.append("| arm | snapshot | window | n | both | Act II only | split only | neither | Act II fired | split fired | φ | Fisher p | Jaccard |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for arm in ARMS:
        for snap in SNAPS:
            for w in WINDOWS:
                c = cells.get("%s_%s_w%d" % (arm, snap, w))
                if not c:
                    continue
                L.append("| %s | %s | %d | %d | %d | %d | %d | %d | %s | %s | %s | %s | %s |" % (
                    LABEL[arm], snap, w, c["n"], c["both"], c["act2_only"], c["split_only"], c["neither"], _pct(c["act2_fired"]), _pct(c["split_fired"]),
                    _f(c["phi"]), _f(c["fisher_p"], "%.3f"), _f(c["jaccard"])))
        p_ = pooled[arm]
        L.append("| **%s, pooled** | — | — | %d | %d | %d | %d | %d | %s | %s | %s | %s | %s |" % (
            LABEL[arm], p_["n"], p_["both"], p_["act2_only"], p_["split_only"], p_["neither"], _pct(p_["act2_fired"]), _pct(p_["split_fired"]),
            _f(p_["phi"]), _f(p_["fisher_p"], "%.3f"), _f(p_["jaccard"])))
    L.append("\n## 3. Act II fit health on synchronised chains\n")
    L.append("| arm | snapshot | window | n | fit ok | g(k) ≥ 0 (butterfly-free) | density ≥ 0 on used range | normalised | mean within 15¢ of F0 | \\|mean − F0\\| median (¢) | p90 | strikes used med | dropped med | Lee slope b(1+\\|ρ\\|) med |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for arm in ARMS:
        for snap in SNAPS:
            for w in WINDOWS:
                c = cells.get("%s_%s_w%d" % (arm, snap, w))
                if not c:
                    continue
                L.append("| %s | %s | %d | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    LABEL[arm], snap, w, c["n"], _pct(c["act2_ok"]), _pct(c["butterfly_free"]), _pct(c["density_nonneg"]), _pct(c["normalised"]), _pct(c["mean_eq_fwd"]),
                    _f(c["mean_drift_abs_median"], "%.1f"), _f(c["mean_drift_abs_p90"], "%.1f"), _f(c["n_used_median"], "%.0f"), _f(c["n_dropped_median"], "%.0f"), _f(c["lee_slope_median"])))
    L.append("\n## 4. What the four classes of synchronised chain look like\n")
    L.append("| class | n | multimodal posterior mean | draws multimodal med | τ med | 90% body width med (¢) | strikes med | χ²/strike med | LOO flags mean | Act II Δ med (¢) | split max\\|z\\| med | Act II min g med | \\|Act II mean − F0\\| med (¢) | \\|ρ\\| med | ATM σ med | skew med | Act II inside band |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k, lab in (("both", "both fire"), ("act2_only", "Act II only"), ("split_only", "split-half only"), ("neither", "neither")):
        p_ = s.get("profiles", {}).get(k, {"n": 0})
        if not p_["n"]:
            L.append("| %s | 0 | | | | | | | | | | | | | | | |" % lab)
            continue
        L.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            lab, p_["n"], _pct(p_["multimodal_mean_frac"]), _pct(p_["draws_multimodal_median"]), _f(p_["tau_median"], "%.1f"), _f(p_["width90_median_cents"], "%.1f"),
            _f(p_["n_strikes_median"], "%.0f"), _f(p_["chi2_median"], "%.1f"), _f(p_["loo_flags_mean"], "%.1f"), _f(p_["act2_cents_median"]), _f(p_["split_z_median"]),
            _f(p_["act2_min_g_median"], "%.3f"), _f(p_["act2_mean_drift_abs_median"], "%.1f"), _f(p_["act2_rho_abs_median"]), _pct(p_["atm_sigma_median"]), _f(p_["skew_median"]),
            _pct(p_["act2_inside_band_frac"])))
    L.append("\nEvery synchronised chain where Act II fires and split-half does not:\n")
    L.append("| date | snap | w | strikes | trusted | Act II Δ (¢) | split max\\|z\\| | χ²/strike | modes | draws multimodal | τ | width90 (¢) | LOO flags | Act II min g | Act II mean − F0 (¢) | ρ | ATM σ | skew |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in A["act2_only_runs"]:
        L.append("| %s | %s | %d | %d | %s | %s | %s | %s | %d | %s | %s | %s | %d | %s | %s | %s | %s | %s |" % (
            r["date"], r["snap"], r["w"], r["n"], "yes" if r["trusted"] else "no", _f(r["cents"]), _f(r["split_z"]), _f(r["chi2"], "%.1f"), r["modes"], _pct(r["draws_mm"]),
            _f(r["tau"], "%.1f"), _f(r["width90"], "%.1f"), r["loo"], _f(r["min_g"], "%.3f"), _f(r["drift"], "%.0f"), _f(r["rho"]), _pct(r["sigma"]), _f(r["skew"])))
    L.append(READING)
    return "\n".join(L) + "\n"


def main() -> int:
    rs = pickle.load(open(HERE / "results_real" / "runs_v2.pkl", "rb"))
    A = analyse(rs)
    json.dump({k: v for k, v in A.items()}, open(HERE / "results_real" / "actii_v2.json", "w"), indent=1, default=str)
    text = render(A)
    (ROOT / "FINDINGS_ACTII_V2.md").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
