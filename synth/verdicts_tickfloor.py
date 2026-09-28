"""Fill the verdict and reading of FINDINGS_TICKFLOOR.md from the aggregates on disk.

    python3 -m synth.verdicts_tickfloor      (after synth.tickfloor_report)
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main() -> int:
    A = json.load(open(HERE / "results_prior" / "summary.json"))["configs"]
    S = json.load(open(HERE / "results_real" / "summary_v2.json"))
    dec = json.load(open(HERE / "results_prior" / "tickfloor_decision.json"))
    c = lambda arm, snap, w=60: S["by_cell"].get("%s_%s_w%d" % (arm, snap, w), {})
    a = lambda name, cand, k: (A.get(name, {}).get(cand) or {}).get(k)
    pct = lambda x: "—" if x is None else "%.0f%%" % (100 * x)
    f = lambda x, fmt="%.1f": "—" if x is None else fmt % x
    b1, fl1, ex1, bo1 = c("real_m48", "T-1d"), c("real_m48_f1", "T-1d"), c("real_m48_x", "T-1d"), c("real_m48_f1x", "T-1d")
    b4, fl4, ex4 = c("real_m48", "T-4h"), c("real_m48_f1", "T-4h"), c("real_m48_x", "T-4h")
    b2, fl2, ex2 = c("real_m48", "T-2d"), c("real_m48_f1", "T-2d"), c("real_m48_x", "T-2d")
    rs = pickle.load(open(HERE / "results_real" / "runs_v2.pkl", "rb"))
    ex_runs = [r for r in rs if r.get("arm") == "real_m48_f1x" and r.get("exclusion") and "act3_bracket_mean" in r]
    have_both = bool(ex_runs) and bool(bo1 and "chi2_per_strike_median" in bo1)
    both_removed = (100.0 * np.mean([r["exclusion"]["frac_removed"] for r in ex_runs])) if ex_runs else None
    both_suspect = (100.0 * np.mean([r["exclusion"]["suspect"] for r in ex_runs])) if ex_runs else None
    verdict = (
        "**Verdict: the floor works on the real chains and the exclusion rule is mostly, not entirely, redundant with it — adopt the 1¢ floor "
        "for the real chains, keep the exclusion rule as a diagnostic, and do not adopt it as a default. With a 1¢ floor and no quote "
        "removed, T-1d/60 χ²/strike goes %s → %s (T-4h %s → %s, T-2d %s → %s), Gate 4 fires on %s instead of %s of T-1d chains, Stage 14 passes "
        "on %s instead of %s, bands narrow slightly (%s → %s¢) and the sampler is unchanged; the exclusion rule gets χ² to %s and Gate 4 to %s "
        "but by deleting %s of quotes. Leave-one-out still flags strikes on %s of floored chains, so a residual of genuinely inconsistent "
        "quotes remains that the tolerance does not explain%s. The synthetic harness could not admit any floor: every variant kept coverage "
        "on the fault, 8-strike and bimodal chains and improved RMSE, but drifted crude-skew coverage to %s–%s because its noise model is "
        "Gaussian-exact with sd = half-spread and has no tick-level inconsistency to absorb — so, by the rule fixed in advance, the full "
        "synthetic study (`FINDINGS_SYNTHETIC_V2.md`) ran without a floor. That is a limitation of the harness, not evidence against the "
        "floor, and it is the one place this document departs from \"synthetic is the arbiter\": the floor exists for a feature of real "
        "quotes the synthetic quotes do not have.**\n" % (
            f(b1.get("chi2_per_strike_median")), f(fl1.get("chi2_per_strike_median")), f(b4.get("chi2_per_strike_median")), f(fl4.get("chi2_per_strike_median")),
            f(b2.get("chi2_per_strike_median")), f(fl2.get("chi2_per_strike_median")), pct(fl1.get("gate4_fired_frac")), pct(b1.get("gate4_fired_frac")),
            pct(fl1.get("checks", {}).get("mean_equals_forward_ok")), pct(b1.get("checks", {}).get("mean_equals_forward_ok")),
            f(b1.get("width90_body_cents_median")), f(fl1.get("width90_body_cents_median")), f(ex1.get("chi2_per_strike_median")), pct(ex1.get("gate4_fired_frac")),
            "8–10%", pct(fl1.get("loo_flagged_frac")),
            (" (the combined arm removes %.1f%% of quotes on top of the floor, %s of chains marked suspect, and reaches χ² %s, Gate 4 %s)" % (
                both_removed, pct(both_suspect / 100.0 if both_suspect is not None else None), f(bo1.get("chi2_per_strike_median")), pct(bo1.get("gate4_fired_frac")))) if have_both else "",
            pct(min(v["crude_cov90"] for v in dec["verdicts"].values() if v["crude_cov90"])), pct(max(v["crude_cov90"] for v in dec["verdicts"].values() if v["crude_cov90"]))))
    reading = """**Why the floor is right on real chains and wrong on the harness.** A 1¢-wide market says the fair price is somewhere inside a
