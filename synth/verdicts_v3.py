"""Append §8 (the stated-in-advance verdict) to FINDINGS_REALCHAIN_V3.md after the tables are
rendered. The criteria come from NightKing/HANDOFF_actii_and_intraday.md Task 3; the numeric
operationalisation below was fixed before the numbers were seen:

    works    paired chi2/strike median at T-1d/60 falls by >= 0.20 from V2 (about half of the 1.6 -> 1.1 gap)
             AND T-4h/60 runs with a multimodal posterior majority fall to <= 12% (about half of V2's 23%)
    partial  exactly one of the two
    does not neither

    python3 -m synth.verdicts_v3
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CHI2_DROP = 0.20
T4H_MM_MAX = 0.12


def _c(S, arm, snap, w):
    return S["by_cell"].get("%s_%s_w%d" % (arm, snap, w), {})


def main() -> int:
    S = json.load(open(HERE / "results_real" / "summary_v2.json"))
    p = ROOT / "FINDINGS_REALCHAIN_V3.md"
    text = p.read_text()
    marker = "## 8. Verdicts\n"
    head = text[: text.index(marker)]
    pct = lambda x: "—" if x is None else "%.0f%%" % (100 * x)
    f = lambda x, fmt="%.1f": "—" if x is None else fmt % x
    pr = S.get("paired", {})
    p1 = pr.get("T-1d_w60", {})
    p4 = pr.get("T-4h_w60", {})
    p2 = pr.get("T-2d_w60", {})
    s1, r1 = _c(S, "sync", "T-1d", 60), _c(S, "real", "T-1d", 60)
    s4, r4 = _c(S, "sync", "T-4h", 60), _c(S, "real", "T-4h", 60)
    s2, r2 = _c(S, "sync", "T-2d", 60), _c(S, "real", "T-2d", 60)
    b1, b4 = _c(S, "base", "T-1d", 60), _c(S, "base", "T-4h", 60)
    v = S.get("path_validation", {})
    chi2_v2 = p1.get("sync", {}).get("chi2_median")
    chi2_v3 = p1.get("real", {}).get("chi2_median")
    mm_v2 = p4.get("sync", {}).get("multimodal_majority_frac")
    mm_v3 = p4.get("real", {}).get("multimodal_majority_frac")
    chi2_ok = chi2_v2 is not None and chi2_v3 is not None and (chi2_v2 - chi2_v3) >= CHI2_DROP
    mm_ok = mm_v3 is not None and mm_v3 <= T4H_MM_MAX
    verdict = "WORKS" if (chi2_ok and mm_ok) else ("PARTIAL" if (chi2_ok or mm_ok) else "DOES NOT")
    L = [marker]
    L.append("Criteria fixed in advance (`synth/verdicts_v3.py`): *works* = paired χ²/strike median at T-1d/60 falls by ≥ %.2f from V2 **and** T-4h/60 "
             "multimodal-majority runs fall to ≤ %.0f%%; *partial* = one of the two; *does not* = neither.\n" % (CHI2_DROP, 100 * T4H_MM_MAX))
    L.append("**Verdict: the real path %s.** Paired χ²/strike at T-1d/60: V2 %s → V3 %s (criterion: a drop of ≥ %.2f → %s). T-4h/60 multimodal-majority "
             "runs: V2 %s → V3 %s (criterion: ≤ %.0f%% → %s).\n" % (
                 {"WORKS": "works", "PARTIAL": "helps partially", "DOES NOT": "does not change the answer"}[verdict], f(chi2_v2), f(chi2_v3), CHI2_DROP,
                 "met" if chi2_ok else "not met", pct(mm_v2), pct(mm_v3), 100 * T4H_MM_MAX, "met" if mm_ok else "not met"))
    L.append("### What changed between V2 and V3, per snapshot (60-minute windows, paired dates)\n")
    L.append("| snapshot | n | χ²/strike med: V1 → V2 → V3 | χ² < 2: V1 → V2 → V3 | multimodal majority: V1 → V2 → V3 | Stage 14 pass: V2 → V3 | Gate 4 fired: V2 → V3 | 90% body width (¢): V2 → V3 |\n|---|---|---|---|---|---|---|---|")
    for snap, row in (("T-2d", p2), ("T-1d", p1), ("T-4h", p4)):
        if not row:
            continue
        g = lambda a, k, fn=f: fn(row.get(a, {}).get(k))
        L.append("| %s | %d | %s → %s → %s | %s → %s → %s | %s → %s → %s | %s → %s | %s → %s | %s → %s |" % (
            snap, row["n_common"], g("base", "chi2_median"), g("sync", "chi2_median"), g("real", "chi2_median"),
            g("base", "chi2_lt2_frac", pct), g("sync", "chi2_lt2_frac", pct), g("real", "chi2_lt2_frac", pct),
            g("base", "multimodal_majority_frac", pct), g("sync", "multimodal_majority_frac", pct), g("real", "multimodal_majority_frac", pct),
            g("sync", "meanF_ok_frac", pct), g("real", "meanF_ok_frac", pct), g("sync", "gate4_fired_frac", pct), g("real", "gate4_fired_frac", pct),
            g("sync", "width90_body_cents_median"), g("real", "width90_body_cents_median")))
    L.append("\n### The reconstruction against the real path\n")
    for k, lab in (("T-1d_w60", "T-1d / 60"), ("T-2d_w60", "T-2d / 60"), ("T-4h_w60", "T-4h / 60")):
        x = v.get(k)
        if not x:
            continue
        bd = {b["bin"]: b for b in x["by_distance"]}
        near = bd.get("0–5") or bd.get("5–15")
        far = bd.get("45–60") or bd.get("30–45")
        L.append("- **%s** (%d jobs, bar coverage %s): the reconstruction's shape error is %s¢ RMSE over the window (MAD %s¢, p10–p90 %s to %s¢), "
                 "%s¢ within 5 minutes of the anchor and %s¢ 45–60 minutes away; the real level at the anchor differs from the settlement/parity anchor "
                 "by %s¢ median (RMSE %s¢), and the real level at the snapshot instant from V2's forward by %s¢ RMSE.\n" % (
                     lab, x["n_jobs"], pct(x["coverage_median"]), f(x["shape"]["rmse_c"]), f(x["shape"]["mad_c"]), f(x["shape"]["p10_c"], "%.0f"), f(x["shape"]["p90_c"], "%.0f"),
                     f(near["rmse_c"]) if near else "—", f(far["rmse_c"]) if far else "—", f(x["level_at_anchor_minus_anchor_c"]["median"]),
                     f(x["level_at_anchor_minus_anchor_c"]["rmse"]), f(x["real_minus_recon_at_ref_c"]["rmse"])))
    L.append("### Reading\n")
    L.append("_(hand-written after the numbers; see below)_\n")
    L.append("READING_PLACEHOLDER\n")
    p.write_text(head + "\n".join(L) + "\n")
    print(verdict, "chi2 V2→V3 %s→%s" % (f(chi2_v2), f(chi2_v3)), "T-4h mm V2→V3 %s→%s" % (pct(mm_v2), pct(mm_v3)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
