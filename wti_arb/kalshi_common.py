"""
kalshi_common.py - shared pieces for probe.py / collect.py / verify.py / findings.py

Everything here is deliberately boring: no clever inference, every API quirk
that has bitten us is encoded once and unit-tested. Python 3.9 compatible
(the Mac Mini runs system Python 3.9) - no match statements, no X | Y at
runtime, no dataclass(slots=...).

VERIFIED FACTS ENCODED HERE (see HANDOFF brief, section 3)
  - two hosts: LIVE and HIST. A finalized market can live on either. Always
    try both and record which answered.
  - candlesticks are capped at 5,000 per request; exceeding it is HTTP 400
    with "max candlesticks: 5000". We chunk to the cap AND parse that message
    so a changed cap re-chunks instead of silently storing nothing.
  - OHLC values arrive as {"open_dollars": "0.0100", ...} decimal-dollar
    strings. Cents are derived by * 100. Legacy integer-cent keys ("open")
    are still accepted. Volume is "volume_fp" (decimal string).
  - orderbook is BIDS ONLY on both sides: yes_ask = 100 - no_bid.
  - events carry mutually_exclusive (bool): RANGE vs CUMULATIVE ladders.
  - page until the cursor is empty. Never cap pages.
"""

from __future__ import annotations

import gzip
import json
import logging
import math
import os
import re
import ssl
import statistics
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

LIVE = "https://api.elections.kalshi.com/trade-api/v2"
HIST = "https://external-api.kalshi.com/trade-api/v2/historical"

UA = "Mozilla/5.0 (compatible; nightking-collector/2.0)"
DEFAULT_PAUSE = 0.10            # seconds between requests, ~10 rps
TIMEOUT = 30
DEFAULT_CANDLE_CAP = 5000       # VERIFIED hard cap per candlestick request
PERIODS = (1, 60, 1440)         # VERIFIED accepted period_interval values
MANIFEST_VERSION = 2
PAGE_SOFT_ALARM = 5000          # pages; warn, never stop

COMMODITY_KEYWORDS = (
    "oil", "crude", "wti", "brent", "natgas", "natural gas", "gasoline",
    "gold", "silver", "copper", "platinum", "palladium", "corn", "wheat",
    "soy", "cotton", "coffee", "sugar", "cattle", "lumber", "heating oil",
    "rbob", "propane", "diesel", "cocoa",
)

CANDIDATE_CATEGORIES = [
    "Commodities", "Economics", "Financials", "Climate and Weather",
    "Politics", "Companies", "Crypto", "Science and Technology", "World",
    "Entertainment", "Sports", "Health",
]

# keyword hits outside the Commodities category are only accepted from these
# categories: a "gold" hit in Entertainment is the Golden Globes, not bullion
KEYWORD_CATEGORIES = ("Economics", "Financials", "Climate and Weather")

CADENCE_ORDER = ["15min", "hourly", "daily", "weekly", "monthly", "longer", "unknown"]
INTRADAY = ("15min", "hourly")

log = logging.getLogger("nightking")


def setup_logging(logfile: Optional[str] = None, level: int = logging.INFO) -> None:
    """stderr always; a file too when asked. Timestamps so a nohup log is readable."""
    fmt = logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger("nightking")
    root.setLevel(level)
    root.handlers = []
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(fmt)
    root.addHandler(h)
    if logfile:
        Path(logfile).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(logfile)
        fh.setFormatter(fmt)
        root.addHandler(fh)


# --------------------------------------------------------------------------
# time helpers
# --------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def now_iso_precise() -> str:
    """Microseconds: used for fetch timestamps that break merge ties."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def iso_to_epoch(s: Any) -> Optional[int]:
    """'2026-07-24T14:00:00Z' -> epoch seconds. None on anything odd."""
    if not s or not isinstance(s, str):
        return None
    try:
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def epoch_to_iso(ts: Any) -> Optional[str]:
    try:
        return datetime.fromtimestamp(int(ts), timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError, OverflowError):
        return None


# --------------------------------------------------------------------------
# preflight
# --------------------------------------------------------------------------

CERT_FIX = """
SSL CERTIFICATE STORE IS EMPTY - every HTTPS call would fail with an opaque URLError.

  Python from python.org on macOS ships its own (empty) certificate bundle.
  FIX 1  run Python's certificate installer:
           /Applications/Python\\ 3.x/Install\\ Certificates.command
  FIX 2  pip3 install --upgrade certifi   (this script then uses it automatically)
  FIX 3  use the conda / Homebrew interpreter instead
"""


def ssl_context() -> Tuple[ssl.SSLContext, str]:
    """Default context, or certifi's bundle if the default store is empty.
    Returns (context, note). Exits 2 when neither has any CA."""
    ctx = ssl.create_default_context()
    n = ctx.cert_store_stats().get("x509_ca", 0)
    if n > 0:
        return ctx, "system store: %d CAs" % n
    try:
        import certifi  # type: ignore
        ctx = ssl.create_default_context(cafile=certifi.where())
        n = ctx.cert_store_stats().get("x509_ca", 0)
        if n > 0:
            return ctx, "certifi bundle: %d CAs (%s)" % (n, certifi.where())
    except ImportError:
        pass
    sys.stderr.write(CERT_FIX)
    sys.exit(2)


def preflight(live_base: str = LIVE, require_network: bool = True,
              fetch: Optional[Callable] = None) -> Tuple[ssl.SSLContext, Dict[str, Any]]:
    """Checks the brief's section 8 list before anything else runs."""
    info: Dict[str, Any] = {
        "python": sys.version.split()[0], "executable": sys.executable,
        "platform": sys.platform, "at": now_iso(),
    }
    log.info("python %s  (%s)", info["python"], info["executable"])
    if sys.version_info < (3, 9):
        sys.exit("python >= 3.9 required, got %s" % info["python"])
    try:
        import pandas
        import pyarrow
        info["pandas"] = pandas.__version__
        info["pyarrow"] = pyarrow.__version__
        log.info("pandas %s  pyarrow %s", pandas.__version__, pyarrow.__version__)
    except ImportError as e:
        sys.exit("needs pandas + pyarrow (%s):  pip3 install pandas pyarrow" % e)
    ctx, note = ssl_context()
    info["ssl"] = note
    log.info("ssl %s", note)
    for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "SSL_CERT_FILE"):
        if os.environ.get(k):
            info.setdefault("env", {})[k] = os.environ[k]
            log.info("env %s=%s", k, os.environ[k])
    if require_network:
        c = Client(live_base=live_base, ssl_ctx=ctx, fetch=fetch, pause=0.0)
        r = c.get(live_base + "/exchange/status")
        info["exchange_status"] = {"http": r.status, "body": (r.text or "")[:200]}
        if r.status != 200:
            sys.exit("cannot reach %s/exchange/status -> HTTP %s %s\n"
                     "  (VPN off? run Diagnose.py for the network layer)"
                     % (live_base, r.status, (r.text or "")[:120]))
        log.info("exchange/status -> 200 %s", (r.text or "")[:80])
    return ctx, info


# --------------------------------------------------------------------------
# http
# --------------------------------------------------------------------------

