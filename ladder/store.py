"""Read the Kalshi store, classify ladders, rebuild the minute grid.

The store is candle-based and SPARSE: a 1-minute candle exists only for minutes
in which the top of book changed (verified on the full store: the open of a
candle equals the close of the previous candle of the same bracket in 99.95% of
58.9M candles, so a missing minute means "the book did not move", not "the book
was not there"). Between candles the last close is carried forward.

Empty sides are encoded by the API as bid=0 / ask=100; both become NaN here and
the "no quote" state is carried forward like any other state.

Ladders are classified from the markets table, per event:
  cumul  - every bracket is a threshold (strike_type greater/greater_or_equal,
           or less/less_or_equal). Ordered by strike. 'less' ladders are flipped
           into 'greater' form (P(>X) = 1 - P(<X), bid/ask swapped) so that the
           monotone constraint is always "non-increasing in the strike".
  range  - at least one 'between' bracket; ordered lower tail, brackets by
           floor, upper tail. Not flipped.
  other  - custom/mixed/fewer than 2 brackets; skipped and counted.
"""
import glob
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "parquet"
CANDLES = DATA / "kalshi_candles" / "period=1"
MARKETS = DATA / "kalshi_markets"

MARKET_COLS = ["ticker", "event_ticker", "series", "strike_type", "floor_strike", "cap_strike",
               "yes_sub_title", "volume_fp", "open_interest_fp", "status", "result",
               "open_time_epoch", "close_time_epoch", "expiration_time_epoch", "expiration_value_num"]
CANDLE_COLS = ["ts", "ticker", "volume", "open_interest",
               "yes_bid_open", "yes_bid_high", "yes_bid_low", "yes_bid_close",
               "yes_ask_open", "yes_ask_high", "yes_ask_low", "yes_ask_close"]

GREATER = ("greater", "greater_or_equal")
LESS = ("less", "less_or_equal")


def paths(root=None):
    """(candles_dir, markets_dir) for a store root; default is the commodity store at ../data."""
    if root is None:
        return CANDLES, MARKETS
    r = Path(root) / "parquet"
    return r / "kalshi_candles" / "period=1", r / "kalshi_markets"


def list_series(root=None):
    _, mk = paths(root)
    return sorted(p.split("series=")[1] for p in glob.glob(str(mk / "series=*")))


def load_markets(series=None, root=None):
    _, mk = paths(root)
    series = list_series(root) if series is None else list(series)
    parts = []
    for s in series:
        f = mk / ("series=%s" % s) / "part.parquet"
        if f.exists():
            parts.append(pd.read_parquet(f, columns=MARKET_COLS))
    if not parts:
        return pd.DataFrame(columns=MARKET_COLS)
    return pd.concat(parts, ignore_index=True)


_NUM = r"\$?\s*([0-9][0-9,]*\.?[0-9]*)"
_RANGE_RE = re.compile(_NUM + r"\s*to\s*" + _NUM, re.I)
_ABOVE_RE = re.compile(r"(?:^above\s*" + _NUM + r")|(?:" + _NUM + r"\s*or\s*(?:above|higher))", re.I)
_BELOW_RE = re.compile(r"(?:^below\s*" + _NUM + r")|(?:" + _NUM + r"\s*or\s*(?:below|lower))", re.I)


def _num(x):
    return float(x.replace(",", "")) if x else None


def fill_strike_from_title(g):
    """Markets from 2022-24 (WTI-22DEC01-B77.5, GOLD-22OCT0316-T1625, ...) carry no
    strike_type/floor/cap; their yes_sub_title does ('$77 to 77.99', '1624.99 or below',
    'Above 3.478'). Fill the three columns from the title where they are missing."""
    if g.strike_type.notna().all():
        return g
    g = g.copy()
    for idx, row in g[g.strike_type.isna()].iterrows():
        t = str(row.yes_sub_title or "").strip()
        m = _RANGE_RE.search(t)
        if m:
            g.loc[idx, ["strike_type", "floor_strike", "cap_strike"]] = ["between", _num(m.group(1)), _num(m.group(2))]
            continue
        m = _ABOVE_RE.search(t)
        if m:
            g.loc[idx, ["strike_type", "floor_strike"]] = ["greater", _num(m.group(1) or m.group(2))]
            continue
        m = _BELOW_RE.search(t)
        if m:
            g.loc[idx, ["strike_type", "cap_strike"]] = ["less", _num(m.group(1) or m.group(2))]
    return g


