"""
db_common.py - shared pieces for db_basis.py / db_pull.py / db_verify.py.

Budget discipline is the hard constraint (handoff brief section 5):
  * every billable request is quoted with metadata.get_cost() FIRST, the quote
    is logged, and the run aborts if the running total would exceed --max-cost
  * nothing is bought without --execute; the default is a dry run that prints
    the plan and the total quoted cost
  * a manifest line per completed request (with its cost) makes re-runs free:
    data already on disk is never bought twice

VERIFIED against the live API on 2026-09-10 (see FINDINGS_CHAIN.md):
  * symbology.resolve() with stype_in="parent" returns the child instruments in
    the response's `partial` list, not `result` - that is why an earlier call
    looked like "0 mappings"
  * WTI option roots that exist on GLBX.MDP3: LO (monthly), LO1-LO5 (Friday
    weeklies), ML1-ML5 (Monday), WL1-WL5 (Wednesday), MCO (Micro WTI).
    LT*, LR*, LW*, LC, LCA, MCO1, LO6 -> 422 symbology_invalid_request
  * option raw symbols look like "LO1Q6 C6975": root, month code, year digit,
    space, C/P, strike*100
  * StatType.SETTLEMENT_PRICE == 3 in the installed databento_dbn

Python 3.9 compatible.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

DATASET = "GLBX.MDP3"
DEFAULT_OUT = Path("data_cme")
DEFAULT_MAX_COST = 25.0
STAT_SETTLEMENT = 3          # databento_dbn.StatType.SETTLEMENT_PRICE
ET = "America/New_York"

OPTION_ROOTS = ["LO"] + ["%s%d" % (p, i) for p in ("LO", "ML", "WL") for i in range(1, 6)] + ["MCO"]
WEEKLY_ROOTS = [r for r in OPTION_ROOTS if r not in ("LO", "MCO")]
MONTH_CODES = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6, "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}
CODE_OF_MONTH = {v: k for k, v in MONTH_CODES.items()}

log = logging.getLogger("nightking.db")


def setup_logging(logfile: Optional[str] = None) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger("nightking.db")
    root.setLevel(logging.INFO)
    root.handlers = []
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(fmt)
    root.addHandler(h)
    if logfile:
        Path(logfile).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(logfile)
        fh.setFormatter(fmt)
        root.addHandler(fh)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# key
# --------------------------------------------------------------------------

def load_key(env_path: str = ".env") -> str:
    """DATABENTO_API_KEY from the environment or .env (explicit path: python-dotenv's
    auto-discovery breaks when run from stdin). Never logged."""
    key = os.environ.get("DATABENTO_API_KEY")
    if not key and Path(env_path).exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
            key = os.environ.get("DATABENTO_API_KEY")
        except ImportError:
            for line in Path(env_path).read_text().splitlines():
                if line.startswith("DATABENTO_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("DATABENTO_API_KEY not set: put it in .env (gitignored) as DATABENTO_API_KEY=db-...")
    return key


def assert_env_gitignored() -> None:
    gi = Path(".gitignore")
    if Path(".env").exists() and not (gi.exists() and any(l.strip() == ".env" for l in gi.read_text().splitlines())):
        sys.exit(".env exists but is NOT in .gitignore - refusing to run (a committed key is compromised forever)")


# --------------------------------------------------------------------------
# symbols
# --------------------------------------------------------------------------

OPT_RE = re.compile(r"^(?P<root>[A-Z]+\d?)(?P<mc>[FGHJKMNQUVXZ])(?P<yr>\d)\s+(?P<right>[CP])(?P<strike>\d+)$")
FUT_RE = re.compile(r"^(?P<root>[A-Z]+)(?P<mc>[FGHJKMNQUVXZ])(?P<yr>\d)$")
KALSHI_FM_RE = re.compile(r"^WBS\s+(?P<yy>\d{2})(?P<mc>[FGHJKMNQUVXZ])-ICE$")


def parse_option_symbol(sym: Any) -> Optional[Dict[str, Any]]:
    """'LO1Q6 C6975' -> root LO1, month Q (Aug), year 2026, call, strike 69.75.
    Strikes are quoted in cents of a dollar per barrel. Spreads (UD:...) -> None."""
    if not isinstance(sym, str):
        return None
    m = OPT_RE.match(sym.strip())
    if not m:
        return None
    return {"root": m.group("root"), "month": MONTH_CODES[m.group("mc")],
            "year": 2020 + int(m.group("yr")), "right": m.group("right"),
            "strike": int(m.group("strike")) / 100.0,
            "contract": "%s%s%s" % (m.group("root"), m.group("mc"), m.group("yr"))}


def parse_future_symbol(sym: Any) -> Optional[Dict[str, Any]]:
    """'CLV6' -> root CL, month 10, year 2026."""
    if not isinstance(sym, str):
        return None
    m = FUT_RE.match(sym.strip())
    if not m:
        return None
    return {"root": m.group("root"), "month": MONTH_CODES[m.group("mc")], "year": 2020 + int(m.group("yr")),
            "contract": sym.strip()}


def kalshi_front_month_to_cl(fm: Any) -> Optional[str]:
    """Kalshi custom_strike.front_month_contract 'WBS 26V-ICE' -> NYMEX 'CLV6'.
    WBS is ICE's WTI code; the delivery month is the same on both exchanges."""
    if not isinstance(fm, str):
        return None
    m = KALSHI_FM_RE.match(fm.strip())
    if not m:
        return None
    return "CL%s%s" % (m.group("mc"), m.group("yy")[-1])