@dataclass
class Resp:
    status: int                     # 0 = network failure
    json: Any = None
    text: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    url: str = ""
    elapsed: float = 0.0

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class RateLimiter:
    """Global min-interval gate. Thread-safe; shared by all workers."""

    def __init__(self, min_interval: float):
        self.min_interval = max(0.0, float(min_interval))
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            delay = self._next - now
            self._next = max(now, self._next) + self.min_interval
        if delay > 0:
            time.sleep(delay)


@dataclass
class PageResult:
    items: List[dict]
    pages: int
    ended_cleanly: bool
    last_status: int
    limit: int

    @property
    def truncation_warning(self) -> bool:
        """An exact multiple of the page size is how the 8,000 bug looked."""
        return bool(self.items) and len(self.items) % self.limit == 0


class Client:
    def __init__(self, live_base: str = LIVE, hist_base: str = HIST,
                 pause: float = DEFAULT_PAUSE, ssl_ctx: Optional[ssl.SSLContext] = None,
                 fetch: Optional[Callable[[str], Resp]] = None,
                 timeout: int = TIMEOUT, retries: int = 3):
        self.live_base = live_base.rstrip("/")
        self.hist_base = hist_base.rstrip("/")
        self.limiter = RateLimiter(pause)
        self.timeout = timeout
        self.retries = retries
        self.fetch = fetch or self._urllib_fetch
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl_ctx or ssl.create_default_context()))
        self.stats: Dict[str, int] = {"requests": 0, "retries": 0, "http_0": 0}
        self._stats_lock = threading.Lock()

    # -- transport -------------------------------------------------------
    def _urllib_fetch(self, url: str) -> Resp:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "application/json"})
        t0 = time.monotonic()
        try:
            with self._opener.open(req, timeout=self.timeout) as r:
                body = r.read().decode("utf-8", "replace")
                return Resp(r.status, _loads(body), body, dict(r.headers), url,
                            time.monotonic() - t0)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:                                    # noqa: BLE001
                pass
            return Resp(e.code, _loads(body), body, dict(e.headers or {}), url,
                        time.monotonic() - t0)
        except Exception as e:                                   # noqa: BLE001
            return Resp(0, None, "%s: %s" % (type(e).__name__, e), {}, url,
                        time.monotonic() - t0)

    def _count(self, key: str) -> None:
        with self._stats_lock:
            self.stats[key] = self.stats.get(key, 0) + 1

    MAX_429 = 8          # throttling waits per request, separate from the 5xx/network budget

    def get(self, url: str, params: Optional[dict] = None,
            retries: Optional[int] = None) -> Resp:
        """One logical request. 429 waits (own budget, growing sleeps) and
        5xx/network retries; other 4xx return immediately WITH the body text
        (the candle-cap message lives there)."""
        full = url + ("?" + urllib.parse.urlencode(params) if params else "")
        n = max(1, self.retries if retries is None else retries)
        attempt = 0
        throttled = 0
        r = Resp(0, None, "not attempted", {}, full)
        while True:
            self.limiter.wait()
            self._count("requests")
            r = self.fetch(full)
            self._count("http_%d" % r.status)
            if r.status == 429:
                throttled += 1
                if throttled > self.MAX_429:
                    log.error("429 x%d on %s - giving up on this request", throttled, _short(full))
                    return r
                wait = max(_retry_after(r.headers), min(30.0, 2.0 * throttled))
                log.warning("429 on %s - sleeping %.1fs (%d/%d)", _short(full), wait,
                            throttled, self.MAX_429)
                self._count("throttled")
                time.sleep(wait)
                continue
            if r.status >= 500 or r.status == 0:
                attempt += 1
                log.warning("HTTP %s on %s (%s) - attempt %d/%d", r.status, _short(full),
                            (r.text or "")[:80], attempt, n)
                if attempt >= n:
                    return r
                self._count("retries")
                time.sleep(0.8 * attempt)
                continue
            if not r.ok:
                log.info("HTTP %s on %s %s", r.status, _short(full), (r.text or "")[:120])
            return r

    # -- paging ----------------------------------------------------------
    def page(self, url: str, params: dict, key: str, limit: int) -> PageResult:
        """Follow `cursor` until it is empty. No page cap - ever."""
        items: List[dict] = []
        cursor: Optional[str] = None
        pages = 0
        last_status = 0
        seen_cursors = set()
        while True:
            p = dict(params)
            p["limit"] = limit
            if cursor:
                p["cursor"] = cursor
            r = self.get(url, p)
            last_status = r.status
            if not r.ok or not isinstance(r.json, dict):
                return PageResult(items, pages, False, last_status, limit)
            pages += 1
            batch = r.json.get(key) or []
            items.extend(batch)
            cursor = r.json.get("cursor") or None
            if pages == PAGE_SOFT_ALARM:
                log.warning("%s: %d pages and still going (%d items) - not stopping",
                            _short(url), pages, len(items))
            if not cursor or not batch:
                return PageResult(items, pages, True, last_status, limit)
            if cursor in seen_cursors:
                log.error("%s: cursor repeated (%s) - stopping to avoid a loop",
                          _short(url), cursor[:16])
                return PageResult(items, pages, False, last_status, limit)
            seen_cursors.add(cursor)

    # -- endpoints -------------------------------------------------------
    def series(self, category: Optional[str] = None, **extra: Any) -> Resp:
        p: Dict[str, Any] = dict(extra)
        if category:
            p["category"] = category
        return self.get(self.live_base + "/series", p or None)

    def events(self, series: str, nested: bool = True, status: Optional[str] = None,
               limit: int = 200) -> PageResult:
        p: Dict[str, Any] = {"series_ticker": series}
        if nested:
            p["with_nested_markets"] = "true"
        if status:
            p["status"] = status
        return self.page(self.live_base + "/events", p, "events", limit)

    def event(self, event_ticker: str, nested: bool = True) -> Resp:
        p = {"with_nested_markets": "true"} if nested else None
        return self.get(self.live_base + "/events/" + event_ticker, p)

    def markets_live(self, series: Optional[str] = None, event_ticker: Optional[str] = None,
                     status: Optional[str] = None, limit: int = 1000) -> PageResult:
        p: Dict[str, Any] = {}
        if series:
            p["series_ticker"] = series
        if event_ticker:
            p["event_ticker"] = event_ticker
        if status:
            p["status"] = status
        pr = self.page(self.live_base + "/markets", p, "markets", limit)
        if not pr.ended_cleanly and pr.last_status == 400 and limit > 200 and not pr.items:
            log.warning("/markets limit=%d rejected (400) - retrying with limit=200", limit)
            pr = self.page(self.live_base + "/markets", p, "markets", 200)
        return pr

    def markets_hist(self, series: str, limit: int = 200) -> PageResult:
        return self.page(self.hist_base + "/markets", {"series_ticker": series},
                         "markets", limit)

    def market(self, ticker: str) -> Resp:
        return self.get(self.live_base + "/markets/" + ticker)

    def orderbook(self, ticker: str, depth: int = 100) -> Resp:
        return self.get(self.live_base + "/markets/%s/orderbook" % ticker, {"depth": depth})

    def candles_url(self, host: str, series: str, ticker: str) -> str:
        if host == "live":
            return "%s/series/%s/markets/%s/candlesticks" % (self.live_base, series, ticker)
        return "%s/markets/%s/candlesticks" % (self.hist_base, ticker)

    def candles(self, host: str, series: str, ticker: str, start: int, end: int,
                period: int) -> Resp:
        return self.get(self.candles_url(host, series, ticker),
                        {"start_ts": int(start), "end_ts": int(end),
                         "period_interval": int(period)})