penny; the writeup's tolerance (sd = half-spread = 0.5¢) says it is known to half a penny at one sigma, so two adjacent tight quotes
that disagree by 2¢ — ordinary on a one-cent grid — are a 4σ event and the fit is pulled toward whichever one it can satisfy. On the
real chains the floor takes T-1d χ²/strike from %s to %s and T-4h to %s, the p90 from %s to %s at T-1d, the split-half gate from %s
to %s, and it does so with every quote in place and bands %s¢ rather than %s¢ (the tight quotes lose some pull, so the posterior
moves less between neighbours). On the synthetic harness the quotes are generated as the true price plus Gaussian noise with exactly
the half-spread as its scale, then rounded; there is no inconsistency between neighbours beyond that rounding, so any floor makes the
assumed noise larger than the real noise and coverage rises above nominal (%s → %s for 0.5¢ in quadrature, %s for 1¢) while width and
RMSE improve. The decision rule was fixed to reject exactly that drift, and it did. The harness would need a tick-inconsistency
component in its noise model to arbitrate the floor's *value*; what it can say is that a 1¢ floor costs nothing on calibration of the
fault detectors (stale and crossed quotes caught on 100%% of chains), on the 8-strike gate or on the bimodal shapes.

**Is the exclusion rule redundant?** Mostly. Under the floor the rule's own criterion (LOO |z| > 3) still fires on %s of T-1d chains
against %s without it, because a subset of quotes disagree with their neighbours by more than a tick — 2026-02-27, 2026-03-06,
2026-04-10, 2026-05-22 and 2026-07-10 in §3 keep 4–8 flags under the floor and only the rule clears them. Those are the chains where
the two treatments disagree; on the other %d chains listed the floor alone brings χ² to ≈ 1 and Gate 4 is quiet either way. The rule
therefore adds a second, smaller effect, and it buys it by deleting a tenth of the quotes on half the T-1d chains. The brief's
question — is deleting good-looking quotes still justified after the tolerance is corrected — has the answer: only as a diagnostic
that names the chains the backtest should distrust, not as a default that edits every chain.

**Recommendation.** For the real chains, `hs_floor = 0.01` (max) is the tolerance; the exclusion rule stays available (`--arms *x`) and
its flag count is reported per chain but nothing is removed by default. The full synthetic numbers in `FINDINGS_SYNTHETIC_V2.md` are
without the floor, per the rule; re-running the harness with a tick-inconsistency noise term and the floor is the natural next
validation, and it is small.
""" % (
        f(b1.get("chi2_per_strike_median")), f(fl1.get("chi2_per_strike_median")), f(fl4.get("chi2_per_strike_median")), f(b1.get("chi2_per_strike_p90")), f(fl1.get("chi2_per_strike_p90")),
        pct(b1.get("gate4_fired_frac")), pct(fl1.get("gate4_fired_frac")), f(fl1.get("width90_body_cents_median")), f(b1.get("width90_body_cents_median")),
        pct(a("A_crude_full", "m48", "cov90_all")), pct(a("A_crude_full", "f05q", "cov90_all")), pct(a("A_crude_full", "f1", "cov90_all")),
        pct(fl1.get("loo_flagged_frac")), pct(b1.get("loo_flagged_frac")), 19)
    p = ROOT / "FINDINGS_TICKFLOOR.md"
    s = p.read_text()
    s = s.replace("**VERDICT_PLACEHOLDER**\n", verdict).replace("READING_PLACEHOLDER\n", reading)
    p.write_text(s)
    print("verdict written; combined arm present:", have_both)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
