"""Phase 0.5 driver — PROTOCOL §1B, Test A then (only on pass) Test B.

Usage, from `marketmaking/`:
    ../.venv/bin/python -m phase05.run --band-rule mid_outside_fit_band

`--band-rule` is required and has no default: see `disagree.py` for the
ambiguity in §1B's second bullet that phase 0.5 refuses to resolve by fiat.

**Current state (2026-10-20).** The staging gate now PASSES: the one-minute
candle store is staged and `panel.py` builds seven of the ten columns §1B's
unit needs. The driver now stops one step later, on `FitGap`: `fit_mean`,
`fit_lo` and `fit_hi` cannot be produced for the §1A universe by anything in
this repository. That is a blocker, not a result — Test A has NOT been run, and
no verdict on the fit may be drawn from its absence. See `FINDINGS_PHASE05.md`
§2 for why all three ways of producing them are closed by §1B's own text.
"""
from __future__ import annotations

import argparse
import json
import sys

from phase05 import disagree, panel, score, stores


class FitGap(RuntimeError):
    """§1B's fair value + credible band has no implementation for the §1A universe."""


def load_observations(root=None):
    """Assemble the tidy (bracket, minute) frame §1B scores.

    Raises StagingGap if the historical minute store is not staged, then FitGap
    because the three fit columns cannot be produced for the §1A universe.
    """
    store_root = stores.check_staging(root)  # raises StagingGap with the full diagnosis
    stores.assert_not_live(store_root)

    have = set(panel.PANEL_COLUMNS)
    missing = [c for c in disagree.REQUIRED_COLUMNS if c not in have and c != "fit_asof"]

    raise FitGap(
        "PHASE 0.5 CANNOT RUN: the fit §1B scores has no implementation here.\n\n"
        "Store staged and readable at %s.\n"
        "`panel.py` supplies: %s\n"
        "§1B additionally requires: %s (+ fit_asof)\n\n"
        "Neither fair-value producer in this repo can supply them on the §1A\n"
        "universe of daily city-temperature ladders:\n"
        "  * wti_arb/synth/act3.py HAS a credible band, but its likelihood is a\n"
        "    vanilla call/put payoff matrix on a log-moneyness grid around a\n"
        "    forward F0. Temperature has no chain, no forward, no implied vol,\n"
        "    and log(s/F0) is undefined on a support that reaches zero.\n"
        "    Giving it a digital likelihood = altering the density extractor,\n"
        "    which §1B forbids.\n"
        "  * ladder/maker.py READS the ladder, but its PAVA fair value is a\n"
        "    point estimate with no interval. Giving it a band = inventing one,\n"
        "    which §1B forbids.\n"
        "  * Running on the commodity series instead = changing the universe\n"
        "    fixed in §1A, which §1B forbids (and wti_arb/data_cme/parquet/ is\n"
        "    absent from this clone anyway).\n\n"
        "This needs a protocol ruling, not a code change. PROTOCOL.md §1B is\n"
        "left exactly as committed at 132ce8c. See FINDINGS_PHASE05.md §2."
        % (store_root, ", ".join(sorted(have)), ", ".join(missing))
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PROTOCOL §1B phase 0.5")
    ap.add_argument("--band-rule", required=True,
                    choices=[r.value for r in disagree.BandRule],
                    help="required; §1B's band sentence has two readings (see disagree.py)")
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--root", default=None)
    args = ap.parse_args(argv)

    try:
        df = load_observations(args.root)
    except (stores.StagingGap, FitGap) as e:
        print(str(e), file=sys.stderr)
        print("\nVERDICT: BLOCKED — Test A not run. See FINDINGS_PHASE05.md.", file=sys.stderr)
        return 2

    obs, cuts = disagree.build_disagreement_set(df, args.band_rule)
    print(json.dumps(cuts, indent=2))

    if cuts["events_disagreement"] < 40:
        print("WARNING: %d events. §1B reporting bar: a result on 40 events is not a result."
              % cuts["events_disagreement"], file=sys.stderr)

    a = score.test_a_verdict(obs["fit_mean"].values, obs["mid_prob"].values,
                             obs["settled_yes"].values, obs["event_id"].values,
                             n_boot=args.n_boot, seed=args.seed)
    print(json.dumps(a, indent=2, default=str))

    if not a["passed"]:
        print("\nTest A FAILED. §1B: stop. Test B is not run and the disagreement set "
              "is not re-cut looking for a subset that passes.", file=sys.stderr)
        return 1

    print("\nTest A passed; Test B may proceed per §1B.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