def _loads(body: str) -> Any:
    try:
        return json.loads(body) if body else None
    except json.JSONDecodeError:
        return None


def _retry_after(headers: Dict[str, str]) -> float:
    for k, v in (headers or {}).items():
        if k.lower() == "retry-after":
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _short(url: str, n: int = 90) -> str:
    u = url.replace("https://", "")
    return u if len(u) <= n else u[:n] + "..."


# --------------------------------------------------------------------------
# value parsing
# --------------------------------------------------------------------------

def to_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def cents(v: Any, dollars: bool) -> Optional[float]:
    """dollars=True: '0.0100' -> 1.0 (cents). dollars=False: 7 -> 7.0 (already cents)."""
    f = to_float(v)
    if f is None:
        return None
    return round(f * 100.0, 4) if dollars else round(f, 4)


OHLC = ("open", "high", "low", "close")


def ohlc(block: Any, prefix: str) -> Dict[str, Optional[float]]:
    """VERIFIED: keys are open_dollars/high_dollars/... as decimal-dollar strings.
    Legacy integer-cent keys (open/high/...) are accepted as a fallback.
    An empty block ({} - e.g. `price` when nothing traded) -> all None."""
    out: Dict[str, Optional[float]] = {"%s_%s" % (prefix, k): None for k in OHLC}
    if not isinstance(block, dict):
        return out
    for k in OHLC:
        if ("%s_dollars" % k) in block:
            out["%s_%s" % (prefix, k)] = cents(block.get("%s_dollars" % k), dollars=True)
        elif k in block:
            v = block.get(k)
            # VERIFIED on the real historical host: bare keys carry decimal-DOLLAR
            # strings ("0.9900"). Only a bare int/float is legacy integer cents.
            # Treating the string as cents stored every archived candle 100x too small.
            out["%s_%s" % (prefix, k)] = cents(v, dollars=isinstance(v, str))
    return out


def candle_field_style(c: Any) -> str:
    """What a raw candle looks like:
         'dollars'       {"close_dollars": "0.0200"}   live host (brief section 3)
         'dollars_bare'  {"close": "0.9900"}           historical host: bare keys, dollar strings
         'cents'         {"close": 2}                  legacy integer cents
         'unknown'       nothing recognisable"""
    if not isinstance(c, dict):
        return "unknown"
    for blk in ("yes_bid", "yes_ask", "price"):
        b = c.get(blk)
        if isinstance(b, dict) and b:
            if any(k.endswith("_dollars") for k in b):
                return "dollars"
            vals = [b[k] for k in OHLC if k in b and b[k] is not None]
            if vals:
                return "dollars_bare" if all(isinstance(v, str) for v in vals) else "cents"
    return "unknown"


def candle_row(c: dict) -> Dict[str, Any]:
    ts = c.get("end_period_ts")
    try:
        ts_i: Optional[int] = int(ts) if ts is not None else None
    except (TypeError, ValueError):
        ts_i = None
    vol = c.get("volume_fp") if "volume_fp" in c else c.get("volume")
    oi = c.get("open_interest_fp") if "open_interest_fp" in c else c.get("open_interest")
    row: Dict[str, Any] = {"ts": ts_i, "volume": to_float(vol), "open_interest": to_float(oi)}
    row.update(ohlc(c.get("yes_bid"), "yes_bid"))
    row.update(ohlc(c.get("yes_ask"), "yes_ask"))
    row.update(ohlc(c.get("price"), "price"))
    return row


CANDLE_COLUMNS = [
    "ts", "dt", "series", "event", "ticker", "bracket", "ladder_kind", "period_min",
    "volume", "open_interest",
    "yes_bid_open", "yes_bid_high", "yes_bid_low", "yes_bid_close",
    "yes_ask_open", "yes_ask_high", "yes_ask_low", "yes_ask_close",
    "price_open", "price_high", "price_low", "price_close",
    "spread", "half_spread", "source",
]
CANDLE_FLOATS = [c for c in CANDLE_COLUMNS
                 if c.startswith(("yes_bid_", "yes_ask_", "price_"))
                 or c in ("volume", "open_interest", "spread", "half_spread")]
CANDLE_INTS = ["ts", "period_min"]
CANDLE_STRINGS = ["series", "event", "ticker", "bracket", "ladder_kind", "source"]
BIDASK_CLOSE = ("yes_bid_close", "yes_ask_close")


def empty_candle_frame():
    import pandas as pd
    df = pd.DataFrame({c: pd.Series(dtype="float64") for c in CANDLE_COLUMNS})
    return coerce_candle_dtypes(df)


def coerce_candle_dtypes(df):
    import pandas as pd
    for c in CANDLE_INTS:
        df[c] = df[c].astype("int64")
    for c in CANDLE_FLOATS:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    for c in CANDLE_STRINGS:
        df[c] = df[c].astype(object)
    df["dt"] = pd.to_datetime(df["ts"], unit="s", utc=True).astype("datetime64[ns, UTC]")
    return df[CANDLE_COLUMNS]


def candles_to_frame(raw: Iterable[dict], series: str, event: str, ticker: str,
                     bracket: str, ladder_kind: str, period: int, source: str):
    """Raw candlesticks -> typed frame. Bid and ask are separate columns; the
    only derived columns are spread/half_spread and they are marked as such.
    Duplicate timestamps (chunk boundaries) keep the last occurrence."""
    import pandas as pd
    recs = []
    dropped = 0
    for c in raw or []:
        if not isinstance(c, dict):
            dropped += 1
            continue
        r = candle_row(c)
        if r["ts"] is None:
            dropped += 1
            continue
        r.update({"series": series, "event": event, "ticker": ticker, "bracket": bracket,
                  "ladder_kind": ladder_kind, "period_min": int(period), "source": source})
        recs.append(r)
    if dropped:
        log.warning("%s: %d candles without a usable end_period_ts dropped", ticker, dropped)
    if not recs:
        return empty_candle_frame()
    df = pd.DataFrame(recs)
    n_dupes = int(df.duplicated("ts", keep="last").sum())
    if n_dupes:
        # the live API hands back one repeated timestamp on open markets; keep
        # the last occurrence and say so, with whether the two rows agreed
        both = df[df.duplicated("ts", keep=False)].sort_values("ts")
        a, b = both.iloc[0], both.iloc[1]
        cols = [c for c in df.columns if c.startswith(("yes_bid_", "yes_ask_", "price_"))]
        identical = bool(all((a[c] == b[c]) or (pd.isna(a[c]) and pd.isna(b[c])) for c in cols))
        log.info("%s: %d duplicate timestamp(s) in the API response, kept the last "
                 "(first at ts=%s, rows identical=%s)", ticker, n_dupes, int(a["ts"]), identical)
    df = df.drop_duplicates("ts", keep="last").sort_values("ts").reset_index(drop=True)
    # DERIVED - never the source of truth; bid/ask stay as stored above
    df["spread"] = df["yes_ask_close"] - df["yes_bid_close"]
    df["half_spread"] = df["spread"] / 2.0
    df = coerce_candle_dtypes(df)
    df.attrs["dupes_dropped"] = n_dupes
    df.attrs["raw_candles"] = len(recs)
    return df


