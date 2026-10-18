"""Exchange-wide discovery: every event with nested markets, all statuses, into
waves_data/discovery/{events,markets}.parquet, then a scale report of the numeric
ladders by category (brief section 3: report the scale before pulling).

    python3 -m waves.discover            # ~10-20 min, resumable per status
    python3 -m waves.discover --report   # only re-print the scale report

A numeric ladder = an event with >= 3 markets whose strike_type is greater / less /
between (or the _or_equal variants). `mutually_exclusive` on the event is kept as the
definitive range/cumulative flag. Candle requests are estimated at one request per
5,000 minutes of each market's open-to-close life (the API cap).
"""
import argparse
import datetime as dt
import json
import logging
import math
import os
import sys
import time
from pathlib import Path

import pandas as pd

from ladder import kapi

log = logging.getLogger("waves.discover")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "waves_data" / "discovery"
NUMERIC = ("greater", "less", "between", "greater_or_equal", "less_or_equal")
STATUSES = ("open", "closed", "settled")


def _epoch(s):
    try:
        return int(pd.Timestamp(s).timestamp()) if s else None
    except Exception:  # noqa: BLE001
        return None


def scan(status, out):
    """Page the whole listing for one status; checkpoint the cursor so a restart resumes."""
    ck = out / (".cursor_%s.json" % status)
    part = out / ("raw_%s.jsonl" % status)
    state = json.loads(ck.read_text()) if ck.exists() else {"cursor": None, "pages": 0, "events": 0, "done": False}
    if state.get("done"):
        log.info("%s: already complete (%d events)", status, state["events"])
        return
    f = open(part, "a")
    cursor = state["cursor"]
    while True:
        params = {"status": status, "limit": 200, "with_nested_markets": "true"}
        if cursor:
            params["cursor"] = cursor
        try:
            d = kapi.get("/events", params)
        except kapi.Transient:
            log.warning("%s: transient failure after retries - pausing 120 s, then resuming", status)
            time.sleep(120)
            continue
        evs = (d or {}).get("events") or []
        for e in evs:
            f.write(json.dumps(e) + "\n")
        f.flush()
        state["pages"] += 1; state["events"] += len(evs)
        cursor = (d or {}).get("cursor")
        state["cursor"] = cursor
        if not cursor or not evs:
            state["done"] = True
        ck.write_text(json.dumps(state))
        if state["pages"] % 25 == 0 or state["done"]:
            log.info("%s: %d pages, %d events%s", status, state["pages"], state["events"], " - done" if state["done"] else "")
        if state["done"]:
            break
    f.close()


def build_tables(out):
    ev_rows, mk_rows = [], []
    for status in STATUSES:
        part = out / ("raw_%s.jsonl" % status)
        if not part.exists():
            continue
        for line in open(part):
            e = json.loads(line)
            ms = e.get("markets") or []
            ev_rows.append(dict(event_ticker=e.get("event_ticker"), series=e.get("series_ticker"), category=e.get("category"),
                                title=e.get("title"), sub_title=e.get("sub_title"), mutually_exclusive=e.get("mutually_exclusive"),
                                strike_period=e.get("strike_period"), n_markets=len(ms), listing_status=status))
            for m in ms:
                mk_rows.append(dict(ticker=m.get("ticker"), event_ticker=e.get("event_ticker"), series=e.get("series_ticker"), category=e.get("category"),
                                    strike_type=m.get("strike_type"), floor_strike=m.get("floor_strike"), cap_strike=m.get("cap_strike"),
                                    yes_sub_title=m.get("yes_sub_title"), status=m.get("status"), result=m.get("result"),
                                    open_time=m.get("open_time"), close_time=m.get("close_time"), expiration_time=m.get("expiration_time"),
                                    open_epoch=_epoch(m.get("open_time")), close_epoch=_epoch(m.get("close_time")),
                                    volume=float(m.get("volume_fp") or 0), open_interest=float(m.get("open_interest_fp") or 0),
                                    yes_bid=kapi.cents(m.get("yes_bid_dollars")), yes_ask=kapi.cents(m.get("yes_ask_dollars"))))
    ev = pd.DataFrame(ev_rows).drop_duplicates("event_ticker", keep="last")
    mk = pd.DataFrame(mk_rows).drop_duplicates("ticker", keep="last")
    num = mk[mk.strike_type.isin(NUMERIC)].groupby("event_ticker").size()
    ev["n_numeric"] = ev.event_ticker.map(num).fillna(0).astype(int)
    ev["is_ladder"] = ev.n_numeric >= 3
    ev.to_parquet(out / "events.parquet", index=False)
    mk.to_parquet(out / "markets.parquet", index=False)
    return ev, mk


def report(out, commodity_series):
    ev = pd.read_parquet(out / "events.parquet"); mk = pd.read_parquet(out / "markets.parquet")
    lad = ev[ev.is_ladder]
    m = mk[mk.event_ticker.isin(lad.event_ticker)].copy()
    m["life_min"] = ((m.close_epoch.fillna(0) - m.open_epoch.fillna(0)).clip(lower=0) / 60.0)
    now = time.time()
    m.loc[m.close_epoch > now, "life_min"] = ((now - m.open_epoch) / 60.0).clip(lower=0)
    m["requests"] = (m.life_min / 5000.0).apply(math.ceil).clip(lower=1)
    m["in_store"] = m.series.isin(commodity_series)
    lines = ["# Discovery scale report (%s)" % dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), ""]
    lines.append("Events listed: %s (open %s, closed %s, settled %s); numeric ladders (>= 3 strike markets): %s events in %s series, %s markets."
                 % ("{:,}".format(len(ev)), "{:,}".format((ev.listing_status == "open").sum()), "{:,}".format((ev.listing_status == "closed").sum()), "{:,}".format((ev.listing_status == "settled").sum()),
                    "{:,}".format(len(lad)), "{:,}".format(lad.series.nunique()), "{:,}".format(len(m))))
    g = m.groupby("category").agg(series=("series", "nunique"), events=("event_ticker", "nunique"), markets=("ticker", "size"), requests=("requests", "sum"),
                                  life_days_median=("life_min", lambda s: s.median() / 1440), volume=("volume", "sum"), already_in_store=("in_store", "mean")).sort_values("requests", ascending=False)
    g["hours_at_4.5rps"] = g.requests / 4.5 / 3600
    lines.append("")
    lines.append(g.round(2).to_markdown())
    lines.append("")
    lines.append("Per series (ladders only, top 60 by requests):")
    gs = m.groupby(["category", "series"]).agg(events=("event_ticker", "nunique"), markets=("ticker", "size"), requests=("requests", "sum"), life_days_median=("life_min", lambda s: s.median() / 1440), volume=("volume", "sum"), in_store=("in_store", "max")).sort_values("requests", ascending=False)
    lines.append(gs.head(60).round(1).to_markdown())
    me = lad.groupby("category").mutually_exclusive.mean()
    lines.append("")
    lines.append("Share of ladder events that are mutually exclusive (range ladders), by category: " + ", ".join("%s %.0f%%" % (k, 100 * v) for k, v in me.items()))
    txt = "\n".join(lines)
    (out / "SCALE.md").write_text(txt)
    print(txt)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    kapi.setup_logging(str(out / "discover.log"))
    if not a.report:
        for st in STATUSES:
            scan(st, out)
        ev, mk = build_tables(out)
        log.info("tables: %d events, %d markets, %d ladders", len(ev), len(mk), int(ev.is_ladder.sum()))
    from ladder.store import list_series
    report(out, set(list_series()))


if __name__ == "__main__":
    main()
