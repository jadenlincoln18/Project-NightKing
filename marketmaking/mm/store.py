"""Parquet store for the shadow run.

Rules, all learned the hard way elsewhere in this project:
  * every write is atomic (tmp file + os.replace), because a 14-day run will be
    interrupted and a half-written parquet is a corrupt day;
  * partitioned by UTC date so a day can be read without touching the rest;
  * full depth is stored without truncation (PROTOCOL §6) -- it cannot be
    reconstructed later, which is the whole reason it is captured now;
  * never written to an iCloud path. See STATE.md.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import pathlib
from typing import Dict, List, Optional

import pandas as pd

from . import config, kapi

log = logging.getLogger("mm.store")

TOUCH = "touch"
DEPTH = "depth"
QUOTES = "quotes"
INCENTIVE = "incentive"
PRICE_RANGES = "price_ranges"


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _part_dir(kind: str, ts: dt.datetime) -> pathlib.Path:
    d = config.DATA / kind / ("date=%s" % ts.strftime("%Y-%m-%d"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_atomic(df: pd.DataFrame, kind: str, ts: Optional[dt.datetime] = None,
                 tag: Optional[str] = None) -> Optional[pathlib.Path]:
    """Atomic parquet write. Returns the path, or None for an empty frame."""
    if df is None or df.empty:
        return None
    ts = ts or utcnow()
    tag = tag or ts.strftime("%H%M%S-%f")
    d = _part_dir(kind, ts)
    final = d / ("%s-%s.parquet" % (kind, tag))
    tmp = d / (".%s-%s.tmp" % (kind, tag))
    df.to_parquet(tmp, index=False)
    os.replace(tmp, final)
    return final


def touch_rows(series: str, markets: List[dict], sweep_ts: dt.datetime) -> List[dict]:
    """One row per open market: the touch, both sides, with sizes.

    PROTOCOL §4's proxy is defined on touch quantities -- spread and
    min(bid_size, ask_size) -- so this sweep, at 1-minute resolution, is what
    carries the designated-provider signature. Depth adds queue realism for
    phase 2; it is not what the proxy keys on.
    """
    rows = []
    for m in markets:
        yb = kapi.cents(m.get("yes_bid_dollars"))
        ya = kapi.cents(m.get("yes_ask_dollars"))
        spread = (ya - yb) if (yb is not None and ya is not None) else None
        rows.append(dict(
            ts=sweep_ts,
            series=series,
            ticker=m.get("ticker"),
            event_ticker=m.get("event_ticker"),
            yes_bid=yb,
            yes_ask=ya,
            spread=spread,
            yes_bid_size=float(m.get("yes_bid_size_fp") or m.get("yes_bid_size") or 0),
            yes_ask_size=float(m.get("yes_ask_size_fp") or m.get("yes_ask_size") or 0),
            last_price=kapi.cents(m.get("last_price_dollars")),
            volume=float(m.get("volume") or 0),
            volume_24h=float(m.get("volume_24h") or 0),
            open_interest=float(m.get("open_interest") or 0),
            close_time=m.get("close_time"),
            status=m.get("status"),
        ))
    return rows


def depth_row(ticker: str, series: str, raw: Optional[dict], ts: dt.datetime) -> dict:
    """Full depth, no truncation.

    Both sides are stored twice: raw as Kalshi returns them (YES bids and NO
    bids), and NO converted to YES-denominated offers (a NO bid at p is a YES
    offer at 100-p). Keeping the raw form means a conversion bug here is
    recoverable from the stored data rather than fatal.
    """
    yes, no = kapi.parse_book(raw)
    yes_offers = sorted([(round(100.0 - p, 4), s) for p, s in no], key=lambda t: t[0])
    best_bid = yes[0][0] if yes else None
    best_ask = yes_offers[0][0] if yes_offers else None
    return dict(
        ts=ts,
        series=series,
        ticker=ticker,
        n_yes_levels=len(yes),
        n_no_levels=len(no),
        yes_bid_total=sum(s for _, s in yes),
        no_bid_total=sum(s for _, s in no),
        best_bid=best_bid,
        best_ask=best_ask,
        spread=(best_ask - best_bid) if (best_bid is not None and best_ask is not None) else None,
        yes_levels=json.dumps(yes),            # [[price_cents, size], ...] all levels
        no_levels=json.dumps(no),              # raw NO bids, all levels
        yes_offers=json.dumps(yes_offers),     # NO bids converted to YES offers
        ok=raw is not None,
    )


def price_range_rows(markets: List[dict], series: str, ts: dt.datetime) -> List[dict]:
    """tick_size is gone from the API; price_ranges is the surviving signal.

    PROTOCOL §1 makes this a standing monitor: a tick change silently
    invalidates every cent-denominated threshold in the protocol.
    """
    rows = []
    for m in markets:
        pr = m.get("price_ranges") or m.get("price_range") or None
        tick = kapi.tick_from_price_ranges(pr)
        rows.append(dict(
            ts=ts, series=series, ticker=m.get("ticker"),
            tick_cents=tick,
            price_ranges=json.dumps(pr) if pr is not None else None,
        ))
    return rows


class Buffer:
    """Accumulates rows and flushes atomically on a size or age trigger."""

    def __init__(self, kind: str, max_rows: int = 20000, max_age_s: int = 300):
        self.kind, self.max_rows, self.max_age_s = kind, max_rows, max_age_s
        self.rows: List[dict] = []
        self.opened = utcnow()

    def add(self, rows) -> None:
        if isinstance(rows, dict):
            self.rows.append(rows)
        else:
            self.rows.extend(rows)

    def due(self) -> bool:
        if not self.rows:
            return False
        age = (utcnow() - self.opened).total_seconds()
        return len(self.rows) >= self.max_rows or age >= self.max_age_s

    def flush(self, force: bool = False) -> Optional[pathlib.Path]:
        if not self.rows or (not force and not self.due()):
            return None
        df = pd.DataFrame(self.rows)
        ts = df["ts"].iloc[0] if "ts" in df.columns else utcnow()
        if not isinstance(ts, dt.datetime):
            ts = utcnow()
        p = write_atomic(df, self.kind, ts)
        log.info("flushed %d %s rows -> %s", len(self.rows), self.kind,
                 p.name if p else "(none)")
        self.rows = []
        self.opened = utcnow()
        return p


def read_day(kind: str, date: str) -> pd.DataFrame:
    """Read one UTC date partition. Empty frame if absent."""
    d = config.DATA / kind / ("date=%s" % date)
    if not d.exists():
        return pd.DataFrame()
    parts = sorted(d.glob("%s-*.parquet" % kind))
    if not parts:
        return pd.DataFrame()
    frames = []
    for p in parts:
        try:
            frames.append(pd.read_parquet(p))
        except Exception as e:                      # a corrupt part must not kill a report
            log.warning("unreadable partition %s: %s", p.name, e)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def read_range(kind: str, start: str, end: str) -> pd.DataFrame:
    d0 = dt.date.fromisoformat(start)
    d1 = dt.date.fromisoformat(end)
    frames = []
    cur = d0
    while cur <= d1:
        f = read_day(kind, cur.isoformat())
        if not f.empty:
            frames.append(f)
        cur += dt.timedelta(days=1)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def available_dates(kind: str) -> List[str]:
    d = config.DATA / kind
    if not d.exists():
        return []
    return sorted(p.name.split("=", 1)[1] for p in d.glob("date=*") if "=" in p.name)
