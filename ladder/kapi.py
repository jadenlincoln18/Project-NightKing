"""Minimal keyless Kalshi client for the ladder study: retry with backoff,
never raises on transient failures, logs with timestamps."""
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = "Mozilla/5.0 (compatible; ladder-study/1.0)"
PAUSE = 0.22  # ~4.5 rps: 9 rps drew 429s on the first live sweep (2026-10-05)
log = logging.getLogger("ladder.kapi")


class Transient(Exception):
    pass


def get(path, params=None, retries=6, timeout=20):
    """GET json. Returns None on 404. Retries 429/5xx/network with backoff; raises
    Transient after `retries` so the caller can pause and resume rather than exit."""
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    delay = 1.0
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read().decode())
            time.sleep(PAUSE)
            return out
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504):
                log.warning("HTTP %s on %s (attempt %d) - backing off %.1fs", e.code, path, attempt + 1, delay)
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            log.warning("%s on %s (attempt %d) - backing off %.1fs", type(e).__name__, path, attempt + 1, delay)
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise Transient(path)


def paged(path, key, params=None, limit=1000):
    params = dict(params or {}, limit=limit)
    out = []
    cursor = None
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
    return out


def cents(v):
    """'0.1200' dollars -> 12.0 cents; None -> None."""
    if v is None or v == "":
        return None
    try:
        return round(float(v) * 100.0, 4)
    except (TypeError, ValueError):
        return None


def setup_logging(path=None):
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)
    if path:
        fh = logging.FileHandler(path)
        fh.setFormatter(fmt)
        root.addHandler(fh)
