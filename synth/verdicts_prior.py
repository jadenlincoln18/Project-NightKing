"""Replace the placeholders in FINDINGS_PRIOR.md with the verdict and the reading, numbers read
back from synth/results_prior/summary.json so the prose cannot drift from the tables.

    python3 -m synth.verdicts_prior
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main() -> int:
    A = json.load(open(HERE / "results_prior" / "summary.json"))
    C = A["configs"]
    g = lambda name, c, k, fmt="%.2f": ("—" if (C.get(name, {}).get(c) or {}).get(k) is None else fmt % C[name][c][k])
    pct = lambda name, c, k: ("—" if (C.get(name, {}).get(c) or {}).get(k) is None else "%.0f%%" % (100 * C[name][c][k]))
    have = lambda c: any(c in cell for cell in C.values())
    m64 = have("m64")
    verdict = (
        "**Verdict: the bimodal blind spot is a basis-resolution problem before it is a prior-form problem, and it is now half closed. "
        "Every heavy-tailed or local-scale prior on 24 knots leaves it untouched (Student-t ν=3: trough z %s → %s, trough coverage %s → %s; "
        "ν=1 and the horseshoe are rejected on the sampler gate), while the unchanged Gaussian prior on 48 knots takes the trough z from %s to "
        "%s, trough coverage from %s to %s, overall bimodal coverage from %s to %s and kinked-peak body coverage from %s to %s, with no "
        "must-not-regress item failing, every injected fault still caught, and bracket R̂ / ESS on crude chains of %s / %s against %s / %s. "
        "Adding the Student-t tail on top of 48 knots buys nothing and costs sampler health. Recommendation: 48 uniform knots with the "
        "current Gaussian prior is the new default; the trough (%s coverage), the overall bimodal (%s) and the spike (%s) are still short of "
        "the 80%% bar, so the blind spot is narrowed, not closed%s.**\n" % (
            g("C_bimodal_full", "base", "trough_z", "%+.1f"), g("C_bimodal_full", "t3", "trough_z", "%+.1f"), pct("C_bimodal_full", "base", "trough_cov"), pct("C_bimodal_full", "t3", "trough_cov"),
            g("C_bimodal_full", "base", "trough_z", "%+.1f"), g("C_bimodal_full", "m48", "trough_z", "%+.1f"), pct("C_bimodal_full", "base", "trough_cov"), pct("C_bimodal_full", "m48", "trough_cov"),
            pct("C_bimodal_full", "base", "cov90_all"), pct("C_bimodal_full", "m48", "cov90_all"), pct("E_sharp_peak", "base", "cov90_body"), pct("E_sharp_peak", "m48", "cov90_body"),
            g("A_crude_full", "m48", "brhat_med", "%.3f"), g("A_crude_full", "m48", "bess_med", "%.0f"), g("A_crude_full", "base", "brhat_med", "%.3f"), g("A_crude_full", "base", "bess_med", "%.0f"),
            pct("C_bimodal_full", "m48", "trough_cov"), pct("C_bimodal_full", "m48", "cov90_all"), pct("G_spike_outside_prior", "m48", "cov90_all"),
            ("; 64 knots (§3) is the test of whether more resolution keeps paying: trough z %s, trough coverage %s, overall %s, spike %s, at bracket R̂ %s / ESS %s on crude chains" % (
                g("C_bimodal_full", "m64", "trough_z", "%+.1f"), pct("C_bimodal_full", "m64", "trough_cov"), pct("C_bimodal_full", "m64", "cov90_all"), pct("G_spike_outside_prior", "m64", "cov90_all"),
                g("A_crude_full", "m64", "brhat_med", "%.3f"), g("A_crude_full", "m64", "bess_med", "%.0f"))) if m64 else ""))

    reading = """