# --------------------------------------------------------------------------
# candle chunking + fetch
# --------------------------------------------------------------------------

CAP_RE = re.compile(r"max\s+candlesticks?\s*[:=]?\s*(\d+)", re.I)


def parse_cap_error(text: Any) -> Optional[int]:
    """'... max candlesticks: 5000' -> 5000."""
    if not text:
        return None
    m = CAP_RE.search(str(text))
    return int(m.group(1)) if m else None


def candle_windows(start: int, end: int, period: int, cap: int = DEFAULT_CANDLE_CAP
                   ) -> List[Tuple[int, int]]:
    """Consecutive (start, end) spans so each holds at most `cap` candles.
    The API counts candles by the requested range, so spans are cap*period
    minutes long. Uses cap-1 candles of margin: an inclusive end boundary
    must never tip a request over the cap."""
    start, end = int(start), int(end)
    if end <= start:
        return []
    span = max(1, (max(2, int(cap)) - 1) * int(period) * 60)
    out: List[Tuple[int, int]] = []
    t = start
    while t < end:
        w1 = min(t + span, end)
        out.append((t, w1))
        t = w1
    return out


def estimate_requests(lifetime_seconds: int, period: int, cap: int = DEFAULT_CANDLE_CAP) -> int:
    if lifetime_seconds <= 0:
        return 0
    return len(candle_windows(0, lifetime_seconds, period, cap))


class CapHolder:
    """Shared, mutable candle cap. Starts at the verified 5,000 and shrinks
    when the API says otherwise. Never grows on its own."""

    def __init__(self, cap: int = DEFAULT_CANDLE_CAP):
        self.cap = int(cap)
        self.observed: Optional[int] = None
        self._lock = threading.Lock()

    def learn(self, n: int) -> bool:
        with self._lock:
            self.observed = n
            if 0 < n < self.cap:
                log.warning("candle cap is %d (was %d) - re-chunking", n, self.cap)
                self.cap = n
                return True
            return False


@dataclass
class CandleResult:
    status: str = "error"            # ok | empty | not_found | error
    fetch_ok: bool = False
    http_live: Optional[int] = None
    http_hist: Optional[int] = None
    source: str = "none"             # live | historical | none
    candles: List[dict] = field(default_factory=list)
    chunks: int = 0
    requests: int = 0
    cap: int = DEFAULT_CANDLE_CAP
    error: Optional[str] = None
    raw: List[dict] = field(default_factory=list)   # per-chunk {host,start,end,status,body}

    @property
    def rows(self) -> int:
        return len(self.candles)


def fetch_market_candles(client: Client, series: str, ticker: str, start: int, end: int,
                         period: int, caps: Optional[CapHolder] = None,
                         hosts: Tuple[str, ...] = ("live", "historical"),
                         keep_raw: bool = True) -> CandleResult:
    """Try each host in order. Classification (this is the bit the old
    manifest got wrong - a network outage must never look like 'never traded'):
        200 on some host, >=1 candle     -> ok        fetch_ok=True
        200 on some host, 0 candles      -> empty     fetch_ok=True
        404 on every host                -> not_found fetch_ok=True
        anything else (0, 4xx, 5xx, ...) -> error     fetch_ok=False
    A 400 carrying 'max candlesticks: N' shrinks the shared cap and re-chunks."""
    caps = caps or CapHolder()
    res = CandleResult(cap=caps.cap)
    start, end = int(start), int(end)
    if end <= start:
        res.status, res.fetch_ok, res.error = "empty", True, "empty time range"
        return res
    errors: List[str] = []
    all_404 = True
    for host in hosts:
        windows = candle_windows(start, end, period, caps.cap)
        got: List[dict] = []
        i = 0
        host_status: Optional[int] = None
        failed = False
        rechunks = 0
        while i < len(windows):
            w0, w1 = windows[i]
            r = client.candles(host, series, ticker, w0, w1, period)
            res.requests += 1
            host_status = r.status
            if keep_raw:
                res.raw.append({"host": host, "start": w0, "end": w1, "status": r.status,
                                "body": r.json if r.json is not None else (r.text or "")[:500]})
            if r.ok and isinstance(r.json, dict):
                got.extend(r.json.get("candlesticks") or [])
                i += 1
                continue
            if r.status == 400:
                n = parse_cap_error(r.text)
                if n and caps.learn(n) and rechunks < 8:
                    rechunks += 1
                    windows = windows[:i] + candle_windows(w0, end, period, caps.cap)
                    continue
            failed = True
            break
        if host == "live":
            res.http_live = host_status
        else:
            res.http_hist = host_status
        if not failed:
            res.status = "ok" if got else "empty"
            res.fetch_ok = True
            res.source = host
            res.candles = got
            res.chunks = len(windows)
            res.cap = caps.cap
            res.error = None
            return res
        if host_status != 404:
            all_404 = False
            errors.append("%s: HTTP %s" % (host, host_status))
    res.cap = caps.cap
    if all_404:
        res.status, res.fetch_ok, res.error = "not_found", True, "404 on all hosts"
    else:
        res.status, res.fetch_ok, res.error = "error", False, "; ".join(errors) or "unknown"
    return res


# --------------------------------------------------------------------------
# tickers, cadence, ladders
# --------------------------------------------------------------------------

MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
TICKER_RE = re.compile(
    r"^(?P<series>[A-Z0-9]+)-(?P<date>\d{2}[A-Z]{3}\d{2}(?:\d{2})?(?:H\d{4})?)(?:-(?P<strike>.+))?$")
DATE_RE = re.compile(r"^(\d{2})([A-Z]{3})(\d{2})(\d{2})?(?:H(\d{2})(\d{2}))?$")


def parse_ticker(t: Any) -> Dict[str, Any]:
    """Both ticker generations:
         old  KXWTIW-24DEC06-T74.99      date only
         new  KXWTIW-26JUL2414-B79.50    date + hour (2 digits)
              KXWTIDIRY-26DEC31H1430     date + Hhhmm
       Event tickers are the same minus the strike. Never raises."""
    out: Dict[str, Any] = {"series": None, "date": None, "hour": None, "minute": None,
                           "strike_code": None, "format": "none", "dt": None}
    if not isinstance(t, str):
        return out
    m = TICKER_RE.match(t.strip())
    if not m:
        out["series"] = t.split("-")[0] if "-" in t else t
        return out
    out["series"] = m.group("series")
    out["strike_code"] = m.group("strike")
    d = DATE_RE.match(m.group("date"))
    if not d:
        return out
    yy, mon, dd, hh, hH, mm = d.groups()
    try:
        y, mo, day = 2000 + int(yy), MONTHS[mon], int(dd)
        hour = int(hh) if hh is not None else (int(hH) if hH is not None else None)
        minute = int(mm) if mm is not None else (0 if hour is not None else None)
        dt = datetime(y, mo, day, hour or 0, minute or 0)
    except (KeyError, ValueError):
        return out
    out.update({"date": dt.strftime("%Y-%m-%d"), "hour": hour, "minute": minute, "dt": dt,
                "format": "new" if hour is not None else "old"})
    return out


def event_datetime(ev: dict) -> Optional[datetime]:
    p = parse_ticker(ev.get("event_ticker") or ev.get("ticker"))
    if p["dt"] is not None:
        return p["dt"]
    e = iso_to_epoch(ev.get("strike_date"))
    if e is not None:
        return datetime.fromtimestamp(e, timezone.utc).replace(tzinfo=None)
    return None


