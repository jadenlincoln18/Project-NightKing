"""Scoped bbo-1m pull for the option legs the backtest prices (Task B, option 1 of
NightKing/HANDOFF_legcount_and_friction.md).

One request per (date, snapshot) window: the options expiring on the Kalshi settlement date (the root the backtest
used), strikes within +/- STRIKE_RANGE of the snapshot forward, the 60 minutes before the snapshot. Dry run by default:
quotes every window, prints the plan and the total, buys nothing. --execute buys, under the cap, with the manifest and
resume discipline of db_common.DBClient (a window already on disk is never bought again).

    python3 db_pull_bbo.py               # dry run: plan + total
    python3 db_pull_bbo.py --execute     # after approval; cap $50

Output: data_cme/parquet/options_bbo_1m/date=<settle_date>/snap=<snap>/part.parquet with strike and right parsed from
the raw symbol, read by synth/friction_measure.py.
"""
import argparse
import os
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import db_common as dc  # noqa: E402
from db_preflight_bbo import windows, symbols_for, with_backoff  # noqa: E402

CAP = 50.0
OUT_REL = "options_bbo_1m"


def parse_symbol(sym: str):
    """'LO2F6 C5125' -> (strike 51.25, right 'C'); CL option strikes are in cents/100 of a dollar? No: the raw symbol
    carries the strike in 1/100 dollars with a trailing digit convention handled by db_common.parse_option_symbol."""
    p = dc.parse_option_symbol(sym)
    if not p:
        return None, None
    return p.get("strike"), p.get("right")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--scoped", action="store_true", help="strikes within $8 of the forward only (default: the whole parent chain, as approved)")
    a = ap.parse_args(argv)
    dc.setup_logging(str(ROOT / "data_cme" / "db.log"))
    cli = dc.DBClient(ROOT / "data_cme", max_cost=CAP, execute=a.execute)
    ws = windows()
    if a.limit:
        ws = ws[:a.limit]
    total = 0.0
    done = 0
    for date, snap, root, t0, t1, F0 in ws:
        syms, stype = (symbols_for(root, date, F0), "raw_symbol") if a.scoped else ([root + ".OPT"], "parent")
        s, e = t0.strftime("%Y-%m-%dT%H:%M:%S"), t1.strftime("%Y-%m-%dT%H:%M:%S")
        rel = "%s/date=%s/snap=%s/part.parquet" % (OUT_REL, date, snap)
        if (ROOT / "data_cme" / "parquet" / rel).exists():
            done += 1
            continue
        cost = with_backoff(lambda: cli.quote("bbo-1m", syms, stype, s, e))
        total += cost if cost == cost else 0.0
        if a.execute:
            df = with_backoff(lambda: cli.pull("bbo1m_%s_%s" % (date, snap), "bbo-1m", syms, stype, s, e, parquet_rel=rel))
            if df is None or (isinstance(df, float)):
                print("  %s %s: pull failed or dry" % (date, snap), flush=True)
                continue
            # attach strike/right from the symbol column if the parquet writer did not
            p = ROOT / "data_cme" / "parquet" / rel
            d = pd.read_parquet(p)
            if "strike" not in d.columns and "symbol" in d.columns:
                pr = d["symbol"].map(lambda x: dc.parse_option_symbol(str(x)) or {})
                d["strike"] = pr.map(lambda t: t.get("strike"))
                d["right"] = pr.map(lambda t: t.get("right"))
                d["contract"] = pr.map(lambda t: t.get("contract"))
                d.to_parquet(p, index=False, compression="snappy")
            done += 1
        print("%s %s %s: %3d symbols $%.2f%s" % (date, snap, root, len(syms), cost, "" if a.execute else "  (dry)"), flush=True)
    print("TOTAL quoted this run: $%.2f over %d windows; on disk: %d" % (total, len(ws), done))
    if a.execute:
        cli.print_plan("BOUGHT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
