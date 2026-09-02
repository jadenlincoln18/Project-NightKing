
"""
pull_history.py - build a local historical store from Kalshi (+ Polymarket).

WHY PARQUET, NOT CSV
  CSV stores everything as text and every reader re-guesses types. Your own
  slippage exports show the damage: spread_bps came back Integer in some files
  and Float in others. Parquet stores the schema, so a column stays what you
  declared. It is also 5-20x smaller and columnar, so reading one field out of
  a 30-column table does not parse the other 29.

WHAT IT PULLS
  Kalshi candlesticks carry yes_bid AND yes_ask as separate OHLC blocks. That
  is the whole point - the half-spread drives the Stage 9 smile weights and the
  Stage 13 likelihood. A stored mid throws that away permanently, so every
  bid/ask is preserved separately and no mid is ever persisted as the source.

TWO BASE URLS (this is the part that bites)
  live/recent   api.elections.kalshi.com/trade-api/v2/...
  archived      external-api.kalshi.com/trade-api/v2/historical/...
  Markets settled more than ~3 months ago move to the historical tier. The
  puller tries live first, falls back to historical, and records which worked.

LAYOUT
  data/
    raw/kalshi/<series>/<ticker>.json.gz        exact API responses
    parquet/kalshi_candles/series=<S>/event=<E>/part.parquet
    parquet/kalshi_markets/part.parquet          one row per market
    parquet/poly_prices/slug=<S>/part.parquet
    manifest.json                                what exists, for resume
    summary.csv                                  small, human/LLM readable

Usage
  python3 pull_history.py --list                      # survey only, no pull
  python3 pull_history.py --period 60                 # hourly, all commodities
  python3 pull_history.py --period 1 --series KXWTIW  # 1-min, one series
  python3 pull_history.py --resume                    # continue a stopped run
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable

try:
    import pandas as pd
except ImportError:
    sys.exit("needs pandas + pyarrow:  pip install pandas pyarrow")

# --------------------------------------------------------------------------

LIVE = "https://api.elections.kalshi.com/trade-api/v2"
HIST = "https://external-api.kalshi.com/trade-api/v2/historical"
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

UA = "Mozilla/5.0 (compatible; pull-history/1.0)"
PAUSE = 0.10                    # ~10 rps, under Kalshi's ~30 rps public cap
TIMEOUT = 30
MAX_CANDLES = 10_000            # documented cap per candlestick request

DEFAULT_KEYWORDS = ("oil,crude,wti,brent,natgas,natural gas,gas,gasoline,"
                    "gold,silver,copper,platinum,palladium,corn,wheat,soy,"
                    "cotton,coffee,sugar,cattle,lumber")
CATEGORIES = ["Commodities"]

ROOT = Path("data")


# --------------------------------------------------------------------------
# http
# --------------------------------------------------------------------------

def get(url: str, params: dict | None = None, retries: int = 3
        ) -> tuple[Any, int]:
    """Returns (json_or_None, http_status). status 0 = network failure."""
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                full, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode()), r.status
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2.0 * (attempt + 1))
                continue
            if e.code >= 500:
                time.sleep(0.8 * (attempt + 1))
                continue
            return None, e.code
        except Exception:                                   # noqa: BLE001
            time.sleep(0.6 * (attempt + 1))
    return None, 0


def save_raw(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(obj, f)


# --------------------------------------------------------------------------
# parsing helpers
# --------------------------------------------------------------------------

def cents(v: Any) -> float | None:
    """Kalshi returns ints (cents) or decimal strings (dollars). Normalise."""
    if v is None:
        return None
    if isinstance(v, str):
        try:
            return round(float(v) * 100.0, 4)
        except ValueError:
            return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def ohlc(block: Any, prefix: str) -> dict:
    out = {f"{prefix}_{k}": None for k in ("open", "high", "low", "close")}
    if isinstance(block, dict):
        for k in ("open", "high", "low", "close"):
            out[f"{prefix}_{k}"] = cents(block.get(k))
    return out


def ladder_kind(labels: list[str]) -> str:
    """
    RANGE  = mutually exclusive brackets ($87.00 to $87.99). Sum to 100.
    CUMUL  = nested thresholds (Above $89.99). Do NOT sum to 100.
    Storing this matters: the ladder-sum check is only valid on RANGE.
    """
    if not labels:
        return "UNKNOWN"
    n = len(labels)
    rng = sum(1 for l in labels if " to " in l.lower())
    above = sum(1 for l in labels
                if l.lower().startswith(("above", "below", "at or")))
    if rng >= max(3, 0.4 * n):
        return "RANGE"
    if above >= 0.7 * n:
        return "CUMUL"
    return "OTHER"


# --------------------------------------------------------------------------
# kalshi discovery
# --------------------------------------------------------------------------

def discover_series(keywords: list[str] | None) -> list[dict]:
    out, seen = [], set()
    for cat in CATEGORIES:
        resp, _ = get(f"{LIVE}/series", {"category": cat})
        time.sleep(PAUSE)
        if not resp:
            print(f"  ! category {cat}: no response", file=sys.stderr)
            continue
        rows = resp.get("series", []) or []
        kept = 0
        for r in rows:
            tk, title = r.get("ticker"), (r.get("title") or "")
            if not tk or tk in seen:
                continue
            if keywords and not any(k in f"{tk} {title}".lower()
                                    for k in keywords):
                continue
            seen.add(tk)
            out.append({"series": tk, "title": title, "category": cat})
            kept += 1
        print(f"  {cat:14s} {len(rows):4d} series -> {kept} match",
              file=sys.stderr)
    return out


def all_events(series: str) -> list[dict]:
    """Every event for a series, open and settled, paging the cursor."""
    events, cursor = [], None
    for _ in range(40):                       # hard page cap
        p = {"series_ticker": series, "limit": 200,
             "with_nested_markets": "true"}
        if cursor:
            p["cursor"] = cursor
        resp, _ = get(f"{LIVE}/events", p)
        time.sleep(PAUSE)
        if not resp:
            break
        batch = resp.get("events", []) or []
        events.extend(batch)
        cursor = resp.get("cursor") or None
        if not cursor or not batch:
            break
    return events


def historical_markets(series: str) -> list[dict]:
    """Archived markets live on a different host under /historical."""
    out, cursor = [], None
    for _ in range(40):
        p = {"series_ticker": series, "limit": 200}
        if cursor:
            p["cursor"] = cursor
        resp, status = get(f"{HIST}/markets", p)
        time.sleep(PAUSE)
        if not resp:
            if status not in (0, 404):
                print(f"    historical/markets -> {status}", file=sys.stderr)
            break
        batch = resp.get("markets", []) or []
        out.extend(batch)
        cursor = resp.get("cursor") or None
        if not cursor or not batch:
            break
    return out


# --------------------------------------------------------------------------
# candles
# --------------------------------------------------------------------------

def candle_windows(start: int, end: int, period: int) -> list[tuple[int, int]]:
    """Chunk so each request stays under the 10k candle cap."""
    span = MAX_CANDLES * period * 60
    out, t = [], start
    while t < end:
        out.append((t, min(t + span, end)))
        t += span
    return out or [(start, end)]


def fetch_candles(series: str, ticker: str, start: int, end: int,
                  period: int) -> tuple[list[dict], str]:
    """Try live endpoint, fall back to archived. Returns (rows, source)."""
    rows, source = [], "none"
    for src, url in (("live", f"{LIVE}/series/{series}/markets/{ticker}/candlesticks"),
                     ("historical", f"{HIST}/markets/{ticker}/candlesticks")):
        got = []
        ok = False
        for w0, w1 in candle_windows(start, end, period):
            resp, status = get(url, {"start_ts": w0, "end_ts": w1,
                                     "period_interval": period})
            time.sleep(PAUSE)
            if resp is None:
                continue
            ok = True
            got.extend(resp.get("candlesticks", []) or [])
        if ok and got:
            rows, source = got, src
            break
    return rows, source


def candles_to_frame(raw: list[dict], series: str, event: str, ticker: str,
                     label: str, kind: str, period: int) -> pd.DataFrame:
    recs = []
    for c in raw:
        ts = c.get("end_period_ts")
        r = {
            "ts": int(ts) if ts is not None else None,
            "series": series, "event": event, "ticker": ticker,
            "bracket": label, "ladder_kind": kind, "period_min": period,
            "volume": cents(c.get("volume")) if isinstance(c.get("volume"), str)
                      else c.get("volume"),
            "open_interest": c.get("open_interest"),
        }
        r.update(ohlc(c.get("yes_bid"), "yes_bid"))
        r.update(ohlc(c.get("yes_ask"), "yes_ask"))
        r.update(ohlc(c.get("price"), "price"))
        recs.append(r)
    df = pd.DataFrame(recs)
    if df.empty:
        return df
    df["dt"] = pd.to_datetime(df["ts"], unit="s", utc=True)
    # derived, clearly marked - the stored source of truth stays bid/ask
    df["spread"] = df["yes_ask_close"] - df["yes_bid_close"]
    df["half_spread"] = df["spread"] / 2.0
    return df


# --------------------------------------------------------------------------
# polymarket
# --------------------------------------------------------------------------

def poly_markets(limit: int = 500) -> list[dict]:
    out, offset = [], 0
    while offset < limit:
        resp, _ = get(f"{GAMMA}/markets",
                      {"limit": 100, "offset": offset, "order": "volume",
                       "ascending": "false"})
        time.sleep(PAUSE)
        if not isinstance(resp, list) or not resp:
            break
        out.extend(resp)
        offset += 100
    return out


def poly_token_ids(m: dict) -> list[str]:
    raw = m.get("clobTokenIds")
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        try:
            v = json.loads(raw)
            return [str(x) for x in v] if isinstance(v, list) else []
        except json.JSONDecodeError:
            return []
    return []


def poly_history(token: str, fidelity: int = 60) -> list[dict]:
    resp, _ = get(f"{CLOB}/prices-history",
                  {"market": token, "interval": "max", "fidelity": fidelity})
    time.sleep(PAUSE)
    if not resp:
        return []
    return resp.get("history", []) or []


# --------------------------------------------------------------------------
# store
# --------------------------------------------------------------------------

class Store:
    def __init__(self, root: Path):
        self.root = root
        self.pq = root / "parquet"
        self.raw = root / "raw"
        self.manifest_path = root / "manifest.json"
        self.manifest = self._load()

    def _load(self) -> dict:
        if self.manifest_path.exists():
            try:
                return json.loads(self.manifest_path.read_text())
            except json.JSONDecodeError:
                pass
        return {"created": datetime.now(timezone.utc).isoformat(),
                "kalshi_candles": {}, "poly": {}, "runs": []}

    def save_manifest(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2))

    def have(self, ticker: str, period: int) -> bool:
        e = self.manifest["kalshi_candles"].get(ticker)
        return bool(e) and e.get("period") == period and e.get("rows", 0) > 0

    def write_candles(self, df: pd.DataFrame, series: str, event: str,
                      ticker: str, source: str, period: int) -> int:
        if df.empty:
            self.manifest["kalshi_candles"][ticker] = {
                "rows": 0, "period": period, "source": source}
            return 0
        d = self.pq / "kalshi_candles" / f"series={series}" / f"event={event}"
        d.mkdir(parents=True, exist_ok=True)
        df.to_parquet(d / f"{ticker}.parquet", index=False,
                      compression="snappy")
        self.manifest["kalshi_candles"][ticker] = {
            "rows": int(len(df)), "period": period, "source": source,
            "series": series, "event": event,
            "t0": int(df["ts"].min()), "t1": int(df["ts"].max()),
        }
        return len(df)

    def write_table(self, df: pd.DataFrame, name: str, **parts) -> None:
        if df.empty:
            return
        d = self.pq / name
        for k, v in parts.items():
            d = d / f"{k}={v}"
        d.mkdir(parents=True, exist_ok=True)
        df.to_parquet(d / "part.parquet", index=False, compression="snappy")

    def summarise(self) -> pd.DataFrame:
        rows = []
        for tk, e in self.manifest["kalshi_candles"].items():
            if not e.get("rows"):
                continue
            rows.append({
                "ticker": tk, "series": e.get("series"),
                "event": e.get("event"), "rows": e["rows"],
                "period_min": e.get("period"), "source": e.get("source"),
                "start": datetime.fromtimestamp(e["t0"], timezone.utc
                                                ).strftime("%Y-%m-%d %H:%M"),
                "end": datetime.fromtimestamp(e["t1"], timezone.utc
                                              ).strftime("%Y-%m-%d %H:%M"),
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            (self.root / "summary.csv").parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(self.root / "summary.csv", index=False)
        return df


# --------------------------------------------------------------------------
# main flows
# --------------------------------------------------------------------------

def survey(keywords) -> list[dict]:
    print("discovering commodity series ...", file=sys.stderr)
    series = discover_series(keywords)
    print(f"  -> {len(series)} series\n", file=sys.stderr)

    out = []
    for i, s in enumerate(series, 1):
        evs = all_events(s["series"])
        if not evs:
            continue
        n_mkt = sum(len(e.get("markets") or []) for e in evs)
        labels = []
        for e in evs[:1]:
            labels = [str(m.get("yes_sub_title") or m.get("subtitle") or "")
                      for m in (e.get("markets") or [])]
        kind = ladder_kind(labels)
        hist = historical_markets(s["series"])
        rec = {**s, "n_events": len(evs), "n_markets": n_mkt,
               "n_archived": len(hist), "ladder_kind": kind,
               "events": evs}
        out.append(rec)
        print(f"  [{i}/{len(series)}] {s['series']:16s} "
              f"{len(evs):4d} events  {n_mkt:5d} markets  "
              f"{len(hist):5d} archived  {kind}", file=sys.stderr)
    return out


def pull(surveyed: list[dict], store: Store, period: int,
         only_series: str | None, max_markets: int) -> None:
    total = 0
    for rec in surveyed:
        s = rec["series"]
        if only_series and s != only_series:
            continue
        kind = rec["ladder_kind"]
        markets = []
        for ev in rec["events"]:
            et = ev.get("event_ticker")
            for m in (ev.get("markets") or []):
                markets.append((et, m))
        if max_markets:
            markets = markets[:max_markets]
        if not markets:
            continue

        print(f"\n{s}  ({len(markets)} markets, period={period}m)",
              file=sys.stderr)
        for j, (event, m) in enumerate(markets, 1):
            tk = m.get("ticker")
            if not tk:
                continue
            if store.have(tk, period):
                continue
            label = str(m.get("yes_sub_title") or m.get("subtitle") or tk)

            # market lifetime -> candle range
            def ts(key, default):
                v = m.get(key)
                if not v:
                    return default
                try:
                    return int(datetime.fromisoformat(
                        v.replace("Z", "+00:00")).timestamp())
                except (ValueError, AttributeError):
                    return default
            now = int(time.time())
            t0 = ts("open_time", now - 400 * 86400)
            t1 = ts("close_time", now)
            t1 = min(t1, now)
            if t1 <= t0:
                continue

            raw, source = fetch_candles(s, tk, t0, t1, period)
            if raw:
                save_raw(store.raw / "kalshi" / s / f"{tk}.json.gz",
                         {"ticker": tk, "series": s, "event": event,
                          "period": period, "source": source,
                          "candlesticks": raw})
            df = candles_to_frame(raw, s, event, tk, label, kind, period)
            n = store.write_candles(df, s, event, tk, source, period)
            total += n
            if j % 20 == 0 or n:
                print(f"  [{j}/{len(markets)}] {tk[:38]:38s} "
                      f"{n:6d} candles ({source})", file=sys.stderr)
            if j % 25 == 0:
                store.save_manifest()
        store.save_manifest()
    print(f"\ntotal candles stored: {total}", file=sys.stderr)


def pull_poly(store: Store, keywords: list[str]) -> None:
    print("\npolymarket ...", file=sys.stderr)
    mkts = poly_markets()
    hits = [m for m in mkts
            if any(k in (m.get("question", "") or "").lower() for k in keywords)]
    print(f"  {len(mkts)} scanned, {len(hits)} commodity-related",
          file=sys.stderr)
    rows = []
    for m in hits:
        toks = poly_token_ids(m)
        if not toks:
            continue
        h = poly_history(toks[0])
        if not h:
            continue
        df = pd.DataFrame(h)
        if df.empty:
            continue
        df = df.rename(columns={"t": "ts", "p": "price"})
        df["ts"] = pd.to_numeric(df["ts"], errors="coerce")
        df["price"] = pd.to_numeric(df["price"], errors="coerce") * 100
        df["dt"] = pd.to_datetime(df["ts"], unit="s", utc=True)
        df["slug"] = m.get("slug", "")
        df["question"] = m.get("question", "")
        slug = (m.get("slug") or "unknown")[:60]
        store.write_table(df, "poly_prices", slug=slug)
        save_raw(store.raw / "poly" / f"{slug}.json.gz",
                 {"market": m, "history": h})
        rows.append({"slug": slug, "question": m.get("question", "")[:80],
                     "rows": len(df), "end": (m.get("endDate") or "")[:10]})
        print(f"  {slug[:44]:44s} {len(df):5d} pts", file=sys.stderr)
    store.manifest["poly"] = {r["slug"]: r for r in rows}


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true",
                    help="survey only: what exists, how much, no pull")
    ap.add_argument("--period", type=int, default=60, choices=[1, 60, 1440],
                    help="candle size in minutes (default 60)")
    ap.add_argument("--series", help="restrict to one series ticker")
    ap.add_argument("--filter", default=DEFAULT_KEYWORDS)
    ap.add_argument("--max-markets", type=int, default=0,
                    help="cap markets per series (0 = all)")
    ap.add_argument("--no-poly", action="store_true")
    ap.add_argument("--resume", action="store_true",
                    help="skip anything already in the manifest")
    ap.add_argument("--out", default="data")
    a = ap.parse_args()

    kw = [k.strip().lower() for k in a.filter.split(",") if k.strip()]
    store = Store(Path(a.out))
    if not a.resume:
        store.manifest["kalshi_candles"] = store.manifest.get(
            "kalshi_candles", {}) if a.list else {}

    surveyed = survey(kw)

    sdf = pd.DataFrame([{k: v for k, v in r.items() if k != "events"}
                        for r in surveyed])
    if not sdf.empty:
        sdf = sdf.sort_values("n_markets", ascending=False)
        print("\n" + "=" * 78)
        print("SURVEY - what exists before you spend anything on CME data")
        print("=" * 78)
        print(sdf.to_string(index=False))
        store.write_table(sdf, "kalshi_series_survey")
        print(f"\nRANGE ladders (ladder-sum valid): "
              f"{int((sdf.ladder_kind == 'RANGE').sum())}")
        print(f"CUMUL ladders (threshold, compare to survival fn): "
              f"{int((sdf.ladder_kind == 'CUMUL').sum())}")

    if a.list:
        store.save_manifest()
        print("\nsurvey only (--list). Re-run without --list to pull candles.")
        return

    pull(surveyed, store, a.period, a.series, a.max_markets)
    if not a.no_poly:
        pull_poly(store, kw)

    store.manifest["runs"].append(
        {"at": datetime.now(timezone.utc).isoformat(),
         "period": a.period, "series": a.series})
    store.save_manifest()

    summ = store.summarise()
    print("\n" + "=" * 78)
    print("STORED")
    print("=" * 78)
    if summ.empty:
        print("nothing stored - check the survey output above")
    else:
        by = (summ.groupby("series")
                  .agg(markets=("ticker", "count"), candles=("rows", "sum"),
                       first=("start", "min"), last=("end", "max"))
                  .sort_values("candles", ascending=False))
        print(by.to_string())
        print(f"\ntotal {summ.rows.sum():,} candles across "
              f"{len(summ)} markets")
        print(f"parquet: {a.out}/parquet/   raw: {a.out}/raw/")
        print(f"summary: {a.out}/summary.csv   manifest: {a.out}/manifest.json")


if __name__ == "__main__":
    main()