def cadence_from_minutes(median_minutes: Optional[float]) -> str:
    if median_minutes is None:
        return "unknown"
    m = median_minutes
    if m <= 20:
        return "15min"
    if m <= 90:
        return "hourly"
    if m <= 36 * 60:
        return "daily"
    if m <= 8 * 24 * 60:
        return "weekly"
    if m <= 35 * 24 * 60:
        return "monthly"
    return "longer"


def cadence_hint(ticker: str, title: str, frequency: Any) -> Optional[str]:
    """What the metadata *claims*. Only ever used to flag a conflict."""
    f = str(frequency or "").lower()
    t = (title or "").lower()
    for src in (f, t):
        if "15" in src and ("min" in src or "-minute" in src or " minute" in src):
            return "15min"
        if "hour" in src:
            return "hourly"
    if f:
        for k, v in (("daily", "daily"), ("weekly", "weekly"), ("monthly", "monthly"),
                     ("annual", "longer"), ("yearly", "longer")):
            if k in f:
                return v
    for k, v in (("daily", "daily"), ("today", "daily"), ("weekly", "weekly"),
                 ("this week", "weekly"), ("monthly", "monthly"), ("yearly", "longer"),
                 ("annual", "longer"), ("end of year", "longer")):
        if k in t:
            return v
    tk = (ticker or "").upper()
    if tk.endswith("15M"):
        return "15min"
    if tk.endswith("H") and not tk.endswith("MONTH"):
        return "hourly"
    return None


def classify_cadence(dts: Iterable[Optional[datetime]], hint: Optional[str] = None
                     ) -> Dict[str, Any]:
    """Median spacing between consecutive distinct event datetimes."""
    xs = sorted({d for d in dts if d is not None})
    out: Dict[str, Any] = {"cadence": "unknown", "group": "unknown", "median_minutes": None,
                           "n_dated": len(xs), "hint": hint, "hint_conflict": False}
    if len(xs) >= 3:
        gaps = [(b - a).total_seconds() / 60.0 for a, b in zip(xs, xs[1:])]
        gaps = [g for g in gaps if g > 0]
        if gaps:
            med = statistics.median(gaps)
            out["median_minutes"] = round(med, 2)
            out["cadence"] = cadence_from_minutes(med)
    elif hint and len(xs) < 3:
        out["cadence"] = hint            # nothing measured; trust the label, say so
        out["from_hint_only"] = True
    out["group"] = cadence_group(out["cadence"])
    if hint and out.get("median_minutes") is not None and hint != out["cadence"]:
        out["hint_conflict"] = True
    return out


def cadence_group(cadence: str) -> str:
    return "intraday" if cadence in INTRADAY else (cadence or "unknown")


def ladder_kind_from_labels(labels: List[str]) -> str:
    """Fallback ONLY. RANGE = '$87.00 to $87.99' brackets (sum to 100).
    CUMUL = 'Above $89.99' thresholds (do not). Ported from the old script."""
    labels = [str(x) for x in labels if x]
    if not labels:
        return "UNKNOWN"
    n = len(labels)
    rng = sum(1 for x in labels if " to " in x.lower())
    above = sum(1 for x in labels
                if x.lower().startswith(("above", "below", "at or", "at least"))
                or x.lower().endswith((" or above", " or below", " or more", " or less")))
    if rng >= max(3, 0.4 * n):
        return "RANGE"
    if above >= 0.7 * n:
        return "CUMUL"
    return "OTHER"


def ladder_kind(mutually_exclusive: Any, labels: Optional[List[str]] = None
                ) -> Tuple[str, str]:
    """(kind, source). VERIFIED: event.mutually_exclusive is definitive."""
    if isinstance(mutually_exclusive, bool):
        return ("RANGE" if mutually_exclusive else "CUMUL"), "mutually_exclusive"
    if isinstance(mutually_exclusive, str) and mutually_exclusive.lower() in ("true", "false"):
        return ("RANGE" if mutually_exclusive.lower() == "true" else "CUMUL"), "mutually_exclusive"
    return ladder_kind_from_labels(labels or []), "labels"


# --------------------------------------------------------------------------
# orderbook (bids only on both sides)
# --------------------------------------------------------------------------

def _parse_side(raw: Any, scale: float) -> List[Tuple[float, int]]:
    out: List[Tuple[float, int]] = []
    for row in raw or []:
        try:
            p, c = float(row[0]) * scale, int(float(row[1]))
        except (TypeError, ValueError, IndexError):
            continue
        if c > 0:
            out.append((round(p, 4), c))
    return out


def book_from_kalshi(raw: Any) -> Dict[str, List[Tuple[float, int]]]:
    """Kalshi gives yes BIDS and no BIDS. A no bid at p is a yes ASK at 100-p.
    Handles {'orderbook': {'yes': [[cents, n]], 'no': [...]}} and
    {'orderbook_fp': {'yes_dollars': [['0.07', n]], 'no_dollars': [...]}}."""
    ob = (raw or {}).get("orderbook") if isinstance(raw, dict) else None
    yes_raw = no_raw = None
    scale = 1.0
    if isinstance(ob, dict) and (ob.get("yes") is not None or ob.get("no") is not None):
        yes_raw, no_raw = ob.get("yes"), ob.get("no")
    else:
        fp = (raw or {}).get("orderbook_fp") if isinstance(raw, dict) else None
        if isinstance(fp, dict):
            yes_raw, no_raw, scale = fp.get("yes_dollars"), fp.get("no_dollars"), 100.0
    yes = _parse_side(yes_raw, scale)
    no = _parse_side(no_raw, scale)
    return {
        "yes_bids": sorted(yes, key=lambda x: -x[0]),
        "yes_asks": sorted(((round(100.0 - p, 4), c) for p, c in no), key=lambda x: x[0]),
    }


# --------------------------------------------------------------------------
# market records: flatten + merge (live vs historical)
# --------------------------------------------------------------------------

def is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    if isinstance(v, (list, dict)) and not v:
        return True
    return False


STATUS_RANK = {"settled": 6, "finalized": 5, "determined": 4, "closed": 3, "paused": 2,
               "open": 2, "active": 2, "unopened": 1, "initialized": 1, "": 0}
VOLATILE_PREFIXES = ("volume", "open_interest", "liquidity", "yes_bid", "yes_ask", "no_bid",
                     "no_ask", "last_price", "previous_", "notional_value", "price_level",
                     "fee_waiver", "tick_size", "response_price_units", "market_type",
                     "can_close_early", "early_close", "settlement_timer", "category")
VOLATILE_FIELDS = {"status", "close_time", "expiration_time", "expected_expiration_time",
                   "latest_expiration_time", "title", "subtitle"}


def record_rank(m: dict) -> Tuple[int, int, int, int]:
    return (0 if is_empty(m.get("settlement_ts")) else 1,
            0 if is_empty(m.get("result")) else 1,
            0 if is_empty(m.get("expiration_value")) else 1,
            STATUS_RANK.get(str(m.get("status") or "").lower(), 0))


def _volatile(k: str) -> bool:
    return k in VOLATILE_FIELDS or k.startswith(VOLATILE_PREFIXES)