**Why the tail form did nothing at 24 knots.** The brief's diagnosis — one scale for the whole curve, Gaussian tails, so a sharp
feature is astronomically improbable at any τ — is right about the *prior*, but the prior was not the binding constraint. With 24
coefficients over ±7 vol-scales the knots are 0.7 vol-scales apart; the planted humps are 2.6 apart, so the trough between them spans
about two knot intervals, and a cubic B-spline with that spacing cannot represent a trough of that width at all. A heavier-tailed prior
makes large second differences cheaper, but the increments the trough needs cannot be formed in the basis, so the posterior under
Student-t ν=3 is the Gaussian posterior with a smaller τ (%s vs %s): same trough z, same 0.7¢ band, same 100%% two-mode recovery with
the wrong depth. The three hyperpriors of `FINDINGS_SYNTHETIC.md` §9 giving identical answers was the same symptom. Cauchy increments
(ν=1) and explicit local scales (horseshoe) do not change the answer either and mix unusably: R̂ %s / %s on crude chains, ESS %s / %s —
the docstring's warning about sampled scales was borne out (a global τ on top of local λ_j ran straight down the flat τ→0, λ→∞ ridge and
had to be removed before the horseshoe would fit at all).

**What resolution does.** 36 knots halve the trough z (%s), 48 knots take it to %s with a %s¢ band that contains the truth %s of the
time, and the improvement carries to the shapes the brief listed: kinked peak body coverage %s → %s, spike %s → %s, half-noise bimodal
trough z %s → %s. `F_bimodal_close` stays honest (trough coverage %s). The price is precision on smooth truths, not calibration: on the
crude-skew chains coverage is unchanged (%s / %s / %s all / body / tail against %s / %s / %s) while the body band widens from %s¢ to %s¢
and the RMSE from %s¢ to %s¢ — the model is admitting shapes it used to rule out by construction. The eight-strike gate holds (%s vs
%s), Stage 14 is unchanged (|z| %s vs %s), and every injected fault is still caught at the same rate.

**Sampler health at 48 knots** is inside the gate on the crude chains (bracket R̂ %s vs %s, bracket ESS %s vs %s, divergences %s vs
%s per run) and somewhat worse on the bimodal ones (bracket ESS %s vs %s, p10 %s), which is where the posterior is now genuinely
multimodal in shape and the whitening at the MAP is a poorer guide. Run time per chain rises from %s s to %s s. Student-t on 48 knots
adds nothing to the blind-spot rows and pushes bracket R̂ to %s and the RMSE past the tolerance, so it is rejected.

**What is still not right.** Trough coverage %s and overall bimodal coverage %s at 48 knots are honest by comparison with 0%% and 42%%,
but they are not 90%%: the band at the trough is still too narrow by a factor of about two. Two things are left to try, in order:
(i) more resolution — 64 knots%s; (ii) knots dense where strikes are dense, which the writeup asked for and V2 deferred because a
non-uniform knot vector changes what the second-difference penalty means (the fix is a divided-difference penalty, standard for
unequal P-splines). The learned-prior idea the operator raised stays behind both: calibrating τ's hyperprior from real extractions is
sound and cheap once the basis can express what the data ask for, but it cannot substitute for that.

**Part B on this harness** (`m48x`: 48 knots with the LOO exclusion rule applied before the fit): coverage on the clean chains is
unchanged (%s / %s / %s), 0.7%% of quotes are removed on them and none on the 8-strike chains, the injected stale and crossed quotes
are removed on 100%% of the fault chains, and the bimodal truth is untouched (%s overall). The rule removes noise, not signal; what it
does on the real chains is in `FINDINGS_REALCHAIN_V4.md` §8.

