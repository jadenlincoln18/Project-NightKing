#!/usr/bin/env python3
"""
collect.py - the Kalshi historical collector. One-shot, comprehensive, resumable.

Reads <out>/probe.json (write it with probe.py first), then for every selected
series:
  1. events      GET /events?series_ticker=S            -> parquet/kalshi_events
  2. markets     GET /markets?series_ticker=S  (live)
                 GET /historical/markets?series_ticker=S
                 merged field-by-field, settlement fields win  -> parquet/kalshi_markets
  3. candles     per market, live host then historical, chunked to the cap,
                 bid and ask stored separately              -> parquet/kalshi_candles
Raw API responses are gzipped next to every derived table (raw/kalshi/...).

The manifest (<out>/manifest.jsonl) is appended after every event, so a killed
run resumes exactly where it stopped. Resume is the DEFAULT. Re-pulling is
explicit (--repull). Markets whose fetch FAILED (network, 5xx, 4xx other than
404) are retried on resume; markets that genuinely returned nothing are not.

Intraday series (15-minute / hourly ladders, ~95% of all markets and not
hedgeable with a CME option) are EXCLUDED by default. --include-intraday adds
them. The run always prints its request estimate by cadence group and waits
for a "y" unless --yes is given.

Usage
  python3 collect.py --smoke                  # ~20 markets, both hosts, then verify.py
  python3 collect.py                          # full run (asks for confirmation)
  nohup caffeinate -is python3 collect.py --yes --workers 3 > collect.log 2>&1 &
  python3 collect.py --series KXWTIW,KXWTI    # a subset
  python3 collect.py --findings-only          # regenerate FINDINGS.md from the store
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import kalshi_common as kc
from kalshi_common import (Client, CapHolder, Store, log, now_iso, iso_to_epoch, fmt_int)

STOP = threading.Event()
_SIGINTS = [0]


def _on_signal(signum, frame):                     # noqa: ARG001
    _SIGINTS[0] += 1
    if _SIGINTS[0] >= 2:
        log.error("second interrupt - exiting now")
        sys.exit(130)
    log.warning("interrupt received - finishing the current event, then stopping "
                "(press again to abort immediately)")
    STOP.set()


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------

def discover_series(client: Client, probe: Optional[dict]) -> List[dict]:
    if probe and probe.get("series", {}).get("selected"):
        return [dict(s) for s in probe["series"]["selected"]]
    log.warning("no probe.json series list - discovering from /series (cadence unknown)")
    allser: Dict[str, dict] = {}
    for cat in kc.CANDIDATE_CATEGORIES:
        r = client.series(category=cat)
        for s in ((r.json or {}).get("series") or []) if isinstance(r.json, dict) else []:
            if s.get("ticker"):
                s.setdefault("category", cat)
                allser.setdefault(s["ticker"], s)
    sel = kc.select_series(list(allser.values()))
    for s in sel:
        s["group"], s["cadence"] = "unknown", "unknown"
    return sel


def apply_filters(series: List[dict], a: argparse.Namespace) -> Tuple[List[dict], List[dict]]:
    """Returns (kept, excluded_with_reason)."""
    kept, excluded = [], []
    only = {s.strip().upper() for s in (a.series or "").split(",") if s.strip()}
    excl = [p.strip() for p in (a.exclude or "").split(",") if p.strip()]
    cad = {c.strip().lower() for c in (a.cadence or "").split(",") if c.strip()}
    for s in series:
        tk = s["ticker"]
        g = s.get("group") or "unknown"
        if only and tk not in only:
            continue
        if excl and kc.glob_match(tk, excl):
            excluded.append(dict(s, reason="--exclude"))
            continue
        if cad:
            if g not in cad and s.get("cadence") not in cad:
                excluded.append(dict(s, reason="--cadence"))
                continue
        elif g == "intraday" and not a.include_intraday and not only:
            excluded.append(dict(s, reason="intraday (default off; --include-intraday)"))
            continue
        kept.append(s)
    if only:
        known = {s["ticker"] for s in kept}
        for tk in sorted(only - known):
            kept.append({"ticker": tk, "title": None, "category": None, "group": "unknown",
                         "cadence": "unknown", "selected_by": "user"})
    prio = ("WTI", "BRENT", "GOLD", "NATGAS", "SILVER", "COPPER")

    def rank(s: dict) -> Tuple[int, str]:
        tk = s["ticker"].upper()
        for i, p in enumerate(prio):
            if p in tk:
                return (i, tk)
        return (len(prio), tk)
    kept.sort(key=rank)
    return kept, excluded


def print_gate(kept: List[dict], excluded: List[dict], probe: Optional[dict],
               a: argparse.Namespace) -> None:
    est = (probe or {}).get("estimate", {}).get("series", {}) if probe else {}
    cap = (probe or {}).get("candles", {}).get("cap") if probe else None
    print("\n" + "=" * 78)
    print("FULL RUN - estimate (period=%d min, cap=%s, pause=%.2fs, workers=%d)"
          % (a.period, cap or kc.DEFAULT_CANDLE_CAP, a.pause, a.workers))
    print("=" * 78)
    eff_rps = min(a.workers / (a.pause + 0.25), (1.0 / a.pause) if a.pause > 0 else 30.0)
    groups: Dict[str, Dict[str, Any]] = OrderedDict()
    for s in kept:
        e = est.get(s["ticker"], {})
        reqs = int((e.get("requests_by_period") or {}).get(str(a.period), e.get("requests", 0)) or 0)
        g = groups.setdefault(s.get("group") or "unknown", {"n": 0, "markets": 0, "requests": 0})
        g["n"] += 1
        g["markets"] += int(e.get("markets", 0) or 0)
        g["requests"] += reqs
    tot_req = sum(g["requests"] for g in groups.values())
    print("%-10s %7s %10s %10s %8s" % ("group", "series", "markets", "requests", "hours"))
    for gname, g in groups.items():
        print("%-10s %7d %10s %10s %8.1f" % (gname, g["n"], fmt_int(g["markets"]),
                                             fmt_int(g["requests"]), g["requests"] / eff_rps / 3600))
    print("%-10s %7d %10s %10s %8.1f" % ("TOTAL", len(kept),
                                         fmt_int(sum(g["markets"] for g in groups.values())),
                                         fmt_int(tot_req), tot_req / eff_rps / 3600))
    if not est:
        print("(no per-series estimate in probe.json - counts unknown until discovery)")
    print("\nseries in this run (%d):" % len(kept))
    for s in kept:
        e = est.get(s["ticker"], {})
        print("  %-18s %-9s markets=%-8s requests=%-8s %s"
              % (s["ticker"], s.get("group"), fmt_int(e.get("markets", "?")),
                 fmt_int((e.get("requests_by_period") or {}).get(str(a.period), e.get("requests", "?"))),
                 str(s.get("title") or "")[:36]))
    if excluded:
        by = defaultdict(list)
        for s in excluded:
            by[s["reason"]].append(s["ticker"])
        print("\nexcluded:")
        for reason, tks in by.items():
            mk = sum(int(est.get(t, {}).get("markets", 0) or 0) for t in tks)
            print("  %-45s %d series, %s markets: %s" % (reason, len(tks), fmt_int(mk),
                                                         ", ".join(tks[:12]) + (" ..." if len(tks) > 12 else "")))
    print()


def confirm(a: argparse.Namespace) -> bool:
    if a.yes:
        return True
    if not sys.stdin.isatty():
        print("not a TTY and no --yes given - refusing to start the full run (exit 3)")
        return False
    try:
        ans = input("proceed with the full run? [y/N] ").strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


# --------------------------------------------------------------------------
# per-series collection
# --------------------------------------------------------------------------

class Progress:
    def __init__(self, total_markets: int):
        self.t0 = time.monotonic()
        self.total = total_markets
        self.done = 0
        self.fetched = 0
        self.counts = {"ok": 0, "empty": 0, "not_found": 0, "error": 0}
        self.rows = 0
        self.requests = 0

    def add(self, res: kc.CandleResult) -> None:
        self.fetched += 1
        self.counts[res.status] = self.counts.get(res.status, 0) + 1
        self.rows += res.rows
        self.requests += res.requests

    def line(self, series: str, extra: str = "") -> str:
        el = max(1e-6, time.monotonic() - self.t0)
        rps = self.requests / el
        remain = max(0, self.total - self.done)
        per = el / max(1, self.done)
        eta = remain * per
        return ("%s  %s/%s markets  ok=%d empty=%d nf=%d err=%d  rows=%s  %.1f req/s  eta %s%s"
                % (series, fmt_int(self.done), fmt_int(self.total), self.counts["ok"],
                   self.counts["empty"], self.counts["not_found"], self.counts["error"],
                   fmt_int(self.rows), rps, _hms(eta), extra))


def _hms(s: float) -> str:
    s = int(s)
    return "%d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)


def load_markets(client: Client, store: Store, tk: str, markets_source: str
                 ) -> Tuple[List[dict], Dict[str, dict], Dict[str, dict], Dict[str, Any]]:
    """Events + merged markets for a series. Returns
    (events, events_by_ticker, merged_markets_by_ticker, discovery_info)."""
    info: Dict[str, Any] = {"markets_source": markets_source}
    fetched_at = kc.now_iso_precise()
    nested = markets_source == "nested"
    evp = client.events(tk, nested=nested)
    info["events"] = {"n": len(evp.items), "pages": evp.pages, "ended_cleanly": evp.ended_cleanly,
                      "http": evp.last_status, "truncation_warning": evp.truncation_warning}
    if not evp.ended_cleanly:
        log.error("%s: /events paging did NOT end cleanly (HTTP %s) after %d pages - "
                  "discovery may be incomplete", tk, evp.last_status, evp.pages)
    events = evp.items
    store.save_raw(Path("events") / ("%s.json.gz" % tk),
                   {"series": tk, "fetched_at": fetched_at, "nested": nested,
                    "pages": evp.pages, "ended_cleanly": evp.ended_cleanly, "events": events})
    ev_by = {e.get("event_ticker"): e for e in events if e.get("event_ticker")}

    live_markets: List[dict] = []
    if nested:
        for e in events:
            for m in (e.get("markets") or []):
                m.setdefault("event_ticker", e.get("event_ticker"))
                live_markets.append(m)
        info["live"] = {"n": len(live_markets), "pages": evp.pages, "ended_cleanly": evp.ended_cleanly,
                        "http": evp.last_status, "truncation_warning": False}
    else:
        lp = client.markets_live(series=tk)
        live_markets = lp.items
        info["live"] = {"n": len(lp.items), "pages": lp.pages, "ended_cleanly": lp.ended_cleanly,
                        "http": lp.last_status, "truncation_warning": lp.truncation_warning}
        if not lp.ended_cleanly:
            log.error("%s: live /markets paging did NOT end cleanly (HTTP %s)", tk, lp.last_status)
    live_at = kc.now_iso_precise()
    store.save_raw(Path("markets") / ("%s.live.json.gz" % tk),
                   {"series": tk, "fetched_at": live_at, "source": markets_source,
                    "info": info["live"], "markets": live_markets})

    hp = client.markets_hist(tk)
    hist_at = kc.now_iso_precise()
    info["historical"] = {"n": len(hp.items), "pages": hp.pages, "ended_cleanly": hp.ended_cleanly,
                          "http": hp.last_status, "truncation_warning": hp.truncation_warning}
    if not hp.ended_cleanly and hp.last_status not in (404,):
        log.error("%s: /historical/markets paging did NOT end cleanly (HTTP %s)", tk, hp.last_status)
    store.save_raw(Path("markets") / ("%s.hist.json.gz" % tk),
                   {"series": tk, "fetched_at": hist_at, "info": info["historical"],
                    "markets": hp.items})

    live_by = {m["ticker"]: m for m in live_markets if m.get("ticker")}
    hist_by = {m["ticker"]: m for m in hp.items if m.get("ticker")}
    merged: Dict[str, dict] = {}
    meta_by: Dict[str, dict] = {}
    n_conf = 0
    for t in sorted(set(live_by) | set(hist_by)):
        m, meta = kc.merge_market(live_by.get(t), hist_by.get(t), live_at, hist_at)
        if meta["merge_conflicts"]:
            n_conf += 1
            for f in meta["merge_conflicts"]:
                log.warning("merge conflict %s.%s live=%r hist=%r (primary=%s)", t, f,
                            live_by[t].get(f), hist_by[t].get(f), meta["primary_source"])
        m["_meta"] = meta
        m["_seen_nested"] = nested and t in live_by
        merged[t] = m
    info["union"] = len(merged)
    info["only_live"] = len(set(live_by) - set(hist_by))
    info["only_hist"] = len(set(hist_by) - set(live_by))
    info["merge_conflicts"] = n_conf

    # events referenced by markets but absent from the events list -> fetch each once
    missing = sorted({m.get("event_ticker") for m in merged.values()
                      if m.get("event_ticker") and m.get("event_ticker") not in ev_by})
    extra_events = []
    for et in missing:
        r = client.event(et, nested=False)
        ev = (r.json or {}).get("event") if isinstance(r.json, dict) else None
        if isinstance(ev, dict):
            ev_by[et] = ev
            extra_events.append(ev)
        else:
            log.warning("%s: event %s referenced by markets but GET /events/%s -> HTTP %s",
                        tk, et, et, r.status)
    info["events_fetched_individually"] = len(missing)
    if extra_events:
        store.save_raw(Path("events") / ("%s.extra.json.gz" % tk),
                       {"series": tk, "fetched_at": now_iso(), "events": extra_events})
        events = events + extra_events
    return events, ev_by, merged, info


def write_metadata(store: Store, tk: str, events: List[dict], ev_by: Dict[str, dict],
                   merged: Dict[str, dict]) -> Tuple[Any, Any]:
    edf = kc.events_frame(events, tk)
    store.write_table(edf, "kalshi_events", series=tk)
    rows = []
    for t, m in merged.items():
        meta = m.get("_meta") or {}
        clean = {k: v for k, v in m.items() if not k.startswith("_")}
        rows.append(kc.market_row(clean, meta, ev_by.get(m.get("event_ticker")), tk,
                                  seen_nested=bool(m.get("_seen_nested"))))
    mdf = kc.markets_frame(rows)
    store.write_table(mdf, "kalshi_markets", series=tk)
    return edf, mdf


def select_markets(merged: Dict[str, dict], a: argparse.Namespace) -> List[dict]:
    since = iso_to_epoch(a.since + "T00:00:00Z") if a.since else None
    out = []
    for m in merged.values():
        if since is not None:
            ct = iso_to_epoch(m.get("close_time"))
            if ct is None or ct < since:
                continue
        if a.min_volume:
            v = kc.to_float(m.get("volume_fp") if "volume_fp" in m else m.get("volume")) or 0.0
            if v < a.min_volume:
                continue
        out.append(m)
    return out


def smoke_pick(merged: Dict[str, dict]) -> List[dict]:
    """10 newest, 6 oldest settled with volume, 4 oldest overall - both hosts,
    and the 404 path, in one small run."""
    ms = [m for m in merged.values() if iso_to_epoch(m.get("close_time"))]
    ms.sort(key=lambda m: iso_to_epoch(m.get("close_time")) or 0)
    newest = ms[-10:]
    settled = [m for m in ms if str(m.get("status")) in ("settled", "finalized")
               and (kc.to_float(m.get("volume_fp") if "volume_fp" in m else m.get("volume")) or 0) > 0]
    oldest_settled = settled[:6]
    oldest = ms[:4]
    seen, out = set(), []
    for m in oldest + oldest_settled + newest:
        if m["ticker"] not in seen:
            seen.add(m["ticker"])
            out.append(m)
    return out


def pull_candles(client: Client, store: Store, caps: CapHolder, tk: str,
                 markets: List[dict], ev_by: Dict[str, dict], a: argparse.Namespace,
                 prog: Progress) -> Dict[str, int]:
    """Per event: fetch every market that needs fetching, write one parquet,
    one raw gz, then the manifest lines. Order within an event is irrelevant."""
    by_event: "OrderedDict[str, List[dict]]" = OrderedDict()
    for m in markets:
        by_event.setdefault(m.get("event_ticker") or "NOEVENT", []).append(m)
    now = int(time.time())
    stats = {"fetched": 0, "skipped": 0, "events": 0}
    pool = ThreadPoolExecutor(max_workers=max(1, a.workers))
    try:
        for et, ms in by_event.items():
            if STOP.is_set():
                break
            ev = ev_by.get(et) or {}
            labels = [str(m.get("yes_sub_title") or m.get("subtitle") or "") for m in ms]
            kind, _src = kc.ladder_kind(ev.get("mutually_exclusive"), labels)
            todo = []
            for m in ms:
                fetch, why = store.decide(m["ticker"], a.period, retry_errors=not a.no_retry_errors,
                                          retry_not_found=a.retry_not_found, repull=a.repull)
                if fetch:
                    todo.append(m)
                else:
                    stats["skipped"] += 1
                    prog.done += 1
            if not todo:
                continue
            stats["events"] += 1

            def work(m: dict) -> Tuple[dict, Optional[kc.CandleResult], str]:
                t0, t1 = kc.market_lifetime(m, now)
                if t0 is None:
                    return m, None, "no open_time/close_time"
                if t1 is None:
                    return m, None, "close_time <= open_time"
                res = kc.fetch_market_candles(client, tk, m["ticker"], t0, t1, a.period, caps)
                return m, res, ""

            futures = [pool.submit(work, m) for m in todo]
            frames = []
            entries = []
            for fut in as_completed(futures):
                m, res, err = fut.result()
                prog.done += 1
                t0, t1 = kc.market_lifetime(m, now)
                if res is None:
                    entries.append({"ticker": m["ticker"], "period": a.period, "series": tk,
                                    "event": et, "status": "empty", "fetch_ok": True,
                                    "http_live": None, "http_hist": None, "source": "none",
                                    "rows": 0, "t0": t0, "t1": t1, "chunks": 0, "requests": 0,
                                    "cap": caps.cap, "error": err})
                    prog.counts["empty"] += 1
                    continue
                prog.add(res)
                n_market = res.rows                      # before the bodies are freed below
                label = str(m.get("yes_sub_title") or m.get("subtitle") or m["ticker"])
                if res.status == "ok":
                    frames.append(kc.candles_to_frame(res.candles, tk, et, m["ticker"], label,
                                                      kind, a.period, res.source))
                # raw first (exact responses), then free the bodies - a 100-bracket
                # weekly event would otherwise hold ~1M candle dicts in memory
                store.save_raw(Path("candles") / tk / et / ("%s.p%d.json.gz" % (m["ticker"], a.period)),
                               {"ticker": m["ticker"], "series": tk, "event": et, "period": a.period,
                                "status": res.status, "source": res.source, "t0": t0, "t1": t1,
                                "fetched_at": now_iso(), "chunks": res.raw})
                res.candles, res.raw = [], []
                entries.append({"ticker": m["ticker"], "period": a.period, "series": tk,
                                "event": et, "status": res.status, "fetch_ok": res.fetch_ok,
                                "http_live": res.http_live, "http_hist": res.http_hist,
                                "source": res.source, "rows": n_market, "t0": t0, "t1": t1,
                                "chunks": res.chunks, "requests": res.requests, "cap": res.cap,
                                "error": res.error,
                                "attempts": int((store.entries.get(kc.manifest_key(m["ticker"], a.period)) or {}).get("attempts", 0)) + 1})
                if res.status == "error":
                    log.error("%s %s -> %s (live=%s hist=%s) %s", tk, m["ticker"], res.status,
                              res.http_live, res.http_hist, res.error)
            # derived parquet first, then the manifest lines (a crash in between
            # re-fetches the event; the manifest never claims rows not stored)
            n_rows = 0
            if frames:
                import pandas as pd
                df = pd.concat(frames, ignore_index=True)
                n_rows = len(df)
                store.write_event_candles(df, a.period, tk, et)
                del df, frames
            for e in entries:
                store.record(e)
            stats["fetched"] += len(entries)
            log.info(prog.line(tk, "  [%s %d mkts %s rows]" % (et[-14:], len(todo), fmt_int(n_rows))))
    finally:
        pool.shutdown(wait=True)
    return stats


def series_summary_row(store: Store, tk: str, info: Dict[str, Any], period: int) -> Dict[str, Any]:
    c = {"ok": 0, "empty": 0, "not_found": 0, "error": 0, "rows": 0}
    t0s, t1s = [], []
    for e in store.entries.values():
        if e.get("series") != tk or e.get("period") != period:
            continue
        c[e.get("status", "error")] = c.get(e.get("status", "error"), 0) + 1
        c["rows"] += int(e.get("rows") or 0)
        if e.get("status") == "ok":
            t0s.append(e.get("t0") or 0)
            t1s.append(e.get("t1") or 0)
    return {"series": tk, "n_events": (info.get("events") or {}).get("n"),
            "n_markets": info.get("union"), "markets_live": (info.get("live") or {}).get("n"),
            "markets_hist": (info.get("historical") or {}).get("n"),
            "ok": c["ok"], "empty": c["empty"], "not_found": c["not_found"], "error": c["error"],
            "candles": c["rows"],
            "first_candle": kc.epoch_to_iso(min(t0s)) if t0s else None,
            "last_candle": kc.epoch_to_iso(max(t1s)) if t1s else None,
            "discovery_complete": all((info.get(k) or {}).get("ended_cleanly", True)
                                      for k in ("events", "live", "historical")
                                      if (info.get(k) or {}).get("http") not in (404,)),
            "merge_conflicts": info.get("merge_conflicts")}


def write_summary(store: Store, rows: List[Dict[str, Any]]) -> None:
    import pandas as pd
    prev = store.root / "summary.csv"
    old = pd.read_csv(prev) if prev.exists() else None
    df = pd.DataFrame(rows)
    if old is not None and not old.empty and not df.empty:
        old = old[~old["series"].isin(set(df["series"]))]
        df = pd.concat([old, df], ignore_index=True)
    elif old is not None and df.empty:
        df = old
    if not df.empty:
        kc.atomic_write_text(prev, df.to_csv(index=False))


def print_settlement_grouping(store: Store) -> None:
    mk = store.read_all("kalshi_markets")
    if mk is None or mk.empty or "settlement_source_name" not in mk.columns:
        return
    print("\n" + "=" * 78)
    print("SERIES BY SETTLEMENT SOURCE (this decides what is hedgeable)")
    print("=" * 78)
    g = (mk.groupby(["settlement_source_name", "series"], dropna=False)
           .size().reset_index(name="markets"))
    for src, sub in g.groupby("settlement_source_name", dropna=False):
        name = src if isinstance(src, str) else "(none recorded)"
        print("%-40s %s" % (name[:40], ", ".join("%s(%d)" % (r.series, r.markets)
                                                 for r in sub.itertuples())))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data")
    ap.add_argument("--period", type=int, default=1, choices=list(kc.PERIODS))
    ap.add_argument("--series", help="comma-separated series tickers (exact)")
    ap.add_argument("--exclude", help="comma-separated glob patterns, e.g. 'KXAAAGAS*'")
    ap.add_argument("--include-intraday", action="store_true",
                    help="include the 15-minute and hourly series (~180k markets)")
    ap.add_argument("--cadence", help="explicit cadence groups, e.g. daily,weekly")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation gate")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--pause", type=float, default=None,
                    help="seconds between requests (default: probe's recommendation, else 0.10)")
    ap.add_argument("--repull", action="store_true", help="ignore the manifest, fetch everything")
    ap.add_argument("--retry-not-found", action="store_true")
    ap.add_argument("--no-retry-errors", action="store_true")
    ap.add_argument("--min-volume", type=float, default=0.0)
    ap.add_argument("--since", help="only markets closing on/after YYYY-MM-DD")
    ap.add_argument("--smoke", action="store_true",
                    help="~20 markets of one series into <out>_smoke, then verify")
    ap.add_argument("--findings-only", action="store_true")
    ap.add_argument("--no-probe", action="store_true", help="run without probe.json (not advised)")
    ap.add_argument("--markets-source", choices=["auto", "markets", "nested"], default="auto")
    ap.add_argument("--live-base", default=kc.LIVE)
    ap.add_argument("--hist-base", default=kc.HIST)
    ap.add_argument("--log", default=None, help="log file (default <out>/collect.log)")
    ap.add_argument("--retries", type=int, default=3, help="attempts per request on 5xx/network")
    a = ap.parse_args(argv)

    out = Path(a.out)
    if a.smoke and not out.name.endswith("_smoke"):
        out = out.with_name(out.name + "_smoke")
    out.mkdir(parents=True, exist_ok=True)
    kc.setup_logging(a.log or str(out / "collect.log"))
    store = Store(out)

    if a.findings_only:
        import findings
        p = findings.write_findings(store, out / "FINDINGS.md")
        print("wrote %s" % p)
        return 0

    ssl_ctx, env = kc.preflight(a.live_base)

    probe_path = Path(a.out) / "probe.json"
    looked = [probe_path]
    if a.smoke and not probe_path.exists():
        probe_path = out / "probe.json"
        looked.append(probe_path)
    probe: Optional[dict] = None
    if probe_path.exists():
        probe = json.loads(probe_path.read_text())
        log.info("probe.json: %s (written %s, cap=%s, field_style=%s, recommended pause=%s)",
                 probe_path, probe.get("at"), (probe.get("candles") or {}).get("cap"),
                 (probe.get("candles") or {}).get("field_style"),
                 (probe.get("rate") or {}).get("recommended_pause"))
        fs = (probe.get("candles") or {}).get("field_style")
        if fs not in (None, "dollars", "cents"):
            log.error("probe recorded candle field style %r - the parser may store nulls; "
                      "verify.py will catch it, but look at probe.json first", fs)
    elif not a.no_probe:
        print("probe.json not found (looked in %s)\n"
              "run `python3 probe.py --out %s` first, or pass --no-probe"
              % (", ".join(str(p) for p in looked), a.out))
        return 2

    if a.pause is None:
        a.pause = float(((probe or {}).get("rate") or {}).get("recommended_pause") or kc.DEFAULT_PAUSE)
    client = Client(a.live_base, a.hist_base, a.pause, ssl_ctx, retries=a.retries)
    caps = CapHolder(int(((probe or {}).get("candles") or {}).get("cap") or kc.DEFAULT_CANDLE_CAP))
    if a.markets_source == "auto":
        complete = (probe or {}).get("markets_endpoint_complete")
        a.markets_source = "nested" if complete is False else "markets"

    series = discover_series(client, probe)
    kept, excluded = apply_filters(series, a)
    if not kept:
        print("no series selected")
        return 2

    if a.smoke:
        pick = next((s for s in kept if s["ticker"] == "KXWTIW"),
                    next((s for s in kept if "WTI" in s["ticker"].upper()), kept[0]))
        kept = [pick]
        log.info("SMOKE: series %s -> %s", pick["ticker"], out)
    else:
        print_gate(kept, excluded, probe, a)
        if not confirm(a):
            return 3

    signal.signal(signal.SIGINT, _on_signal)
    try:
        signal.signal(signal.SIGTERM, _on_signal)
    except (ValueError, OSError):
        pass

    run = {"at": now_iso(), "period": a.period, "series": [s["ticker"] for s in kept],
           "smoke": a.smoke, "workers": a.workers, "pause": a.pause, "repull": a.repull,
           "markets_source": a.markets_source}
    summary_rows = []
    incomplete = []
    est_series = ((probe or {}).get("estimate") or {}).get("series") or {}
    total_est = sum(int((est_series.get(s["ticker"]) or {}).get("markets", 0) or 0) for s in kept)
    prog = Progress(0 if a.smoke else total_est)
    t_start = time.monotonic()
    for i, s in enumerate(kept, 1):
        if STOP.is_set():
            break
        tk = s["ticker"]
        log.info("[%d/%d] %s  discovery ...", i, len(kept), tk)
        try:
            events, ev_by, merged, info = load_markets(client, store, tk, a.markets_source)
        except Exception as e:                                # noqa: BLE001
            log.exception("%s: discovery failed: %s", tk, e)
            incomplete.append(tk)
            continue
        log.info("%s  events=%d  markets live=%d hist=%d union=%d (only_live=%d only_hist=%d, "
                 "%d merge conflicts)", tk, info["events"]["n"], info["live"]["n"],
                 info["historical"]["n"], info["union"], info["only_live"], info["only_hist"],
                 info["merge_conflicts"])
        write_metadata(store, tk, events, ev_by, merged)
        markets = select_markets(merged, a)
        if a.smoke:
            markets = smoke_pick(merged)
            log.info("SMOKE: %d markets picked: %s", len(markets),
                     ", ".join(m["ticker"] for m in markets))
        if a.smoke or tk not in est_series:
            prog.total += len(markets)           # no probe estimate for this series
        st = pull_candles(client, store, caps, tk, markets, ev_by, a, prog)
        row = series_summary_row(store, tk, info, a.period)
        if not row["discovery_complete"]:
            incomplete.append(tk)
        summary_rows.append(row)
        store.snapshot({"probe": {"at": (probe or {}).get("at"), "cap": caps.cap,
                                  "cap_observed": caps.observed}})
        log.info("%s done: fetched=%d skipped=%d ok=%d empty=%d not_found=%d error=%d candles=%s",
                 tk, st["fetched"], st["skipped"], row["ok"], row["empty"], row["not_found"],
                 row["error"], fmt_int(row["candles"]))

    run["finished_at"] = now_iso()
    run["elapsed_s"] = round(time.monotonic() - t_start, 1)
    run["interrupted"] = STOP.is_set()
    run["requests"] = client.stats.get("requests", 0)
    run["cap_observed"] = caps.observed
    store.snapshot({"run": run})
    store.close()
    write_summary(store, summary_rows)

    counts = store.counts(a.period)
    print("\n" + "=" * 78)
    print("STORED  (period=%d min)" % a.period)
    print("=" * 78)
    for r in summary_rows:
        print("%-18s events=%-6s markets=%-7s ok=%-6d empty=%-5d nf=%-6d err=%-4d candles=%-12s %s"
              % (r["series"], r["n_events"], r["n_markets"], r["ok"], r["empty"], r["not_found"],
                 r["error"], fmt_int(r["candles"]),
                 "" if r["discovery_complete"] else "!! DISCOVERY INCOMPLETE"))
    print("\nmanifest: ok=%d empty=%d not_found=%d error=%d  candles=%s  requests=%s  elapsed=%s"
          % (counts["ok"], counts["empty"], counts["not_found"], counts["error"],
             fmt_int(counts["rows"]), fmt_int(run["requests"]), _hms(run["elapsed_s"])))
    print("parquet: %s   raw: %s   manifest: %s" % (store.pq, store.raw, store.manifest_jsonl))
    print_settlement_grouping(store)

    import findings
    fp = findings.write_findings(store, out / "FINDINGS.md")
    print("\nFINDINGS: %s" % fp)

    rc = 0
    if counts["error"]:
        print("!! %d markets ended in status=error - re-run (resume retries them)" % counts["error"])
        rc = 1
    if incomplete:
        print("!! discovery incomplete for: %s" % ", ".join(incomplete))
        rc = 1
    if STOP.is_set():
        print("interrupted - re-run to resume")
        return 130
    if a.smoke:
        import verify
        print("\nSMOKE: running verify.py on %s" % out)
        vrc = verify.run(out, strict=False)
        return vrc if vrc else rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
