"""Run the wave census over one or more stores.

    python3 -m waves.run                              # commodity store (../data), resume by default
    python3 -m waves.run --store waves_data --tag new # the expanded store
    python3 -m waves.run --aggregate                  # rebuild aggregates from the parts

Per-event checkpoint results/parts/<tag>/<series>/<event>.pkl (atomic); status.jsonl marks
ok | failed | skipped (too few changes) per attempt; absent = not attempted. Timestamped log.
Aggregates: results/events.parquet (sampled event table with weights), results/summary.parquet.
"""
import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_k, "1")

import argparse
import datetime as dt
import glob
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
from . import census

log = logging.getLogger("waves.run")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = HERE / "results"


def job_path(results, tag, series, event):
    return Path(results) / "parts" / tag / series / ("%s.pkl" % event)


def run_event(args):
    row, root, tag, results, spread_cap, min_changes = args
    t0 = time.time()
    out = dict(series=row["series"], event=row["event"], kind=row["kind"], tag=tag)
    try:
        c = store.load_event_candles(row["series"], row["event"], root=root)
        g = store.build_grid(c, row)
        if g is None:
            out.update(status="failed", error="no candles for the ladder's tickers", seconds=time.time() - t0)
            return out
        s, df = census.census(g, spread_cap=spread_cap, min_changes=min_changes)
        s["close_epoch"] = row.get("close_epoch"); s["category"] = row.get("category"); s["tag"] = tag
        if len(df):
            df["category"] = row.get("category"); df["tag"] = tag
            df["min_to_close"] = ((row.get("close_epoch") or np.nan) - df.ts) / 60.0
        p = job_path(results, tag, row["series"], row["event"])
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        with open(tmp, "wb") as f:
            pickle.dump(dict(summary=s, events=df), f, protocol=4)
        os.replace(tmp, p)
        out.update(status="skipped" if "skipped" in s else "ok", seconds=time.time() - t0, events=int(len(df)), changes=s["changes"])
    except Exception as e:  # noqa: BLE001
        out.update(status="failed", error="%s: %s" % (type(e).__name__, e), trace=traceback.format_exc(), seconds=time.time() - t0)
    return out


def categories(root):
    """series -> category from the store's events table (collect.py writes category per event)."""
    _, mk = store.paths(root)
    evdir = mk.parent / "kalshi_events"
    out = {}
    for f in glob.glob(str(evdir / "series=*" / "part.parquet")):
        try:
            d = pd.read_parquet(f, columns=["series", "category"])
            if len(d):
                out[d.series.iloc[0]] = d.category.dropna().iloc[0] if d.category.notna().any() else None
        except Exception:  # noqa: BLE001
            pass
    return out


def aggregate(results):
    results = Path(results)
    parts = sorted(results.glob("parts/*/*/*.pkl"))
    sums, evs = [], []
    for p in parts:
        with open(p, "rb") as f:
            r = pickle.load(f)
        s = r["summary"]
        s = dict(s, q_pooled=json.dumps(s.get("q_pooled")))
        sums.append(s)
        if len(r["events"]):
            evs.append(r["events"])
    sm = pd.DataFrame(sums)
    sm.to_parquet(results / "summary.parquet", index=False)
    ev = pd.concat(evs, ignore_index=True) if evs else pd.DataFrame()
    ev.to_parquet(results / "events.parquet", index=False)
    log.info("aggregated %d parts: %d ladders, %s sampled events (weighted %s)", len(parts), len(sm), "{:,}".format(len(ev)), "{:,}".format(int(ev.weight.sum())) if len(ev) else 0)
    return sm, ev


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store", default=None, help="store root (default: the commodity store ../data)")
    ap.add_argument("--tag", default="commodity")
    ap.add_argument("--series", default="ALL")
    ap.add_argument("--workers", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--results", default=str(RESULTS))
    ap.add_argument("--spread-cap", type=float, default=10.0)
    ap.add_argument("--min-changes", type=int, default=50)
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--no-resume", action="store_true")
    a = ap.parse_args(argv)
    results = Path(a.results); results.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    root_log = logging.getLogger(); root_log.setLevel(logging.INFO)
    for h in list(root_log.handlers):
        root_log.removeHandler(h)
    for h in (logging.StreamHandler(), logging.FileHandler(results / "run.log")):
        h.setFormatter(fmt); root_log.addHandler(h)
    if a.aggregate:
        aggregate(results); return
    root = str(ROOT / a.store) if a.store and not os.path.isabs(a.store) else a.store
    t0 = time.time()
    series = store.list_series(root) if a.series == "ALL" else a.series.split(",")
    ev = store.events_table(store.load_markets(series, root=root), root=root)
    cats = categories(root)
    jobs = []
    for _, row in ev.iterrows():
        if row.kind == "other" or not row.has_candles:
            continue
        d = row.to_dict(); d["category"] = cats.get(row.series, "Commodities" if root is None else None)
        jobs.append((d, root, a.tag, str(results), a.spread_cap, a.min_changes))
    if not a.no_resume:
        before = len(jobs)
        jobs = [j for j in jobs if not job_path(results, a.tag, j[0]["series"], j[0]["event"]).exists()]
        log.info("resume: %d of %d already done", before - len(jobs), before)
    log.info("store=%s tag=%s: %d series, %d events, %d jobs, %d workers", root or "../data", a.tag, len(series), len(ev), len(jobs), a.workers)
    sf = open(results / "status.jsonl", "a")
    done = failed = skipped = 0; tl = time.time()
    with mp.Pool(a.workers) as pool:
        for out in pool.imap_unordered(run_event, jobs, chunksize=4):
            out["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            sf.write(json.dumps(out) + "\n"); sf.flush()
            if out["status"] == "ok":
                done += 1
            elif out["status"] == "skipped":
                skipped += 1
            else:
                failed += 1; log.warning("FAILED %s: %s", out["event"], out.get("error"))
            if time.time() - tl > 30:
                log.info("progress: %d ok, %d skipped, %d failed of %d (%.0fs)", done, skipped, failed, len(jobs), time.time() - t0); tl = time.time()
    sf.close()
    log.info("finished: %d ok, %d skipped, %d failed of %d in %.0fs", done, skipped, failed, len(jobs), time.time() - t0)
    aggregate(results)


if __name__ == "__main__":
    main()
