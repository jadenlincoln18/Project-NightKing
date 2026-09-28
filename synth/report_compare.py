"""FINDINGS_SYNTHETIC_V2.md: the full synthetic study at 48 knots (synth/results48) against the 24-knot
study behind FINDINGS_SYNTHETIC.md (synth/results), side by side on every table, same configurations,
same seeds, same sampler settings.

    python3 -m synth.report_compare
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from . import report, runner

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIR24 = HERE / "results"
DIR48 = HERE / "results48"


def _pct(x):
    return "—" if x is None else "%.0f%%" % (100 * x)


def _f(x, fmt="%.2f"):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else fmt % x


def _load_summary(d: Path) -> Dict[str, Any]:
    p = d / "summary.json"
    if p.exists():
        return json.load(open(p))
    runner.RESULTS = d
    return report.aggregate(list(runner.CONFIGS))


def _pair(s):
    return "%s → %s" % s


def render(S24: Dict[str, Any], S48: Dict[str, Any], floor: float, mode: str) -> str:
    names = [n for n in runner.CONFIGS if n in S24 and n in S48 and S48[n].get("n_runs")]
    L: List[str] = []
    L.append("# FINDINGS_SYNTHETIC_V2 — the full synthetic study at 48 knots, 24 vs 48 side by side\n")
    L.append("Task 2 of `NightKing/HANDOFF_tickfloor_and_fullsynth.md`. Every configuration, seed and sampler setting of `FINDINGS_SYNTHETIC.md` "
             "(the 24-knot study) re-run with `act3.M_COEF = 48`%s. Each cell is 24 → 48. Coverage is the headline; band width is the cost "
             "and is reported next to it everywhere.\n" % ((" and a %.0f¢ tick floor (%s) on the likelihood tolerance, adopted in `FINDINGS_TICKFLOOR.md`" % (100 * floor, mode)) if floor > 0 else " and no tick floor (`FINDINGS_TICKFLOOR.md` did not adopt one)"))
    L.append("**VERDICT_PLACEHOLDER**\n")
    L.append("## 1. Bracket coverage at 90% (the primary test), by region\n")
    L.append("Body = brackets worth ≥ 10¢, tail = 1–10¢ (where the strategy trades), far < 1¢, open = the two open-ended brackets. n = runs.\n")
    L.append("| config | n | all | body | tail | far | open | 50% level (all) | 95% level (all) |\n|---|---|---|---|---|---|---|---|---|")
    for n in names:
        a, b = S24[n]["coverage_bracket"], S48[n]["coverage_bracket"]
        g = lambda t, r, k: _pct((t.get(r) or {}).get(k))
        L.append("| %s | %d → %d | %s | %s | %s | %s | %s | %s | %s |" % (
            n, S24[n]["n_runs"], S48[n]["n_runs"], _pair((g(a, "all", "90"), g(b, "all", "90"))), _pair((g(a, "body", "90"), g(b, "body", "90"))), _pair((g(a, "tail", "90"), g(b, "tail", "90"))),
            _pair((g(a, "far", "90"), g(b, "far", "90"))), _pair((g(a, "open", "90"), g(b, "open", "90"))), _pair((g(a, "all", "50"), g(b, "all", "50"))), _pair((g(a, "all", "95"), g(b, "all", "95")))))
    L.append("\n## 2. Error and band width (¢), by region\n")
    L.append("| config | RMSE body | RMSE tail | bias body | width90 body | width90 tail | density RMSE body (rel. peak) |\n|---|---|---|---|---|---|---|")
    for n in names:
        a, b = S24[n]["errors_act3"], S48[n]["errors_act3"]
        da, db = S24[n]["density_err_act3"], S48[n]["density_err_act3"]
        g = lambda t, r, k, fmt="%.2f": _f((t.get(r) or {}).get(k), fmt)
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            n, _pair((g(a, "body", "rmse_c"), g(b, "body", "rmse_c"))), _pair((g(a, "tail", "rmse_c"), g(b, "tail", "rmse_c"))), _pair((g(a, "body", "bias_c", "%+.2f"), g(b, "body", "bias_c", "%+.2f"))),
            _pair((g(a, "body", "width90_c"), g(b, "body", "width90_c"))), _pair((g(a, "tail", "width90_c"), g(b, "tail", "width90_c"))),
            _pair((_f((da.get("body") or {}).get("rmse_rel_peak"), "%.3f"), _f((db.get("body") or {}).get("rmse_rel_peak"), "%.3f")))))
    L.append("\n## 3. The blind spot: bimodal, spike, kink\n")
    L.append("| config | trough z med | trough 90% width (¢) | trough coverage | modes recovered | cov90 all | cov90 body | χ²/strike med | τ med |\n|---|---|---|---|---|---|---|---|---|")
    for n in [x for x in names if x.startswith(("C", "F", "G", "E", "D"))]:
        a, b = S24[n], S48[n]
        ta, tb = a.get("bimodal_trough") or {}, b.get("bimodal_trough") or {}
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            n, _pair((_f(ta.get("z_median"), "%+.1f"), _f(tb.get("z_median"), "%+.1f"))), _pair((_f(ta.get("width90_c_median")), _f(tb.get("width90_c_median")))),
            _pair((_pct(ta.get("coverage90")), _pct(tb.get("coverage90")))), _pair((_pct(a["modes"]["frac_recovered"]), _pct(b["modes"]["frac_recovered"]))),
            _pair((_pct(a["coverage_bracket"]["all"]["90"]), _pct(b["coverage_bracket"]["all"]["90"]))), _pair((_pct((a["coverage_bracket"].get("body") or {}).get("90")), _pct((b["coverage_bracket"].get("body") or {}).get("90")))),
            _pair((_f(a["checks"]["chi2_per_strike_median"]), _f(b["checks"]["chi2_per_strike_median"]))), _pair((_f(a["checks"]["tau_median"]), _f(b["checks"]["tau_median"])))))
    L.append("\n## 4. Sampler health\n")
    L.append("| config | R̂ max med (p90), raw | min ESS med | divergences med | bracket R̂ med (p90) | bracket ESS med (p10) | bracket R̂ < 1.01 | bracket ESS ≥ 400 | s / run |\n|---|---|---|---|---|---|---|---|---|")
    for n in names:
        a, b = S24[n]["sampler"], S48[n]["sampler"]
        L.append("| %s | %s (%s) | %s | %s | %s (%s) | %s (%s) | %s | %s | %s |" % (
            n, _pair((_f(a["rhat_max_median"], "%.3f"), _f(b["rhat_max_median"], "%.3f"))), _pair((_f(a["rhat_max_p90"], "%.3f"), _f(b["rhat_max_p90"], "%.3f"))),
            _pair((_f(a["ess_min_median"], "%.0f"), _f(b["ess_min_median"], "%.0f"))), _pair((_f(a["divergences_median"], "%.0f"), _f(b["divergences_median"], "%.0f"))),
            _pair((_f(a["bracket_rhat_max_median"], "%.3f"), _f(b["bracket_rhat_max_median"], "%.3f"))), _pair((_f(a["bracket_rhat_max_p90"], "%.3f"), _f(b["bracket_rhat_max_p90"], "%.3f"))),
            _pair((_f(a["bracket_ess_min_median"], "%.0f"), _f(b["bracket_ess_min_median"], "%.0f"))), _pair((_f(a["bracket_ess_min_p10"], "%.0f"), _f(b["bracket_ess_min_p10"], "%.0f"))),
            _pair((_pct(a["frac_bracket_rhat_lt_1_01"]), _pct(b["frac_bracket_rhat_lt_1_01"]))), _pair((_pct(a["frac_bracket_ess_ge_400"]), _pct(b["frac_bracket_ess_ge_400"]))),
            _pair((_f(S24[n]["seconds_per_run"], "%.0f"), _f(S48[n]["seconds_per_run"], "%.0f")))))
    L.append("\n## 5. Stage 14, the forward, and the injected faults\n")
    L.append("| config | Stage 14 bias (¢) | \\|z\\| vs truth med | E[F] 90% cov | parity flags the forward | z(used) > 3 | injected resid > 3 | χ² > 2 | edge-mass fails | sampler flagged | Act II − Act III med (¢) |\n|---|---|---|---|---|---|---|---|---|---|---|")
    for n in [x for x in names if x.startswith(("M", "X", "A_"))]:
        a, b = S24[n], S48[n]
        fa, fb, ca, cb = a["forward"], b["forward"], a["checks"], b["checks"]
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            n, _pair((_f(fa["posterior_mean_minus_true_cents_mean"], "%+.2f"), _f(fb["posterior_mean_minus_true_cents_mean"], "%+.2f"))), _pair((_f(fa["z_vs_true_abs_median"]), _f(fb["z_vs_true_abs_median"]))),
            _pair((_pct(a["coverage_meanF_posterior"]["90"]), _pct(b["coverage_meanF_posterior"]["90"]))), _pair((_pct(fa["frac_parity_vs_used_gt3se"]), _pct(fb["frac_parity_vs_used_gt3se"]))),
            _pair((_pct(fa["frac_z_vs_used_gt3"]), _pct(fb["frac_z_vs_used_gt3"]))), _pair((_pct(ca["frac_inject_resid_gt3"]), _pct(cb["frac_inject_resid_gt3"]))),
            _pair((_pct(ca["frac_chi2_gt2"]), _pct(cb["frac_chi2_gt2"]))), _pair((_pct(ca["frac_edge_mass_fail"]), _pct(cb["frac_edge_mass_fail"]))), _pair((_pct(ca["frac_sampler_flagged"]), _pct(cb["frac_sampler_flagged"]))),
            _pair((_f(a["act2"]["vs_act3_max_abs_cents_median"]), _f(b["act2"]["vs_act3_max_abs_cents_median"])))))
    fs24, fs48 = S24.get("_forward_sensitivity", {}), S48.get("_forward_sensitivity", {})
    if fs24 and fs48:
        L.append("\nForward sensitivity (¢ of bracket per ¢ of forward error, max over brackets, median run): " + "; ".join(
            "%s %s → %s" % (k, _f(fs24[k]["max_abs_cents_per_cent_median"], "%.3f"), _f(fs48[k]["max_abs_cents_per_cent_median"], "%.3f")) for k in fs24 if k in fs48) + ".\n")
    u24, u48 = S24.get("_unconverged_width_ratio"), S48.get("_unconverged_width_ratio")
    if u24 and u48:
        L.append("Unconverged-chain band width relative to converged (median): %s → %s.\n" % (_f(u24["median"]), _f(u48["median"])))
    L.append("\n## 6. Mechanical criteria (the report's own verdict function, on each study)\n")
    V24, V48 = report.verdict(S24), report.verdict(S48)
    L.append("| criterion | 24 knots | 48 knots |\n|---|---|---|")
    def _crit(t):
        if t is None:
            return "—"
        v, ok = t
        vv = ("%.3f" % v) if isinstance(v, float) else (", ".join(("%.2f" % x) if isinstance(x, float) else str(x) for x in v) if isinstance(v, tuple) else str(v))
        return "%s %s" % (vv, "✓" if ok else ("✗" if ok is False else ""))
    for k in V24.get("core", {}):
        L.append("| %s | %s | %s |" % (k, _crit(V24["core"].get(k)), _crit(V48["core"].get(k))))
    L.append("| **verdict** | **%s** (%d core failures) | **%s** (%d core failures) |" % (V24["verdict"], len(V24["failed"]), V48["verdict"], len(V48["failed"])))
    L.append("\n## 7. Verdict and what remains unfixed\n\nREADING_PLACEHOLDER\n")
    L.append("Plots: `synth/plots48/` (48 knots) and `synth/plots/` (24 knots), same file names.\n")
    return "\n".join(L) + "\n"


def main() -> int:
    S24 = _load_summary(DIR24)
    S48 = _load_summary(DIR48)
    dec_p = HERE / "results_prior" / "tickfloor_decision.json"
    dec = json.load(open(dec_p)) if dec_p.exists() else {"hs_floor": 0.0, "hs_floor_mode": "max"}
    text = render(S24, S48, float(dec.get("hs_floor", 0.0)), dec.get("hs_floor_mode", "max"))
    p = ROOT / "FINDINGS_SYNTHETIC_V2.md"
    p.write_text(text)
    print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
