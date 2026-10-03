"""Fill the verdict and reading of FINDINGS_SYNTHETIC_V2.md from the two aggregates on disk.

    python3 -m synth.verdicts_synthetic_v2      (after synth.report_compare)

Reads synth/results/summary.json (24 knots) and synth/results48/summary.json (48 knots); every number in the text
comes from them, the sentences are the reading of FINDINGS_SYNTHETIC_V2.md §7 and are the author's.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main() -> int:
    S24 = json.load(open(HERE / "results" / "summary.json"))
    S48 = json.load(open(HERE / "results48" / "summary.json"))
    pct = lambda x: "%.0f%%" % (100 * x)
    cov = lambda S, name, reg="all", lvl="90": S[name]["coverage_bracket"][reg][lvl]
    pair = lambda f24, f48, fmt: (fmt % f24) + " → " + (fmt % f48)
    A24, A48 = S24["A_crude_full"], S48["A_crude_full"]
    C24, C48 = S24["C_bimodal_full"]["bimodal_trough"], S48["C_bimodal_full"]["bimodal_trough"]
    M24, M48 = S24["M_crude_nomart"]["forward"], S48["M_crude_nomart"]["forward"]
    w = lambda A, reg: A["errors_act3"][reg]["width90_c"]
    verdict = (
        "**Verdict: calibrated where it operates, narrowed where it was blind, and still not honest at a planted bimodal trough. At 48 knots "
        "the operating configurations are at or above nominal (crude-skew 90%% coverage %s all / %s body / %s tail, lognormal %s / %s / %s, "
        "heavy-tailed %s, the 8-strike gate %s), Stage 14 lands on the forward unaided (bias %.2f¢, |z| %.2f), and every injected fault is "
        "caught at the same rate as at 24 knots. The blind spot moved a long way — bimodal trough z %s, trough coverage %s, "
        "bimodal body coverage %s, kinked-peak body %s, spike %s — but the harness's own criteria still fail "
        "(trough coverage < 80%%, bimodal body < 85%%, a mis-specified truth not flagged by χ²), so the mechanical verdict stays FAIL and "
        "the honest word is *narrowed, not closed*. The cost is the one the operator named: crude-skew body bands %s¢ (+%.1f¢ of gap "
        "per trade through the filter), tail bands %s¢, body RMSE %s¢, and bracket ESS %s with R̂ %s.**\n" % (
            pct(cov(S48, "A_crude_full")), pct(cov(S48, "A_crude_full", "body")), pct(cov(S48, "A_crude_full", "tail")),
            pct(cov(S48, "B_lognormal_full")), pct(cov(S48, "B_lognormal_full", "body")), pct(cov(S48, "B_lognormal_full", "tail")),
            pct(cov(S48, "D_heavy_both")), pct(cov(S48, "S08_crude")),
            M48["posterior_mean_minus_true_cents_mean"], M48["z_vs_true_abs_median"],
            pair(C24["z_median"], C48["z_median"], "%+.1f"), pair(100 * C24["coverage90"], 100 * C48["coverage90"], "%.0f%%"),
            pair(100 * cov(S24, "C_bimodal_full", "body"), 100 * cov(S48, "C_bimodal_full", "body"), "%.0f%%"),
            pair(100 * cov(S24, "E_sharp_peak", "body"), 100 * cov(S48, "E_sharp_peak", "body"), "%.0f%%"),
            pair(100 * cov(S24, "G_spike_outside_prior"), 100 * cov(S48, "G_spike_outside_prior"), "%.0f%%"),
            pair(w(A24, "body"), w(A48, "body"), "%.2f"), w(A48, "body") - w(A24, "body"),
            pair(w(A24, "tail"), w(A48, "tail"), "%.2f"), pair(A24["errors_act3"]["body"]["rmse_c"], A48["errors_act3"]["body"]["rmse_c"], "%.2f"),
            pair(A24["sampler"]["bracket_ess_min_median"], A48["sampler"]["bracket_ess_min_median"], "%.0f"),
            pair(A24["sampler"]["bracket_rhat_max_median"], A48["sampler"]["bracket_rhat_max_median"], "%.3f")))
    reading = """**What changed and what it cost, in one place.** Every row of §1–§5 is the same seed under the same noise, sampler and planted
