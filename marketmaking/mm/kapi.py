"""Keyless Kalshi client for the marketmaking stack.

Deliberately a separate copy from ladder/kapi.py: ladder/ is read-only to this
project and is under active work elsewhere, so importing it would couple a
14-day continuous run to someone else's edits.

Keyless public market data only. There is no authentication in this module and
no code path to an order endpoint.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from . import config

log = logging.getLogger("mm.kapi")


class Transient(Exception):
    """Raised after retries are exhausted so the caller can pause and resume
    rather than exit. A 14-day run must never die on a transient network fault."""


def get(path: str, params: Optional[dict] = None, retries: int = 6,
        timeout: int = 20, pause: Optional[float] = None) -> Optional[dict]:
    """GET json. None on 404. Retries 429/5xx/network with exponential backoff."""
    url = config.API_BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    delay = 1.0
    pause = config.REQ_PAUSE_S if pause is None else pause
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": config.USER_AGENT, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read().decode())
            if pause:
                time.sleep(pause)
            return out
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504):
                log.warning("HTTP %s on %s (attempt %d) backing off %.1fs",
                            e.code, path, attempt + 1, delay)
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            log.warning("%s on %s (attempt %d) backing off %.1fs",
                        type(e).__name__, path, attempt + 1, delay)
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise Transient(path)


def paged(path: str, key: str, params: Optional[dict] = None, limit: int = 1000) -> List[dict]:
    params = dict(params or {}, limit=limit)
    out: List[dict] = []
    cursor = None
    seen = 0
    while True:
        p = dict(params, cursor=cursor) if cursor else params
        d = get(path, p)
        if not d:
            break
        items = d.get(key) or []
        out.extend(items)
        cursor = d.get("cursor")
        if not cursor or not items:
            break
        seen += 1
        if seen > 500:                      # endpoint known to not terminate (FINDINGS_LIP §6.3)
            log.warning("paged(%s) hit page guard at %d items", path, len(out))
            break
    return out


def cents(v: Any) -> Optional[float]:
    """'0.1200' dollars -> 12.0 cents. None/'' -> None."""
    if v is None or v == "":
        return None
    try:
        return round(float(v) * 100.0, 4)
    except (TypeError, ValueError):
        return None


def open_markets(series: str) -> List[dict]:
    return paged("/markets", "markets", {"series_ticker": series, "status": "open"})


# Measured 2026-10-18: depth=1000 returns HTTP 400, depth=100 returns 200.
# 100 is not a truncation in practice -- the tick is 1c on a 1-99c range, so a
# side cannot hold more than 99 price levels. PROTOCOL §6's "no truncation" is
# satisfied: this is the full book, and `n_*_levels` in the store lets any
# clipping be detected after the fact rather than assumed away.
DEPTH_PARAM = 100


def orderbook(ticker: str) -> Optional[dict]:
    """Full depth, both sides (PROTOCOL §6).

    Returns the raw payload. Kalshi returns `orderbook_fp` (fixed point) and/or
    `orderbook` with `yes_dollars`/`no_dollars` as [price, size] string pairs.
    """
    return get("/markets/%s/orderbook" % ticker, {"depth": DEPTH_PARAM})


def tick_from_price_ranges(pr) -> Optional[float]:
    """Extract tick in cents from a `price_ranges` value.

    Measured shape (2026-10-18) is a *list* of range dicts:
        [{"start": "0.0000", "end": "1.0000", "step": "0.0100"}]
    The dict form is accepted too, since the API has already dropped
    `tick_size` once and may change shape again. Returns the finest step
    present, because the finest step is what invalidates a threshold.
    """
    if pr is None:
        return None
    items = pr if isinstance(pr, list) else [pr]
    steps = []
    for it in items:
        if not isinstance(it, dict):
            continue
        v = it.get("step") or it.get("step_dollars") or it.get("tick_size") \
            or it.get("tick_size_dollars")
        c = cents(v)
        if c is not None and c > 0:
            steps.append(c)
    return min(steps) if steps else None


def parse_book(raw: Optional[dict]) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """-> (yes_levels, no_levels) as [(price_cents, size), ...] sorted best-first.

    Kalshi quotes both sides as *bids*: `yes_dollars` are bids to buy YES,
    `no_dollars` are bids to buy NO. A NO bid at price p is equivalent to a YES
    offer at (100 - p). Conversion to a YES-denominated book is done in store.py
    so the raw structure stays untouched here.
    """
    if not raw:
        return [], []
    ob = raw.get("orderbook_fp") or raw.get("orderbook") or {}
    if not isinstance(ob, dict):
        return [], []

    def side(key_fp: str, key_alt: str) -> List[Tuple[float, float]]:
        lv = ob.get(key_fp)
        if lv is None:
            lv = ob.get(key_alt)
        out: List[Tuple[float, float]] = []
        for item in (lv or []):
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    p, s = item[0], item[1]
                    pc = float(p) * 100.0 if "." in str(p) else float(p)
                    out.append((round(pc, 4), float(s)))
            except (TypeError, ValueError):
                continue
        return out

    yes = side("yes_dollars", "yes")
    no = side("no_dollars", "no")
    yes.sort(key=lambda t: -t[0])
    no.sort(key=lambda t: -t[0])
    return yes, no


def setup_logging(path=None, level=logging.INFO) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)
    if path:
        fh = logging.FileHandler(str(path))
        fh.setFormatter(fmt)
        root.addHandler(fh)
