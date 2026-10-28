"""Price (never buy) the futures pulls the underlying-lag study might want, with Databento's
metadata.get_cost via the previous study's DBClient (execute=False). Writes waves/results_underlying/preflight.json.

    python3 -m waves.preflight_futures
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "wti_arb"))
import db_common as dc  # noqa: E402

OUT = ROOT / "waves" / "results_underlying" / "preflight.json"


def q(cli, schema, syms, stype, s, e, tries=5):
    for i in range(tries):
        try:
            return float(cli.quote(schema, syms, stype, s, e))
        except Exception as exc:  # noqa: BLE001
            print("  retry %d after %s" % (i + 1, type(exc).__name__), flush=True); time.sleep(3 * 2 ** i)
    return float("nan")


def main():
    dc.setup_logging()
    cli = dc.DBClient(ROOT / "data_cme", max_cost=0.0, execute=False)
    rows = []
    # (a) extend the CL minute coverage from the end of the current pull to today, front two contracts
    for schema in ("ohlcv-1m", "bbo-1m"):
        c = q(cli, schema, ["CLX6", "CLZ6"], "raw_symbol", "2026-09-05T00:00:00", "2026-10-27T00:00:00")
        rows.append(dict(what="CL minute coverage extension 2026-09-05..10-27, CLX6+CLZ6", schema=schema, cost=c))
    # (b) tick-level CL for the matched span: trades and top-of-book, one contract-month at a time
    for schema in ("trades", "mbp-1", "tbbo"):
        c = q(cli, schema, ["CLQ6"], "raw_symbol", "2026-06-24T00:00:00", "2026-07-10T21:00:00")
        rows.append(dict(what="CL tick-level, one contract window (CLQ6, 2026-06-24..07-10, 15 days)", schema=schema, cost=c))
    for schema in ("trades", "mbp-1"):
        c = q(cli, schema, ["CLQ6"], "raw_symbol", "2026-07-01T13:00:00", "2026-07-01T21:00:00")
        rows.append(dict(what="CL tick-level, one US session (CLQ6, 2026-07-01 13:00-21:00 UTC)", schema=schema, cost=c))
    # (c) Pyth-settled commodities: COMEX/NYMEX minute bars for the ladder span
    for root, syms in (("GC", ["GCM6", "GCQ6", "GCZ6"]), ("SI", ["SIK6", "SIN6", "SIU6"]), ("NG", ["NGK6", "NGM6", "NGN6", "NGQ6", "NGU6"]), ("HG", ["HGK6", "HGN6", "HGU6"])):
        c = q(cli, "ohlcv-1m", syms, "raw_symbol", "2026-03-01T00:00:00", "2026-09-10T00:00:00")
        rows.append(dict(what="%s minute bars 2026-03-01..09-10 (%s)" % (root, ",".join(syms)), schema="ohlcv-1m", cost=c))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    for r in rows:
        print("$%8.2f  %-9s %s" % (r["cost"], r["schema"], r["what"]))


if __name__ == "__main__":
    main()
