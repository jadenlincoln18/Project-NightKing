#!/usr/bin/env python3
"""
probe.py - resolve every UNVERIFIED item in the handoff brief by asking the API.

Nothing here is assumed. Each section queries, prints what it found, and the
findings land in <out>/probe.json, which collect.py reads before pulling.
Do not run collect.py until you have looked at this output.

Sections (brief section 4, in order)
  env         python / pandas / pyarrow / certificate store / hosts reachable
  categories  which categories exist, series per category
  series      discovered series (Commodities + keyword hits elsewhere)
  events      per series: count, paging sanity, mutually_exclusive, settlement
              sources, month histogram, CADENCE (15min/hourly/daily/weekly/...)
  markets     per series: live vs historical market counts, ticker formats
  hosts       an archived and a recent market on BOTH hosts (section 3 says the
              routing is counterintuitive - so we measure it)
  candles     the per-request cap (expect 400 "max candlesticks: 5000"), the
              field style (*_dollars), the exact first candle
  period      which period_interval values the API accepts
  rate        one bounded burst to find where 429s begin
  gap         months with no events, per series, and who covers the KXWTIW gap
  estimate    requests / hours by cadence group - the numbers the confirm gate
              in collect.py shows

Usage
  python3 probe.py                       # everything, writes data/probe.json
  python3 probe.py --series KXWTIW,KXWTI # only these series (faster)
  python3 probe.py --skip-rate           # no 429 burst
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import kalshi_common as kc
from kalshi_common import (Client, CapHolder, log, now_iso, parse_ticker, iso_to_epoch,
                           fmt_int)

WTI_HINT = "WTI"


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def month_of(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m") if dt else None


def months_between(a: str, b: str) -> List[str]:
    y, m = int(a[:4]), int(a[5:7])
    y2, m2 = int(b[:4]), int(b[5:7])
    out = []
    while (y, m) <= (y2, m2):
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------

def probe_categories(client: Client) -> Dict[str, Any]:
    section("CATEGORIES - which exist, and how many series each")
    out: Dict[str, Any] = {"no_category": None, "candidates": OrderedDict(), "observed": {},
                           "tags": {}}
    all_series: Dict[str, dict] = {}

    r = client.series()
    rows = (r.json or {}).get("series") if isinstance(r.json, dict) else None
    out["no_category"] = {"http": r.status, "n": len(rows or [])}
    print("GET /series (no category)      -> HTTP %s, %s series" % (r.status, len(rows or [])))
    for s in rows or []:
        if s.get("ticker"):
            all_series.setdefault(s["ticker"], s)

    for cat in kc.CANDIDATE_CATEGORIES:
        r = client.series(category=cat)
        rows = (r.json or {}).get("series") if isinstance(r.json, dict) else None
        n = len(rows or [])
        out["candidates"][cat] = {"http": r.status, "n": n}
        print("GET /series?category=%-24s -> HTTP %s, %4d series" % (cat, r.status, n))
        for s in rows or []:
            if s.get("ticker"):
                ex = all_series.get(s["ticker"])
                if ex is None:
                    all_series[s["ticker"]] = s
                elif not ex.get("category"):
                    ex["category"] = cat
                if not all_series[s["ticker"]].get("category"):
                    all_series[s["ticker"]]["category"] = cat

    cats = Counter(str(s.get("category") or "") for s in all_series.values())
    out["observed"] = dict(cats.most_common())
    tags = Counter(str(t) for s in all_series.values() for t in (s.get("tags") or []))
    out["tags"] = dict(tags.most_common(60))
    freq = Counter(str(s.get("frequency") or "") for s in all_series.values())
    out["frequency_values"] = dict(freq.most_common())
    print("\nobserved category field values: %s" % json.dumps(out["observed"]))
    print("observed frequency field values: %s" % json.dumps(out["frequency_values"]))
    print("total distinct series discovered: %d" % len(all_series))
    return {"summary": out, "all": [
        {"ticker": s.get("ticker"), "title": s.get("title"), "category": s.get("category"),
         "frequency": s.get("frequency"), "tags": s.get("tags")}
        for s in all_series.values()]}


def probe_events(client: Client, tk: str, title: str, frequency: Any) -> Dict[str, Any]:
    pr = client.events(tk, nested=False)
    evs = pr.items
    dts = [kc.event_datetime(e) for e in evs]
    months = Counter(month_of(d) for d in dts if d)
    me = Counter()
    for e in evs:
        v = e.get("mutually_exclusive")
        me["true" if v is True else "false" if v is False else "missing"] += 1
    srcs = Counter()
    for e in evs:
        for s in (e.get("settlement_sources") or []):
            if isinstance(s, dict):
                srcs["name=%s | url=%s" % (s.get("name"), s.get("url"))] += 1
            else:
                srcs[str(s)] += 1
    hint = kc.cadence_hint(tk, title, frequency)
    cad = kc.classify_cadence(dts, hint)
    dated = sorted(d for d in dts if d)
    out = {
        "n": len(evs), "pages": pr.pages, "ended_cleanly": pr.ended_cleanly,
        "http": pr.last_status, "truncation_warning": pr.truncation_warning,
        "first": dated[0].strftime("%Y-%m-%d") if dated else None,
        "last": dated[-1].strftime("%Y-%m-%d") if dated else None,
        "n_dated": len(dated),
        "months": dict(sorted(months.items())),
        "mutually_exclusive": dict(me),
        "settlement_sources": [k for k, _ in srcs.most_common(8)],
        "cadence": cad,
        "sample_event_tickers": [e.get("event_ticker") for e in evs[:3]] +
                                [e.get("event_ticker") for e in evs[-2:]],
        "event_keys": sorted({k for e in evs[:50] for k in e.keys()}),
    }
    return out


def probe_markets(client: Client, tk: str, nested_n: Optional[int] = None) -> Dict[str, Any]:
    live = client.markets_live(series=tk)
    hist = client.markets_hist(tk)
    lt = {m.get("ticker") for m in live.items if m.get("ticker")}
    ht = {m.get("ticker") for m in hist.items if m.get("ticker")}
    fmts = Counter(parse_ticker(t)["format"] for t in (lt | ht))
    statuses_live = Counter(str(m.get("status")) for m in live.items)
    statuses_hist = Counter(str(m.get("status")) for m in hist.items)
    allm = {}
    for m in hist.items + live.items:          # live wins for the sample; merge is collect's job
        if m.get("ticker"):
            allm[m["ticker"]] = m
    lifetimes = []
    for m in allm.values():
        t0, t1 = iso_to_epoch(m.get("open_time")), iso_to_epoch(m.get("close_time"))
        if t0 and t1 and t1 > t0:
            lifetimes.append((t1 - t0) / 60.0)
    settled = [m for m in allm.values()
               if str(m.get("status")) in ("settled", "finalized") and iso_to_epoch(m.get("close_time"))]
    settled.sort(key=lambda m: iso_to_epoch(m.get("close_time")) or 0)
    # a never-traded market 404s everywhere and says nothing about routing:
    # prefer the oldest settled market that has volume
    traded = [m for m in settled
              if (kc.to_float(m.get("volume_fp") if "volume_fp" in m else m.get("volume")) or 0) > 0]
    if traded:
        settled = traded
    newest = sorted([m for m in allm.values() if iso_to_epoch(m.get("close_time"))],
                    key=lambda m: iso_to_epoch(m.get("close_time")) or 0)
    reqs = {}
    for period in kc.PERIODS:
        reqs[str(period)] = sum(kc.estimate_requests(int(x * 60), period) for x in lifetimes)
    return {
        "live": {"n": len(live.items), "pages": live.pages, "ended_cleanly": live.ended_cleanly,
                 "http": live.last_status, "truncation_warning": live.truncation_warning,
                 "statuses": dict(statuses_live)},
        "historical": {"n": len(hist.items), "pages": hist.pages,
                       "ended_cleanly": hist.ended_cleanly, "http": hist.last_status,
                       "truncation_warning": hist.truncation_warning,
                       "statuses": dict(statuses_hist)},
        "union": len(lt | ht), "both": len(lt & ht), "only_live": len(lt - ht),
        "only_hist": len(ht - lt),
        "nested_markets": nested_n,
        "live_matches_nested": (None if nested_n is None else len(lt) >= nested_n),
        "ticker_formats": dict(fmts),
        "lifetime_minutes_median": round(statistics.median(lifetimes), 1) if lifetimes else None,
        "requests_by_period": reqs,
        "oldest_settled": settled[0].get("ticker") if settled else None,
        "oldest_settled_close": settled[0].get("close_time") if settled else None,
        "newest": newest[-1].get("ticker") if newest else None,
        "newest_close": newest[-1].get("close_time") if newest else None,
        "open_now": [m.get("ticker") for m in allm.values()
                     if str(m.get("status")) in ("open", "active")][:5],
        "market_keys": sorted({k for m in list(allm.values())[:50] for k in m.keys()}),
        "custom_strike_keys": sorted({k for m in allm.values()
                                      if isinstance(m.get("custom_strike"), dict)
                                      for k in m["custom_strike"].keys()}),
        "_markets": allm,       # stripped before writing; used by later sections
    }


def probe_hosts(client: Client, series: str, archived: Optional[dict], recent: Optional[dict]
                ) -> Dict[str, Any]:
    section("HOSTS - does an archived market answer on live? does a recent one on historical?")
    out: Dict[str, Any] = {"series": series}
    for label, m in (("archived_market", archived), ("recent_market", recent)):
        if not m:
            out[label] = None
            print("%-16s no candidate market" % label)
            continue
        t1 = iso_to_epoch(m.get("close_time")) or int(time.time())
        t1 = min(t1, int(time.time()))
        t0 = t1 - 86400
        rec: Dict[str, Any] = {"ticker": m.get("ticker"), "status": m.get("status"),
                               "close_time": m.get("close_time"), "window": [t0, t1]}
        for host in ("live", "historical"):
            r = client.candles(host, series, m["ticker"], t0, t1, 60)
            cs = (r.json or {}).get("candlesticks") if isinstance(r.json, dict) else None
            rows = len(cs or []) if cs is not None else None
            rec[host] = {"http": r.status, "rows": rows, "body": (r.text or "")[:120] if not r.ok else None}
            style = None
            if cs:
                c0 = cs[0]
                style = kc.candle_field_style(c0)
                parsed = kc.candle_row(c0)
                rec[host].update({"field_style": style, "first_candle": c0,
                                  "parsed_bid_close": parsed["yes_bid_close"],
                                  "parsed_ask_close": parsed["yes_ask_close"]})
                out.setdefault("field_style_by_host", {})[host] = style
            print("%-16s %-34s %-10s -> HTTP %s  rows=%s%s" % (
                label, m.get("ticker"), host, r.status, rows,
                ("  field style: %s (bid_close=%s ask_close=%s cents)" % (
                    style, rec[host]["parsed_bid_close"], rec[host]["parsed_ask_close"])) if style else ""))
            if style == "unknown":
                print("  !! unrecognised candle shape on the %s host: %s" % (host, json.dumps(cs[0])[:200]))
        out[label] = rec
    styles = set(out.get("field_style_by_host", {}).values())
    if len(styles) > 1:
        print("note: the two hosts serve DIFFERENT candle shapes %s - both are parsed to cents"
              % sorted(styles))
    return out


def probe_candles(client: Client, series: str, market: Optional[dict], caps: CapHolder
                  ) -> Dict[str, Any]:
    section("CANDLES - per-request cap, field names, first candle")
    out: Dict[str, Any] = {"probe_market": market.get("ticker") if market else None,
                           "cap": caps.cap, "cap_evidence": "default (unverified this run)",
                           "cap_tests": [], "field_style": None, "keys": None,
                           "block_keys": {}, "first_candle": None, "legal_window": None}
    if not market:
        print("no market available to probe candles")
        return out
    tk = market["ticker"]
    now = int(time.time())
    end = min(iso_to_epoch(market.get("close_time")) or now, now)
    observed = None
    for minutes in (6000, 12000):
        r = client.candles("live", series, tk, end - minutes * 60, end, 1)
        n = kc.parse_cap_error(r.text)
        rows = len((r.json or {}).get("candlesticks") or []) if isinstance(r.json, dict) else None
        out["cap_tests"].append({"minutes": minutes, "http": r.status, "rows": rows,
                                 "body": (r.text or "")[:160] if not r.ok else None,
                                 "cap_in_body": n})
        print("1-min window of %6d minutes -> HTTP %s  rows=%s  %s"
              % (minutes, r.status, rows, ("cap message: %s" % n) if n else ""))
        if n:
            observed = n
    if observed:
        caps.learn(observed)
        out["cap"] = min(observed, caps.cap)
        out["cap_evidence"] = "HTTP 400 'max candlesticks: %d'" % observed
    elif out["cap_tests"] and out["cap_tests"][0]["http"] == 200:
        out["cap_evidence"] = ("6000-minute 1-min request returned 200 - cap is >= 6000 or the "
                               "market had fewer candles; keeping %d as the safe chunk" % caps.cap)
    print("cap used by collect.py: %d   (%s)" % (out["cap"], out["cap_evidence"]))

    legal = min(4000, max(60, out["cap"] - 100))
    r = client.candles("live", series, tk, end - legal * 60, end, 1)
    cs = (r.json or {}).get("candlesticks") if isinstance(r.json, dict) else None
    out["legal_window"] = {"minutes": legal, "http": r.status, "rows": len(cs or [])}
    print("legal %d-minute window -> HTTP %s rows=%s" % (legal, r.status, len(cs or [])))
    if cs:
        c0 = cs[0]
        out["first_candle"] = c0
        out["keys"] = sorted(c0.keys())
        out["block_keys"] = {b: sorted(c0[b].keys()) if isinstance(c0.get(b), dict) else None
                             for b in ("yes_bid", "yes_ask", "price")}
        out["field_style"] = kc.candle_field_style(c0)
        row = kc.candle_row(c0)
        print("first candle keys : %s" % out["keys"])
        print("yes_bid keys      : %s" % out["block_keys"].get("yes_bid"))
        print("field style       : %s" % out["field_style"])
        print("parsed (cents)    : bid_close=%s ask_close=%s volume=%s"
              % (row["yes_bid_close"], row["yes_ask_close"], row["volume"]))
        if row["yes_bid_close"] is None and row["yes_ask_close"] is None:
            print("  !! PARSER RETURNED NULL BID AND ASK - the collector would store nothing "
                  "useful. Raw block: %s" % json.dumps(c0)[:300])
    else:
        print("no candles in the legal window - field style unverified this run")
    return out


def probe_periods(client: Client, series: str, market: Optional[dict]) -> Dict[str, Any]:
    section("PERIOD_INTERVAL - which values are accepted")
    out: Dict[str, Any] = {}
    if not market:
        print("no market to probe")
        return out
    tk = market["ticker"]
    now = int(time.time())
    end = min(iso_to_epoch(market.get("close_time")) or now, now)
    for p in (1, 5, 15, 30, 60, 240, 1440):
        r = client.candles("live", series, tk, end - 4000 * 60, end, p)
        rows = len((r.json or {}).get("candlesticks") or []) if isinstance(r.json, dict) else None
        out[str(p)] = {"http": r.status, "rows": rows,
                       "body": (r.text or "")[:100] if not r.ok else None}
        print("period_interval=%-5d -> HTTP %s rows=%s %s"
              % (p, r.status, rows, (r.text or "")[:80] if not r.ok else ""))
    return out


def probe_rate(live_base: str, ssl_ctx, n: int = 40) -> Dict[str, Any]:
    section("RATE - one bounded burst of %d requests with no pause" % n)
    c = Client(live_base=live_base, pause=0.0, ssl_ctx=ssl_ctx, retries=1)
    t0 = time.monotonic()
    first_429 = None
    retry_after = None
    statuses = Counter()
    for i in range(n):
        r = c.get(live_base + "/exchange/status", retries=1)
        statuses[r.status] += 1
        if r.status == 429 and first_429 is None:
            first_429 = i
            retry_after = kc._retry_after(r.headers) or None
            break
    el = max(1e-6, time.monotonic() - t0)
    sent = sum(statuses.values())
    rps = sent / el
    rec = 0.10 if first_429 is None else max(0.25, round(2.0 / max(rps, 1.0), 2))
    out = {"burst_n": n, "sent": sent, "statuses": dict(statuses), "elapsed_s": round(el, 2),
           "observed_rps": round(rps, 1), "first_429_index": first_429,
           "retry_after": retry_after, "recommended_pause": rec}
    print("sent %d in %.2fs (%.1f rps), statuses=%s, first 429 at index %s, Retry-After=%s"
          % (sent, el, rps, dict(statuses), first_429, retry_after))
    print("recommended --pause for collect.py: %.2f s" % rec)
    return out


def probe_gap(events: Dict[str, Dict[str, Any]], selected: List[dict]) -> Dict[str, Any]:
    section("GAP - months with no events, and WTI family coverage")
    out: Dict[str, Any] = {"missing_months": {}, "wti_family": {}}
    for tk, ev in events.items():
        if not ev.get("first") or not ev.get("last"):
            continue
        rng = months_between(ev["first"][:7], ev["last"][:7])
        missing = [m for m in rng if m not in ev["months"]]
        if missing:
            out["missing_months"][tk] = missing
            print("%-18s %s .. %s  missing %d month(s): %s"
                  % (tk, ev["first"], ev["last"], len(missing),
                     ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else "")))
    wti = [s["ticker"] for s in selected if WTI_HINT in s["ticker"].upper()]
    months = sorted({m for tk in wti for m in events.get(tk, {}).get("months", {})})
    if wti and months:
        table = {}
        for m in months:
            table[m] = {tk: events[tk]["months"].get(m, 0) for tk in wti if tk in events}
        out["wti_family"] = table
        print("\nWTI family events per month:")
        print("%-8s " % "month" + " ".join("%10s" % tk[-10:] for tk in wti if tk in events))
        for m, row in table.items():
            print("%-8s " % m + " ".join("%10d" % row.get(tk, 0) for tk in wti if tk in events))
    gap_note = out["missing_months"].get("KXWTIW")
    if gap_note:
        print("\nKXWTIW missing months: %s" % ", ".join(gap_note))
        others = {}
        for m in gap_note:
            others[m] = {tk: events[tk]["months"].get(m, 0) for tk in wti
                         if tk != "KXWTIW" and tk in events and events[tk]["months"].get(m, 0)}
        out["kxwtiw_gap_covered_by"] = others
        print("covered by other WTI series: %s" % json.dumps(others))
    return out


def build_estimate(selected: List[dict], markets: Dict[str, Dict[str, Any]], cap: int,
                   pause: float) -> Dict[str, Any]:
    section("ESTIMATE - what a full 1-minute pull costs, by cadence group")
    groups: Dict[str, Dict[str, Any]] = {}
    per_series: Dict[str, Any] = {}
    for s in selected:
        tk = s["ticker"]
        mk = markets.get(tk) or {}
        g = s.get("group") or "unknown"
        reqs = (mk.get("requests_by_period") or {}).get("1", 0)
        per_series[tk] = {"group": g, "cadence": s.get("cadence"), "markets": mk.get("union", 0),
                          "requests_by_period": mk.get("requests_by_period") or {},
                          "requests": reqs}
        gg = groups.setdefault(g, {"series": [], "markets": 0, "requests": 0})
        gg["series"].append(tk)
        gg["markets"] += mk.get("union", 0)
        gg["requests"] += reqs
    per_req = pause + 0.25                         # pause + typical latency, 1 worker
    print("%-10s %7s %10s %10s %8s  %s" % ("group", "series", "markets", "requests", "hours", "(1 worker, pause %.2fs)" % pause))
    order = ["intraday", "daily", "weekly", "monthly", "longer", "unknown"]
    for g in order + [x for x in groups if x not in order]:
        if g not in groups:
            continue
        gg = groups[g]
        gg["hours_1_worker"] = round(gg["requests"] * per_req / 3600.0, 1)
        flag = "   <- excluded by default (--include-intraday)" if g == "intraday" else ""
        print("%-10s %7d %10s %10s %8.1f%s" % (g, len(gg["series"]), fmt_int(gg["markets"]),
                                               fmt_int(gg["requests"]), gg["hours_1_worker"], flag))
    print("\nper series:")
    print("%-18s %-9s %-8s %9s %9s" % ("series", "group", "cadence", "markets", "requests"))
    for tk, v in sorted(per_series.items(), key=lambda kv: -kv[1]["requests"]):
        print("%-18s %-9s %-8s %9s %9s" % (tk, v["group"], v["cadence"], fmt_int(v["markets"]),
                                          fmt_int(v["requests"])))
    return {"period": 1, "cap": cap, "pause": pause, "seconds_per_request_assumed": per_req,
            "groups": groups, "series": per_series}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data")
    ap.add_argument("--live-base", default=kc.LIVE)
    ap.add_argument("--hist-base", default=kc.HIST)
    ap.add_argument("--pause", type=float, default=kc.DEFAULT_PAUSE)
    ap.add_argument("--series", help="comma-separated tickers to restrict the survey to")
    ap.add_argument("--skip-rate", action="store_true", help="skip the 429 burst")
    ap.add_argument("--rate-n", type=int, default=40)
    ap.add_argument("--max-series", type=int, default=0, help="debug: cap number of series")
    a = ap.parse_args(argv)

    kc.setup_logging()
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    section("ENV")
    ssl_ctx, env = kc.preflight(a.live_base)
    client = Client(a.live_base, a.hist_base, a.pause, ssl_ctx)
    P: Dict[str, Any] = {"version": 2, "at": now_iso(), "env": env,
                         "hosts": {"live": a.live_base, "historical": a.hist_base},
                         "pause_used": a.pause}
    hr = client.get(a.hist_base + "/markets", {"limit": 1})
    P["hosts"]["historical_reachable"] = {"http": hr.status, "body": (hr.text or "")[:100] if not hr.ok else None}
    print("historical host /markets?limit=1 -> HTTP %s" % hr.status)

    cats = probe_categories(client)
    P["categories"] = cats["summary"]
    all_series = cats["all"]
    selected = kc.select_series(all_series)
    if a.series:
        want = {s.strip().upper() for s in a.series.split(",") if s.strip()}
        known = {s["ticker"] for s in selected}
        for tk in sorted(want - known):
            selected.append({"ticker": tk, "title": None, "category": None, "frequency": None,
                             "tags": None, "selected_by": "user"})
        selected = [s for s in selected if s["ticker"] in want]
    if a.max_series:
        selected = selected[:a.max_series]

    section("SERIES - %d selected of %d discovered" % (len(selected), len(all_series)))
    for s in selected:
        print("%-18s %-14s %-40s %s" % (s["ticker"], str(s.get("category"))[:14],
                                        str(s.get("title") or "")[:40], s["selected_by"]))

    section("EVENTS - paging, ladder type, settlement sources, cadence")
    events: Dict[str, Dict[str, Any]] = {}
    print("%-18s %6s %5s %-5s %-10s %-10s %-8s %-6s %s" %
          ("series", "events", "pages", "clean", "first", "last", "cadence", "mutex", "settles on"))
    for s in selected:
        ev = probe_events(client, s["ticker"], s.get("title") or "", s.get("frequency"))
        events[s["ticker"]] = ev
        s["cadence"] = ev["cadence"]["cadence"]
        s["group"] = ev["cadence"]["group"]
        s["cadence_median_minutes"] = ev["cadence"]["median_minutes"]
        s["cadence_hint_conflict"] = ev["cadence"]["hint_conflict"]
        me = ev["mutually_exclusive"]
        mex = "T%d/F%d/?%d" % (me.get("true", 0), me.get("false", 0), me.get("missing", 0))
        warn = ""
        if ev["truncation_warning"]:
            warn += "  !! count is an exact multiple of the page size"
        if not ev["ended_cleanly"]:
            warn += "  !! paging did not end cleanly (HTTP %s)" % ev["http"]
        if ev["cadence"]["hint_conflict"]:
            warn += "  (metadata says %s)" % ev["cadence"]["hint"]
        print("%-18s %6d %5d %-5s %-10s %-10s %-8s %-6s %s%s" %
              (s["ticker"], ev["n"], ev["pages"], ev["ended_cleanly"], ev["first"], ev["last"],
               ev["cadence"]["cadence"], mex,
               (ev["settlement_sources"][0][:40] if ev["settlement_sources"] else "-"), warn))
    P["events"] = events

    # does the unfiltered /events include settled ones? check on one WTI series
    chk_series = next((s["ticker"] for s in selected if s["ticker"] == "KXWTIW"),
                      next((s["ticker"] for s in selected if WTI_HINT in s["ticker"]),
                           selected[0]["ticker"] if selected else None))
    if chk_series:
        settled = client.events(chk_series, nested=False, status="settled")
        unf = events.get(chk_series, {}).get("n", 0)
        P["settled_check"] = {"series": chk_series, "unfiltered_n": unf,
                              "settled_n": len(settled.items), "http": settled.last_status,
                              "settled_lte_unfiltered": len(settled.items) <= unf}
        print("\nsettled-check %s: unfiltered=%d  status=settled=%d  -> unfiltered %s settled events"
              % (chk_series, unf, len(settled.items),
                 "includes" if len(settled.items) <= unf and unf > 0 else "MAY NOT include"))

    section("MARKETS - live /markets vs /historical/markets, per series")
    markets: Dict[str, Dict[str, Any]] = {}
    nested_check_series = chk_series
    print("%-18s %8s %8s %8s %6s %6s  %-24s %s" %
          ("series", "live", "hist", "union", "onlyL", "onlyH", "ticker formats", "warnings"))
    for s in selected:
        tk = s["ticker"]
        nested_n = None
        if tk == nested_check_series:
            nev = client.events(tk, nested=True)
            nested_n = sum(len(e.get("markets") or []) for e in nev.items)
        mk = probe_markets(client, tk, nested_n)
        markets[tk] = mk
        warn = ""
        for host in ("live", "historical"):
            if mk[host]["truncation_warning"]:
                warn += " (%s count is a multiple of page size)" % host
            if not mk[host]["ended_cleanly"] and mk[host]["http"] not in (404,):
                warn += " !!%s paging ended HTTP %s" % (host, mk[host]["http"])
        if nested_n is not None:
            warn += "  nested-events markets=%d live-endpoint=%s" % (
                nested_n, "complete" if mk["live_matches_nested"] else "INCOMPLETE")
        print("%-18s %8d %8d %8d %6d %6d  %-24s %s" %
              (tk, mk["live"]["n"], mk["historical"]["n"], mk["union"], mk["only_live"],
               mk["only_hist"], json.dumps(mk["ticker_formats"]), warn))
    P["markets_endpoint_complete"] = (markets.get(nested_check_series, {}).get("live_matches_nested")
                                      if nested_check_series else None)

    # hosts / candles / periods on a representative series
    rep = next((s["ticker"] for s in selected if s["ticker"] == "KXWTIW"),
               next((s["ticker"] for s in selected if markets[s["ticker"]]["union"] > 0), None))
    caps = CapHolder()
    if rep:
        mk = markets[rep]
        allm = mk["_markets"]
        archived = allm.get(mk["oldest_settled"]) if mk["oldest_settled"] else None
        recent = allm.get(mk["newest"]) if mk["newest"] else None
        P["host_matrix"] = probe_hosts(client, rep, archived, recent)
        active = None
        for t in mk["open_now"]:
            active = allm.get(t)
            if active:
                break
        if not active:
            active = recent
        P["candles"] = probe_candles(client, rep, active, caps)
        P["period_interval"] = probe_periods(client, rep, active)
        # the live style is verified by the candle step; the host matrix may have
        # had no live rows in its one-day window
        if P["candles"].get("field_style"):
            P["host_matrix"].setdefault("field_style_by_host", {}).setdefault(
                "live", P["candles"]["field_style"])
    else:
        P["host_matrix"], P["candles"], P["period_interval"] = None, {"cap": caps.cap}, {}

    P["rate"] = (probe_rate(a.live_base, ssl_ctx, a.rate_n) if not a.skip_rate
                 else {"skipped": True, "recommended_pause": a.pause})
    P["gap"] = probe_gap(events, selected)

    for mk in markets.values():
        mk.pop("_markets", None)
    P["markets"] = markets
    # 429s seen anywhere in this run (paging is where they showed up on the real
    # API, not in the burst) push the recommended pause up
    n429 = client.stats.get("http_429", 0)
    if n429:
        bumped = round(max(P["rate"].get("recommended_pause", a.pause), a.pause * 2), 2)
        print("\n%d throttling responses (429) during this probe at pause %.2fs -> "
              "recommended pause raised to %.2fs" % (n429, a.pause, bumped))
        P["rate"]["throttled_during_probe"] = n429
        P["rate"]["recommended_pause"] = bumped
    # series with neither events nor markets (retired pre-KX tickers) are kept in
    # probe.json but not in the collect list
    empty = [s for s in selected if events.get(s["ticker"], {}).get("n", 0) == 0
             and markets.get(s["ticker"], {}).get("union", 0) == 0]
    selected = [s for s in selected if s not in empty]
    P["series"] = {"all": all_series, "selected": selected,
                   "dropped_empty": [s["ticker"] for s in empty]}
    if empty:
        print("\n%d selected series have no events and no markets (retired tickers) - dropped: %s"
              % (len(empty), ", ".join(s["ticker"] for s in empty)))
    P["estimate"] = build_estimate(selected, markets, caps.cap, P["rate"]["recommended_pause"])
    P["client_stats"] = client.stats

    path = out_dir / "probe.json"
    kc.atomic_write_text(path, json.dumps(P, indent=2, sort_keys=True, default=str))

    section("SUMMARY")
    print("probe.json         : %s" % path)
    print("series selected    : %d  (groups: %s)" % (
        len(selected), json.dumps(Counter(s.get("group") for s in selected))))
    print("candle cap         : %s  (%s)" % (P["candles"].get("cap"), P["candles"].get("cap_evidence")))
    print("candle field style : %s" % P["candles"].get("field_style"))
    hm = P.get("host_matrix") or {}
    for label in ("archived_market", "recent_market"):
        rec = hm.get(label)
        if rec:
            print("%-19s: %s  live=%s hist=%s" % (label, rec["ticker"], rec["live"]["http"], rec["historical"]["http"]))
    print("field style by host: %s" % json.dumps(hm.get("field_style_by_host", {})))
    print("recommended pause  : %s s" % P["rate"].get("recommended_pause"))
    print("requests made      : %s" % fmt_int(client.stats.get("requests", 0)))
    bad = [tk for tk, ev in events.items() if not ev["ended_cleanly"]]
    bad += [tk for tk, mk in markets.items()
            if any(not mk[h]["ended_cleanly"] and mk[h]["http"] != 404 for h in ("live", "historical"))]
    multiples = [tk for tk, mk in markets.items()
                 if any(mk[h]["truncation_warning"] for h in ("live", "historical"))]
    if bad:
        print("!! paging did not end cleanly - review before pulling: %s" % sorted(set(bad)))
    if multiples:
        print("note: %d series have a market count that is an exact multiple of the page size "
              "(%s); paging ended cleanly so this is a coincidence, not the old 8,000 truncation"
              % (len(multiples), ", ".join(sorted(multiples)[:6])))
    print("\nnext: review the output above, then   python3 collect.py --smoke")
    return 0


if __name__ == "__main__":
    sys.exit(main())