RULES_RE = re.compile(r"\((January|February|March|April|May|June|July|August|September|October|November|December)"
                      r"\s+(\d{4})\s+contract\)", re.I)
MONTH_NAMES = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                            "august", "september", "october", "november", "december"], 1)}


def rules_contract(rules_text: Any) -> Optional[str]:
    """Kalshi rules_primary: '... WTI crude oil(September 2026 contract) on ...' -> 'CLU6'.
    Present on every 2026 event from June on; the earlier wording is 'the front-month
    settle price' with no month named."""
    if not isinstance(rules_text, str):
        return None
    m = RULES_RE.search(rules_text)
    if not m:
        return None
    mo = MONTH_NAMES[m.group(1).lower()]
    return "CL%s%s" % (CODE_OF_MONTH[mo], m.group(2)[-1])


def kalshi_calendar_contract(d: date) -> str:
    """Kalshi's observed convention (VERIFIED on the 98 events that name a contract,
    98/98): from the 16th of month M the reference contract is delivery month M+2,
    before the 16th it is M+1. Kalshi rolls weeks before either exchange's expiry."""
    m = d.month + (2 if d.day >= 16 else 1)
    y = d.year + (1 if m > 12 else 0)
    m = ((m - 1) % 12) + 1
    return "CL%s%s" % (CODE_OF_MONTH[m], str(y)[-1])


def year_digit_ambiguity_note() -> str:
    return ("CME raw symbols carry a single year digit (CLV6 = Oct 2026); within a 2026 window "
            "that is unambiguous.")


# --------------------------------------------------------------------------
# Kalshi settlement dates (from the local store - never hardcoded)
# --------------------------------------------------------------------------

