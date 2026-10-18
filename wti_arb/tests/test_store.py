"""Store: parquet round-trip dtypes, JSONL manifest replay, resume decisions,
old manifest guard, atomic raw writes, per-event merge on resume."""
import json
import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import fixture, kc


def frame(ticker, n=3, start=1_787_961_600):
    c = fixture("candle_dollars.json")
    rows = [dict(c, end_period_ts=start + 60 * i) for i in range(n)]
    return kc.candles_to_frame(rows, "S", "E", ticker, "b", "RANGE", 1, "live")


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = kc.Store(self.root)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_parquet_roundtrip_preserves_dtypes(self):
        df = frame("T1")
        self.store.write_event_candles(df, 1, "S", "E")
        back = self.store.read_event_candles(1, "S", "E")
        self.assertEqual(list(back.columns), kc.CANDLE_COLUMNS)
        for c in kc.CANDLE_INTS:
            self.assertEqual(str(back[c].dtype), "int64", c)
        for c in kc.CANDLE_FLOATS:
            self.assertEqual(str(back[c].dtype), "float64", c)
        self.assertEqual(str(back["dt"].dtype), "datetime64[ns, UTC]")
        for c in kc.CANDLE_STRINGS:
            self.assertTrue(pd.api.types.is_string_dtype(back[c]) or back[c].dtype == object, c)
        self.assertEqual(back["yes_bid_close"].tolist(), [2.0, 2.0, 2.0])
        self.assertTrue(back["price_close"].isna().all())

    def test_markets_table_roundtrip(self):
        m, meta = kc.merge_market(fixture("market_live.json"), fixture("market_hist.json"), "a", "b")
        df = kc.markets_frame([kc.market_row(m, meta, fixture("event_range.json"), "KXWTIW")])
        self.store.write_table(df, "kalshi_markets", series="KXWTIW")
        back = self.store.read_table("kalshi_markets", series="KXWTIW")
        self.assertEqual(str(back["floor_strike"].dtype), "float64")
        self.assertEqual(str(back["settlement_timer_seconds"].dtype), "Int64")
        self.assertEqual(str(back["mutually_exclusive"].dtype), "boolean")
        self.assertEqual(back["expiration_value"].iloc[0], "69.23")
        allm = self.store.read_all("kalshi_markets")
        self.assertEqual(len(allm), 1)
        self.assertEqual(allm["series"].iloc[0], "KXWTIW")

    def test_event_file_merge_on_resume(self):
        self.store.write_event_candles(frame("T1"), 1, "S", "E")
        self.store.write_event_candles(frame("T2", n=2), 1, "S", "E")
        back = self.store.read_event_candles(1, "S", "E")
        self.assertEqual(sorted(back["ticker"].unique()), ["T1", "T2"])
        self.assertEqual(len(back), 5)
        # re-pull of T1 replaces only T1's rows
        self.store.write_event_candles(frame("T1", n=1), 1, "S", "E")
        back = self.store.read_event_candles(1, "S", "E")
        self.assertEqual(len(back), 3)
        self.assertEqual(int((back["ticker"] == "T1").sum()), 1)
        self.assertEqual(int(back.duplicated(["ticker", "ts"]).sum()), 0)

    def test_manifest_jsonl_replay_last_wins(self):
        self.store.record({"ticker": "T", "period": 1, "series": "S", "event": "E",
                           "status": "error", "fetch_ok": False, "rows": 0})
        self.store.record({"ticker": "T", "period": 1, "series": "S", "event": "E",
                           "status": "ok", "fetch_ok": True, "rows": 5})
        self.store.record({"ticker": "T", "period": 60, "series": "S", "event": "E",
                           "status": "empty", "fetch_ok": True, "rows": 0})
        self.store.close()
        lines = (self.root / "manifest.jsonl").read_text().strip().splitlines()
        self.assertEqual(len(lines), 3, "append-only: every record is a line")
        s2 = kc.Store(self.root)
        self.assertEqual(s2.entries["T@1"]["status"], "ok")
        self.assertEqual(s2.entries["T@60"]["status"], "empty")
        self.assertIn("at", s2.entries["T@1"])
        self.assertEqual(s2.counts(1), {"ok": 1, "empty": 0, "not_found": 0, "error": 0, "rows": 5})

    def test_corrupt_line_is_skipped(self):
        self.store.record({"ticker": "A", "period": 1, "series": "S", "event": "E",
                           "status": "ok", "fetch_ok": True, "rows": 1})
        self.store.close()
        with open(self.root / "manifest.jsonl", "a") as f:
            f.write('{"ticker": "B", "period": 1, "sta')      # crash mid-write
        s2 = kc.Store(self.root)
        self.assertEqual(set(s2.entries), {"A@1"})

    def test_decide_matrix(self):
        for st in ("ok", "empty", "not_found", "error"):
            self.store.record({"ticker": st, "period": 1, "series": "S", "event": "E",
                               "status": st, "fetch_ok": st != "error", "rows": 0})
        d = self.store.decide
        self.assertEqual(d("new", 1), (True, "new"))
        self.assertEqual(d("ok", 1)[0], False)
        self.assertEqual(d("empty", 1)[0], False)
        self.assertEqual(d("not_found", 1)[0], False)
        self.assertEqual(d("not_found", 1, retry_not_found=True)[0], True)
        self.assertEqual(d("error", 1)[0], True, "errors retry by default")
        self.assertEqual(d("error", 1, retry_errors=False)[0], False)
        self.assertEqual(d("ok", 1, repull=True), (True, "repull"))
        self.assertEqual(d("ok", 60)[0], True, "a different period is a different pull")

    def test_old_manifest_is_renamed_not_overwritten(self):
        old = {"created": "x", "kalshi_candles": {"KXWTIW-1": {"rows": 0}}, "poly": {}, "runs": []}
        (self.root / "manifest.json").write_text(json.dumps(old))
        self.store.snapshot({"run": {"at": "now"}})
        self.assertTrue((self.root / "manifest.v1.json").exists())
        self.assertEqual(json.loads((self.root / "manifest.v1.json").read_text()), old)
        snap = json.loads((self.root / "manifest.json").read_text())
        self.assertEqual(snap["version"], 2)
        self.assertEqual(len(snap["runs"]), 1)
        self.store.snapshot({"run": {"at": "later"}})
        self.assertEqual(len(json.loads((self.root / "manifest.json").read_text())["runs"]), 2)

    def test_raw_gzip_roundtrip_and_atomic(self):
        p = self.store.save_raw(Path("candles") / "S" / "E.p1.json.gz", {"a": [1, 2]})
        self.assertTrue(p.exists())
        self.assertEqual(self.store.load_raw(Path("candles") / "S" / "E.p1.json.gz"), {"a": [1, 2]})
        self.assertFalse(any(x.name.endswith(".tmp") or ".tmp-" in x.name for x in p.parent.iterdir()))
        self.assertIsNone(self.store.load_raw(Path("nope.json.gz")))

    def test_owned_paths_only(self):
        (self.root / "wtiw").mkdir()
        (self.root / "wtiw" / "keep.txt").write_text("old pull")
        self.store.write_event_candles(frame("T1"), 1, "S", "E")
        self.store.record({"ticker": "T1", "period": 1, "series": "S", "event": "E",
                           "status": "ok", "fetch_ok": True, "rows": 3})
        self.store.snapshot()
        self.assertEqual((self.root / "wtiw" / "keep.txt").read_text(), "old pull")


if __name__ == "__main__":
    unittest.main()
