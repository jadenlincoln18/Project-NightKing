#!/usr/bin/env python3
"""
venue_scan.py — survey commodity prediction markets on Kalshi and Polymarket.

Answers two questions per market, using only public keyless endpoints:

  1. LADDER SUM  (Kalshi only, mutually-exclusive bracket ladders)
       Exactly one bracket in a ladder pays $1. So:
         - sum of YES ASKS  < 100c - fees  ->  buy every bracket, locked profit
         - sum of YES BIDS  > 100c + fees  ->  sell every bracket, locked profit
       This is a pure within-venue arb. No options, no hedge, no basis.

  2. EXECUTABLE DEPTH
       Not lifetime volume - actual resting contracts at the touch, on the
       side you would have to hit. Reported in contracts and dollars, with
       the size-weighted price of sweeping N contracts.

KALSHI ORDERBOOK NOTE (this trips everyone up):
  Kalshi returns *bids only*, for both sides. A YES bid at 7c is identical to
  a NO ask at 93c. So the YES ask must be DERIVED:
        yes_ask = 100 - best_no_bid
  Treating the raw book as yes-bid/yes-ask is simply wrong.

POLYMARKET NOTE:
  gamma returns clobTokenIds as a JSON *string*; it must be json.loads'd or you
  get a double-encoded mess. Polymarket books are true bid/ask on each token.

Usage:
    python venue_scan.py                      # scan both venues
    python venue_scan.py --venue kalshi
    python venue_scan.py --series KXWTIW      # one Kalshi series
    python venue_scan.py --size 500           # depth target, contracts
    python venue_scan.py --json out.json      # machine-readable dump

No API keys. Read-only. Rate-limited well under Kalshi's ~30 rps public cap.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------

KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

UA = "Mozilla/5.0 (compatible; venue-scan/1.0)"
PAUSE = 0.08           # ~12 rps, well under Kalshi's ~30 rps public limit
TIMEOUT = 20

# Categories to pull series from. The series themselves are DISCOVERED at
# runtime via /series - never hardcoded, because guessed tickers silently
# 404 and get misreported as "no open markets".
KALSHI_CATEGORIES = ["Commodities", "Economics", "Financials"]

# Series are matched against ticker+title. Keeps the scan to instruments that
# plausibly have a listed options chain to hedge against.
DEFAULT_KEYWORDS = ("oil,crude,wti,brent,gas,gasoline,natural,gold,silver,"
                    "copper,platinum,corn,wheat,soy,cotton,coffee,sugar,"
                    "s&p,nasdaq,dow,russell,vix,index,treasury,yield,fed")

POLY_QUERIES = ["oil", "crude", "wti", "brent", "natural gas",
                "gold", "silver", "copper", "gasoline", "wheat", "corn"]

# Kalshi fee: ceil(0.07 * C * P * (1-P)) cents per contract, per side.
KALSHI_FEE_COEF = 0.07


# --------------------------------------------------------------------------
# http
# --------------------------------------------------------------------------

def get(url: str, params: dict | None = None, retries: int = 3) -> Any:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                return None
            if e.code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            if e.code >= 500:
                time.sleep(0.6 * (attempt + 1))
                continue
            return None
        except Exception as e:                     # noqa: BLE001
            last = e
            time.sleep(0.5 * (attempt + 1))
    if last:
        print(f"    ! {type(last).__name__} on {url[:70]}", file=sys.stderr)
    return None


def fee_cents(price_cents: float, contracts: int = 1) -> float:
    """Kalshi trading fee, cents. ceil per Kalshi's published formula."""
    import math
    p = max(0.0, min(1.0, price_cents / 100.0))
    return math.ceil(KALSHI_FEE_COEF * contracts * p * (1 - p) * 100) / 100 * 100 / 100


# --------------------------------------------------------------------------
# book model
# --------------------------------------------------------------------------

@dataclass
class Level:
    price: float          # cents, 0-100
    size: int             # contracts


