"""
fake_databento.py - an offline stand-in for databento.Historical used by the
tests and by `--client fake`. Reproduces the shapes verified on 2026-09-10:
  * metadata.get_cost / get_record_count (free quotes)
  * symbology.resolve(parent) with children in `partial`
  * timeseries.get_range(path=...) returning a store whose to_df() gives
    statistics / definition / tbbo frames with the real column names
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def settle_utc(d: date, hh: int = 14, mm: int = 30) -> datetime:
    """14:30 New York on date d, in UTC - the CME settlement instant (DST-aware)."""
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET).astimezone(timezone.utc)

COST = {"statistics": 0.01, "definition": 0.07, "tbbo": 0.08, "bbo-1m": 40.0, "ohlcv-1d": 0.0}
MONTHS = "FGHJKMNQUVXZ"


def _cl_contract_for(d: date) -> str:
    """NYMEX front month for date d (approximation for the fake: rolls on the 20th)."""
    m = d.month + (2 if d.day > 20 else 1)
    y = d.year + (1 if m > 12 else 0)
    m = ((m - 1) % 12) + 1
    return "CL%s%d" % (MONTHS[m - 1], y % 10)


class FakeStore:
    def __init__(self, df):
        self._df = df

    def to_df(self, pretty_ts=True, map_symbols=True, **kw):
        return self._df.copy()


class _Meta:
    def __init__(self, parent):
        self.p = parent

    def get_cost(self, dataset, start, end, symbols, stype_in, schema, **kw):
        base = COST.get(schema, 1.0)
        days = max(1, (datetime.fromisoformat(str(end)) - datetime.fromisoformat(str(start))).days)
        mult = 40.0 if any(str(s).startswith("LO.") for s in symbols) else 1.0
        return round(base * mult * (days / 190.0 if schema != "statistics" else 1.0), 2)

    def get_record_count(self, dataset, start, end, symbols, stype_in, schema, **kw):
        return 1000

    def get_dataset_range(self, dataset):
        return {"start": "2010-06-06T00:00:00Z", "end": "2026-09-10T00:00:00Z"}

    def list_schemas(self, dataset):
        return list(COST)


class _Sym:
    def __init__(self, parent):
        self.p = parent

    def resolve(self, dataset, symbols, stype_in, stype_out, start_date, end_date=None):
        out = {"result": {s: [] for s in symbols}, "partial": [], "not_found": [], "message": "ok", "status": 200}
        for s in symbols:
            root = s.split(".")[0]
            if root in self.p.roots:
                out["partial"] += [d["raw_symbol"] for d in self.p.definitions(root)] + ["UD:1N: GN 25%05d" % i for i in range(3)]
        return out


class _TS:
    def __init__(self, parent):
        self.p = parent

    def get_range(self, dataset, symbols, stype_in, schema, start, end, path=None, **kw):
        import pandas as pd
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(b"DBN-FAKE " + json.dumps({"schema": schema, "symbols": list(symbols)}).encode())
        d0, d1 = date.fromisoformat(str(start)[:10]), date.fromisoformat(str(end)[:10])
        if schema == "statistics":
            return FakeStore(pd.DataFrame(self.p.statistics(symbols, stype_in, d0, d1)))
        if schema == "definition":
            rows = []
            for s in symbols:
                rows += self.p.definitions(s.split(".")[0], d0, d1)
            return FakeStore(pd.DataFrame(rows))
        if schema == "tbbo":
            rows = []
            for s in symbols:
                rows += self.p.tbbo(s.split(".")[0], d0, d1)
            return FakeStore(pd.DataFrame(rows))
        raise ValueError("fake has no schema %s" % schema)


class FakeHistorical:
    """Kalshi-like settlement dates are Fridays (weekly) and every weekday (daily);
    the fake lists LO1..LO5 Friday weeklies, ML1/WL1 Monday/Wednesday, LO monthly
    on the 17th, with 12 strikes each side of 70."""

    roots = ["LO", "LO1", "LO2", "LO3", "LO4", "LO5", "ML1", "WL1", "MCO"]

    def __init__(self, ice_offset: float = 0.03, sparse_roots: Optional[List[str]] = None):
        self.metadata = _Meta(self)
        self.symbology = _Sym(self)
        self.timeseries = _TS(self)
        self.ice_offset = ice_offset
        self.sparse_roots = set(sparse_roots or [])
        self.window = (date(2026, 3, 1), date(2026, 9, 10))

    # -- futures ----------------------------------------------------------
    def nymex_settle(self, d: date) -> float:
        return round(65.0 + 12.0 * ((d.toordinal() * 7919) % 100) / 100.0, 2)

    def statistics(self, symbols, stype_in, d0, d1):
        import pandas as pd
        rows = []
        d = d0
        while d <= d1:
            if d.weekday() < 5:
                ts = settle_utc(d, 14, 35)
                contracts = [_cl_contract_for(d)] if stype_in == "continuous" else sorted({_cl_contract_for(d + timedelta(days=k)) for k in (0, 30, 60)})
                for ct in contracts:
                    px = self.nymex_settle(d) + (0.4 if ct != _cl_contract_for(d) else 0.0)
                    for st, val in ((3, px), (9, 100000.0), (6, 5000.0)):
                        rows.append({"ts_recv": ts, "ts_event": ts, "ts_ref": ts, "symbol": ct, "stat_type": st,
                                     "price": val if st == 3 else float("nan"), "quantity": val if st != 3 else float("nan"),
                                     "instrument_id": 1000 + hash(ct) % 1000})
            d += timedelta(days=1)
        return rows

    # -- options ------------------------------------------------------------
    def expiries(self, root: str, d0: date, d1: date) -> List[date]:
        out = []
        d = d0
        while d <= d1:
            if root.startswith("LO") and len(root) == 3 and d.weekday() == 4 and ((d.day - 1) // 7 + 1) == int(root[2]):
                out.append(d)
            elif root == "ML1" and d.weekday() == 0 and d.day <= 7:
                out.append(d)
            elif root == "WL1" and d.weekday() == 2 and d.day <= 7:
                out.append(d)
            elif root in ("LO", "MCO") and d.day == 17 and d.weekday() < 5:
                out.append(d)
            d += timedelta(days=1)
        return out

    def definitions(self, root: str, d0: Optional[date] = None, d1: Optional[date] = None) -> List[dict]:
        d0, d1 = d0 or self.window[0], d1 or self.window[1]
        rows = []
        for exp in self.expiries(root, d0, d1):
            code = "%s%s%d" % (root, MONTHS[exp.month - 1], exp.year % 10)
            for k in range(58, 83, 2):
                for right in "CP":
                    sym = "%s %s%d" % (code, right, k * 100)
                    rows.append({"ts_recv": datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc), "raw_symbol": sym,
                                 "symbol": sym, "instrument_id": abs(hash(sym)) % 10 ** 7,
                                 "expiration": settle_utc(exp),
                                 "activation": datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc),
                                 "strike_price": float(k), "instrument_class": right, "underlying": "CL" + code[-2:],
                                 "asset": root, "security_type": "OOF", "min_price_increment": 0.01})
        return rows

    def tbbo(self, root: str, d0: date, d1: date) -> List[dict]:
        rows = []
        sparse = root in self.sparse_roots
        for exp in self.expiries(root, d0, d1):
            F = self.nymex_settle(exp)
            code = "%s%s%d" % (root, MONTHS[exp.month - 1], exp.year % 10)
            settle = settle_utc(exp)
            for k in range(58, 83, 2):
                if sparse and abs(k - F) > 4:
                    continue                                   # wings never trade
                for right in "CP":
                    sym = "%s %s%d" % (code, right, k * 100)
                    intrinsic = max(0.0, (F - k) if right == "C" else (k - F))
                    for minutes_before in (400, 200, 90, 45, 20, 5):
                        if sparse and minutes_before < 90:
                            continue
                        ts = settle - timedelta(minutes=minutes_before)
                        mid = round(intrinsic + 0.35, 2)
                        rows.append({"ts_recv": ts, "ts_event": ts, "symbol": sym, "instrument_id": abs(hash(sym)) % 10 ** 7,
                                     "price": mid, "size": 3, "side": "B", "bid_px_00": round(mid - 0.03, 2),
                                     "ask_px_00": round(mid + 0.03, 2), "bid_sz_00": 10, "ask_sz_00": 12})
        return rows