def merge_market(live: Optional[dict], hist: Optional[dict],
                 live_at: Optional[str] = None, hist_at: Optional[str] = None
                 ) -> Tuple[dict, Dict[str, Any]]:
    """Field-level, settlement-first merge. The record with more settlement
    information is primary; empty primary fields are filled from the other;
    both-non-empty-and-different on a non-volatile field is a recorded conflict."""
    meta: Dict[str, Any] = {"seen_live": live is not None, "seen_hist": hist is not None,
                            "primary_source": None, "merge_conflicts": [],
                            "live_fetched_at": live_at if live is not None else None,
                            "hist_fetched_at": hist_at if hist is not None else None}
    if live is None and hist is None:
        return {}, meta
    if live is None or hist is None:
        src = "live" if live is not None else "historical"
        meta["primary_source"] = src
        return dict(live if live is not None else hist), meta      # type: ignore[arg-type]
    rl, rh = record_rank(live), record_rank(hist)
    if rl > rh:
        primary, other, src = live, hist, "live"
    elif rh > rl:
        primary, other, src = hist, live, "historical"
    else:
        # tie: the record fetched later
        later_live = (live_at or "") >= (hist_at or "")
        primary, other, src = (live, hist, "live") if later_live else (hist, live, "historical")
    meta["primary_source"] = src
    merged = dict(primary)
    conflicts: List[str] = []
    for k, v in other.items():
        pv = merged.get(k)
        if is_empty(pv):
            merged[k] = v
        elif not is_empty(v) and not _volatile(k) and _canon(pv) != _canon(v):
            conflicts.append(k)
    meta["merge_conflicts"] = sorted(conflicts)
    return merged, meta


def _canon(v: Any) -> str:
    if isinstance(v, (dict, list)):
        return json.dumps(v, sort_keys=True)
    f = to_float(v) if not isinstance(v, bool) else None
    if f is not None and not isinstance(v, str):
        return repr(f)
    if isinstance(v, str):
        ff = to_float(v)
        if ff is not None:
            return repr(ff)
    return str(v)


def flatten_record(d: dict, flatten_keys: Tuple[str, ...] = ("custom_strike",)) -> Dict[str, Any]:
    """Every scalar survives as-is. Nested dict/list -> '<k>_json'. Keys in
    `flatten_keys` are additionally flattened as '<k>.<sub>' for scalar members."""
    out: Dict[str, Any] = {}
    for k, v in (d or {}).items():
        if isinstance(v, (dict, list)):
            out["%s_json" % k] = json.dumps(v, sort_keys=True)
            if k in flatten_keys and isinstance(v, dict):
                for sk, sv in v.items():
                    if isinstance(sv, (dict, list)):
                        out["%s.%s_json" % (k, sk)] = json.dumps(sv, sort_keys=True)
                    else:
                        out["%s.%s" % (k, sk)] = sv
        else:
            out[k] = v
    return out


TIMESTAMP_FIELDS = ("open_time", "close_time", "expiration_time", "expected_expiration_time",
                    "latest_expiration_time", "settlement_ts", "occurrence_datetime")
MARKET_FLOATS = ("floor_strike", "cap_strike", "expiration_value_num", "volume_fp",
                 "open_interest_fp", "liquidity_fp")
MARKET_TYPED = [
    "ticker", "event_ticker", "series", "yes_sub_title", "open_time", "close_time",
    "expiration_time", "expected_expiration_time", "latest_expiration_time",
    "settlement_ts", "occurrence_datetime", "settlement_timer_seconds", "status", "result",
    "strike_type", "floor_strike", "cap_strike", "expiration_value", "expiration_value_num",
    "custom_strike_json", "custom_strike.front_month_contract", "custom_strike.strike_date",
    "rules_primary", "rules_secondary", "volume_fp", "open_interest_fp", "liquidity_fp",
    "settlement_sources", "settlement_source_name", "settlement_source_url",
    "mutually_exclusive", "ladder_kind", "ladder_kind_source", "ticker_format",
    "ticker_date", "ticker_hour", "seen_live", "seen_hist", "seen_nested",
    "primary_source", "live_fetched_at", "hist_fetched_at", "merge_conflicts",
]


def settlement_source_fields(sources: Any) -> Tuple[Optional[str], Optional[str]]:
    """settlement_sources is a list of {name, url}. Join multiples with ' | '."""
    if not isinstance(sources, list) or not sources:
        return None, None
    names, urls = [], []
    for s in sources:
        if isinstance(s, dict):
            if s.get("name"):
                names.append(str(s["name"]))
            if s.get("url"):
                urls.append(str(s["url"]))
        elif isinstance(s, str):
            names.append(s)
    return (" | ".join(names) or None), (" | ".join(urls) or None)


def market_row(merged: dict, meta: Dict[str, Any], event: Optional[dict], series: str,
               seen_nested: bool = False) -> Dict[str, Any]:
    """One markets-table row: typed columns first, then every other scalar."""
    flat = flatten_record(merged)
    ev = event or {}
    row: Dict[str, Any] = dict(flat)
    row["series"] = series
    row["seen_nested"] = bool(seen_nested)
    row.update({k: meta.get(k) for k in ("seen_live", "seen_hist", "primary_source",
                                         "live_fetched_at", "hist_fetched_at")})
    row["merge_conflicts"] = json.dumps(meta.get("merge_conflicts") or [])
    tp = parse_ticker(merged.get("ticker"))
    row["ticker_format"], row["ticker_date"], row["ticker_hour"] = tp["format"], tp["date"], tp["hour"]
    row["expiration_value_num"] = to_float(merged.get("expiration_value"))
    for k in TIMESTAMP_FIELDS:
        row["%s_epoch" % k] = iso_to_epoch(merged.get(k))
    ss = ev.get("settlement_sources")
    if ss is None:
        ss = merged.get("settlement_sources")
    row["settlement_sources"] = json.dumps(ss, sort_keys=True) if ss is not None else None
    row["settlement_source_name"], row["settlement_source_url"] = settlement_source_fields(ss)
    me = ev.get("mutually_exclusive")
    if me is None:
        me = merged.get("mutually_exclusive")
    row["mutually_exclusive"] = me if isinstance(me, bool) else None
    kind, ksrc = ladder_kind(me, None)
    row["ladder_kind"], row["ladder_kind_source"] = kind, ksrc
    row.setdefault("yes_sub_title", merged.get("subtitle"))
    for k in ("custom_strike.front_month_contract", "custom_strike.strike_date",
              "custom_strike_json", "rules_secondary", "settlement_timer_seconds",
              "occurrence_datetime", "settlement_ts", "expected_expiration_time",
              "latest_expiration_time", "liquidity_fp", "open_interest_fp", "volume_fp",
              "result", "expiration_value", "strike_type", "floor_strike", "cap_strike"):
        row.setdefault(k, None)
    return row


