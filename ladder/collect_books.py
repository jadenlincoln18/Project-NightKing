"""Live top-of-book-with-size collector for Kalshi ladders (brief section 4).

The stored candles carry bid/ask but no resting size. The open-markets listing
(`GET /markets?status=open&series_ticker=S`) returns, for every open bracket in
one request per series: yes_bid, yes_ask, yes_bid_size, yes_ask_size, volume,
open interest. One sweep of all ladder series is ~60-160 requests (~10-20 s);
at a 60 s cadence that is the whole cost. No key, no money.

Optionally (`--books`) the full orderbook of each open market in the focus
series is fetched every `--book-every` sweeps (one request per market, ~350
markets -> ~40 s) and summarised as resting contracts within 1c / 3c / 5c of the
touch on each side.

Long-run discipline: never exits on a transient failure (pauses with backoff);
flushes a parquet part every `--flush` sweeps and on SIGTERM/SIGINT; `state.json`
records sweeps done; resume is the default (a restart appends new parts).

    python3 -m ladder.collect_books                       # all series, 60 s
    python3 -m ladder.collect_books --series KXWTI,KXNATGASD --interval 30 --books
    python3 -m ladder.collect_books --hours 6             # stop after 6 h

Output: ladder/data/books/date=YYYY-MM-DD/touch-<utc time>.parquet
        ladder/data/books/date=YYYY-MM-DD/depth-<utc time>.parquet   (with --books)
"""
import argparse
import datetime as dt
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path

import pandas as pd

from . import kapi
from .store import list_series

log = logging.getLogger("ladder.collect")
HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "books"
FOCUS = ["KXWTI", "KXWTIW", "KXNATGASD", "KXGOLDD", "KXSILVERD", "KXBRENTD", "KXCOPPERD",
         "KXAAAGASD", "KXAAAGASDCA", "KXAAAGASW", "KXGOLDW", "KXDIESELD"]
EMPTY_RECHECK = 1800  # s before re-asking a series that had no open markets


def touch_rows(series, markets, sweep_ts):
    rows = []
    for m in markets:
        rows.append(dict(
            sweep_ts=sweep_ts, series=series, event=m.get("event_ticker"), ticker=m.get("ticker"),
            strike_type=m.get("strike_type"), floor_strike=m.get("floor_strike"), cap_strike=m.get("cap_strike"),
            yes_bid=kapi.cents(m.get("yes_bid_dollars")), yes_ask=kapi.cents(m.get("yes_ask_dollars")),
            yes_bid_size=float(m.get("yes_bid_size_fp") or 0), yes_ask_size=float(m.get("yes_ask_size_fp") or 0),
            last_price=kapi.cents(m.get("last_price_dollars")),
            volume=float(m.get("volume_fp") or 0), volume_24h=float(m.get("volume_24h_fp") or 0),
            open_interest=float(m.get("open_interest_fp") or 0),
            close_time=m.get("close_time"), updated_time=m.get("updated_time")))
    return rows


def book_summary(ticker, raw, sweep_ts):
    """Kalshi returns bids only on both sides; YES ask = 100 - NO bid."""
    ob = (raw or {}).get("orderbook_fp") or {}
    yes = [(kapi.cents(p), float(c)) for p, c in (ob.get("yes_dollars") or [])]
    no = [(100.0 - kapi.cents(p), float(c)) for p, c in (ob.get("no_dollars") or [])]
    yes = sorted([x for x in yes if x[0] is not None and x[1] > 0], key=lambda x: -x[0])
    asks = sorted([x for x in no if x[0] is not None and x[1] > 0], key=lambda x: x[0])
    row = dict(sweep_ts=sweep_ts, ticker=ticker,
               bid=yes[0][0] if yes else None, ask=asks[0][0] if asks else None,
               bid_size=yes[0][1] if yes else 0.0, ask_size=asks[0][1] if asks else 0.0,
               n_bid_levels=len(yes), n_ask_levels=len(asks),
               bid_total=sum(c for _, c in yes), ask_total=sum(c for _, c in asks))
    for w in (1, 3, 5):
        row["bid_within_%dc" % w] = sum(c for p, c in yes if p >= yes[0][0] - w) if yes else 0.0
        row["ask_within_%dc" % w] = sum(c for p, c in asks if p <= asks[0][0] + w) if asks else 0.0
    row["levels"] = json.dumps({"yes_bids": yes[:10], "yes_asks": asks[:10]})
    return row