def classify_event(g):
    """g: markets of one event. Returns (kind, orient, ordered DataFrame)."""
    g = fill_strike_from_title(g)
    st = set(g.strike_type.dropna())
    n = len(g)
    if n < 2:
        return "other", None, g
    if "between" in st:
        lo = g[g.strike_type.isin(LESS)].copy()
        mid = g[g.strike_type == "between"].sort_values("floor_strike")
        hi = g[g.strike_type.isin(GREATER)].copy()
        if (st - {"between"} - set(LESS) - set(GREATER)) or len(lo) > 1 or len(hi) > 1:
            return "other", None, g
        lo["_key"] = lo.cap_strike - 1e-6
        mid = mid.assign(_key=mid.floor_strike)
        hi["_key"] = hi.floor_strike + 1e-6
        out = pd.concat([lo, mid, hi]).sort_values("_key")
        if out.floor_strike.isna().sum() > 1 or out._key.duplicated().any():
            return "other", None, g
        return "range", None, out.drop(columns="_key")
    if st and st <= set(GREATER):
        out = g.dropna(subset=["floor_strike"]).sort_values("floor_strike")
        if len(out) < 2 or out.floor_strike.duplicated().any():
            return "other", None, g
        return "cumul", "greater", out
    if st and st <= set(LESS):
        out = g.dropna(subset=["cap_strike"]).sort_values("cap_strike")
        if len(out) < 2 or out.cap_strike.duplicated().any():
            return "other", None, g
        return "cumul", "less", out
    return "other", None, g


def events_table(markets, root=None):
    cd, _ = paths(root)
    rows = []
    for (s, ev), g in markets.groupby(["series", "event_ticker"], sort=True):
        kind, orient, ordered = classify_event(g)
        strikes = (ordered.cap_strike if orient == "less" else ordered.floor_strike).tolist() if kind != "other" else []
        if kind == "range":
            strikes = [ordered.iloc[0].cap_strike] + ordered.iloc[1:].floor_strike.tolist()
        rows.append(dict(series=s, event=ev, kind=kind, orient=orient, n=len(g),
                         tickers=ordered.ticker.tolist() if kind != "other" else [],
                         strikes=[float(x) for x in strikes],
                         open_epoch=int(g.open_time_epoch.min()) if g.open_time_epoch.notna().any() else None,
                         close_epoch=int(g.close_time_epoch.max()) if g.close_time_epoch.notna().any() else None,
                         volume=float(g.volume_fp.fillna(0).sum()),
                         has_candles=(cd / ("series=%s" % s) / ("event=%s" % ev) / "part.parquet").exists()))
    return pd.DataFrame(rows)


def load_event_candles(series, event, root=None):
    cd, _ = paths(root)
    f = cd / ("series=%s" % series) / ("event=%s" % event) / "part.parquet"
    if not f.exists():
        return None
    return pd.read_parquet(f, columns=CANDLE_COLS)


class Grid:
    """Minute grid for one ladder. Arrays are (n_min, n_br) float32, NaN = no quote.
    bid/ask: carried-forward closes. bid_hi/ask_lo: intra-minute extremes, only on
    minutes with a candle. vol: contracts traded in the minute (0 elsewhere).
    oi: open interest carried forward. has: a candle exists this minute."""
    __slots__ = ("series", "event", "kind", "orient", "tickers", "strikes", "ts",
                 "bid", "ask", "bid_hi", "ask_lo", "vol", "oi", "has", "n_candles")

    @property
    def mid(self):
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self):
        return self.ask - self.bid

    @property
    def shape(self):
        return self.bid.shape


EMPTY = -1.0  # sentinel for "no quote" that survives the forward fill


