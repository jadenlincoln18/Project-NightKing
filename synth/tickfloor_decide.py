"""Task 1 decision rule, fixed before the runs (HANDOFF_tickfloor_and_fullsynth.md): which tick floor,
if any, to adopt. Judged on the synthetic harness against the 48-knot no-floor baseline (`m48`) on the
same seeds:

    a floor is admissible if   crude-skew 90% bracket coverage is within [0.88, 0.95] and not more than 3
                               points below m48; the injected stale and crossed quotes are still caught by
                               the residual check on >= 90% of chains; bimodal coverage is not more than 5
                               points below m48; bracket R-hat on crude chains <= 1.03
    among admissible floors    adopt the smallest one (0.5c quadrature < 1c max < 1c quadrature < 2c max, by
                               the tolerance it adds to a 0.5c quote); if none is admissible, adopt no floor.

Writes synth/results_prior/tickfloor_decision.json, which the driver reads to configure the real-chain
arms it runs next and the full synthetic study.

    python3 -m synth.tickfloor_decide
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = [("f05q", 0.005, "quad"), ("f1", 0.01, "max"), ("f1q", 0.01, "quad"), ("f2", 0.02, "max")]


def main() -> int:
    A = json.load(open(HERE / "results_prior" / "summary.json"))
    C = A["configs"]
    g = lambda name, c, k: (C.get(name, {}).get(c) or {}).get(k)
    verdicts = {}
    for cand, floor, mode in ORDER:
        cov = g("A_crude_full", cand, "cov90_all")
        checks = {
            "crude_cov90_in_band": cov is not None and 0.88 <= cov <= 0.95,
            "crude_cov90_vs_m48": cov is not None and cov >= (g("A_crude_full", "m48", "cov90_all") or 0) - 0.03,
            "stale_caught": (g("X_stale", cand, "fault_resid") or 0) >= 0.90,
            "convexity_caught": (g("X_convexity", cand, "fault_resid") or 0) >= 0.90,
            "bimodal_cov_vs_m48": (g("C_bimodal_full", cand, "cov90_all") or 0) >= (g("C_bimodal_full", "m48", "cov90_all") or 0) - 0.05,
            "bracket_rhat": (g("A_crude_full", cand, "brhat_med") or 9) <= 1.03,
            "ran": bool(g("A_crude_full", cand, "n")),
        }
        verdicts[cand] = {"floor": floor, "mode": mode, "checks": checks, "admissible": all(checks.values()),
                          "crude_cov90": cov, "crude_width_body": g("A_crude_full", cand, "width_body"), "crude_rmse_body": g("A_crude_full", cand, "rmse_body")}
    chosen = next((c for c, _, _ in ORDER if verdicts[c]["admissible"]), None)
    out = {"chosen": chosen, "hs_floor": verdicts[chosen]["floor"] if chosen else 0.0, "hs_floor_mode": verdicts[chosen]["mode"] if chosen else "max",
           "verdicts": verdicts, "rule": __doc__}
    json.dump(out, open(HERE / "results_prior" / "tickfloor_decision.json", "w"), indent=1)
    print("chosen:", chosen, "->", out["hs_floor"], out["hs_floor_mode"])
    for c, v in verdicts.items():
        print(" ", c, "admissible" if v["admissible"] else "rejected", {k: bool(x) for k, x in v["checks"].items() if not x})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
