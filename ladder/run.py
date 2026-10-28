"""Run the ladder study over the store (brief: NightKing/HANDOFF_ladder_dynamics.md).

    python3 -m ladder.run                      # every series, resume by default
    python3 -m ladder.run --series KXWTI,KXNATGASD --workers 4
    python3 -m ladder.run --live               # also the events under ladder/data/live_candles
    python3 -m ladder.run --aggregate          # only rebuild the aggregates from the parts

One job per event. Each finished job is checkpointed to results/parts/<series>/<event>.pkl
(atomic write); on restart finished jobs are skipped. results/status.jsonl records every
attempt as ok | failed with the error; an event absent from it was not attempted.
Timestamped log in results/run.log.
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

from . import census, maker, propagation, store

log = logging.getLogger("ladder.run")
HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
LIVE = HERE / "data" / "live_candles"
PROP_THRESHOLDS = (1.0, 2.0, 3.0, 5.0)


def job_path(results, series, event):
    return Path(results) / "parts" / series / ("%s.pkl" % event)


def run_event(args):
    row, results, live_dir = args
    t0 = time.time()
    out = dict(series=row["series"], event=row["event"], kind=row["kind"])
    try:
        if live_dir:
            c = pd.read_parquet(Path(live_dir) / ("event=%s" % row["event"]) / "part.parquet", columns=store.CANDLE_COLS)
        else:
            c = store.load_event_candles(row["series"], row["event"])
        g = store.build_grid(c, row)
        if g is None:
            out.update(status="failed", error="no candles for the ladder's tickers", seconds=time.time() - t0)
            return out
        s, eps = census.census(g)
        s["quoted_first_ts"] = int(g.ts[0]); s["quoted_last_ts"] = int(g.ts[-1])
        s["orient"] = g.orient
        res = dict(summary=s, episodes=eps, prop={}, prop_samples={}, maker=None)
        if g.kind == "cumul":
            for thr in PROP_THRESHOLDS:
                acc, smp = propagation.impulse(g, thr=thr)
                res["prop"][thr] = acc
                if thr == 2.0:
                    res["prop_samples"] = smp
            res["maker"] = maker.maker_stats(g)
        p = job_path(results, row["series"], row["event"])
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        with open(tmp, "wb") as f:
            pickle.dump(res, f, protocol=4)
        os.replace(tmp, p)
        out.update(status="ok", seconds=time.time() - t0, minutes=s["minutes"], episodes=s["episodes"])
    except Exception as e:  # noqa: BLE001
        out.update(status="failed", error="%s: %s" % (type(e).__name__, e), trace=traceback.format_exc(), seconds=time.time() - t0)
    return out


def live_events(live_dir):
    rows = []
    for d in sorted(Path(live_dir).glob("event=*")):
        mk = d / "markets.parquet"
        if not mk.exists():
            continue
        m = pd.read_parquet(mk)
        for c in store.MARKET_COLS:
            if c not in m.columns:
                m[c] = None
        ev = store.events_table(m)
        ev["has_candles"] = (d / "part.parquet").exists()
        rows.append(ev)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def aggregate(results):
    results = Path(results)
    parts = sorted(results.glob("parts/*/*.pkl"))
    summaries, episodes, range_eps, prop, prop_by_series, mk, mk_by_series, samples = [], [], [], {}, {}, {}, {}, []
    for p in parts:
        with open(p, "rb") as f:
            r = pickle.load(f)
        s = r["summary"]
        summaries.append({k: v for k, v in s.items() if not k.startswith("hist_")} | {k: json.dumps(v) for k, v in s.items() if k.startswith("hist_")})
        if len(r["episodes"]):
            (episodes if s["kind"] == "cumul" else range_eps).append(r["episodes"])
        for thr, acc in r["prop"].items():
            propagation.merge(prop.setdefault(thr, {}), acc)
            propagation.merge(prop_by_series.setdefault((s["series"], thr), {}), acc)
        if r["maker"]:
            maker.merge(mk, r["maker"])
            maker.merge(mk_by_series.setdefault(s["series"], {}), r["maker"])
        for smp in r.get("prop_samples", []):
            samples.append((s["series"], s["event"]) + tuple(smp))
    sm = pd.DataFrame(summaries)
    sm.to_parquet(results / "summary.parquet", index=False)
    (pd.concat(episodes, ignore_index=True) if episodes else pd.DataFrame()).to_parquet(results / "episodes.parquet", index=False)
    (pd.concat(range_eps, ignore_index=True) if range_eps else pd.DataFrame()).to_parquet(results / "range_episodes.parquet", index=False)
    with open(results / "propagation.pkl", "wb") as f:
        pickle.dump(dict(all=prop, by_series=prop_by_series), f, protocol=4)
    with open(results / "maker.pkl", "wb") as f:
        pickle.dump(dict(all=mk, by_series=mk_by_series), f, protocol=4)
    pd.DataFrame(samples, columns=["series", "event", "k", "h", "pnl", "init_band", "nb_band"]).to_parquet(results / "prop_samples.parquet", index=False)
    log.info("aggregated %d parts: %d events, %d cumul episodes, %d range episodes", len(parts), len(sm),
             sum(len(e) for e in episodes), sum(len(e) for e in range_eps))
    return sm


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--series", default="ALL")
    ap.add_argument("--workers", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--results", default=str(RESULTS))
    ap.add_argument("--live", action="store_true", help="also run the events under ladder/data/live_candles")
    ap.add_argument("--aggregate", action="store_true", help="only rebuild aggregates from existing parts")
    ap.add_argument("--no-resume", action="store_true", help="recompute finished events")
    a = ap.parse_args(argv)
    results = Path(a.results)
    results.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger(); root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in (logging.StreamHandler(), logging.FileHandler(results / "run.log")):
        h.setFormatter(fmt); root.addHandler(h)
    if a.aggregate:
        aggregate(results)
        return
    series = store.list_series() if a.series == "ALL" else a.series.split(",")
    t0 = time.time()
    ev = store.events_table(store.load_markets(series))
    live_dir = None
    jobs = []
    for _, row in ev.iterrows():
        if row.kind == "other" or not row.has_candles:
            continue
        jobs.append((row.to_dict(), str(results), None))
    if a.live and LIVE.exists():
        lv = live_events(LIVE)
        for _, row in lv.iterrows():
            if row.kind != "other" and row.has_candles:
                jobs.append((row.to_dict(), str(results), str(LIVE)))
    n_other = int((ev.kind == "other").sum()); n_nocand = int((~ev.has_candles & (ev.kind != "other")).sum())
    if not a.no_resume:
        before = len(jobs)
        jobs = [j for j in jobs if not job_path(results, j[0]["series"], j[0]["event"]).exists()]
        log.info("resume: %d of %d events already done", before - len(jobs), before)
    log.info("%d series, %d events (%d 'other' skipped, %d without candles), %d jobs to run, %d workers",
             len(series), len(ev), n_other, n_nocand, len(jobs), a.workers)
    status_f = open(results / "status.jsonl", "a")
    done = failed = 0
    tl = time.time()
    with mp.Pool(a.workers) as pool:
        for out in pool.imap_unordered(run_event, jobs, chunksize=4):
            out["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            status_f.write(json.dumps(out) + "\n"); status_f.flush()
            if out["status"] == "ok":
                done += 1
            else:
                failed += 1
                log.warning("FAILED %s: %s", out["event"], out.get("error"))
            if time.time() - tl > 30:
                log.info("progress: %d ok, %d failed of %d (%.0fs)", done, failed, len(jobs), time.time() - t0)
                tl = time.time()
    status_f.close()
    log.info("finished: %d ok, %d failed of %d in %.0fs", done, failed, len(jobs), time.time() - t0)
    aggregate(results)


if __name__ == "__main__":
    main()
