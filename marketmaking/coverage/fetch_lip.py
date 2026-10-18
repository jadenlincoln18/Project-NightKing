"""Snapshot Kalshi's retail Liquidity Incentive Program (LIP) into a dated file.

The second coverage channel. The LPP (marketmaking/lpp/) is the *professional*
designated-provider list, scraped from a help-centre page. This is the *retail*
one: a keyless, public endpoint that pays per-market rewards to anyone who
quotes inside the target.

    GET https://api.elections.kalshi.com/trade-api/v2/incentive_programs

Quirks established in phase 0 and not re-litigated here:

  * The endpoint IGNORES series_ticker / market_ticker filters. You cannot ask
    it about one series; you have to page the whole thing and filter locally.
  * It never returns a terminating cursor. `next_cursor` keeps coming back
    non-empty forever. So "no more data" has to be inferred -- we stop when a
    page yields no program id we have not already seen, or the cursor repeats,
    or we hit the page cap.
  * Because of that, LIP *absence* for a series is a large-sample observation,
    never a proof. Every claim downstream is worded that way.
  * `period_reward` is in centi-cents ($0.0001). 3000000 -> $300.00 per period.

Output: lip_<date>.json next to this file, containing every deduped program
row plus pagination diagnostics (how we stopped, how many pages, whether the
cursor ever repeated) so a reader can judge how exhaustive the sweep was.

Re-running on a later date writes a new dated file; old ones are kept, same as
the LPP snapshots, because the program list moves.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
URL = "https://api.elections.kalshi.com/trade-api/v2/incentive_programs"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36")
PAGE_LIMIT = 200          # server max observed
MAX_PAGES = 3000          # the 500-page cap in the brief did not saturate
SLEEP = 0.16              # ~6.2 req/s, under the ~7/s ceiling

# Market tickers are <SERIES>-<EVENT SUFFIX>-<STRIKE>. The series is the part
# before the first hyphen that is followed by a date-ish or numeric suffix;
# in practice Kalshi series tickers never contain a hyphen, so split-on-first
# is correct and is what the rest of the repo assumes.
SERIES_RE = re.compile(r"^([A-Z0-9]+)-")


def series_of(market_ticker: str) -> str:
    if not market_ticker:
        return ""
    m = SERIES_RE.match(market_ticker)
    return m.group(1) if m else market_ticker


def _get(url: str, retries: int = 4) -> dict:
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:          # noqa: PERF203
            last = e
            if e.code == 429:
                wait = float(e.headers.get("Retry-After") or (2 ** attempt))
                time.sleep(wait)
                continue
            if 500 <= e.code < 600:
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError("GET failed after %d attempts: %r" % (retries, last))


def sweep(max_pages: int = MAX_PAGES) -> dict:
    seen: dict[str, dict] = {}
    cursors: list[str] = []
    first_page_of_series: dict[str, int] = {}
    series_curve: list[list[int]] = []   # [page, n_series, n_programs] every 50 pages
    cursor = ""
    pages = 0
    stop = "page_cap"
    empty_streak = 0
    for pages in range(1, max_pages + 1):
        url = "%s?limit=%d" % (URL, PAGE_LIMIT)
        if cursor:
            url += "&cursor=" + urllib.parse.quote(cursor, safe="")
        payload = _get(url)
        rows = payload.get("incentive_programs") or []
        nxt = payload.get("next_cursor") or ""
        new = 0
        for row in rows:
            pid = row.get("id")
            if pid and pid not in seen:
                seen[pid] = row
                new += 1
                s = series_of(row.get("market_ticker", ""))
                first_page_of_series.setdefault(s, pages)
        if pages % 50 == 0:
            series_curve.append([pages, len(first_page_of_series), len(seen)])
        if not rows:
            stop = "empty_page"
            break
        if new == 0:
            empty_streak += 1
            if empty_streak >= 2:
                stop = "no_new_ids"
                break
        else:
            empty_streak = 0
        if not nxt:
            stop = "null_cursor"
            break
        if nxt in cursors:
            stop = "cursor_repeat"
            break
        cursors.append(nxt)
        cursor = nxt
        time.sleep(SLEEP)
    series_curve.append([pages, len(first_page_of_series), len(seen)])
    last_new_series_page = max(first_page_of_series.values()) if first_page_of_series else 0
    return {"programs": list(seen.values()), "pages": pages, "stop_reason": stop,
            "cursor_repeated": stop == "cursor_repeat",
            "distinct_cursors": len(set(cursors)),
            "last_page_that_revealed_a_new_series": last_new_series_page,
            "series_discovery_curve": series_curve}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES)
    a = ap.parse_args()

    t0 = time.time()
    res = sweep(a.max_pages)
    progs = res.pop("programs")
    for p in progs:
        p["series"] = series_of(p.get("market_ticker", ""))
    progs.sort(key=lambda p: (p.get("series", ""), p.get("market_ticker", ""), p.get("id", "")))

    by_series: dict[str, dict] = {}
    for p in progs:
        s = p["series"]
        e = by_series.setdefault(s, {"n_programs": 0, "n_markets": 0,
                                     "period_reward_total_usd": 0.0,
                                     "period_reward_per_market_usd": [],
                                     "descriptions": set(), "types": set()})
        e["n_programs"] += 1
        usd = (p.get("period_reward") or 0) / 10000.0
        e["period_reward_total_usd"] += usd
        e["period_reward_per_market_usd"].append(usd)
        if p.get("incentive_description"):
            e["descriptions"].add(p["incentive_description"])
        if p.get("incentive_type"):
            e["types"].add(p["incentive_type"])
    for s, e in by_series.items():
        mts = {p["market_ticker"] for p in progs if p["series"] == s}
        e["n_markets"] = len(mts)
        rs = sorted(e.pop("period_reward_per_market_usd"))
        e["period_reward_median_usd"] = rs[len(rs) // 2] if rs else 0.0
        e["period_reward_total_usd"] = round(e["period_reward_total_usd"], 4)
        e["descriptions"] = sorted(e["descriptions"])
        e["types"] = sorted(e["types"])

    out = {
        "snapshot_date": a.date,
        "source_url": URL,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 1),
        "pagination": res,
        "exhaustive": False,
        "exhaustiveness_note": (
            "The endpoint never returns a terminating cursor, so this sweep "
            "stopped on %r. Treat LIP absence as a large-sample observation, "
            "not proof." % res["stop_reason"]),
        "n_programs": len(progs),
        "n_series": len(by_series),
        "by_series": dict(sorted(by_series.items())),
        "programs": progs,
    }
    p = HERE / ("lip_%s.json" % a.date)
    p.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("wrote %s" % p)
    print("programs=%d series=%d pages=%d stop=%s"
          % (len(progs), len(by_series), res["pages"], res["stop_reason"]))


if __name__ == "__main__":
    main()
