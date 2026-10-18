#!/usr/bin/env python3
"""Task 2 of NightKing/HANDOFF_actii_and_intraday.md: intraday CL futures for the 30 study dates.

Scope. For every KXWTIW date in the real-chain study (the 30 that clear Gate 0), the CL
contract its weekly option exercises into (`options_definition.underlying`, verified on
100% of dates in FINDINGS_REALCHAIN.md §7) on the three session days the snapshots use:
T-2d and T-1d (14:30 ET snapshots, windows back to 13:30) and settlement day (T-4h at
10:30 ET with its window back to 09:30, and T-0 at 14:30). One request per contract over
the span of its needed days, whole sessions, so nothing has to be re-bought if a snapshot
moves.

Schema. `ohlcv-1m` by default: the level is what the synchronisation needs (one bar per
minute, the close of the 14:29 bar is the level at 14:30), and it is the cheapest. The
dry run also quotes `bbo-1m` and `trades` for the same scope so the choice is visible.

Discipline (same as db_pull.py): every billable call is cost-preflighted with
metadata.get_cost, the quote is logged, the run aborts before buying if the total would
exceed --max-cost ($25). Dry run by default; --execute spends. The manifest
(data_cme/manifest.jsonl) records ok / error per request - a request absent from it was
never attempted, one with status=error is retried, one with status=ok is never bought
again. A raw download whose record count is below Databento's own count is a partial and
is discarded. Resume is the default; --repull ignores the manifest for these requests.

Resilience. Network failures (connection reset, timeout, DNS, 5xx) are retried with
exponential backoff (5 s doubling to 5 min) for up to --max-wait-hours; the log shows every
pause and resume with timestamps. A 4xx (bad request, auth, out of range) is a real error
and is recorded, not retried.

    python3 db_pull_futures.py                    # dry run: plan + quotes for all three schemas
    python3 db_pull_futures.py --execute          # buy ohlcv-1m (or --schema bbo-1m / trades)
    nohup caffeinate -is python3 db_pull_futures.py --execute > data_cme/db_futures.log 2>&1 &
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import db_common as dc  # noqa: E402

log = logging.getLogger("nightking.db")
SCHEMAS = ("ohlcv-1m", "bbo-1m", "trades")
DEFAULT_SCHEMA = "ohlcv-1m"
STORE = (ROOT / "data_cme" / "parquet").resolve().parent   # the real store, even when data_cme/parquet is a symlink
BACKOFF_START, BACKOFF_CAP = 5.0, 300.0


# --------------------------------------------------------------------------
# retry with backoff: network failures pause, client errors fail
# --------------------------------------------------------------------------

def _is_network_error(exc: BaseException) -> bool:
    try:
        from databento.common.error import BentoClientError, BentoServerError
        if isinstance(exc, BentoClientError):
            return False          # 4xx: a real error
        if isinstance(exc, BentoServerError):
            return True           # 5xx: transient
    except ImportError:
        pass
    try:
        import requests
        if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ChunkedEncodingError)):
            return True
    except ImportError:
        pass
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True
    name = type(exc).__name__.lower()
    return any(k in name for k in ("connection", "timeout", "remotedisconnected", "protocolerror", "incompleteread"))


def with_retry(fn: Callable[[], Any], what: str, max_wait_hours: float) -> Any:
    delay = BACKOFF_START
    deadline = time.monotonic() + max_wait_hours * 3600.0
    attempt = 0
    while True:
        try:
            out = fn()
            if attempt:
                log.info("RESUME %s succeeded after %d retries", what, attempt)
            return out
        except BaseException as exc:                                    # noqa: BLE001
            if isinstance(exc, (KeyboardInterrupt, SystemExit)) or not _is_network_error(exc):
                raise
            attempt += 1
            if time.monotonic() > deadline:
                log.error("GIVE UP %s after %.1f h of network failures: %s", what, max_wait_hours, str(exc)[:160])
                raise
            log.warning("PAUSE %s: %s: %s - retry %d in %.0fs", what, type(exc).__name__, str(exc)[:120], attempt, delay)
            time.sleep(delay)
            delay = min(delay * 2.0, BACKOFF_CAP)


# --------------------------------------------------------------------------
# the plan: (contract, start, end) per contract over the days the snapshots need
# --------------------------------------------------------------------------

def plan_requests() -> List[Dict[str, Any]]:
    import pandas as pd
    from synth import realchain
    inp = realchain.load_inputs()
    need: Dict[str, set] = {}
    detail: List[Dict[str, Any]] = []
    for d in inp["dates"]:
        under = inp["underlying"].get((d["root"], d["settle_date"]))
        if not under:
            log.warning("no underlying for %s %s - skipped", d["root"], d["settle_date"])
            continue
        times = realchain.snapshot_times(d["settle_ts"])
        days = sorted({times[s].strftime("%Y-%m-%d") for s in ("T-2d", "T-1d", "T-0")})
        need.setdefault(under, set()).update(days)
        detail.append({"settle_date": d["settle_date"], "root": d["root"], "underlying": under, "days": days,
                       "kalshi_contract": d["cl_contract"], "match": under == d["cl_contract"]})
    reqs = []
    for sym in sorted(need):
        days = sorted(need[sym])
        start = days[0]
        end = (pd.Timestamp(days[-1]) + timedelta(days=1)).strftime("%Y-%m-%d")
        reqs.append({"symbol": sym, "start": start, "end": end, "days_needed": days, "n_days_needed": len(days),
                     "n_calendar_days": (pd.Timestamp(end) - pd.Timestamp(start)).days})
    return reqs, detail


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--execute", action="store_true", help="spend; default is a dry run")
    ap.add_argument("--schema", default=DEFAULT_SCHEMA, choices=SCHEMAS)
    ap.add_argument("--max-cost", type=float, default=dc.DEFAULT_MAX_COST)
    ap.add_argument("--max-wait-hours", type=float, default=12.0, help="keep retrying network failures this long")
    ap.add_argument("--out", default=str(STORE))
    ap.add_argument("--repull", action="store_true", help="ignore manifest entries for these requests")
    ap.add_argument("--logfile", default=None)
    a = ap.parse_args(argv)
    dc.setup_logging(a.logfile or str(Path(a.out) / "db_futures.log"))
    dc.assert_env_gitignored()
    reqs, detail = plan_requests()
    log.info("scope: %d study dates, %d contracts, %d session days; contract = Kalshi contract on %d/%d dates",
             len(detail), len(reqs), sum(r["n_days_needed"] for r in reqs), sum(1 for x in detail if x["match"]), len(detail))
    for r in reqs:
        log.info("  %s  %s..%s  (%d needed days of %d calendar)", r["symbol"], r["start"], r["end"], r["n_days_needed"], r["n_calendar_days"])
    dbc = dc.DBClient(Path(a.out), max_cost=a.max_cost, execute=a.execute)
    if a.repull:
        for r in reqs:
            k = dc.request_key(dc.DATASET, a.schema, [r["symbol"]], "raw_symbol", r["start"], r["end"])
            dbc.manifest.entries.pop(k, None)
    # quotes for every schema, so the choice is visible; only a.schema is bought
    totals: Dict[str, float] = {}
    for schema in SCHEMAS:
        tot = 0.0
        for r in reqs:
            tot += with_retry(lambda: dbc.quote(schema, [r["symbol"]], "raw_symbol", r["start"], r["end"]),
                              "quote %s %s" % (schema, r["symbol"]), a.max_wait_hours)
        totals[schema] = tot
    print("\nquoted for the whole scope:")
    for schema, tot in totals.items():
        print("  %-9s $%8.2f%s" % (schema, tot, "   <- selected" if schema == a.schema else ""))
    if totals[a.schema] > a.max_cost:
        print("\n!! %s would cost $%.2f > --max-cost $%.2f; nothing bought" % (a.schema, totals[a.schema], a.max_cost))
        return 2
    n_ok = 0
    for r in reqs:
        name = "futures_intraday_%s_%s" % (a.schema.replace("-", ""), r["symbol"])
        df = with_retry(lambda: dbc.pull(name, a.schema, [r["symbol"]], "raw_symbol", r["start"], r["end"],
                                         parquet_rel="futures_intraday/schema=%s/symbol=%s/part.parquet" % (a.schema, r["symbol"])),
                        "pull %s" % name, a.max_wait_hours)
        if df is not None:
            n_ok += 1
            log.info("  %s: %s records, %s..%s", r["symbol"], "{:,}".format(len(df)),
                     str(df["ts_event"].min())[:19] if "ts_event" in df else "?", str(df["ts_event"].max())[:19] if "ts_event" in df else "?")
    total = dbc.print_plan("INTRADAY FUTURES PLAN (%s)" % a.schema)
    if a.execute:
        errs = [e for e in dbc.manifest.entries.values() if e.get("status") == "error" and e.get("schema") == a.schema]
        print("  bought/cached %d of %d requests; %d recorded as error (re-run to retry)" % (n_ok, len(reqs), len(errs)))
        return 0 if not errs else 1
    print("  dry run: re-run with --execute to buy %s for $%.2f" % (a.schema, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