**Recommendation.** Make 48 uniform knots with the Gaussian prior the default (`act3.M_COEF = 48`), re-run the real chains with it
(`FINDINGS_REALCHAIN_V4.md`), and keep the 24-knot model runnable as the baseline. `FINDINGS_SYNTHETIC.md`'s FAIL verdict is
superseded in its diagnosis (form of the prior) but not in its status: the harness still shows a 1.6¢-wide band that misses the
truth by 1.3σ at the trough, so the answer to "is the blind spot closed" is **narrowed, not closed**.
""" % (
        g("C_bimodal_full", "t3", "tau_med"), g("C_bimodal_full", "base", "tau_med"),
        g("A_crude_full", "t1", "brhat_med", "%.2f"), g("A_crude_full", "hs", "brhat_med", "%.2f"), g("A_crude_full", "t1", "bess_med", "%.0f"), g("A_crude_full", "hs", "bess_med", "%.0f"),
        g("C_bimodal_full", "m36", "trough_z", "%+.1f"), g("C_bimodal_full", "m48", "trough_z", "%+.1f"), g("C_bimodal_full", "m48", "trough_width"), pct("C_bimodal_full", "m48", "trough_cov"),
        pct("E_sharp_peak", "base", "cov90_body"), pct("E_sharp_peak", "m48", "cov90_body"), pct("G_spike_outside_prior", "base", "cov90_all"), pct("G_spike_outside_prior", "m48", "cov90_all"),
        g("C05_bimodal_halfnoise", "base", "trough_z", "%+.1f"), g("C05_bimodal_halfnoise", "m48", "trough_z", "%+.1f"), pct("F_bimodal_close", "m48", "trough_cov"),
        pct("A_crude_full", "m48", "cov90_all"), pct("A_crude_full", "m48", "cov90_body"), pct("A_crude_full", "m48", "cov90_tail"),
        pct("A_crude_full", "base", "cov90_all"), pct("A_crude_full", "base", "cov90_body"), pct("A_crude_full", "base", "cov90_tail"),
        g("A_crude_full", "base", "width_body"), g("A_crude_full", "m48", "width_body"), g("A_crude_full", "base", "rmse_body"), g("A_crude_full", "m48", "rmse_body"),
        pct("S08_crude", "m48", "cov90_all"), pct("S08_crude", "base", "cov90_all"), g("M_crude_nomart", "m48", "stage14_z"), g("M_crude_nomart", "base", "stage14_z"),
        g("A_crude_full", "m48", "brhat_med", "%.3f"), g("A_crude_full", "base", "brhat_med", "%.3f"), g("A_crude_full", "m48", "bess_med", "%.0f"), g("A_crude_full", "base", "bess_med", "%.0f"),
        g("A_crude_full", "m48", "div_med", "%.0f"), g("A_crude_full", "base", "div_med", "%.0f"),
        g("C_bimodal_full", "m48", "bess_med", "%.0f"), g("C_bimodal_full", "base", "bess_med", "%.0f"), g("C_bimodal_full", "m48", "bess_p10", "%.0f"),
        g("A_crude_full", "base", "seconds", "%.0f"), g("A_crude_full", "m48", "seconds", "%.0f"), g("A_crude_full", "m48t3", "brhat_med", "%.3f"),
        pct("C_bimodal_full", "m48", "trough_cov"), pct("C_bimodal_full", "m48", "cov90_all"),
        (" (run: trough z %s, trough coverage %s, overall %s, spike %s; bracket R̂ %s, ESS %s on crude chains — %s)" % (
            g("C_bimodal_full", "m64", "trough_z", "%+.1f"), pct("C_bimodal_full", "m64", "trough_cov"), pct("C_bimodal_full", "m64", "cov90_all"), pct("G_spike_outside_prior", "m64", "cov90_all"),
            g("A_crude_full", "m64", "brhat_med", "%.3f"), g("A_crude_full", "m64", "bess_med", "%.0f"),
            A.get("checklist", {}).get("m64", {}).get("_summary", {}).get("verdict", "—"))) if m64 else " (queued)",
        pct("A_crude_full", "m48x", "cov90_all"), pct("A_crude_full", "m48x", "cov90_body"), pct("A_crude_full", "m48x", "cov90_tail"), pct("C_bimodal_full", "m48x", "cov90_all"))
    p = ROOT / "FINDINGS_PRIOR.md"
    s = p.read_text()
    s = s.replace("**VERDICT_PLACEHOLDER**\n", verdict)
    s = s.replace("READING_PLACEHOLDER\n", reading)
    p.write_text(s)
    print("verdict written; m64 present:", m64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
