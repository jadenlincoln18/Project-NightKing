"""Phase 0.5 driver — PROTOCOL §1B, Test A then (only on pass) Test B.

Usage, from `marketmaking/`:
    ../.venv/bin/python -m phase05.run --band-rule mid_outside_fit_band

`--band-rule` is required and has no default: see `disagree.py` for the
ambiguity in §1B's second bullet that phase 0.5 refuses to resolve by fiat.

The driver stops at the staging gate while the one-minute candle store is not
staged under `marketmaking/data/_import/`. That is the current state of this
run and it is a blocker, not a result: Test A has NOT been run, and no verdict
on the fit may be drawn from its absence.
"""
from __future__ import annotations

import argparse
import json
import sys

from phase05 import disagree, score, stores


def load_observations(root=None):
    """Assemble the tidy (bracket, minute) frame §1B scores.

    Raises StagingGap until the historical minute store is staged. The loader is
    written against `ladder.store`'s existing reader so that staging the tree is
    the only remaining step.
    """
    store_root = stores.check_staging(root)  # raises StagingGap with the full diagnosis
    stores.assert_not_live(store_root)
    stores.add_repo_to_path()
    from ladder import store as lstore  # read-only reuse; ladder/ is never modified

    raise NotImplementedError(
        "Store found at %s. Wire `ladder.store.build_grid` into the tidy frame "
        "(columns: %s) and join settlement from the markets table before scoring."
        % (store_root, ", ".join(disagree.REQUIRED_COLUMNS))
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
    except stores.StagingGap as e:
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
