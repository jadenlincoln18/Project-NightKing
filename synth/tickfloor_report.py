"""FINDINGS_TICKFLOOR.md: a tick floor on the likelihood tolerance against the LOO exclusion rule,
on the synthetic harness (synth/results_prior, candidates m48 / f1 / f2 / f1q / m48x / f1x on the same
seeds) and on the real chains (arms real_m48 / real_m48_x / real_m48_f1 / real_m48_f2 / real_m48_f1x).

    python3 -m synth.tickfloor_report
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from . import prior_study

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SYN = ["m48", "f1", "f1q", "f2", "m48x", "f1x"]
SYN_LABEL = {"m48": "base48: 48 knots, no floor, no exclusion", "f1": "floor48: 1¢ (max)", "f1q": "floor48: 1¢ (quadrature)", "f2": "floor48: 2¢ (max)",
             "m48x": "excl48: LOO exclusion, no floor", "f1x": "both: 1¢ floor + exclusion"}
REAL = ["real_m48", "real_m48_f1", "real_m48_f2", "real_m48_x", "real_m48_f1x"]
REAL_LABEL = {"real_m48": "base48", "real_m48_f1": "floor48 1¢", "real_m48_f2": "floor48 2¢", "real_m48_x": "excl48", "real_m48_f1x": "both (1¢ + excl)"}
SNAPS = ("T-2d", "T-1d", "T-4h")


def _pct(x):
    return "—" if x is None else "%.0f%%" % (100 * x)


def _f(x, fmt="%.2f"):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else fmt % x


def _cell(S, arm, snap, w):
    return S["by_cell"].get("%s_%s_w%d" % (arm, snap, w), {})


def render() -> str:
    A = json.load(open(HERE / "results_prior" / "summary.json"))
    C = A["configs"]
    dec = json.load(open(HERE / "results_prior" / "tickfloor_decision.json")) if (HERE / "results_prior" / "tickfloor_decision.json").exists() else {}
    S = json.load(open(HERE / "results_real" / "summary_v2.json"))
    rs = pickle.load(open(HERE / "results_real" / "runs_v2.pkl", "rb"))
    by = {(r["settle_date"], r["snap"], r.get("window_min", 60), r.get("arm")): r for r in rs if r.get("error") is None and "act3_bracket_mean" in r}
    syn = [c for c in SYN if any(c in cell for cell in C.values())]
    real = [a for a in REAL if any(k.startswith(a + "_T") for k in S["by_cell"])]
    L: List[str] = []
    L.append("# FINDINGS_TICKFLOOR — a tick floor on the likelihood tolerance, against the LOO exclusion rule\n")
    L.append("Task 1 of `NightKing/HANDOFF_tickfloor_and_fullsynth.md`. The likelihood's tolerance is the quote's half-spread; options trade in 1¢ ticks, "
             "so a 1¢-wide market (half-spread 0.5¢) does not locate the price to 0.5¢, and `FINDINGS_PRIOR.md` Part B found that the exclusion rule "
             "was removing exactly those quotes (57% of removed quotes had a 0.5¢ half-spread). On the real chains 26–32% of quotes are 1¢ wide and a "
             "further 20–23% are 2¢ wide, so a half-tick floor is a no-op (nothing is below 0.5¢) and the sweep is 1¢, 1¢ added in quadrature, and 2¢. "
             "Every arm is 48 knots with the Gaussian prior; the exclusion rule is Part B's (LOO |z| > 3, once, Gate 0 preserved).\n")
    L.append("**VERDICT_PLACEHOLDER**\n")
    if dec:
        L.append("Decision rule fixed before the runs (`synth/tickfloor_decide.py`): a floor is admissible if crude-skew 90% coverage stays in [88%, 95%] and "
                 "within 3 points of base48, the stale and crossed injected quotes are still caught on ≥ 90% of chains, bimodal coverage is within 5 points of "
                 "base48, and bracket R̂ ≤ 1.03; the smallest admissible floor is adopted. Outcome: **%s**.\n" % (
                     ("adopt %s" % SYN_LABEL[dec["chosen"]]) if dec.get("chosen") else "no floor admissible"))
        L.append("| candidate | admissible | crude cov90 in [88, 95]% | not 3 pts below base48 | stale caught | crossed caught | bimodal within 5 pts | bracket R̂ ≤ 1.03 |\n|---|---|---|---|---|---|---|---|")
        for c, v in dec["verdicts"].items():
            ch = v["checks"]
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (SYN_LABEL.get(c, c), "**yes**" if v["admissible"] else "no", *["✓" if ch[k] else "✗" for k in
                     ("crude_cov90_in_band", "crude_cov90_vs_m48", "stale_caught", "convexity_caught", "bimodal_cov_vs_m48", "bracket_rhat")]))
    # ---- synthetic
    L.append("\n## 1. Synthetic harness (paired seeds, 48 knots throughout)\n")
    L.append("| config | arm | n | cov90 all | body | tail | RMSE body (¢) | tail | width body (¢) | tail | χ²/strike med | bracket R̂ med | bracket ESS med | quotes removed / chain | injected strike removed | injected resid > 3 | Stage 14 \\|z\\| |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name in ["A_crude_full", "B_lognormal_full", "S08_crude", "C_bimodal_full", "X_stale", "X_convexity"]:
        cell = C.get(name, {})
        for c in syn:
            m = cell.get(c)
            if not m or not m.get("n"):
                continue
            rem = inj = None
            p = HERE / "results_prior" / c / ("%s.pkl" % name)
            if p.exists():
                rr = [r for r in pickle.load(open(p, "rb")) if r.get("error") is None and r.get("exclusion")]
                if rr:
                    rem = float(np.mean([r["exclusion"]["n_removed"] for r in rr]))
                    inj = float(np.mean([r["exclusion"]["injected_removed"] for r in rr])) if name.startswith("X_") else None
            L.append("| %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                name, SYN_LABEL[c], m["n"], _pct(m["cov90_all"]), _pct(m["cov90_body"]), _pct(m["cov90_tail"]), _f(m["rmse_body"]), _f(m["rmse_tail"]), _f(m["width_body"]), _f(m["width_tail"]),
                _f(m["chi2_med"]), _f(m["brhat_med"], "%.3f"), _f(m["bess_med"], "%.0f"), _f(rem) if rem is not None else "0", _pct(inj) if inj is not None else "—",
                _pct(m.get("fault_resid")) if name.startswith("X_") else "—", _f(m.get("stage14_z"))))
    # ---- real chains
    L.append("\n## 2. Real chains (30 dates, every snapshot; 48 knots throughout)\n")
    L.append("| snapshot | window | arm | n | χ²/strike med (p90) | χ² < 2 | max resid < 3 | Gate 4 fired | LOO flags / chain | chains with a LOO flag | quotes removed / chain | share removed | Stage 14 pass | \\|z\\| med | multimodal majority | 90% body width (¢) | bracket R̂ med | bracket ESS med | divergences med |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for snap in SNAPS:
        for w in (60, 10):
            for a in real:
                d = _cell(S, a, snap, w)
                if not d or "chi2_per_strike_median" not in d:
                    continue
                ex = [r["exclusion"] for (dt, sn, ww, ar), r in by.items() if ar == a and sn == snap and ww == w and r.get("exclusion")]
                rem = float(np.mean([e["n_removed"] for e in ex])) if ex else 0.0
                share = float(np.mean([e["frac_removed"] for e in ex])) if ex else 0.0
                sm = d.get("sampler", {})
                L.append("| %s | %d | %s | %d | %s (%s) | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    snap, w, REAL_LABEL[a], d["n_extracted"], _f(d["chi2_per_strike_median"], "%.1f"), _f(d["chi2_per_strike_p90"], "%.1f"), _pct(d["checks"]["act3_chi2_ok"]),
                    _pct(d["checks"]["act3_max_resid_ok"]), _pct(d["gate4_fired_frac"]), _f(d["loo_n_flagged_mean"], "%.1f"), _pct(d["loo_flagged_frac"]), _f(rem, "%.1f"), _pct(share),
                    _pct(d["checks"]["mean_equals_forward_ok"]), _f(d["mean_equals_forward_z_abs_median"], "%.1f"), _pct(d["frac_runs_multimodal_majority"]),
                    _f(d["width90_body_cents_median"], "%.1f"), _f(sm.get("bracket_rhat_max_median"), "%.3f"), _f(sm.get("bracket_ess_min_median"), "%.0f"), _f(sm.get("divergences_median"), "%.0f")))
    # ---- disagreement
    if "real_m48_x" in real and any(a.startswith("real_m48_f") for a in real):
        fa = "real_m48_f1" if "real_m48_f1" in real else [a for a in real if a.startswith("real_m48_f")][0]
        L.append("\n## 3. Where the floor and the exclusion rule disagree (60-minute windows, %s vs excl48)\n" % REAL_LABEL[fa])
        L.append("Gate 4 (split-half) and the LOO flag count per chain under each treatment; a chain is listed if Gate 4's answer differs or the "
                 "χ²/strike differs by more than 0.5.\n")
        L.append("| date | snap | strikes | χ²: base48 / floor / excl | Gate 4: base48 / floor / excl | LOO flags: base48 / floor / excl | quotes removed by excl | modes: floor / excl | width (¢): floor / excl |\n|---|---|---|---|---|---|---|---|---|")
        n_dis = 0
        for (date, snap, w, a), rb in sorted(by.items()):
            if a != "real_m48" or w != 60:
                continue
            rf, rx = by.get((date, snap, w, fa)), by.get((date, snap, w, "real_m48_x"))
            if rf is None or rx is None:
                continue
            gf, gx = bool(rf["split_half"]["max_abs_z"] > rf["detector"].get("cutoff", 2.65)), bool(rx["split_half"]["max_abs_z"] > rx["detector"].get("cutoff", 2.65))
            if gf != gx or abs(rf["act3_chi2_per_strike"] - rx["act3_chi2_per_strike"]) > 0.5:
                n_dis += 1
                L.append("| %s | %s | %d | %.1f / %.1f / %.1f | %s / %s / %s | %d / %d / %d | %d | %d / %d | %.1f / %.1f |" % (
                    date, snap, rb["n_strikes"], rb["act3_chi2_per_strike"], rf["act3_chi2_per_strike"], rx["act3_chi2_per_strike"],
                    "fired" if rb["split_half"]["max_abs_z"] > rb["detector"].get("cutoff", 2.65) else "quiet", "fired" if gf else "quiet", "fired" if gx else "quiet",
                    rb["loo"]["n_flagged"], rf["loo"]["n_flagged"], rx["loo"]["n_flagged"], rx["exclusion"]["n_removed"], rf["act3_n_modes"], rx["act3_n_modes"],
                    100 * float(np.max(rf["act3_bracket_width90"])), 100 * float(np.max(rx["act3_bracket_width90"]))))
        L.append("\n%d chains listed.\n" % n_dis)
    L.append("\n## 4. Reading\n\nREADING_PLACEHOLDER\n")
    return "\n".join(L) + "\n"


def main() -> int:
    text = render()
    p = ROOT / "FINDINGS_TICKFLOOR.md"
    p.write_text(text)
    print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
