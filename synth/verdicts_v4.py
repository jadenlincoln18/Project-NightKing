"""Append §8 to FINDINGS_REALCHAIN_V4.md: V3 vs V4 (48 / 36 knots) on the real chains, the two
watched chains individually, Part B (LOO exclusion) if its arm ran, and the verdict. Numbers come
from summary_v2.json and runs_v2.pkl.

    python3 -m synth.verdicts_v4
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WATCH = [("2026-05-01", "T-4h", 60), ("2026-03-06", "T-4h", 60), ("2026-05-29", "T-4h", 60)]
ARMS = ["real", "real_m36", "real_m48", "real_m48_x"]
LABEL = {"real": "V3 (24 knots)", "real_m36": "V4 36 knots", "real_m48": "V4 48 knots", "real_m48_x": "V4 48 knots + LOO exclusion", "real_t3": "V4 Student-t"}


def _c(S, arm, snap, w):
    return S["by_cell"].get("%s_%s_w%d" % (arm, snap, w), {})


def main() -> int:
    S = json.load(open(HERE / "results_real" / "summary_v2.json"))
    rs = pickle.load(open(HERE / "results_real" / "runs_v2.pkl", "rb"))
    by = {(r["settle_date"], r["snap"], r.get("window_min", 60), r.get("arm")): r for r in rs if r.get("error") is None}
    arms = [a for a in ARMS if any(k.startswith(a + "_T") for k in S["by_cell"])]
    pct = lambda x: "—" if x is None else "%.0f%%" % (100 * x)
    f = lambda x, fmt="%.1f": "—" if x is None else fmt % x
    L: List[str] = ["## 8. Verdicts\n"]
    # ---- summary table per snapshot
    L.append("### V3 → V4 on the 60-minute windows, all extracted dates\n")
    L.append("| snapshot | arm | n | χ²/strike med (p90) | χ² < 2 | multimodal majority | posterior-mean modes | Stage 14 pass | \\|z\\| med | Gate 4 fired | Act II fired | LOO flags / chain | 90% body width (¢) | bracket R̂ med | bracket ESS med | τ med | s / run |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for snap in ("T-2d", "T-1d", "T-4h"):
        for a in arms:
            d = _c(S, a, snap, 60)
            if not d or "chi2_per_strike_median" not in d:
                continue
            sm = d.get("sampler", {})
            L.append("| %s | %s | %d | %s (%s) | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                snap, LABEL.get(a, a), d["n_extracted"], f(d["chi2_per_strike_median"]), f(d["chi2_per_strike_p90"]), pct(d["checks"]["act3_chi2_ok"]),
                pct(d["frac_runs_multimodal_majority"]), d["modes_hist"], pct(d["checks"]["mean_equals_forward_ok"]), f(d["mean_equals_forward_z_abs_median"]),
                pct(d["gate4_fired_frac"]), pct(d["v1_fired_frac"]), f(d["loo_n_flagged_mean"]), f(d["width90_body_cents_median"]),
                f(sm.get("bracket_rhat_max_median"), "%.3f"), f(sm.get("bracket_ess_min_median"), "%.0f"), f(d["tau_median"]), f(sm.get("seconds_median"), "%.0f")))
    # ---- watched chains
    L.append("\n### The chains to watch: 2026-05-01 and 2026-03-06 at T-4h (and 2026-05-29, which lost its modes under the real path)\n")
    L.append("| date | arm | strikes | χ²/strike | modes (posterior mean) | draws multimodal | τ med | 90% body width (¢) | split-half max\\|z\\| | LOO flags | Act II Δ (¢) | bracket R̂ | bracket ESS | Stage 14 z |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for date, snap, w in WATCH:
        for a in ["real", "real_t3"] + [x for x in arms if x != "real"]:
            r = by.get((date, snap, w, a))
            if r is None or "act3_n_modes" not in r:
                continue
            L.append("| %s | %s | %d | %s | %d | %s | %s | %s | %s | %d | %s | %s | %s | %s |" % (
                date, LABEL.get(a, a), r["n_strikes"], f(r["act3_chi2_per_strike"], "%.2f"), r["act3_n_modes"], pct(r["act3_frac_draws_multimodal"]), f(r["act3_tau_q"][1], "%.2f"),
                f(100 * float(np.max(r["act3_bracket_width90"]))), f(r["split_half"]["max_abs_z"]), r["loo"]["n_flagged"], f(r["act2_signal"]["cents"], "%.2f"),
                f(r["act3_bracket_rhat_max"], "%.3f"), f(r["act3_bracket_ess_min"], "%.0f"), f(r["checks"]["mean_equals_forward_z"])))
    # ---- multimodal chains under V4: which ones, and were they multimodal under V3?
    L.append("\nChains whose posterior mean is multimodal under 48 knots (60-minute windows), with their V3 state:\n")
    L.append("| date | snap | V3 modes | V3 draws multimodal | V4(48) modes | V4(48) draws multimodal | V4(48) χ²/strike | V4(48) τ | V4(48) LOO flags | V4(48) split max\\|z\\| |\n|---|---|---|---|---|---|---|---|---|---|")
    for (date, snap, w, a), r in sorted(by.items()):
        if a != "real_m48" or w != 60 or "act3_n_modes" not in r or r["act3_n_modes"] < 2:
            continue
        v3 = by.get((date, snap, w, "real"), {})
        L.append("| %s | %s | %s | %s | %d | %s | %s | %s | %d | %s |" % (
            date, snap, v3.get("act3_n_modes", "—"), pct(v3.get("act3_frac_draws_multimodal")), r["act3_n_modes"], pct(r["act3_frac_draws_multimodal"]),
            f(r["act3_chi2_per_strike"], "%.2f"), f(r["act3_tau_q"][1], "%.2f"), r["loo"]["n_flagged"], f(r["split_half"]["max_abs_z"])))
    # ---- Part B
    ex_runs = [r for (d_, s_, w_, a_), r in by.items() if a_ == "real_m48_x" and r.get("exclusion") and "act3_bracket_mean" in r]
    if ex_runs:
        L.append("\n### Part B — quote-level exclusion at 48 knots (rule fixed in advance: LOO |z| > 3, one pass, Gate 0 preserved)\n")
        rem = [x for r in ex_runs for x in r["exclusion"]["removed"]]
        n_q = sum(r["n_strikes_pre_exclusion"] for r in ex_runs)
        L.append("Over %d chains and %d quotes the rule removed %d quotes (%.1f%%); %d chains (%s) lost more than 10%% of their quotes and are "
                 "marked suspect. Removed quotes: %s calls / %s puts; moneyness rank median %s (0 = nearest the money; chain median %s strikes); "
                 "quote age median %s min (all quotes: %s); half-spread median %s¢ (all: %s¢); |z| median %s.\n" % (
                     len(ex_runs), n_q, len(rem), 100.0 * len(rem) / max(n_q, 1), sum(1 for r in ex_runs if r["exclusion"]["suspect"]),
                     pct(np.mean([r["exclusion"]["suspect"] for r in ex_runs])), pct(np.mean([x["right"] == "C" for x in rem])) if rem else "—",
                     pct(np.mean([x["right"] == "P" for x in rem])) if rem else "—", f(np.median([x["moneyness_rank"] for x in rem]), "%.0f") if rem else "—",
                     f(np.median([r["n_strikes_pre_exclusion"] for r in ex_runs]), "%.0f"),
                     f(np.median([x["age_min"] for x in rem if x["age_min"] is not None])) if rem else "—",
                     f(np.median([r["quote_age_median_min"] for r in ex_runs])), f(100 * np.median([x["hs"] for x in rem])) if rem else "—",
                     f(100 * np.median([r["hs_median"] for r in ex_runs])), f(np.median([abs(x["z"]) for x in rem])) if rem else "—"))
        L.append("| snapshot | window | chains | quotes removed / chain (mean) | share removed | chains > 10% | χ²/strike med: 48 knots → + exclusion | χ² < 2 | max resid < 3 | Gate 4 fired | LOO flags after | multimodal majority | Stage 14 pass | 90% body width (¢) |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for snap in ("T-2d", "T-1d", "T-4h"):
            for w in (60, 10):
                sub = [r for r in ex_runs if r["snap"] == snap and r.get("window_min", 60) == w]
                base = _c(S, "real_m48", snap, w)
                d = _c(S, "real_m48_x", snap, w)
                if not sub or not d or "chi2_per_strike_median" not in d:
                    continue
                L.append("| %s | %d | %d | %s | %s | %s | %s → %s | %s → %s | %s → %s | %s → %s | %s → %s | %s → %s | %s → %s | %s → %s |" % (
                    snap, w, len(sub), f(np.mean([r["exclusion"]["n_removed"] for r in sub])), pct(np.mean([r["exclusion"]["frac_removed"] for r in sub])),
                    pct(np.mean([r["exclusion"]["suspect"] for r in sub])), f(base.get("chi2_per_strike_median")), f(d["chi2_per_strike_median"]),
                    pct(base.get("checks", {}).get("act3_chi2_ok")), pct(d["checks"]["act3_chi2_ok"]), pct(base.get("checks", {}).get("act3_max_resid_ok")), pct(d["checks"]["act3_max_resid_ok"]),
                    pct(base.get("gate4_fired_frac")), pct(d["gate4_fired_frac"]), f(base.get("loo_n_flagged_mean")), f(d["loo_n_flagged_mean"]),
                    pct(base.get("frac_runs_multimodal_majority")), pct(d["frac_runs_multimodal_majority"]), pct(base.get("checks", {}).get("mean_equals_forward_ok")), pct(d["checks"]["mean_equals_forward_ok"]),
                    f(base.get("width90_body_cents_median")), f(d["width90_body_cents_median"])))
        # by position / age / spread
        if rem:
            ranks = np.array([x["moneyness_rank"] for x in rem]); ages = np.array([x["age_min"] if x["age_min"] is not None else np.nan for x in rem])
            hs = np.array([x["hs"] for x in rem]) * 100
            L.append("\nRemoved quotes by position (moneyness rank quartile of the chain), age and spread:\n")
            L.append("| | rank 0–4 | rank 5–9 | rank 10–19 | rank ≥ 20 | age < 5 min | 5–20 | 20–40 | > 40 | half-spread ≤ 1¢ | 1–2¢ | > 2¢ |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
            L.append("| removed quotes | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |" % (
                (ranks <= 4).sum(), ((ranks >= 5) & (ranks <= 9)).sum(), ((ranks >= 10) & (ranks <= 19)).sum(), (ranks >= 20).sum(),
                (ages < 5).sum(), ((ages >= 5) & (ages < 20)).sum(), ((ages >= 20) & (ages < 40)).sum(), (ages >= 40).sum(),
                (hs <= 1.0001).sum(), ((hs > 1.0001) & (hs <= 2.0001)).sum(), (hs > 2.0001).sum()))
    L.append("\n### Reading\n\nREADING_V4_PLACEHOLDER\n")
    p = ROOT / "FINDINGS_REALCHAIN_V4.md"
    text = p.read_text()
    marker = "## 8. Verdicts\n"
    head = text[: text.index(marker)]
    p.write_text(head + "\n".join(L) + "\n")
    print("appended §8; arms:", arms, "exclusion chains:", len(ex_runs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