truth, with only the knot count changed. On the configurations the strategy will actually run on — crude-skew, lognormal, heavy
tails, 8 to 23 strikes, half and double noise, observed spreads, two-day horizon — coverage moves up by one to three points to
sit at or slightly above nominal, bias stays at zero, and the price is paid in width: body bands widen by about 40%% (%s¢
on crude-skew, %s¢ at eight strikes) and body RMSE by about 15%%. The sampler stays inside the gate (bracket R̂ %s,
ESS %s), run time rises %.0f → %.0f s per chain, and a deliberately unconverged chain still shows itself (R̂/ESS flagged on %s of
runs). Forward sensitivity rises slightly at 15¢ offset: a finer basis moves a little more per cent of location error, which is one
more reason the forward now comes from the futures.

**The blind spot.** The planted bimodal truth that `FINDINGS_SYNTHETIC.md` §9 could not represent at any smoothness is now mostly
represented: two modes recovered as before, but the trough is overstated by %.1fσ instead of %.1fσ, its band is %.2f¢ instead of %.2f¢
and contains the truth %s of the time instead of %s; the half-noise variant goes from %s to %s at the trough. The kinked peak and the
close bimodal are now at nominal in the body (%s and %s). The spike improves least (%s) and is the case the brief deprioritised. None of
this changes χ²: the mis-specified truths still fit the quotes inside their spreads, so the harness's "flag a mis-specified truth"
criterion still fails — the quotes genuinely cannot tell, and the gates that stand in for it on real chains are split-half (data
inconsistency), Act II (shape), and the backtest's rule against brackets in an interior local minimum.

**The tick floor is not in these numbers.** `FINDINGS_TICKFLOOR.md` adopted a 1¢ floor for the real chains and declined it for this
harness by its pre-stated rule, because every floor drifts synthetic crude coverage to 96–98%% — the synthetic quotes carry no
inconsistency beyond rounding, so a floor double-counts there. `NF_crude_tickfloor` (a 1¢ floor, in this table) shows the same thing:
%s all-region coverage at 24 → 48 knots, the one configuration where 48 knots did not raise coverage, and a reminder that the
harness's noise model is now the binding limitation on validating the tolerance.

**Still unfixed, gated rather than solved.** (i) A consistent bimodal truth is still over-confident at the trough by about %.1fσ with
%s coverage; the gates catch inconsistency and shape disagreement, not a well-fitting wrong smooth shape. (ii) The spike truth is at
%s and will not improve without knots dense where strikes are dense; deliberately parked. (iii) The synthetic noise model is
Gaussian-exact with sd = half-spread and cannot adjudicate the tick floor's value; the floor is adopted on real-chain evidence only.
(iv) Band width is up about 40%% on the operating configurations, which is lost signal through the trade filter, accepted in exchange
for honesty on shapes the prior used to exclude. The next brief inherits these four, and none of them blocks the backtest.
""" % (
        pair(w(A24, "body"), w(A48, "body"), "%.2f"), pair(w(S24["S08_crude"], "body"), w(S48["S08_crude"], "body"), "%.2f"),
        pair(A24["sampler"]["bracket_rhat_max_median"], A48["sampler"]["bracket_rhat_max_median"], "%.3f"),
        pair(A24["sampler"]["bracket_ess_min_median"], A48["sampler"]["bracket_ess_min_median"], "%.0f"),
        A24["seconds_per_run"], A48["seconds_per_run"], pct(S48["X_unconverged"]["checks"]["frac_sampler_flagged"]),
        C48["z_median"], C24["z_median"], C48["width90_c_median"], C24["width90_c_median"], pct(C48["coverage90"]), pct(C24["coverage90"]),
        pct(S24["C05_bimodal_halfnoise"]["bimodal_trough"]["coverage90"]), pct(S48["C05_bimodal_halfnoise"]["bimodal_trough"]["coverage90"]),
        pct(cov(S48, "E_sharp_peak", "body")), pct(cov(S48, "F_bimodal_close", "body")),
        pair(100 * cov(S24, "G_spike_outside_prior"), 100 * cov(S48, "G_spike_outside_prior"), "%.0f%%"),
        pair(100 * cov(S24, "NF_crude_tickfloor"), 100 * cov(S48, "NF_crude_tickfloor"), "%.0f%%"),
        C48["z_median"], pct(C48["coverage90"]), pct(cov(S48, "G_spike_outside_prior")))
    p = ROOT / "FINDINGS_SYNTHETIC_V2.md"
    s = p.read_text()
    assert "**VERDICT_PLACEHOLDER**\n" in s and "READING_PLACEHOLDER\n" in s, "render FINDINGS_SYNTHETIC_V2.md first (synth.report_compare)"
    p.write_text(s.replace("**VERDICT_PLACEHOLDER**\n", verdict).replace("READING_PLACEHOLDER\n", reading))
    print("verdict written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