def _ffill(a):
    """Forward-fill NaN along axis 0."""
    n, m = a.shape
    idx = np.where(~np.isnan(a), np.arange(n)[:, None], 0)
    np.maximum.accumulate(idx, axis=0, out=idx)
    out = a[idx, np.arange(m)[None, :]]
    out[np.isnan(a[0]) & (idx == 0)] = np.nan
    first_valid = np.argmax(~np.isnan(a), axis=0)
    never = ~np.any(~np.isnan(a), axis=0)
    rows = np.arange(n)[:, None]
    out[rows < first_valid[None, :]] = np.nan
    out[:, never] = np.nan
    return out


def build_grid(candles, info, ffill_to_close=True):
    """info: a row of events_table (dict-like with tickers, strikes, kind, orient, close_epoch)."""
    tickers = list(info["tickers"])
    col = {t: i for i, t in enumerate(tickers)}
    c = candles[candles.ticker.isin(col)]
    if c.empty:
        return None
    t0 = int(c.ts.min())
    t1 = int(c.ts.max())
    if ffill_to_close and info.get("close_epoch"):
        t1 = max(t1, min(int(info["close_epoch"]), t1 + 7 * 1440 * 60))  # carry at most 7 days past the last print
        t1 = min(t1, int(info["close_epoch"]))
        t1 = max(t1, int(c.ts.max()))
    n = (t1 - t0) // 60 + 1
    m = len(tickers)
    bid = np.full((n, m), np.nan, dtype=np.float32)
    ask = np.full((n, m), np.nan, dtype=np.float32)
    bid_hi = np.full((n, m), np.nan, dtype=np.float32)
    ask_lo = np.full((n, m), np.nan, dtype=np.float32)
    vol = np.zeros((n, m), dtype=np.float32)
    oi = np.full((n, m), np.nan, dtype=np.float32)
    has = np.zeros((n, m), dtype=bool)
    r = ((c.ts.values - t0) // 60).astype(np.int64)
    j = c.ticker.map(col).values.astype(np.int64)
    ok = (r >= 0) & (r < n)
    r, j = r[ok], j[ok]
    cc = c[ok]
    b = cc.yes_bid_close.values.astype(np.float32)
    a = cc.yes_ask_close.values.astype(np.float32)
    bh = cc.yes_bid_high.values.astype(np.float32)
    al = cc.yes_ask_low.values.astype(np.float32)
    b = np.where(np.isnan(b) | (b <= 0), EMPTY, b)
    a = np.where(np.isnan(a) | (a >= 100) | (a <= 0), EMPTY, a)
    bh = np.where(np.isnan(bh) | (bh <= 0), np.nan, bh)
    al = np.where(np.isnan(al) | (al >= 100) | (al <= 0), np.nan, al)
    bid[r, j] = b
    ask[r, j] = a
    bid_hi[r, j] = bh
    ask_lo[r, j] = al
    vol[r, j] = np.nan_to_num(cc.volume.values.astype(np.float32))
    oi[r, j] = cc.open_interest.values.astype(np.float32)
    has[r, j] = True
    bid = _ffill(bid)
    ask = _ffill(ask)
    oi = _ffill(oi)
    bid[bid == EMPTY] = np.nan
    ask[ask == EMPTY] = np.nan
    g = Grid()
    g.series, g.event, g.kind, g.orient = info["series"], info["event"], info["kind"], info["orient"]
    g.tickers, g.strikes = tickers, np.asarray(info["strikes"], dtype=float)
    g.ts = t0 + 60 * np.arange(n, dtype=np.int64)
    g.n_candles = int(len(cc))
    if g.orient == "less":
        # P(<X) ladder -> P(>X) form: buy YES on ">X" == buy NO on "<X" == pay 100 - bid(<X)
        bid, ask = 100.0 - ask, 100.0 - bid
        bid_hi, ask_lo = 100.0 - ask_lo, 100.0 - bid_hi
    g.bid, g.ask, g.bid_hi, g.ask_lo, g.vol, g.oi, g.has = bid, ask, bid_hi, ask_lo, vol, oi, has
    return g
