#!/usr/bin/env python3
"""
fake_kalshi.py - a local stand-in for BOTH Kalshi hosts, shape-faithful to the
brief's VERIFIED section, so probe/collect/verify can be exercised end to end
without network access.

Both hosts are served by one HTTP server:
    live  base = http://127.0.0.1:<port>/trade-api/v2
    hist  base = http://127.0.0.1:<port>/trade-api/v2/historical

What it reproduces
  - series in several categories; events with mutually_exclusive and
    settlement_sources; markets with *_fp / *_dollars fields, custom_strike,
    settlement_ts, expiration_value, occurrence_datetime
  - cursor paging on /events, /markets, /historical/markets
  - candlesticks as {"open_dollars": "0.0100", ...} decimal strings, volume_fp;
    >5000 candles per request -> HTTP 400 "max candlesticks: 5000";
    period_interval outside 1/60/1440 -> 400
  - host routing: old markets only on the historical host (live candles 404),
    recent ones only on live, an overlap band on both hosts (the historical
    record carrying settlement fields the live one lacks, plus one deliberate
    conflict), one archived market whose candles are served by LIVE only,
    and never-traded markets that 404 on both hosts
  - a control endpoint: GET /__control/fail/on makes candle endpoints return
    503 (simulates an outage), /__control/fail/off restores them
  - optional 429s: --rate-limit N -> more than N requests/second gets a 429

Standalone:  python3 tests/fake_kalshi.py [--port 8765] [--rate-limit 0]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
import urllib.parse
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

CAP = 5000
PERIODS = (1, 60, 1440)
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
LIVE_PREFIX = "/trade-api/v2"
HIST_PREFIX = "/trade-api/v2/historical"


def h32(*parts: Any) -> int:
    return int(hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:8], 16)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def kt_date(dt: datetime, with_hour: bool) -> str:
    return "%02d%s%02d%s" % (dt.year % 100, MON[dt.month - 1], dt.day,
                             ("%02d" % dt.hour) if with_hour else "")


SERIES_SPEC = [
    # ticker, category, title, frequency, cadence, n_events, brackets, exclusive, source
    ("KXFAKEWTIW", "Commodities", "WTI oil price this week (fake)", "weekly", "weekly", 12,
     [("Below $70.00", "less", None, 70.0), ("$70.00 to $70.99", "between", 70.0, 70.99),
      ("$71.00 to $71.99", "between", 71.0, 71.99), ("Above $71.99", "greater", 71.99, None)],
     True, {"name": "ICE", "url": "https://www.theice.com/products/213/WTI-Crude-Futures"}),
    ("KXFAKEGOLDD", "Commodities", "Gold price today (fake)", "daily", "daily", 30,
     [("Above $4000", "greater", 4000.0, None), ("Above $4050", "greater", 4050.0, None),
      ("Above $4100", "greater", 4100.0, None)],
     False, {"name": "Pyth - Gold", "url": "https://app.pyth.com/price-feeds/metal/gold"}),
    ("KXFAKEWTIH", "Commodities", "WTI oil price hourly (fake)", "hourly", "hourly", 48,
     [("Above $70.49", "greater", 70.49, None), ("Above $70.99", "greater", 70.99, None),
      ("Above $71.49", "greater", 71.49, None)],
     False, {"name": "ICE", "url": "https://www.theice.com/products/213/WTI-Crude-Futures"}),
    ("KXFAKEHEATOIL", "Economics", "Heating oil price this month (fake)", "monthly", "monthly", 4,
     [("Above $2.50", "greater", 2.5, None), ("Above $2.75", "greater", 2.75, None),
      ("Above $3.00", "greater", 3.0, None)],
     False, {"name": "NYMEX", "url": "https://www.cmegroup.com/markets/energy/refined-products/heating-oil.html"}),
    ("KXFAKEPOTUS", "Politics", "Who wins (fake)", "annual", "longer", 2,
     [("Candidate A", "custom", None, None), ("Candidate B", "custom", None, None)],
     True, {"name": "AP", "url": "https://apnews.com"}),
]


class World:
    def __init__(self, now: Optional[int] = None):
        self.now = int(now or time.time())
        self.series: List[dict] = []
        self.events: Dict[str, dict] = {}
        self.event_markets: Dict[str, List[str]] = defaultdict(list)
        self.markets: Dict[str, dict] = {}                 # canonical record
        self.live_markets: Dict[str, dict] = {}            # what live /markets serves
        self.hist_markets: Dict[str, dict] = {}            # what /historical/markets serves
        self.candles_on: Dict[str, set] = {}               # ticker -> {"live","hist"}
        self.fail = False
        self.rate_limit = 0
        self._recent = deque()
        self._lock = threading.Lock()
        self.requests = 0
        self.by_path = defaultdict(int)
        self._build()

    # -- data ----------------------------------------------------------------
    def _build(self) -> None:
        now = datetime.fromtimestamp(self.now, timezone.utc).replace(minute=0, second=0, microsecond=0)
        for (tk, cat, title, freq, cad, n, brackets, excl, src) in SERIES_SPEC:
            self.series.append({"ticker": tk, "title": title, "category": cat, "frequency": freq,
                                "tags": ["Oil"] if "WTI" in tk or "HEAT" in tk else ["Metals"] if "GOLD" in tk else [],
                                "settlement_sources": [src], "contract_url": "https://kalshi.com/%s" % tk.lower()})
            step = {"weekly": timedelta(days=7), "daily": timedelta(days=1), "hourly": timedelta(hours=1),
                    "monthly": timedelta(days=30), "longer": timedelta(days=365)}[cad]
            life = {"weekly": timedelta(days=7), "daily": timedelta(days=1), "hourly": timedelta(hours=1),
                    "monthly": timedelta(days=30), "longer": timedelta(days=200)}[cad]
            for i in range(-1, n - 1):
                close = now - step * i
                open_ = close - life
                with_hour = cad in ("weekly", "daily", "hourly") and not (cad == "weekly" and i >= 7)
                et = "%s-%s" % (tk, kt_date(close, with_hour))
                if cad == "longer":
                    et = "%s-%d" % (tk, close.year)
                status = "open" if close > now else ("closed" if (now - close) < timedelta(hours=6) else "settled")
                # routing bands (in event index i): recent -> live only; middle -> both; old -> hist only
                if cad == "weekly":
                    band = "live" if i <= 3 else "both" if i <= 6 else "hist"
                elif cad == "daily":
                    band = "live" if i <= 9 else "both" if i <= 19 else "hist"
                elif cad == "hourly":
                    band = "live" if i <= 29 else "hist"
                else:
                    band = "live"
                ev = {"event_ticker": et, "series_ticker": tk, "title": "%s %s" % (title, close.strftime("%b %d")),
                      "sub_title": close.strftime("%b %d, %Y"), "category": cat, "mutually_exclusive": excl,
                      "settlement_sources": [src], "strike_date": iso(close), "strike_period": cad,
                      "collateral_return_type": "binary", "available_on_brokers": False}
                self.events[et] = ev
                for j, (label, stype, floor, cap) in enumerate(brackets):
                    code = ("B%.2f" % ((floor or 0) + 0.5) if stype == "between" else
                            "T%.2f" % (floor if floor is not None else cap) if stype in ("greater", "less") else "C%d" % j)
                    mt = "%s-%s" % (et, code)
                    settled_val = "%.2f" % (70.0 + (h32(et) % 300) / 100.0) if cat != "Politics" else ""
                    never_traded = cad == "weekly" and i >= 9
                    m = {
                        "ticker": mt, "event_ticker": et, "market_type": "binary",
                        "title": "%s: %s" % (ev["title"], label), "subtitle": label, "yes_sub_title": label,
                        "no_sub_title": "Not " + label, "open_time": iso(open_), "close_time": iso(close),
                        "expiration_time": iso(close + timedelta(hours=1)),
                        "expected_expiration_time": iso(close + timedelta(hours=1)),
                        "latest_expiration_time": iso(close + timedelta(days=1)),
                        "settlement_timer_seconds": 3600, "status": status,
                        "response_price_units": "usd_cent", "notional_value_dollars": "1.0000",
                        "yes_bid_dollars": "0.%04d" % (h32(mt, "b") % 9000), "yes_ask_dollars": "0.%04d" % (h32(mt, "a") % 9000),
                        "last_price_dollars": "0.%04d" % (h32(mt, "l") % 9000),
                        "previous_yes_bid_dollars": "0.0100", "previous_price_dollars": "0.0200",
                        "volume_fp": "0.00" if never_traded else "%.2f" % (10 + h32(mt, "v") % 500),
                        "volume_24h_fp": "0.00", "liquidity_fp": "%.2f" % (h32(mt, "q") % 100000),
                        "open_interest_fp": "%.2f" % (h32(mt, "o") % 1000),
                        "result": "", "expiration_value": "", "settlement_ts": "", "occurrence_datetime": "",
                        "can_close_early": True, "strike_type": stype,
                        "rules_primary": "If the %s settles %s, the market resolves to Yes." % (title, label),
                        "rules_secondary": "Settlement is based on %s." % src["name"], "category": cat,
                        "tick_size": 1, "fee_waiver_expiration_time": None,
                        "custom_strike": {"front_month_contract": "WBS %dV-ICE" % (close.year % 100),
                                          "strike_date": iso(close)},
                    }
                    if floor is not None:
                        m["floor_strike"] = floor
                    if cap is not None:
                        m["cap_strike"] = cap
                    if status == "settled":
                        m["result"] = "yes" if h32(mt, "r") % 2 else "no"
                        m["expiration_value"] = settled_val
                        m["settlement_ts"] = iso(close + timedelta(minutes=2))
                        m["occurrence_datetime"] = iso(close)
                    self.markets[mt] = m
                    self.event_markets[et].append(mt)
                    live_rec = dict(m)
                    hist_rec = dict(m)
                    if band == "both" and status == "settled":
                        # the live record lags: finalized, no settlement fields (brief section 3)
                        live_rec.update({"status": "finalized", "expiration_value": "", "result": "",
                                         "settlement_ts": "", "occurrence_datetime": ""})
                        if cad == "weekly" and i == 4 and j == 1:
                            live_rec["floor_strike"] = 70.01            # deliberate conflict
                    if band in ("live", "both"):
                        self.live_markets[mt] = live_rec
                    if band in ("both", "hist"):
                        self.hist_markets[mt] = hist_rec
                    hosts = set()
                    if never_traded:
                        pass                                             # 404 everywhere
                    elif cad == "weekly" and i == 7:
                        hosts = {"live"}                                 # archived but served by live
                    elif band == "live":
                        hosts = {"live"}
                    elif band == "both":
                        hosts = {"live", "hist"}
                    else:
                        hosts = {"hist"}
                    self.candles_on[mt] = hosts
        self.live_only_archived = [t for t, m in self.markets.items()
                                   if t not in self.live_markets and self.candles_on[t] == {"live"}]

    # -- candles ------------------------------------------------------------
    def candles(self, ticker: str, start: int, end: int, period: int, host: str = "live") -> List[dict]:
        m = self.markets[ticker]
        t0 = int(datetime.strptime(m["open_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
        t1 = int(datetime.strptime(m["close_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
        step = period * 60
        lo, hi = max(start, t0), min(end, t1, self.now)
        first = (lo // step + 1) * step
        out = []
        ts = first
        while ts <= hi:
            x = h32(ticker, ts)
            b = 5 + x % 60
            a = b + 1 + x % 3
            bid = {"open": b, "high": b + 2, "low": max(0, b - 1), "close": b + 1}
            ask = {"open": a, "high": a + 2, "low": a, "close": a + 1}
            px = {"open": b + 1, "high": a, "low": b, "close": b + 1} if x % 5 == 0 else None
            vol = x % 20 if x % 5 == 0 else 0
            if host == "live":
                # VERIFIED live shape: *_dollars keys, volume_fp / open_interest_fp
                c = {"end_period_ts": ts,
                     "yes_bid": {k + "_dollars": "%.4f" % (v / 100) for k, v in bid.items()},
                     "yes_ask": {k + "_dollars": "%.4f" % (v / 100) for k, v in ask.items()},
                     "price": ({k + "_dollars": "%.4f" % (v / 100) for k, v in px.items()} if px else {}),
                     "volume_fp": "%.2f" % vol, "open_interest_fp": "%.2f" % (x % 500)}
            else:
                # VERIFIED historical shape: bare keys holding decimal-DOLLAR strings,
                # price block with nulls + mean/previous, volume / open_interest as strings
                c = {"end_period_ts": ts,
                     "yes_bid": {k: "%.4f" % (v / 100) for k, v in bid.items()},
                     "yes_ask": {k: "%.4f" % (v / 100) for k, v in ask.items()},
                     "price": ({k: "%.4f" % (v / 100) for k, v in px.items()} if px else
                               {"open": None, "high": None, "low": None, "close": None, "mean": None, "previous": None}),
                     "volume": "%.2f" % vol, "open_interest": "%.2f" % (x % 500)}
            out.append(c)
            ts += step
        return out

    # -- rate limiting --------------------------------------------------------
    def limited(self) -> bool:
        if self.rate_limit <= 0:
            return False
        with self._lock:
            now = time.monotonic()
            while self._recent and now - self._recent[0] > 1.0:
                self._recent.popleft()
            self._recent.append(now)
            return len(self._recent) > self.rate_limit


def page(items: List[dict], q: Dict[str, str], key: str, max_limit: int) -> Tuple[int, dict]:
    try:
        limit = max(1, min(int(q.get("limit", "100")), max_limit))
    except ValueError:
        return 400, {"error": {"message": "invalid limit"}}
    cur = q.get("cursor") or ""
    try:
        off = int(cur) if cur else 0
    except ValueError:
        return 400, {"error": {"message": "invalid cursor"}}
    batch = items[off:off + limit]
    nxt = str(off + limit) if off + limit < len(items) else ""
    return 200, {key: batch, "cursor": nxt}


class Handler(BaseHTTPRequestHandler):
    world: World = None    # type: ignore[assignment]
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):            # noqa: A003
        pass

    def _send(self, status: int, body: Any, headers: Optional[dict] = None) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):                             # noqa: N802
        W = self.world
        u = urllib.parse.urlsplit(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        path = u.path
        with W._lock:
            W.requests += 1
        if path.startswith("/__control/"):
            return self._control(path)
        if W.limited():
            return self._send(429, {"error": {"message": "rate limited"}}, {"Retry-After": "1"})
        W.by_path[path.split("?")[0][:40]] += 1
        if path.startswith(HIST_PREFIX + "/"):
            return self._hist(path[len(HIST_PREFIX):], q)
        if path.startswith(LIVE_PREFIX + "/"):
            return self._live(path[len(LIVE_PREFIX):], q)
        return self._send(404, {"error": {"message": "no such path"}})

    def _control(self, path: str) -> None:
        W = self.world
        if path == "/__control/fail/on":
            W.fail = True
            return self._send(200, {"fail": True})
        if path == "/__control/fail/off":
            W.fail = False
            return self._send(200, {"fail": False})
        if path == "/__control/stats":
            return self._send(200, {"requests": W.requests, "by_path": dict(W.by_path),
                                    "fail": W.fail, "markets": len(W.markets),
                                    "live_only_archived": W.live_only_archived})
        return self._send(404, {"error": "unknown control"})

    def _candles(self, ticker: str, q: Dict[str, str], host: str) -> None:
        W = self.world
        if W.fail:
            return self._send(503, {"error": {"message": "simulated outage"}})
        m = W.markets.get(ticker)
        if not m or host not in W.candles_on.get(ticker, set()):
            return self._send(404, {"error": {"code": "not_found", "message": "market not found"}})
        try:
            s, e, p = int(q["start_ts"]), int(q["end_ts"]), int(q["period_interval"])
        except (KeyError, ValueError):
            return self._send(400, {"error": {"code": "invalid_parameters", "message": "start_ts, end_ts, period_interval required"}})
        if p not in PERIODS:
            return self._send(400, {"error": {"code": "invalid_parameters", "message": "invalid period_interval"}})
        if e < s:
            return self._send(400, {"error": {"code": "invalid_parameters", "message": "end before start"}})
        if (e - s) / (p * 60) > CAP:
            return self._send(400, {"error": {"code": "invalid_parameters", "message": "max candlesticks: %d" % CAP}})
        return self._send(200, {"ticker": ticker, "candlesticks": W.candles(ticker, s, e, p, host)})

    def _live(self, path: str, q: Dict[str, str]) -> None:
        W = self.world
        parts = [p for p in path.split("/") if p]
        if parts == ["exchange", "status"]:
            return self._send(200, {"exchange_active": True, "trading_active": True})
        if parts == ["series"]:
            cat = q.get("category")
            rows = [s for s in W.series if not cat or s["category"] == cat]
            return self._send(200, {"series": rows})
        if len(parts) == 2 and parts[0] == "series":
            s = next((x for x in W.series if x["ticker"] == parts[1]), None)
            return self._send(200, {"series": s}) if s else self._send(404, {"error": "no series"})
        if parts == ["events"]:
            st = q.get("series_ticker")
            status = q.get("status")
            evs = [e for e in W.events.values() if (not st or e["series_ticker"] == st)]
            if status:
                want = set(status.split(","))
                evs = [e for e in evs if any(W.markets[t]["status"] in want for t in W.event_markets[e["event_ticker"]])]
            evs = sorted(evs, key=lambda e: e["strike_date"], reverse=True)
            code, body = page(evs, q, "events", 200)
            if code == 200 and q.get("with_nested_markets") == "true":
                body["events"] = [dict(e, markets=[W.live_markets.get(t, W.markets[t])
                                                   for t in W.event_markets[e["event_ticker"]]])
                                  for e in body["events"]]
            return self._send(code, body)
        if len(parts) == 2 and parts[0] == "events":
            e = W.events.get(parts[1])
            if not e:
                return self._send(404, {"error": {"code": "not_found", "message": "event not found"}})
            body = {"event": e}
            if q.get("with_nested_markets") == "true":
                body["markets"] = [W.live_markets.get(t, W.markets[t]) for t in W.event_markets[parts[1]]]
            return self._send(200, body)
        if parts == ["markets"]:
            st, et, status = q.get("series_ticker"), q.get("event_ticker"), q.get("status")
            ms = [m for m in W.live_markets.values()
                  if (not st or m["ticker"].split("-")[0] == st) and (not et or m["event_ticker"] == et)]
            if status:
                ms = [m for m in ms if m["status"] in set(status.split(","))]
            ms.sort(key=lambda m: (m["close_time"], m["ticker"]), reverse=True)
            code, body = page(ms, q, "markets", 1000)
            return self._send(code, body)
        if len(parts) == 2 and parts[0] == "markets":
            m = W.live_markets.get(parts[1]) or W.markets.get(parts[1])
            return self._send(200, {"market": m}) if m else self._send(404, {"error": "no market"})
        if len(parts) == 3 and parts[0] == "markets" and parts[2] == "orderbook":
            x = h32(parts[1])
            return self._send(200, {"orderbook": {"yes": [[5 + x % 20, 100], [4 + x % 20, 50]],
                                                  "no": [[90 - x % 20, 20], [89 - x % 20, 10]]}})
        if len(parts) == 5 and parts[0] == "series" and parts[2] == "markets" and parts[4] == "candlesticks":
            return self._candles(parts[3], q, "live")
        return self._send(404, {"error": {"code": "not_found", "message": "no such live path %s" % path}})

    def _hist(self, path: str, q: Dict[str, str]) -> None:
        W = self.world
        parts = [p for p in path.split("/") if p]
        if parts == ["markets"]:
            st = q.get("series_ticker")
            ms = [m for m in W.hist_markets.values() if (not st or m["ticker"].split("-")[0] == st)]
            ms.sort(key=lambda m: (m["close_time"], m["ticker"]))
            code, body = page(ms, q, "markets", 200)
            return self._send(code, body)
        if len(parts) == 3 and parts[0] == "markets" and parts[2] == "candlesticks":
            return self._candles(parts[1], q, "hist")
        return self._send(404, {"error": {"code": "not_found", "message": "no such historical path %s" % path}})


class FakeKalshi:
    def __init__(self, port: int = 0, rate_limit: int = 0, now: Optional[int] = None):
        self.world = World(now)
        self.world.rate_limit = rate_limit
        handler = type("H", (Handler,), {"world": self.world})
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def live_base(self) -> str:
        return "http://127.0.0.1:%d%s" % (self.port, LIVE_PREFIX)

    @property
    def hist_base(self) -> str:
        return "http://127.0.0.1:%d%s" % (self.port, HIST_PREFIX)

    def start(self) -> "FakeKalshi":
        self.thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--rate-limit", type=int, default=0)
    a = ap.parse_args(argv)
    srv = FakeKalshi(a.port, a.rate_limit).start()
    print("live  base: %s" % srv.live_base)
    print("hist  base: %s" % srv.hist_base)
    print("markets: %d  events: %d  (ctrl-c to stop)" % (len(srv.world.markets), len(srv.world.events)))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        srv.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