@dataclass
class Book:
    """Normalised two-sided YES book, prices in cents."""
    yes_bids: list[Level] = field(default_factory=list)   # desc price
    yes_asks: list[Level] = field(default_factory=list)   # asc price

    @property
    def best_bid(self) -> float | None:
        return self.yes_bids[0].price if self.yes_bids else None

    @property
    def best_ask(self) -> float | None:
        return self.yes_asks[0].price if self.yes_asks else None

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def mid(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    def depth_at_touch(self, side: str) -> tuple[float, int]:
        lv = self.yes_bids if side == "bid" else self.yes_asks
        if not lv:
            return (0.0, 0)
        return (lv[0].price, lv[0].size)

    def sweep(self, side: str, want: int) -> dict:
        """Walk the book for `want` contracts. side='ask' to buy, 'bid' to sell."""
        levels = self.yes_asks if side == "ask" else self.yes_bids
        if not levels:
            return {"filled": 0, "vwap": None, "touch": None,
                    "slip_cents": None, "complete": False}
        got, cost = 0, 0.0
        for lv in levels:
            take = min(lv.size, want - got)
            if take <= 0:
                break
            got += take
            cost += take * lv.price
        if got == 0:
            return {"filled": 0, "vwap": None, "touch": levels[0].price,
                    "slip_cents": None, "complete": False}
        vwap = cost / got
        touch = levels[0].price
        return {
            "filled": got,
            "vwap": round(vwap, 3),
            "touch": touch,
            "slip_cents": round(abs(vwap - touch), 3),
            "complete": got >= want,
        }

    def total_size(self, side: str) -> int:
        lv = self.yes_bids if side == "bid" else self.yes_asks
        return sum(x.size for x in lv)


# --------------------------------------------------------------------------
# kalshi
# --------------------------------------------------------------------------

def kalshi_discover_series(categories: Iterable[str],
                           keywords: list[str] | None = None
                           ) -> list[tuple[str, str]]:
    """Ask Kalshi which series exist. Never guess tickers."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for cat in categories:
        resp = get(f"{KALSHI}/series", {"category": cat})
        time.sleep(PAUSE)
        if not resp:
            print(f"  ! category '{cat}' returned nothing", file=sys.stderr)
            continue
        rows = resp.get("series", []) or []
        kept = 0
        for r in rows:
            tk = r.get("ticker")
            title = (r.get("title") or tk or "")
            if not tk or tk in seen:
                continue
            if keywords:
                hay = f"{tk} {title}".lower()
                if not any(k in hay for k in keywords):
                    continue
            seen.add(tk)
            out.append((tk, title[:46]))
            kept += 1
        print(f"  {cat:14s} {len(rows):4d} series -> {kept} kept", file=sys.stderr)
    return out


def _book_from_sides(yes_raw, no_raw, scale=1.0) -> Book:
    yes = [(p * scale, c) for p, c in _parse_kalshi_side(yes_raw)]
    no = [(p * scale, c) for p, c in _parse_kalshi_side(no_raw)]
    book = Book()
    book.yes_bids = sorted((Level(round(p, 2), c) for p, c in yes),
                           key=lambda l: -l.price)
    # yes_ask = 100 - no_bid  (Kalshi returns bids only, on both sides)
    book.yes_asks = sorted((Level(round(100.0 - p, 2), c) for p, c in no),
                           key=lambda l: l.price)
    return book


def kalshi_books_bulk(tickers: list[str]) -> dict[str, Book]:
    """
    Fetch up to 100 orderbooks per request via /markets/orderbooks.
    Falls back to per-ticker calls if the bulk endpoint isn't available.
    """
    books: dict[str, Book] = {}
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i + 100]
        raw = get(f"{KALSHI}/markets/orderbooks", {"tickers": ",".join(chunk)})
        time.sleep(PAUSE)
        if not raw:
            for tk in chunk:                       # fallback: one at a time
                bk = kalshi_book(tk)
                time.sleep(PAUSE)
                if bk:
                    books[tk] = bk
            continue
        entries = (raw.get("orderbooks") or raw.get("markets")
                   or (raw if isinstance(raw, list) else []))
        for e in entries:
            if not isinstance(e, dict):
                continue
            tk = e.get("ticker") or e.get("market_ticker")
            if not tk:
                continue
            ob = e.get("orderbook") or e
            y, n, sc = ob.get("yes"), ob.get("no"), 1.0
            if y is None and n is None:
                fp = e.get("orderbook_fp") or ob.get("orderbook_fp") or {}
                y, n = fp.get("yes_dollars"), fp.get("no_dollars")
                sc = 100.0
            if y is None and n is None:
                continue
            books[tk] = _book_from_sides(y, n, sc)
    return books


def kalshi_events(series: str, nested: bool = True) -> list[dict]:
    p = {"series_ticker": series, "status": "open", "limit": 200}
    if nested:
        p["with_nested_markets"] = "true"
    out = get(f"{KALSHI}/events", p)
    if not out:
        return []
    return out.get("events", []) or []


def kalshi_markets(event_ticker: str) -> list[dict]:
    out = get(f"{KALSHI}/markets", {"event_ticker": event_ticker,
                                    "status": "open", "limit": 1000})
    if not out:
        return []
    return out.get("markets", []) or []


def _parse_kalshi_side(raw: Any) -> list[tuple[float, int]]:
    """Kalshi levels arrive ascending as [price, count]; price may be str."""
    if not raw:
        return []
    out = []
    for row in raw:
        try:
            p, c = float(row[0]), int(float(row[1]))
        except (TypeError, ValueError, IndexError):
            continue
        if c > 0:
            out.append((p, c))
    return out


def kalshi_book(ticker: str, depth: int = 100) -> Book | None:
    """
    Fetch and normalise. Kalshi gives BIDS ONLY on each side:
        yes_bids -> our yes bids
        no_bids  -> yes ASKS at (100 - no_price), same size
    Handles both the cents `orderbook` and the dollars `orderbook_fp` shapes.
    """
    raw = get(f"{KALSHI}/markets/{ticker}/orderbook", {"depth": depth})
    if not raw:
        return None
    ob = raw.get("orderbook") or {}
    yes_raw, no_raw, scale = ob.get("yes"), ob.get("no"), 1.0
    if yes_raw is None and no_raw is None:
        fp = raw.get("orderbook_fp") or {}
        yes_raw, no_raw = fp.get("yes_dollars"), fp.get("no_dollars")
        scale = 100.0                      # dollars -> cents
    yes = [(p * scale, c) for p, c in _parse_kalshi_side(yes_raw)]
    no = [(p * scale, c) for p, c in _parse_kalshi_side(no_raw)]

    return _book_from_sides(yes_raw, no_raw, scale)


def scan_kalshi_ladder(series: str, label: str, size: int,
                       max_events: int = 3) -> list[dict]:
    results = []
    events = kalshi_events(series)
    if not events:
        return results

    for ev in events[:max_events]:              # nearest few expiries
        et = ev.get("event_ticker")
        # nested markets come back with the event -> saves a round trip
        markets = ev.get("markets") or []
        if not markets:
            markets = kalshi_markets(et)
            time.sleep(PAUSE)
        if len(markets) < 3:                    # not a bracket ladder
            continue

        tickers = [m.get("ticker") for m in markets if m.get("ticker")]
        books = kalshi_books_bulk(tickers)      # 1 call per 100 brackets

        rows = []
        for m in markets:
            tk = m.get("ticker")
            bk = books.get(tk)
            if bk is None:
                continue
            rows.append({
                "ticker": tk,
                "label": m.get("yes_sub_title") or m.get("subtitle") or tk,
                "bid": bk.best_bid,
                "ask": bk.best_ask,
                "spread": bk.spread,
                "bid_size": bk.depth_at_touch("bid")[1],
                "ask_size": bk.depth_at_touch("ask")[1],
                "buy_sweep": bk.sweep("ask", size),
                "sell_sweep": bk.sweep("bid", size),
                "book": bk,
            })
        if len(rows) < 3:
            continue

        # ---- ladder sum ----
        asks = [r["ask"] for r in rows if r["ask"] is not None]
        bids = [r["bid"] for r in rows if r["bid"] is not None]
        n_all, n_ask, n_bid = len(rows), len(asks), len(bids)
        ask_sum = sum(asks) if n_ask == n_all else None   # need EVERY leg
        bid_sum = sum(bids) if n_bid == n_all else None

        # round-trip fee estimate across the ladder, at each leg's own price
        fee_buy = sum(fee_cents(r["ask"]) for r in rows if r["ask"] is not None)
        fee_sell = sum(fee_cents(r["bid"]) for r in rows if r["bid"] is not None)

        buy_edge = (100.0 - ask_sum - fee_buy) if ask_sum is not None else None
        sell_edge = (bid_sum - 100.0 - fee_sell) if bid_sum is not None else None

        # binding size for the whole-ladder trade = thinnest leg
        buy_cap = min((r["ask_size"] for r in rows), default=0)
        sell_cap = min((r["bid_size"] for r in rows), default=0)

        # ---- moderate-tail depth (5-20c brackets: where FLB lives) ----
        tails = [r for r in rows
                 if r["bid"] is not None and 5.0 <= r["bid"] <= 20.0]

        results.append({
            "venue": "kalshi",
            "series": series,
            "label": label,
            "event": et,
            "title": ev.get("title", ""),
            "n_brackets": n_all,
            "n_quoted_ask": n_ask,
            "n_quoted_bid": n_bid,
            "ask_sum": round(ask_sum, 2) if ask_sum else None,
            "bid_sum": round(bid_sum, 2) if bid_sum else None,
            "fee_buy": round(fee_buy, 2),
            "fee_sell": round(fee_sell, 2),
            "buy_edge": round(buy_edge, 2) if buy_edge is not None else None,
            "sell_edge": round(sell_edge, 2) if sell_edge is not None else None,
            "buy_cap": buy_cap,
            "sell_cap": sell_cap,
            "rows": [{k: v for k, v in r.items() if k != "book"} for r in rows],
            "tails": [{k: v for k, v in r.items() if k != "book"} for r in tails],
        })
    return results


# --------------------------------------------------------------------------
# polymarket
# --------------------------------------------------------------------------

def poly_search(q: str, limit: int = 60) -> list[dict]:
    out = get(f"{GAMMA}/markets", {"active": "true", "closed": "false",
                                   "limit": limit, "order": "volume24hr",
                                   "ascending": "false"})
    if not isinstance(out, list):
        return []
    ql = q.lower()
    return [m for m in out if ql in (m.get("question", "") or "").lower()]


def poly_token_ids(m: dict) -> list[str]:
    """clobTokenIds is a JSON STRING. Naive parsers double-encode it."""
    raw = m.get("clobTokenIds")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    try:
        v = json.loads(raw)
        return [str(x) for x in v] if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def poly_book(token_id: str) -> Book | None:
    raw = get(f"{CLOB}/book", {"token_id": token_id})
    if not raw:
        return None
    book = Book()
    for b in raw.get("bids", []) or []:
        try:
            book.yes_bids.append(Level(round(float(b["price"]) * 100, 2),
                                       int(float(b["size"]))))
        except (KeyError, TypeError, ValueError):
            continue
    for a in raw.get("asks", []) or []:
        try:
            book.yes_asks.append(Level(round(float(a["price"]) * 100, 2),
                                       int(float(a["size"]))))
        except (KeyError, TypeError, ValueError):
            continue
    book.yes_bids.sort(key=lambda l: -l.price)
    book.yes_asks.sort(key=lambda l: l.price)
    return book


def scan_polymarket(size: int) -> list[dict]:
    seen, results = set(), []
    for q in POLY_QUERIES:
        for m in poly_search(q):
            cid = m.get("conditionId")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            toks = poly_token_ids(m)
            if not toks:
                continue
            bk = poly_book(toks[0])            # YES token
            time.sleep(PAUSE)
            if bk is None or (bk.best_bid is None and bk.best_ask is None):
                continue
            results.append({
                "venue": "polymarket",
                "query": q,
                "question": m.get("question", "")[:90],
                "slug": m.get("slug", ""),
                "end": (m.get("endDate") or "")[:10],
                "vol24": float(m.get("volume24hr") or 0),
                "liquidity": float(m.get("liquidity") or 0),
                "neg_risk": bool(m.get("negRisk", False)),
                "bid": bk.best_bid,
                "ask": bk.best_ask,
                "spread": bk.spread,
                "bid_size": bk.depth_at_touch("bid")[1],
                "ask_size": bk.depth_at_touch("ask")[1],
                "book_bid_total": bk.total_size("bid"),
                "book_ask_total": bk.total_size("ask"),
                "buy_sweep": bk.sweep("ask", size),
                "sell_sweep": bk.sweep("bid", size),
            })
    return results


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def hr(c="-", n=94):
    print(c * n)


def report_kalshi(res: list[dict], size: int) -> None:
    hr("=")
    print("KALSHI  —  ladder-sum arbitrage + executable depth")
    hr("=")
    if not res:
        print("no open commodity ladders found")
        return

    print("\nLADDER SUM (exactly one bracket pays $1)")
    print("  buy_edge  = 100 - sum(asks) - fees   >0 means buy every bracket")
    print("  sell_edge = sum(bids) - 100 - fees   >0 means sell every bracket")
    print("  cap = thinnest leg, i.e. max ladders you could actually do\n")
    print(f"{'event':30s} {'n':>3s} {'askSum':>7s} {'bidSum':>7s} "
          f"{'buyEdge':>8s} {'sellEdge':>9s} {'cap':>6s}")
    hr()
    hits = []
    for r in res:
        be = f"{r['buy_edge']:+.1f}" if r["buy_edge"] is not None else "  n/a"
        se = f"{r['sell_edge']:+.1f}" if r["sell_edge"] is not None else "  n/a"
        cap = r["buy_cap"] if (r["buy_edge"] or -1) > 0 else r["sell_cap"]
        flag = ""
        if (r["buy_edge"] or -1) > 0 or (r["sell_edge"] or -1) > 0:
            flag = "  <== ARB"
            hits.append(r)
        # None means NOT ALL LEGS QUOTED - print n/a, never 0.0, which reads
        # as "no bids" when it actually means "ladder incomplete".
        asum = f"{r['ask_sum']:7.1f}" if r["ask_sum"] is not None else "    n/a"
        bsum = f"{r['bid_sum']:7.1f}" if r["bid_sum"] is not None else "    n/a"
        miss = ""
        if r["ask_sum"] is None or r["bid_sum"] is None:
            miss = (f"  [{r['n_quoted_bid']}/{r['n_brackets']} bid, "
                    f"{r['n_quoted_ask']}/{r['n_brackets']} ask]")
        print(f"{r['event'][:30]:30s} {r['n_brackets']:3d} "
              f"{asum} {bsum} {be:>8s} {se:>9s} {cap:6d}{flag}{miss}")

    if not hits:
        print("\n  no ladder-sum arbitrage. Expected — this is the cheap check,")
        print("  and a negative result is genuine information, not a failure.")

    print(f"\n\nMODERATE-TAIL DEPTH  (5-20c brackets, target {size} contracts)")
    print("  This is the gate. 'complete=False' means you cannot get the")
    print("  minimum hedged unit done at any price.\n")
    print(f"{'bracket':26s} {'bid':>5s} {'ask':>5s} {'sprd':>5s} "
          f"{'bidSz':>6s} {'askSz':>6s} {'sellVWAP':>9s} {'slip':>6s} {'full':>5s}")
    hr()
    any_tail = False
    for r in res:
        for t in r["tails"]:
            any_tail = True
            sw = t["sell_sweep"]
            vw = f"{sw['vwap']:.2f}" if sw["vwap"] is not None else "   -"
            sl = f"{sw['slip_cents']:.2f}" if sw["slip_cents"] is not None else "   -"
            print(f"{str(t['label'])[:26]:26s} "
                  f"{(t['bid'] or 0):5.1f} {(t['ask'] or 0):5.1f} "
                  f"{(t['spread'] or 0):5.1f} {t['bid_size']:6d} {t['ask_size']:6d} "
                  f"{vw:>9s} {sl:>6s} {'Y' if sw['complete'] else 'N':>5s}")
    if not any_tail:
        print("  no brackets currently quoted in the 5-20c range")


def report_poly(res: list[dict], size: int) -> None:
    print()
    hr("=")
    print("POLYMARKET  —  commodity markets, executable depth")
    hr("=")
    if not res:
        print("no matching commodity markets found")
        return
    print("\nNOTE: these are standalone binaries, not exclusive ladders, so a")
    print("ladder sum is meaningless here. Depth and spread only.")
    print("Check each market's resolution text before pairing with options.\n")
    print(f"{'question':46s} {'end':>10s} {'bid':>5s} {'ask':>5s} "
          f"{'sprd':>5s} {'bidSz':>7s} {'askSz':>7s} {'full':>5s}")
    hr()
    for r in sorted(res, key=lambda x: -x["vol24"]):
        sw = r["sell_sweep"]
        print(f"{r['question'][:46]:46s} {r['end']:>10s} "
              f"{(r['bid'] or 0):5.1f} {(r['ask'] or 0):5.1f} "
              f"{(r['spread'] or 0):5.1f} {r['bid_size']:7d} {r['ask_size']:7d} "
              f"{'Y' if sw['complete'] else 'N':>5s}")


def verdict(kal: list[dict], poly: list[dict], size: int) -> None:
    print()
    hr("=")
    print("VERDICT")
    hr("=")
    tradeable = []
    for r in kal:
        for t in r["tails"]:
            if t["sell_sweep"]["complete"] or t["buy_sweep"]["complete"]:
                tradeable.append((r["label"], t["label"],
                                  t["bid"], t["bid_size"], t["ask_size"]))
    print(f"\nKalshi ladders scanned      : {len(kal)}")
    print(f"Kalshi moderate-tail quotes : {sum(len(r['tails']) for r in kal)}")
    print(f"  ...with >= {size} contracts : {len(tradeable)}")
    print(f"Polymarket markets scanned  : {len(poly)}")
    p_ok = sum(1 for r in poly if r["sell_sweep"]["complete"])
    print(f"  ...with >= {size} contracts : {p_ok}")

    if tradeable:
        print(f"\nKalshi brackets deep enough for a {size}-contract hedged unit:")
        for lab, br, bid, bsz, asz in tradeable[:15]:
            print(f"   {lab:22s} {str(br)[:22]:22s} bid {bid:5.1f}c  "
                  f"bidSz {bsz:5d}  askSz {asz:5d}")
    else:
        print(f"\nNo moderate-tail Kalshi bracket has {size} contracts resting.")
        print("That is the fedarb failure repeating: signal where you cannot size.")
        print(f"Retry with --size 50 (Micro WTI unit) before concluding.")

    print("\nReminder: depth at one instant is a snapshot. Run this repeatedly")
    print("across a session before drawing conclusions about a market.")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--venue", choices=["kalshi", "polymarket", "both"],
                    default="both")
    ap.add_argument("--series", help="single Kalshi series ticker, e.g. KXWTIW")
    ap.add_argument("--categories",
                    help="comma-separated Kalshi categories to discover "
                         "(default: Commodities,Economics,Financials)")
    ap.add_argument("--filter", default=DEFAULT_KEYWORDS,
                    help="comma-separated keywords; a series is scanned only "
                         "if its ticker or title matches one")
    ap.add_argument("--no-filter", action="store_true",
                    help="scan every discovered series (slow)")
    ap.add_argument("--max-events", type=int, default=3,
                    help="expiries per series to scan (default 3)")
    ap.add_argument("--size", type=int, default=500,
                    help="depth target in contracts (500=std CL unit, 50=Micro)")
    ap.add_argument("--json", help="write full results to this path")
    a = ap.parse_args()

    kal: list[dict] = []
    poly: list[dict] = []

    if a.venue in ("kalshi", "both"):
        if a.series:
            series = [(a.series, "user-specified")]
        else:
            cats = a.categories.split(",") if a.categories else KALSHI_CATEGORIES
            kw = None if a.no_filter else [k.strip().lower()
                                           for k in a.filter.split(",")]
            print("discovering Kalshi series ...", file=sys.stderr)
            series = kalshi_discover_series(cats, kw)
            print(f"  -> {len(series)} series to scan\n", file=sys.stderr)

        for i, (tk, label) in enumerate(series, 1):
            try:
                got = scan_kalshi_ladder(tk, label, a.size, a.max_events)
            except Exception as e:                       # noqa: BLE001
                print(f"  ! {tk}: {type(e).__name__}: {e}", file=sys.stderr)
                continue
            if got:
                n = sum(r["n_brackets"] for r in got)
                print(f"  [{i}/{len(series)}] {tk:18s} "
                      f"{len(got)} ladder(s), {n} brackets", file=sys.stderr)
                kal.extend(got)
            elif i % 10 == 0:
                print(f"  [{i}/{len(series)}] ...", file=sys.stderr)
            time.sleep(PAUSE)

    if a.venue in ("polymarket", "both"):
        print("scanning Polymarket ...", file=sys.stderr)
        try:
            poly = scan_polymarket(a.size)
            print(f"  {len(poly)} market(s)", file=sys.stderr)
        except Exception as e:                           # noqa: BLE001
            print(f"  ! polymarket: {type(e).__name__}: {e}", file=sys.stderr)

    if a.venue in ("kalshi", "both"):
        report_kalshi(kal, a.size)
    if a.venue in ("polymarket", "both"):
        report_poly(poly, a.size)
    verdict(kal, poly, a.size)

    if a.json:
        with open(a.json, "w") as f:
            json.dump({"ts": time.time(), "size": a.size,
                       "kalshi": kal, "polymarket": poly}, f, indent=2)
        print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()