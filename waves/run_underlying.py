"""Run the underlying-lag analysis over the WTI ladders (commodity + expanded stores) and the
hourly ETH ladders (expanded store), with per-ladder checkpoints and resume.

    python3 -m waves.run_underlying                 # WTI series, both stores
    python3 -m waves.run_underlying --eth           # KXETH (needs waves_data/crypto/ETH-USD_1m.parquet)
    python3 -m waves.run_underlying --aggregate
"""
import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_k, "1")
import argparse
import datetime as dt
import json
import logging
import multiprocessing as mp
import pickle
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from ladder import store
from . import underlying as U

log = logging.getLogger("waves.run_underlying")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = HERE / "results_underlying"
EVENTS = HERE / "results" / "events.parquet"


def job_path(results, tag, series, event):
    return Path(results) / "parts" / tag / series / ("%s.pkl" % event)


_EV = {}


def _events_for(tag, series, event):
    key = (tag, series)
    if key not in _EV:
        ev = pd.read_parquet(EVENTS, filters=[("tag", "==", tag), ("series", "==", series)])
        _EV[key] = ev
    ev = _EV[key]
    return ev[ev.event == event]


def run_event(args):
    row, root, tag, results = args
    t0 = time.time()
    out = dict(series=row["series"], event=row["event"], tag=tag)
    try:
        c = store.load_event_candles(row["series"], row["event"], root=root)
        g = store.build_grid(c, row)
        mk = store.load_markets([row["series"]], root=root)
        mk = mk if "rules_primary" in mk else mk
        full = pd.read_parquet(store.paths(root)[1] / ("series=%s" % row["series"]) / "part.parquet")
        mrows = full[full.event_ticker == row["event"]]
        u, contract, src = U.underlying_for(g, mrows)
        if u is None:
            out.update(status="no_coverage", contract=contract, source=src, seconds=time.time() - t0)
            p = job_path(results, tag, row["series"], row["event"]); p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "wb") as f:
                pickle.dump(dict(summary=dict(series=row["series"], event=row["event"], kind=g.kind, contract=contract, source=src, covered=False, tag=tag, close_epoch=row.get("close_epoch")), events=pd.DataFrame()), f)
            return out
        ev = _events_for(tag, row["series"], row["event"])
        s, df = U.analyse(g, u, ev)
        s.update(contract=contract, source=src, covered=True, tag=tag, close_epoch=row.get("close_epoch"), n_events_in=int(len(ev)))
        p = job_path(results, tag, row["series"], row["event"]); p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        with open(tmp, "wb") as f:
            pickle.dump(dict(summary=s, events=df), f, protocol=4)
        os.replace(tmp, p)
        out.update(status="ok", contract=contract, source=src, seconds=time.time() - t0, events=int(len(df)))
    except Exception as e:  # noqa: BLE001
        out.update(status="failed", error="%s: %s" % (type(e).__name__, e), trace=traceback.format_exc(), seconds=time.time() - t0)
    return out


def aggregate(results):
    results = Path(results)
    parts = sorted(results.glob("parts/*/*/*.pkl"))
    sums, evs = [], []
    for p in parts:
        with open(p, "rb") as f:
            r = pickle.load(f)
        s = dict(r["summary"])
        for k in list(s):
            if k.startswith("xc_"):
                s[k] = json.dumps({str(L): v.tolist() for L, v in s[k].items()})
        sums.append(s)
        if len(r["events"]):
            evs.append(r["events"])
    sm = pd.DataFrame(sums); sm.to_parquet(results / "summary.parquet", index=False)
    ev = pd.concat(evs, ignore_index=True) if evs else pd.DataFrame(); ev.to_parquet(results / "events.parquet", index=False)
    log.info("aggregated %d parts: %d covered ladders, %s events", len(parts), int(sm.covered.sum()) if len(sm) else 0, "{:,}".format(len(ev)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--eth", action="store_true")
    ap.add_argument("--workers", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--results", default=str(RESULTS))
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--no-resume", action="store_true")
    a = ap.parse_args(argv)
    results = Path(a.results); results.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    rl = logging.getLogger(); rl.setLevel(logging.INFO)
    for h in list(rl.handlers):
        rl.removeHandler(h)
    for h in (logging.StreamHandler(), logging.FileHandler(results / "run.log")):
        h.setFormatter(fmt); rl.addHandler(h)
    if a.aggregate:
        aggregate(results); return
    jobs = []
    if a.eth:
        plan = [(str(ROOT / "waves_data"), "expanded", list(U.ETH_SERIES))]
    else:
        plan = [(None, "commodity", list(U.WTI_SERIES)), (str(ROOT / "waves_data"), "expanded", list(U.WTI_SERIES))]
    for root, tag, series in plan:
        series = [s for s in series if s in store.list_series(root)]
        ev = store.events_table(store.load_markets(series, root=root), root=root)
        for _, row in ev.iterrows():
            if row.kind == "other" or not row.has_candles:
                continue
            jobs.append((row.to_dict(), root, tag, str(results)))
    # dedupe: an event in both stores -> expanded only
    seen = {j[0]["event"] for j in jobs if j[2] == "expanded"}
    jobs = [j for j in jobs if not (j[2] == "commodity" and j[0]["event"] in seen)]
    if not a.no_resume:
        before = len(jobs); jobs = [j for j in jobs if not job_path(results, j[2], j[0]["series"], j[0]["event"]).exists()]
        log.info("resume: %d of %d already done", before - len(jobs), before)
    log.info("%d jobs, %d workers", len(jobs), a.workers)
    sf = open(results / "status.jsonl", "a"); t0 = time.time(); c = {"ok": 0, "no_coverage": 0, "failed": 0}; tl = time.time()
    with mp.Pool(a.workers) as pool:
        for out in pool.imap_unordered(run_event, jobs, chunksize=2):
            out["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            sf.write(json.dumps(out) + "\n"); sf.flush(); c[out["status"]] += 1
            if out["status"] == "failed":
                log.warning("FAILED %s: %s", out["event"], out.get("error"))
            if time.time() - tl > 30:
                log.info("progress: %s of %d (%.0fs)", c, len(jobs), time.time() - t0); tl = time.time()
    sf.close(); log.info("finished: %s in %.0fs", c, time.time() - t0)
    aggregate(results)


if __name__ == "__main__":
    main()
