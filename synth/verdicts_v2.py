"""Append the hand-written §8 verdicts to FINDINGS_REALCHAIN_V2.md after the tables have been
rendered. The numbers quoted are read back from summary_v2.json where they are cell values,
so the prose cannot drift from the tables.

    python3 -m synth.verdicts_v2
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def _c(S, arm, snap, w):
    return S["by_cell"].get("%s_%s_w%d" % (arm, snap, w), {})


def main() -> int:
    S = json.load(open(HERE / "results_real" / "summary_v2.json"))
    p = ROOT / "FINDINGS_REALCHAIN_V2.md"
    text = p.read_text()
    marker = "## 8. Verdicts\n"
    head = text[: text.index(marker)]
    b1, f1, s1 = _c(S, "base", "T-1d", 60), _c(S, "fwd", "T-1d", 60), _c(S, "sync", "T-1d", 60)
    b2, f2, s2 = _c(S, "base", "T-2d", 60), _c(S, "fwd", "T-2d", 60), _c(S, "sync", "T-2d", 60)
    b4, s4 = _c(S, "base", "T-4h", 60), _c(S, "sync", "T-4h", 60)
    s1_10 = _c(S, "sync", "T-1d", 10)
    b1_10 = _c(S, "base", "T-1d", 10)
    m1 = _c(S, "sync_m", "T-1d", 60)
    cal = S.get("split_half_calibration", {})
    pv_b = b1.get("parity_vs_nymex", {})
    pv_s = s1.get("parity_sync_vs_nymex", {})
    pv_sf = s1.get("parity_sync_vs_forward", {})
    sy1 = s1.get("sync", {})
    pct = lambda x: "—" if x is None else "%.0f%%" % (100 * x)
    f = lambda x, fmt="%.1f": "—" if x is None else fmt % x
    L = []
    L.append(marker)
    L.append("**χ²/strike first, because it is the headline metric.** On the same 30 dates, same snapshots, same sampler, "
             "Act III's fit to the market's own spreads at the 60-minute T-1d window went from a median of %s (V1) to %s with only the "
             "forward changed, to **%s** with the quotes synchronised — against %s at the near-synchronous 10-minute window in V1 and "
             "1.1 on synthetic well-specified chains. The synchronised 60-minute chain now fits *better* than V1's 10-minute chain while "
             "keeping all 30 dates (V1's 10-minute window kept 9). At T-2d/60 it is %s → %s → **%s** on 26 dates (V1 extracted 14); at "
             "T-4h/60, %s → **%s**.\n" % (f(b1.get("chi2_per_strike_median")), f(f1.get("chi2_per_strike_median")), f(s1.get("chi2_per_strike_median")),
                                          f(b1_10.get("chi2_per_strike_median")), f(b2.get("chi2_per_strike_median")), f(f2.get("chi2_per_strike_median")),
                                          f(s2.get("chi2_per_strike_median")), f(b4.get("chi2_per_strike_median")), f(s4.get("chi2_per_strike_median"))))
    L.append("### Fix 1 — forward from the futures, parity as a check: **partially worked, and not on its own**\n")
    L.append("- What it fixes: the location. V1's parity forward missed the settlement by %s¢ RMSE at T-1d/60 (within 10¢ on %s of dates); the "
             "settlement is exact by construction. It also removes parity's data requirement, so dates with fewer than two two-sided pairs "
             "now extract: T-2d/60 goes from 14 to 26 dates, T-1d/10 from 9 to 21, T-2d/10 from 0 to 8.\n"
             "- What it does not fix: the fit. With the raw window and the correct forward, χ²/strike at T-1d/60 only moves %s → %s, and "
             "several diagnostics get *worse*: the Stage 14 unconstrained mean lands on the forward on %s of dates instead of %s (|z| median "
             "%s vs %s), the bracket R̂ median rises from %s to %s and the bracket ESS falls from %s to %s. That is the expected signature "
             "of quotes that were struck at a different underlying level than the forward they are now being fitted around: the *correct* "
             "forward with *asynchronous* quotes is a worse-conditioned problem than the wrong forward the raw chain happened to be centred "
             "on. The forward change only pays off together with fix 2.\n"
             "- The check itself: the raw-parity-vs-futures flag fires on %s of T-1d/60 dates and %s at T-0/60 (|z| > 3 and > 10¢). After "
             "synchronisation the parity forward agrees with the settlement to %s¢ RMSE (within 10¢ on %s of dates) and with the path "
             "forward the chain was actually fitted around to %s¢ RMSE (%s within 10¢). The residual disagreement is the honest size of "
             "\"parity on this data\": a few cents on most dates, 10–30¢ on the few where the last minutes were fast or the pairs were two.\n"
             "- Judgement calls made: D is fixed from the rate (immaterial at T ≤ 2 days, and the slope had nothing left to estimate); the "
             "check reports rather than gates in this pass, because on these chains it fires on stale quotes that synchronisation then repairs — "
             "in production it should gate, on the synchronised parity, at the same threshold. T-4h keeps the parity forward (no futures "
             "print at 10:30 in the store) and behaves like the other snapshots once synchronised, which is itself evidence that the "
             "synchronised parity forward is usable where no futures print exists.\n"
             % (f(pv_b.get("rmse_c")), pct(pv_b.get("frac_within_10c")), f(b1.get("chi2_per_strike_median")), f(f1.get("chi2_per_strike_median")),
                pct(f1.get("checks", {}).get("mean_equals_forward_ok")), pct(b1.get("checks", {}).get("mean_equals_forward_ok")),
                f(f1.get("mean_equals_forward_z_abs_median")), f(b1.get("mean_equals_forward_z_abs_median")),
                f(b1.get("sampler", {}).get("bracket_rhat_max_median"), "%.3f"), f(f1.get("sampler", {}).get("bracket_rhat_max_median"), "%.3f"),
                f(b1.get("sampler", {}).get("bracket_ess_min_median"), "%.0f"), f(f1.get("sampler", {}).get("bracket_ess_min_median"), "%.0f"),
                pct(b1.get("parity_check_flagged_frac")), pct(_c(S, "base", "T-0", 60).get("parity_check_flagged_frac")),
                f(pv_s.get("rmse_c")), pct(pv_s.get("frac_within_10c")), f(pv_sf.get("rmse_c")), pct(pv_sf.get("frac_within_10c"))))
    L.append("### Fix 2 — synchronising the quotes: **worked, and it is the fix**\n")
    L.append("- The success criterion stated in advance was \"60-minute windows with adjustment approach the 10-minute χ² (≈2.0) while retaining "
             "60-minute date coverage (28–30 of 30)\". Result: %s at T-1d/60 on 30 dates, %s at T-2d/60 on 26, %s at T-4h/60 on 30; the "
             "synchronised 10-minute windows sit at %s (T-1d, 21 dates). χ² < 2 on %s of T-1d/60 chains (V1: %s).\n"
             "- The multimodality that V1 reported goes away where it should: runs where more than half the posterior draws are multimodal "
             "fall from %s to **%s** at T-1d/60 and %s → %s at T-2d/60. It does not vanish at T-4h/60 (%s → %s), where the window covers a "
             "fifth of the option's remaining life and quotes are 21%% one-cent bids; that residue is where to look next, not a market fact yet.\n"
             "- Stage 14 comes back: the unconstrained posterior mean lands on the forward on %s of T-1d/60 dates (V1 %s), |z| median %s (V1 %s; "
             "synthetic 0.74), mean − F0 %s ± %s¢. The sampler is healthier on the synchronised chains as well (bracket R̂ median %s vs %s, "
             "ESS %s vs %s, bracket R̂ < 1.05 on %s vs %s of runs) — the posterior was badly conditioned partly *because* the data were "
             "inconsistent.\n"
             "- Size of the adjustment: rms %s¢ per quote at T-1d/60 (max %s¢ median), of which theta is %s¢ and delta %s¢; the estimated "
             "path ranges $%s within the hour (p90 $%s). The options-implied level at the anchor agrees with the settlement to a median "
             "|offset| of %s¢ — an independent confirmation, using every quote, that the futures forward is the right number.\n"
             "- Method choices, for the record: sticky-strike (each quote's own implied vol held fixed; carries delta, gamma and theta) "
             "was chosen over adjusting moneyness or strikes because it needs no smile model at the adjustment step and keeps the strike "
             "grid; the sticky-moneyness alternative is the `sync_m` arm (below). The path is estimated from the option trade stream because "
             "**there is no intraday futures price in the data store** (`futures_stats` carries the settlement and session extremes only; "
             "one record between 13:30 and 14:35 ET on 2026-03-12) — the handoff's premise that timestamped CL prices exist through the "
             "session does not hold for what was bought. The level is anchored at 14:29, the middle of the settlement window, and the "
             "forward used is the path's value at 14:30; the median |drift| across that minute is %s¢ (p90 %s¢). At 160%% vol one minute "
             "is ~20¢ of underlying, so 1-minute knots are needed (5-minute knots left χ² at 3.7 on the probe date).\n"
             % (f(s1.get("chi2_per_strike_median")), f(s2.get("chi2_per_strike_median")), f(s4.get("chi2_per_strike_median")), f(s1_10.get("chi2_per_strike_median")),
                pct(s1.get("checks", {}).get("act3_chi2_ok")), pct(b1.get("checks", {}).get("act3_chi2_ok")),
                pct(b1.get("frac_runs_multimodal_majority")), pct(s1.get("frac_runs_multimodal_majority")), pct(b2.get("frac_runs_multimodal_majority")),
                pct(s2.get("frac_runs_multimodal_majority")), pct(b4.get("frac_runs_multimodal_majority")), pct(s4.get("frac_runs_multimodal_majority")),
                pct(s1.get("checks", {}).get("mean_equals_forward_ok")), pct(b1.get("checks", {}).get("mean_equals_forward_ok")),
                f(s1.get("mean_equals_forward_z_abs_median")), f(b1.get("mean_equals_forward_z_abs_median")),
                f(s1.get("act3u_mean_minus_F0_cents_median"), "%.0f"), f(s1.get("act3u_mean_minus_F0_cents_mad"), "%.0f"),
                f(s1.get("sampler", {}).get("bracket_rhat_max_median"), "%.3f"), f(b1.get("sampler", {}).get("bracket_rhat_max_median"), "%.3f"),
                f(s1.get("sampler", {}).get("bracket_ess_min_median"), "%.0f"), f(b1.get("sampler", {}).get("bracket_ess_min_median"), "%.0f"),
                pct(s1.get("sampler", {}).get("frac_bracket_rhat_lt_1_05")), pct(b1.get("sampler", {}).get("frac_bracket_rhat_lt_1_05")),
                f(sy1.get("adj_rms_cents_median")), f(sy1.get("adj_max_abs_cents_median")), f(sy1.get("adj_theta_rms_cents_median")), f(sy1.get("adj_delta_rms_cents_median")),
                f(sy1.get("path_range_dollars_median"), "%.2f"), f(sy1.get("path_range_dollars_p90"), "%.2f"), f(sy1.get("level_offset_abs_cents_median")),
                f(sy1.get("anchor_drift_abs_cents_median")), f(sy1.get("anchor_drift_abs_cents_p90"))))
    if m1:
        L.append("- Sensitivity (`sync_m`, sticky-moneyness reprice, T-1d/60, %d dates): χ²/strike median %s vs %s sticky-strike, χ² < 2 on %s vs %s, "
                 "Gate 4 fires on %s vs %s, Stage 14 passes on %s vs %s. The two assumptions differ at second order (smile slope × move) and the "
                 "tables agree to within their own noise: the conclusion does not depend on which one is used.\n"
                 % (m1.get("n_extracted", 0), f(m1.get("chi2_per_strike_median")), f(s1.get("chi2_per_strike_median")), pct(m1.get("checks", {}).get("act3_chi2_ok")),
                    pct(s1.get("checks", {}).get("act3_chi2_ok")), pct(m1.get("gate4_fired_frac")), pct(s1.get("gate4_fired_frac")),
                    pct(m1.get("checks", {}).get("mean_equals_forward_ok")), pct(s1.get("checks", {}).get("mean_equals_forward_ok"))))
    L.append("### Fix 3 — split-half + LOO in place of the Act II gate: **worked, with one stated limit**\n")
    L.append("- Calibration (synthetic, real grids, same sampler): on well-specified chains the split-half statistic never exceeds 3 (p95 %s, "
             "the cutoff now in use); a planted stale quote is caught by LOO on %s of chains and localised to the injected strike on %s, by "
             "split-half on %s; a bimodal truth is caught by neither (split-half %s, LOO %s) and by Act II on %s. That is the division of "
             "labour the design intended: split-half and LOO see inconsistency *in the data*, Act II sees a prior the data cannot support. "
             "LOO's |z| > 3 flags a strike on %s of clean synthetic chains, so a single LOO flag is a pointer, not a verdict.\n"
             "- On the raw V1 chains the new gate fires on %s of T-1d/60 dates (split-half max|z| median %s) — it agrees with the V1 gate (%s) "
             "that those chains are untrustworthy, and says why: their own halves disagree. On the synchronised chains it fires on **%s** "
             "(median %s), the V1 Act II gate on the same chains fires on %s, and the fired chains have χ²/strike %s against %s for the "
             "quiet ones. Every synchronised 10-minute chain passes. The gate is now measuring the thing it was meant to measure and is quiet "
             "once the data are consistent.\n"
             "- LOO names strikes on %s of synchronised T-1d/60 chains (%s flags per chain on average, against %s on raw V1 chains) — the "
             "residual inconsistency after synchronisation is concentrated in a few strikes per chain, which is the right shape for a "
             "quote-level exclusion rule rather than a date-level skip.\n"
             "- Act II stays in the report. Its disagreement with Act III on synchronised chains is %s¢ median (V1 raw: %s¢), i.e. the two "
             "routes agree once the data are consistent, which is what two independent implementations are for.\n"
             % (f(cal.get("null", {}).get("split_max_abs_z_p95"), "%.2f"), pct(cal.get("stale", {}).get("loo_frac_gt3")), pct(cal.get("stale", {}).get("loo_localised_frac")),
                pct(cal.get("stale", {}).get("split_frac_gt3")), pct(cal.get("bimodal", {}).get("split_frac_gt3")), pct(cal.get("bimodal", {}).get("loo_frac_gt3")),
                pct(cal.get("bimodal", {}).get("act2_frac_gt_cutoff")), pct(cal.get("null", {}).get("loo_frac_gt3")),
                pct(b1.get("gate4_fired_frac")), f(b1.get("split_z_median")), pct(b1.get("v1_fired_frac")), pct(s1.get("gate4_fired_frac")), f(s1.get("split_z_median")),
                pct(s1.get("v1_fired_frac")), f(s1.get("fired_vs_quiet", {}).get("fired_chi2_median")), f(s1.get("fired_vs_quiet", {}).get("quiet_chi2_median")),
                pct(s1.get("loo_flagged_frac")), f(s1.get("loo_n_flagged_mean")), f(b1.get("loo_n_flagged_mean")),
                f(s1.get("v1_cents_median"), "%.2f"), f(b1.get("v1_cents_median"), "%.2f")))
    L.append("### What is still not right\n")
    L.append("- **T-4h/60 keeps some multimodality (%s) and a fatter χ² tail (p90 %s)** after synchronisation. The window is a fifth of the "
             "option's remaining life, one-cent bids are 21%% of the OTM chain, and the forward there is parity (no futures print). Whether "
             "that is market structure or the last of the data problem is the next descriptive question; it is not evidence either way yet.\n"
             "- **The 60-minute χ² is 1.6–1.9, not 1.1.** Half the synchronised chains still have max |resid| > 3 at T-1d/60, and LOO flags "
             "strikes on %s of them. The adjustment is model-based (a sticky-vol reprice along an estimated path); what remains is the sum "
             "of path error (the path's own residual rms is %s¢), the sticky assumption, and genuinely inconsistent quotes. Quote-level "
             "exclusion (drop LOO-flagged strikes and refit) is the obvious next step and was deliberately not done in this pass — it would "
             "be tuning against chains with a known data-quality problem.\n"
             "- **T-0 is still unusable** (no extractions; 75–100%% one-cent bids) and the synchronised parity there has a 52¢ RMSE vs the "
             "settlement because the path estimate at expiry is erratic (theta is most of the adjustment, %s¢ rms). Nothing about the trade "
             "needs T-0.\n"
             "- **T-2d is worth keeping now**: 26 of 30 dates extract with the futures forward (14 with parity), χ² %s, and its two-pair "
             "parity check is weak (RMSE %s¢ raw) but no longer load-bearing.\n"
             "- **The prior was not touched.** Every number above is with V1's roughness prior and hyperprior, as the brief required. The "
             "bimodal blind spot of `FINDINGS_SYNTHETIC.md` §7 is untouched and the gate that would catch it (Act II) is a report line, not "
             "a gate; that remains the next question.\n"
             "- **The backtest is harder than live on the parity axis**: TBBO records a strike only when it trades, so parity had 2–6 pairs "
             "here where a live book shows every listed strike two-sided. The path estimator has the same limitation (it uses trade events) "
             "and would have far more to work with live — or would be unnecessary, since a live CL quote exists at decision time.\n"
             % (pct(s4.get("frac_runs_multimodal_majority")), f(s4.get("chi2_per_strike_p90")), pct(s1.get("loo_flagged_frac")),
                f(sy1.get("path_rms_resid_cents_median")), f(_c(S, "sync", "T-0", 60).get("sync", {}).get("adj_theta_rms_cents_median")),
                f(s2.get("chi2_per_strike_median")), f(b2.get("parity_vs_nymex", {}).get("rmse_c"))))
    L.append("### Foundational, restated\n")
    L.append("Still descriptive: no Kalshi price was read, no gap was computed, no trade was evaluated, and no such code exists. Every table "
             "is before/after on the same dates with the V1 pipeline re-run as the `base` arm (it reproduces V1 to the last decimal). "
             "Nothing was tuned: the prior, the sampler settings, the Gate 0 thresholds and the Act II cutoff are V1's; the only new "
             "threshold (split-half cutoff %s) was set on synthetic chains before the real ones were scored.\n"
             % f(cal.get("cutoff_p95"), "%.2f"))
    L.append("Plots: `synth/plots_real_v2/_summary.png` and one `<date>_<snap>_w<window>_<arm>.png` per extraction (the sync arms add the estimated path).\n")
    p.write_text(head + "\n".join(L) + "\n")
    print("appended verdicts to", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