def kalshi_settlements(kalshi_root: Path = Path("data"), series: Iterable[str] = ("KXWTI", "KXWTIW"),
                       since: str = "2026-01-01"):
    """One row per Kalshi EVENT: series, event_ticker, settle_ts (UTC), settle_date (ET),
    settle_time_et, expiration_value (ICE settlement, float or NaN), front_month (Kalshi's
    ICE contract code) and cl_contract (its NYMEX equivalent)."""
    import pandas as pd
    files = sorted((Path(kalshi_root) / "parquet" / "kalshi_markets").rglob("part.parquet"))
    if not files:
        sys.exit("no Kalshi markets table under %s - run the Kalshi collector first" % kalshi_root)
    cols = ["series", "event_ticker", "close_time", "expiration_value", "custom_strike.front_month_contract",
            "rules_primary"]
    frames = []
    for f in files:
        have = set(pd.read_parquet(f).columns)
        frames.append(pd.read_parquet(f, columns=[c for c in cols if c in have]))
    mk = pd.concat(frames, ignore_index=True)
    mk = mk[mk["series"].isin(list(series))].copy()
    mk["close"] = pd.to_datetime(mk["close_time"], utc=True, errors="coerce")
    mk = mk[mk["close"] >= pd.Timestamp(since, tz="UTC")]
    for c in ("custom_strike.front_month_contract", "rules_primary"):
        if c not in mk.columns:
            mk[c] = None

    def first_value(s):
        for v in s:
            if v not in (None, "") and not (isinstance(v, float) and v != v):
                return v
        return None
    ev = (mk.groupby(["series", "event_ticker"])
            .agg(settle_ts=("close", "min"),
                 expiration_value=("expiration_value", first_value),
                 front_month=("custom_strike.front_month_contract", first_value),
                 rules=("rules_primary", first_value),
                 n_markets=("event_ticker", "size"))
            .reset_index())
    ev["expiration_value"] = pd.to_numeric(ev["expiration_value"], errors="coerce")
    et = ev["settle_ts"].dt.tz_convert(ET)
    ev["settle_date"] = et.dt.date
    ev["settle_time_et"] = et.dt.strftime("%H:%M")
    ev["weekday"] = et.dt.day_name()
    ev["contract_rules"] = ev["rules"].map(rules_contract)
    ev["contract_named"] = ev["front_month"].map(kalshi_front_month_to_cl)
    ev["contract_calendar"] = ev["settle_date"].map(kalshi_calendar_contract)
    # authority: the rules text > custom_strike > Kalshi's calendar convention
    ev["cl_contract"] = ev["contract_rules"].where(ev["contract_rules"].notna(), ev["contract_named"])
    ev["front_month_source"] = ev["contract_rules"].map(lambda v: "rules" if isinstance(v, str) else None)
    ev.loc[ev["front_month_source"].isna() & ev["contract_named"].notna(), "front_month_source"] = "named"
    fill = ev["cl_contract"].isna()
    ev.loc[fill, "cl_contract"] = ev.loc[fill, "contract_calendar"]
    ev.loc[fill, "front_month_source"] = "calendar"
    ev = ev.drop(columns=["rules"])
    return ev.sort_values(["series", "settle_ts"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# timestamps: Kalshi bars vs Databento events
# --------------------------------------------------------------------------

def kalshi_bar_end(ts) -> Any:
    """Databento records are event-timestamped (ts_event = matching-engine time,
    ts_recv = capture time). Kalshi 1-minute candles are keyed by end_period_ts,
    the END of the minute: the bar with end_period_ts=T covers (T-60s, T].
    So an event at ts_event t belongs to the Kalshi bar ending at ceil_minute(t)."""
    import pandas as pd
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.ceil("1min")


# --------------------------------------------------------------------------
# manifest + cost-preflighted client
# --------------------------------------------------------------------------

def request_key(dataset: str, schema: str, symbols: Iterable[str], stype_in: str, start: str, end: str) -> str:
    return "|".join([dataset, schema, ",".join(sorted(symbols)), stype_in, str(start), str(end)])


class Manifest:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.entries: Dict[str, dict] = {}
        self._lock = threading.Lock()
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("key"):
                    self.entries[e["key"]] = e

    def record(self, entry: dict) -> None:
        entry = dict(entry)
        entry["at"] = now_iso()
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
            self.entries[entry["key"]] = entry

    def spent(self) -> float:
        return float(sum(float(e.get("cost") or 0.0) for e in self.entries.values() if e.get("status") == "ok"))


class BudgetExceeded(SystemExit):
    pass


def load_dbn(path: Path):
    """Read a raw DBN file back into a DataFrame (module-level so tests can swap it)."""
    import databento as db
    return db.DBNStore.from_file(str(path)).to_df(pretty_ts=True, map_symbols=True)


class DBClient:
    """Wraps databento.Historical with the brief's discipline. Every pull:
    quote -> log -> cap check -> (dry run: plan only) -> fetch to raw DBN -> parquet -> manifest.
    A raw file on disk without a manifest entry (crash between download and record)
    is rebuilt from the file, never bought again. A failed request is recorded as
    status=error and the run continues; the next run quotes and retries it."""

    def __init__(self, out: Path, max_cost: float = DEFAULT_MAX_COST, execute: bool = False,
                 client: Any = None, key: Optional[str] = None):
        self.out = Path(out)
        self.max_cost = float(max_cost)
        self.execute = bool(execute)
        self.manifest = Manifest(self.out / "manifest.jsonl")
        self.run_total = 0.0
        self.plan: List[dict] = []
        self.quotes: Dict[str, float] = {}
        if client is not None:
            self.client = client
        else:
            import databento as db
            self.client = db.Historical(key or load_key())

    # -- free calls ------------------------------------------------------
    def quote(self, schema: str, symbols: Iterable[str], stype_in: str, start: str, end: str,
              dataset: str = DATASET) -> float:
        symbols = list(symbols)
        k = request_key(dataset, schema, symbols, stype_in, start, end)
        if k in self.quotes:
            return self.quotes[k]
        cost = float(self.client.metadata.get_cost(dataset, start=start, end=end, symbols=symbols,
                                                   stype_in=stype_in, schema=schema))
        self.quotes[k] = cost
        log.info("quote  $%8.2f  %-11s %-22s %s..%s", cost, schema, ",".join(symbols)[:22], start, end)
        return cost

    def record_count(self, schema: str, symbols: Iterable[str], stype_in: str, start: str, end: str,
                     dataset: str = DATASET) -> int:
        return int(self.client.metadata.get_record_count(dataset, start=start, end=end, symbols=list(symbols),
                                                         stype_in=stype_in, schema=schema))

    def resolve_children(self, parent: str, start: str, end: str, dataset: str = DATASET) -> List[str]:
        """Child raw symbols of a parent symbol. VERIFIED: they arrive in `partial`."""
        r = self.client.symbology.resolve(dataset, [parent], stype_in="parent", stype_out="instrument_id",
                                          start_date=start, end_date=end)
        kids = list(r.get("partial") or [])
        for m in (r.get("result") or {}).get(parent) or []:
            if isinstance(m, dict) and m.get("s"):
                kids.append(m["s"])
        return kids

    # -- the one billable path --------------------------------------------
    def pull(self, name: str, schema: str, symbols: Iterable[str], stype_in: str, start: str, end: str,
             dataset: str = DATASET, parquet_rel: Optional[str] = None):
        """Returns a DataFrame, or None in dry-run mode. Resume: if the manifest
        has this exact request with its parquet on disk, it is read back and
        nothing is bought."""
        import pandas as pd
        symbols = list(symbols)
        k = request_key(dataset, schema, symbols, stype_in, start, end)
        pq = self.out / "parquet" / (parquet_rel or ("%s/part.parquet" % name))
        prev = self.manifest.entries.get(k)
        if prev and prev.get("status") == "ok" and Path(prev.get("parquet_path", "")).exists():
            log.info("cached $%8.2f  %-11s %-22s (bought %s)", float(prev.get("cost") or 0), schema,
                     ",".join(symbols)[:22], prev.get("at", "?")[:10])
            return pd.read_parquet(prev["parquet_path"])
        raw = self.out / "raw" / ("%s.dbn.zst" % name)
        cost = self.quote(schema, symbols, stype_in, start, end, dataset)
        if raw.exists() and raw.stat().st_size > 0 and self.execute:
            # paid for and downloaded, but never recorded: rebuild, do not buy again
            log.warning("RECOVER %s: raw %s exists without a manifest entry - rebuilding from it (no purchase)",
                        name, raw.name)
            t0 = time.monotonic()
            try:
                df = load_dbn(raw)
            except Exception as e:                                       # noqa: BLE001
                log.error("RECOVER %s failed to read %s (%s) - will re-buy", name, raw.name, str(e)[:120])
                df = None
            if df is not None:
                df = df.reset_index() if df.index.name else df
                pq.parent.mkdir(parents=True, exist_ok=True)
                df.to_parquet(pq, index=False, compression="snappy")
                self.manifest.record({"key": k, "name": name, "dataset": dataset, "schema": schema,
                                      "symbols": symbols, "stype_in": stype_in, "start": start, "end": end,
                                      "cost": cost, "records": int(len(df)), "raw_path": str(raw),
                                      "parquet_path": str(pq), "elapsed_s": round(time.monotonic() - t0, 1),
                                      "status": "ok", "recovered_from_raw": True})
                self.plan.append({"name": name, "schema": schema, "symbols": symbols, "stype_in": stype_in,
                                  "start": start, "end": end, "cost": cost, "cached": True})
                return df
        self.plan.append({"name": name, "schema": schema, "symbols": symbols, "stype_in": stype_in,
                          "start": start, "end": end, "cost": cost, "cached": False})
        if not self.execute:
            return None
        if self.run_total + cost > self.max_cost:
            raise BudgetExceeded(
                "BUDGET: %s would cost $%.2f; run total $%.2f + this exceeds --max-cost $%.2f. Nothing bought."
                % (name, cost, self.run_total, self.max_cost))
        raw.parent.mkdir(parents=True, exist_ok=True)
        log.info("BUYING $%8.2f  %-11s %-22s %s..%s -> %s", cost, schema, ",".join(symbols)[:22], start, end, raw.name)
        t0 = time.monotonic()
        try:
            store = self.client.timeseries.get_range(dataset=dataset, symbols=symbols, stype_in=stype_in,
                                                     schema=schema, start=start, end=end, path=str(raw))
            df = store.to_df(pretty_ts=True, map_symbols=True)
        except Exception as e:                                           # noqa: BLE001
            log.error("FAILED %s: %s: %s - recorded as error; the next run retries it", name,
                      type(e).__name__, str(e)[:200])
            self.manifest.record({"key": k, "name": name, "dataset": dataset, "schema": schema, "symbols": symbols,
                                  "stype_in": stype_in, "start": start, "end": end, "cost": 0.0,
                                  "quoted": cost, "status": "error", "error": "%s: %s" % (type(e).__name__, str(e)[:200]),
                                  "raw_path": str(raw) if raw.exists() else None})
            return None
        df = df.reset_index() if df.index.name else df
        pq.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(pq, index=False, compression="snappy")
        self.run_total += cost
        self.manifest.record({"key": k, "name": name, "dataset": dataset, "schema": schema, "symbols": symbols,
                              "stype_in": stype_in, "start": start, "end": end, "cost": cost,
                              "records": int(len(df)), "raw_path": str(raw), "parquet_path": str(pq),
                              "elapsed_s": round(time.monotonic() - t0, 1), "status": "ok"})
        log.info("bought  %s records in %.1fs; run total $%.2f of $%.2f cap; lifetime spend in this store $%.2f",
                 "{:,}".format(len(df)), time.monotonic() - t0, self.run_total, self.max_cost, self.manifest.spent())
        return df

    def print_plan(self, title: str = "PLAN") -> float:
        total = sum(p["cost"] for p in self.plan)
        print("\n" + "=" * 78)
        print("%s  (%s)" % (title, "EXECUTING" if self.execute else "DRY RUN - nothing bought; add --execute"))
        print("=" * 78)
        for p in self.plan:
            print("  $%8.2f  %-11s %-26s %s..%s  [%s]" % (p["cost"], p["schema"], ",".join(p["symbols"])[:26],
                                                         p["start"], p["end"], p["name"]))
        print("  --------")
        print("  $%8.2f  total quoted for this run   (cap $%.2f; already in store $%.2f)"
              % (total, self.max_cost, self.manifest.spent()))
        if total > self.max_cost:
            print("  !! exceeds --max-cost; raise the cap or narrow the request")
        return total


# --------------------------------------------------------------------------
# parquet helpers
# --------------------------------------------------------------------------

def write_parquet(df, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    saved = dict(df.attrs)                     # attrs are working notes, not parquet metadata
    try:
        df.attrs = {}
        df.to_parquet(tmp, index=False, compression="snappy")
    finally:
        df.attrs = saved
    os.replace(tmp, path)
    return path


def read_all(base: Path):
    import pandas as pd
    base = Path(base)
    files = sorted(base.rglob("part.parquet")) if base.exists() else []
    if not files:
        return None
    frames = []
    for f in files:
        d = pd.read_parquet(f)
        for part in f.relative_to(base).parts[:-1]:
            if "=" in part:
                k, v = part.split("=", 1)
                if k not in d.columns:
                    d[k] = v
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)