class Collector:
    def __init__(self, series, out, interval, books, book_series, book_every, flush_every):
        self.series, self.out, self.interval = series, Path(out), interval
        self.books, self.book_series, self.book_every, self.flush_every = books, set(book_series), book_every, flush_every
        self.out.mkdir(parents=True, exist_ok=True)
        self.state_path = self.out / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {"sweeps": 0, "rows": 0}
        self.empty_until = {}
        self.touch, self.depth = [], []
        self.stop = False
        signal.signal(signal.SIGTERM, self._sig)
        signal.signal(signal.SIGINT, self._sig)

    def _sig(self, *_):
        log.info("signal received - flushing and stopping")
        self.stop = True

    def flush(self):
        now = dt.datetime.now(dt.timezone.utc)
        d = self.out / ("date=%s" % now.strftime("%Y-%m-%d"))
        d.mkdir(parents=True, exist_ok=True)
        tag = now.strftime("%H%M%S")
        if self.touch:
            df = pd.DataFrame(self.touch)
            tmp = d / (".touch-%s.tmp" % tag)
            df.to_parquet(tmp, index=False)
            os.replace(tmp, d / ("touch-%s.parquet" % tag))
            self.state["rows"] = self.state.get("rows", 0) + len(df)
            log.info("flushed %d touch rows -> %s", len(df), d / ("touch-%s.parquet" % tag))
            self.touch = []
        if self.depth:
            df = pd.DataFrame(self.depth)
            tmp = d / (".depth-%s.tmp" % tag)
            df.to_parquet(tmp, index=False)
            os.replace(tmp, d / ("depth-%s.parquet" % tag))
            log.info("flushed %d depth rows", len(df))
            self.depth = []
        tmp = self.out / ".state.tmp"
        tmp.write_text(json.dumps(self.state))
        os.replace(tmp, self.state_path)

    def sweep(self):
        sweep_ts = int(time.time())
        n_markets = 0
        n_series = 0
        tickers_for_books = []
        for s in self.series:
            if self.stop:
                break
            if self.empty_until.get(s, 0) > sweep_ts:
                continue
            try:
                ms = kapi.paged("/markets", "markets", {"status": "open", "series_ticker": s})
            except kapi.Transient:
                log.warning("series %s: transient failure, skipped this sweep", s)
                continue
            if not ms:
                self.empty_until[s] = sweep_ts + EMPTY_RECHECK
                continue
            n_series += 1
            n_markets += len(ms)
            self.touch.extend(touch_rows(s, ms, sweep_ts))
            if self.books and s in self.book_series:
                tickers_for_books.extend(m["ticker"] for m in ms if m.get("ticker"))
        do_books = self.books and tickers_for_books and (self.state["sweeps"] % self.book_every == 0)
        n_books = 0
        if do_books:
            for tk in tickers_for_books:
                if self.stop:
                    break
                try:
                    raw = kapi.get("/markets/%s/orderbook" % tk, {"depth": 50})
                except kapi.Transient:
                    continue
                if raw is not None:
                    self.depth.append(book_summary(tk, raw, sweep_ts))
                    n_books += 1
        self.state["sweeps"] += 1
        self.state["last_sweep_ts"] = sweep_ts
        log.info("sweep %d: %d open markets in %d series%s (%.0fs)", self.state["sweeps"], n_markets, n_series,
                 (", %d books" % n_books) if do_books else "", time.time() - sweep_ts)

    def run(self, hours):
        t_end = time.time() + hours * 3600 if hours > 0 else float("inf")
        log.info("collector start: %d series, interval %ds, books=%s, out=%s, resumed at sweep %d",
                 len(self.series), self.interval, self.books, self.out, self.state["sweeps"])
        while not self.stop and time.time() < t_end:
            t0 = time.time()
            try:
                self.sweep()
            except Exception as e:  # noqa: BLE001 - never exit on a bad sweep
                log.exception("sweep failed: %s - pausing 60s", e)
                time.sleep(60)
            if self.state["sweeps"] % self.flush_every == 0:
                self.flush()
            wait = self.interval - (time.time() - t0)
            while wait > 0 and not self.stop:
                time.sleep(min(wait, 1.0))
                wait -= 1.0
        self.flush()
        log.info("collector stopped at sweep %d", self.state["sweeps"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--series", default="ALL", help="comma list or ALL (every series in the store)")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--hours", type=float, default=0, help="0 = run until stopped")
    ap.add_argument("--books", action="store_true", help="also fetch full orderbooks for the focus series")
    ap.add_argument("--book-series", default=",".join(FOCUS))
    ap.add_argument("--book-every", type=int, default=5, help="orderbook sweep every N touch sweeps")
    ap.add_argument("--flush", type=int, default=5)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    series = list_series() if a.series == "ALL" else [s for s in a.series.split(",") if s]
    Path(a.out).mkdir(parents=True, exist_ok=True)
    kapi.setup_logging(str(Path(a.out) / "collect.log"))
    Collector(series, a.out, a.interval, a.books, a.book_series.split(","), a.book_every, a.flush).run(a.hours)


if __name__ == "__main__":
    main()