def markets_frame(rows: List[Dict[str, Any]]):
    """Typed columns first (stable order), then everything else as string."""
    import pandas as pd
    if not rows:
        return pd.DataFrame(columns=MARKET_TYPED)
    df = pd.DataFrame(rows)
    for c in MARKET_TYPED:
        if c not in df.columns:
            df[c] = None
    for c in MARKET_FLOATS:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    df["settlement_timer_seconds"] = pd.to_numeric(df["settlement_timer_seconds"],
                                                   errors="coerce").astype("Int64")
    df["ticker_hour"] = pd.to_numeric(df["ticker_hour"], errors="coerce").astype("Int64")
    for c in [c for c in df.columns if c.endswith("_epoch")]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    df["mutually_exclusive"] = df["mutually_exclusive"].astype("boolean")
    for c in ("seen_live", "seen_hist", "seen_nested"):
        df[c] = df[c].fillna(False).astype(bool)
    typed = set(MARKET_TYPED) | set(MARKET_FLOATS) | {c for c in df.columns if c.endswith("_epoch")}
    extra = [c for c in df.columns if c not in typed]
    for c in extra:
        if df[c].dtype == object or str(df[c].dtype) == "bool":
            df[c] = df[c].map(lambda v: None if is_empty(v) else str(v)
                              if not isinstance(v, str) else v)
        else:
            df[c] = df[c].astype(object).where(df[c].notna(), None).map(
                lambda v: None if v is None else str(v))
    order = [c for c in MARKET_TYPED if c in df.columns]
    order += [c for c in df.columns if c.endswith("_epoch") and c not in order]
    order += sorted(c for c in df.columns if c not in order)
    return df[order]


def events_frame(events: List[dict], series: str, source: str = "live"):
    import pandas as pd
    rows = []
    for ev in events:
        flat = flatten_record(ev, flatten_keys=())
        flat.pop("markets_json", None)
        flat["series"] = series
        flat["source"] = source
        flat["n_markets"] = len(ev.get("markets") or [])
        ss = ev.get("settlement_sources")
        flat["settlement_sources"] = json.dumps(ss, sort_keys=True) if ss is not None else None
        flat["settlement_source_name"], flat["settlement_source_url"] = settlement_source_fields(ss)
        me = ev.get("mutually_exclusive")
        flat["mutually_exclusive"] = me if isinstance(me, bool) else None
        flat["ladder_kind"], flat["ladder_kind_source"] = ladder_kind(me, [
            str(m.get("yes_sub_title") or m.get("subtitle") or "") for m in (ev.get("markets") or [])])
        flat["strike_date_epoch"] = iso_to_epoch(ev.get("strike_date"))
        rows.append(flat)
    cols = ["event_ticker", "series", "title", "sub_title", "category", "mutually_exclusive",
            "ladder_kind", "ladder_kind_source", "settlement_sources", "settlement_source_name",
            "settlement_source_url", "strike_date", "strike_date_epoch", "strike_period",
            "n_markets", "source"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df["mutually_exclusive"] = df["mutually_exclusive"].astype("boolean")
    df["n_markets"] = df["n_markets"].astype("int64")
    df["strike_date_epoch"] = pd.to_numeric(df["strike_date_epoch"], errors="coerce").astype("Int64")
    extra = sorted(c for c in df.columns if c not in cols)
    for c in extra:
        df[c] = df[c].map(lambda v: None if is_empty(v) else (v if isinstance(v, str) else str(v)))
    return df[cols + extra]


# --------------------------------------------------------------------------
# series selection
# --------------------------------------------------------------------------

def keyword_hit(ticker: str, title: str, tags: Any, keywords: Iterable[str]) -> Optional[str]:
    """Whole-word match on title and tags ('gold' must not match 'Golden Globe',
    'corn' must not match 'Corners', 'oil' must not match 'Poilievre'); on the
    ticker only as a prefix after the KX namespace (KXOILRIGS, KXWTIVSBRENT)."""
    text = " ".join([str(title or ""), " ".join(str(t) for t in (tags or []))]).lower()
    tk = (ticker or "").lower()
    for k in keywords:
        k = k.lower()
        if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(k), text):
            return k
        if re.match(r"^(kx)?%s" % re.escape(k.replace(" ", "")), tk):
            return k
    return None


def select_series(all_series: List[dict], keywords: Iterable[str] = COMMODITY_KEYWORDS,
                  primary_category: str = "Commodities",
                  keyword_categories: Iterable[str] = KEYWORD_CATEGORIES) -> List[dict]:
    """Everything in the Commodities category, plus whole-word keyword hits in
    the economics/financial categories. Each selected record says why it was
    selected. Never a hardcoded list."""
    kws = [k.lower() for k in keywords]
    kcats = {c.lower() for c in keyword_categories}
    out: List[dict] = []
    seen = set()
    for s in all_series:
        tk = s.get("ticker")
        if not tk or tk in seen:
            continue
        cat = str(s.get("category") or "")
        reason = None
        if cat.lower() == primary_category.lower():
            reason = "category:%s" % cat
        elif cat.lower() in kcats:
            hit = keyword_hit(tk, s.get("title"), s.get("tags"), kws)
            if hit:
                reason = "keyword:%s" % hit
        if reason:
            seen.add(tk)
            out.append({"ticker": tk, "title": s.get("title"), "category": cat,
                        "frequency": s.get("frequency"), "tags": s.get("tags"),
                        "selected_by": reason})
    return out


# --------------------------------------------------------------------------
# store
# --------------------------------------------------------------------------

def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-%d" % os.getpid())
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def manifest_key(ticker: str, period: int) -> str:
    return "%s@%d" % (ticker, int(period))


