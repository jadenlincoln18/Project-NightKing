"""Cost preflight (free) for a scoped bbo-1m pull on the option legs the backtest would trade.

Scope: for every KXWTIW date that reached the comparison, the options expiring that day (the root the backtest used),
strikes within +/- STRIKE_RANGE dollars of the snapshot forward, for the 60 minutes before each snapshot
(T-1d 13:30-14:30 ET the day before, T-4h 09:30-10:30 ET on the day). Quotes only; nothing is bought here.

    python3 db_preflight_bbo.py            # print the per-window quotes and the total; writes db_preflight_bbo.json
    python3 db_preflight_bbo.py --parent   # also quote the whole parent chain per window, for comparison

HANDOFF_legcount_and_friction.md: cap $50, dry-run by default, report the quote and wait for approval.
"""
import argparse
import json
import os
import pickle
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import db_common as dc  # noqa: E402
import db_pull  # noqa: E402

STRIKE_RANGE = 8.0
ET = "America/New_York"


def windows():
    """(date, snap, root, start_utc, end_utc, F0) for every KXWTIW record that reached the comparison."""
    rs = pickle.load(open(ROOT / "synth" / "results_backtest" / "runs_KXWTIW.pkl", "rb"))
    out = []
    for r in rs:
        if r["outcome"] not in ("cleared", "g4_split_half_fired", "sampler_fail") or not r.get("snap_time_et"):
            continue
        t = pd.Timestamp(r["snap_time_et"]).tz_localize(ET)
        out.append((r["settle_date"], r["snap"], r["root"], (t - pd.Timedelta(minutes=60)).tz_convert("UTC"), t.tz_convert("UTC"), r["F0"]))
    return sorted(out)


def with_backoff(fn, tries: int = 6, base: float = 3.0):
    """Databento's gateway 504s under load; retry with exponential backoff, then give up on that window."""
    import time
    for i in range(tries):
        try:
            return fn()
        except Exception as exc:  # BentoServerError, timeouts
            wait = base * (2 ** i)
            print("  retry %d/%d after %s (%.0fs)" % (i + 1, tries, type(exc).__name__, wait), flush=True)
            time.sleep(wait)
    return float("nan")


def symbols_for(root, settle_date, F0):
    files = sorted((ROOT / "data_cme" / "parquet" / "options_definition" / ("root=%s" % root)).glob("*.parquet"))
    defs = db_pull.parse_definitions(pd.concat([pd.read_parquet(f) for f in files], ignore_index=True), root)
    d = defs[(defs["expiry_date"].astype(str) == settle_date) & ((defs["strike"] - F0).abs() <= STRIKE_RANGE)]
    col = "raw_symbol" if "raw_symbol" in d.columns else "symbol"
    return sorted(set(d[col].astype(str)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="quote only the first N windows (a quick look)")
    a = ap.parse_args(argv)
    dc.setup_logging()
    cli = dc.DBClient(ROOT / "data_cme", max_cost=50.0, execute=False)
    rows = []
    total = 0.0
    total_parent = 0.0
    for i, (date, snap, root, t0, t1, F0) in enumerate(windows()):
        if a.limit and i >= a.limit:
            break
        syms = symbols_for(root, date, F0)
        s, e = t0.strftime("%Y-%m-%dT%H:%M:%S"), t1.strftime("%Y-%m-%dT%H:%M:%S")
        cost = with_backoff(lambda: cli.quote("bbo-1m", syms, "raw_symbol", s, e))
        row = {"date": date, "snap": snap, "root": root, "start": s, "end": e, "n_symbols": len(syms), "cost": cost}
        if a.parent:
            cp = with_backoff(lambda: cli.quote("bbo-1m", [root + ".OPT"], "parent", s, e))
            row["cost_parent"] = cp
            total_parent += cp
        rows.append(row)
        total += cost
        print("%s %s %s: %3d symbols, $%.2f%s" % (date, snap, root, len(syms), cost, ("  (parent $%.2f)" % row["cost_parent"]) if a.parent else ""), flush=True)
    print("TOTAL: %d windows, $%.2f%s" % (len(rows), total, ("; whole parent chain $%.2f" % total_parent) if a.parent else ""))
    json.dump({"windows": rows, "total": total, "total_parent": total_parent if a.parent else None, "strike_range": STRIKE_RANGE},
              open(ROOT / "db_preflight_bbo.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