class Store:
    """Owns, under root: parquet/kalshi_candles/period=*, parquet/kalshi_markets,
    parquet/kalshi_events, raw/kalshi/, manifest.jsonl, manifest.json, summary.csv,
    probe.json, collect.log, FINDINGS.md. Touches nothing else."""

    OWNED = ("parquet/kalshi_candles", "parquet/kalshi_markets", "parquet/kalshi_events",
             "raw/kalshi", "manifest.jsonl", "manifest.json", "summary.csv", "probe.json",
             "collect.log", "FINDINGS.md")

    def __init__(self, root: Path):
        self.root = Path(root)
        self.pq = self.root / "parquet"
        self.raw = self.root / "raw" / "kalshi"
        self.manifest_jsonl = self.root / "manifest.jsonl"
        self.manifest_json = self.root / "manifest.json"
        self.entries: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._jsonl_fh = None
        self.load()

    # -- manifest ----------------------------------------------------------
    def load(self) -> int:
        """Replay manifest.jsonl (authoritative). Last line per key wins."""
        self.entries = {}
        bad = 0
        if self.manifest_jsonl.exists():
            with open(self.manifest_jsonl, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        bad += 1
                        continue
                    k = e.get("key")
                    if k:
                        self.entries[k] = e
        if bad:
            log.warning("manifest.jsonl: %d unreadable lines skipped (a crash mid-write)", bad)
        return len(self.entries)

    def _guard_old_manifest(self) -> None:
        """A v1 manifest.json (old collector) is renamed, never overwritten."""
        if self.manifest_json.exists():
            try:
                old = json.loads(self.manifest_json.read_text())
            except (json.JSONDecodeError, OSError):
                old = {}
            if not isinstance(old, dict) or old.get("version") != MANIFEST_VERSION:
                dst = self.root / "manifest.v1.json"
                if dst.exists():
                    dst = self.root / ("manifest.v1.%d.json" % int(time.time()))
                os.replace(self.manifest_json, dst)
                log.warning("old-format manifest.json moved to %s", dst)

    def record(self, entry: dict) -> None:
        """Append one line = the checkpoint. Crash-safe by construction."""
        entry = dict(entry)
        entry["key"] = manifest_key(entry["ticker"], entry["period"])
        entry["at"] = now_iso()
        line = json.dumps(entry, sort_keys=True) + "\n"
        with self._lock:
            self.manifest_jsonl.parent.mkdir(parents=True, exist_ok=True)
            if self._jsonl_fh is None:
                self._jsonl_fh = open(self.manifest_jsonl, "a", encoding="utf-8")
            self._jsonl_fh.write(line)
            self._jsonl_fh.flush()
            self.entries[entry["key"]] = entry

    def close(self) -> None:
        with self._lock:
            if self._jsonl_fh is not None:
                self._jsonl_fh.close()
                self._jsonl_fh = None

    def decide(self, ticker: str, period: int, retry_errors: bool = True,
               retry_not_found: bool = False, repull: bool = False) -> Tuple[bool, str]:
        """(fetch?, why). Resume is the default; re-pulling is explicit."""
        if repull:
            return True, "repull"
        e = self.entries.get(manifest_key(ticker, period))
        if not e:
            return True, "new"
        st = e.get("status")
        if st in ("ok", "empty"):
            return False, "done:%s" % st
        if st == "not_found":
            return (True, "retry:not_found") if retry_not_found else (False, "done:not_found")
        if st == "error":
            return (True, "retry:error") if retry_errors else (False, "skip:error")
        return True, "unknown-status:%s" % st

    def counts(self, period: Optional[int] = None) -> Dict[str, int]:
        c: Dict[str, int] = {"ok": 0, "empty": 0, "not_found": 0, "error": 0, "rows": 0}
        for e in self.entries.values():
            if period is not None and e.get("period") != period:
                continue
            c[e.get("status", "error")] = c.get(e.get("status", "error"), 0) + 1
            c["rows"] += int(e.get("rows") or 0)
        return c

    def series_counts(self, period: Optional[int] = None) -> Dict[str, Dict[str, int]]:
        out: Dict[str, Dict[str, int]] = {}
        for e in self.entries.values():
            if period is not None and e.get("period") != period:
                continue
            s = out.setdefault(e.get("series") or "?", {"ok": 0, "empty": 0, "not_found": 0,
                                                           "error": 0, "rows": 0})
            s[e.get("status", "error")] = s.get(e.get("status", "error"), 0) + 1
            s["rows"] += int(e.get("rows") or 0)
        return out

    def snapshot(self, extra: Optional[dict] = None) -> None:
        """Human-readable summary. The JSONL stays authoritative."""
        self._guard_old_manifest()
        prev: Dict[str, Any] = {}
        if self.manifest_json.exists():
            try:
                prev = json.loads(self.manifest_json.read_text())
            except (json.JSONDecodeError, OSError):
                prev = {}
        snap = {
            "version": MANIFEST_VERSION,
            "created": prev.get("created") or now_iso(),
            "updated": now_iso(),
            "entries_file": self.manifest_jsonl.name,
            "n_entries": len(self.entries),
            "counts": self.counts(),
            "series": self.series_counts(),
            "runs": list(prev.get("runs") or []),
            "probe": prev.get("probe"),
        }
        if extra:
            for k, v in extra.items():
                if k == "run":
                    snap["runs"].append(v)
                else:
                    snap[k] = v
        atomic_write_text(self.manifest_json, json.dumps(snap, indent=2, sort_keys=True))

    # -- parquet -----------------------------------------------------------
    def candle_dir(self, period: int, series: str, event: str) -> Path:
        return (self.pq / "kalshi_candles" / ("period=%d" % int(period))
                / ("series=%s" % series) / ("event=%s" % event))

    def candle_file(self, period: int, series: str, event: str) -> Path:
        return self.candle_dir(period, series, event) / "part.parquet"

    def read_event_candles(self, period: int, series: str, event: str):
        import pandas as pd
        p = self.candle_file(period, series, event)
        if not p.exists():
            return empty_candle_frame()
        return pd.read_parquet(p)

    def write_event_candles(self, df, period: int, series: str, event: str,
                            merge_existing: bool = True) -> Path:
        """Rows for `df`'s tickers replace any earlier rows for those tickers;
        other tickers already in the event file are kept (resume-safe)."""
        import pandas as pd
        path = self.candle_file(period, series, event)
        if merge_existing and path.exists():
            old = pd.read_parquet(path)
            if not old.empty:
                keep = old[~old["ticker"].isin(set(df["ticker"]))]
                df = pd.concat([keep, df], ignore_index=True) if not keep.empty else df
        if df.empty:
            return path
        df = (df.drop_duplicates(["ticker", "ts"], keep="last")
                .sort_values(["ticker", "ts"]).reset_index(drop=True))
        df = coerce_candle_dtypes(df)
        self._write_parquet(df, path)
        return path

    def _write_parquet(self, df, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp-%d" % os.getpid())
        df.to_parquet(tmp, index=False, compression="snappy")
        os.replace(tmp, path)

    def table_path(self, name: str, **parts: Any) -> Path:
        d = self.pq / name
        for k, v in parts.items():
            d = d / ("%s=%s" % (k, v))
        return d / "part.parquet"

    def write_table(self, df, name: str, **parts: Any) -> Optional[Path]:
        if df is None or df.empty:
            return None
        p = self.table_path(name, **parts)
        self._write_parquet(df, p)
        return p

    def read_table(self, name: str, **parts: Any):
        import pandas as pd
        p = self.table_path(name, **parts)
        return pd.read_parquet(p) if p.exists() else None

    def read_all(self, name: str):
        """Concatenate every part.parquet under parquet/<name>/ (hive layout)."""
        import pandas as pd
        base = self.pq / name
        if not base.exists():
            return None
        frames = []
        for p in sorted(base.rglob("part.parquet")):
            f = pd.read_parquet(p)
            for part in p.relative_to(base).parts[:-1]:
                if "=" in part:
                    k, v = part.split("=", 1)
                    if k not in f.columns:
                        f[k] = v
            frames.append(f)
        if not frames:
            return None
        return pd.concat(frames, ignore_index=True)

    # -- raw ---------------------------------------------------------------
    def raw_path(self, *parts: str) -> Path:
        return self.raw.joinpath(*parts)

    def save_raw(self, rel: Path, obj: Any) -> Path:
        path = rel if rel.is_absolute() else self.raw / rel
        data = gzip.compress(json.dumps(obj, sort_keys=True).encode("utf-8"))
        atomic_write_bytes(path, data)
        return path

    def load_raw(self, rel: Path) -> Any:
        path = rel if rel.is_absolute() else self.raw / rel
        if not path.exists():
            return None
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)


# --------------------------------------------------------------------------
# misc
# --------------------------------------------------------------------------

def market_lifetime(m: dict, now: Optional[int] = None) -> Tuple[Optional[int], Optional[int]]:
    """(t0, t1) for a candle pull: open_time .. min(close_time, now)."""
    now = now or int(time.time())
    t0 = iso_to_epoch(m.get("open_time"))
    t1 = iso_to_epoch(m.get("close_time"))
    if t1 is None:
        t1 = iso_to_epoch(m.get("expiration_time"))
    if t0 is None or t1 is None:
        return None, None
    t1 = min(t1, now)
    return (t0, t1) if t1 > t0 else (t0, None)


def fmt_int(n: Any) -> str:
    try:
        return "{:,}".format(int(n))
    except (TypeError, ValueError):
        return str(n)


def glob_match(name: str, patterns: Iterable[str]) -> bool:
    import fnmatch
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)
