"""verify.py must read the parquet, not the logs: an all-null bid/ask store
passed the previous smoke test because only rows were counted."""
import io
import contextlib
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import fixture, kc, ROOT
import sys
sys.path.insert(0, str(ROOT))
import verify  # noqa: E402
import findings  # noqa: E402


def build_store(root, n=5, ticker="KXWTIW-26JUN2614-T83.99"):
    st = kc.Store(root)
    c = fixture("candle_dollars.json")
    t0 = kc.iso_to_epoch("2026-06-19T14:00:00Z")
    rows = [dict(c, end_period_ts=t0 + 60 * (i + 1)) for i in range(n)]
    df = kc.candles_to_frame(rows, "KXWTIW", "KXWTIW-26JUN2614", ticker, "Above $83.99", "CUMUL", 1, "historical")
    st.write_event_candles(df, 1, "KXWTIW", "KXWTIW-26JUN2614")
    st.record({"ticker": ticker, "period": 1, "series": "KXWTIW", "event": "KXWTIW-26JUN2614",
               "status": "ok", "fetch_ok": True, "http_live": 404, "http_hist": 200,
               "source": "historical", "rows": n, "t0": t0, "t1": t0 + 60 * n})
    live, hist = fixture("market_live.json"), fixture("market_hist.json")
    st.save_raw(Path("markets") / "KXWTIW.live.json.gz", {"markets": [live]})
    st.save_raw(Path("markets") / "KXWTIW.hist.json.gz", {"markets": [hist]})
    m, meta = kc.merge_market(live, hist, "a", "b")
    st.write_table(kc.markets_frame([kc.market_row(m, meta, fixture("event_range.json"), "KXWTIW")]),
                   "kalshi_markets", series="KXWTIW")
    st.write_table(kc.events_frame([fixture("event_range.json")], "KXWTIW"), "kalshi_events", series="KXWTIW")
    st.snapshot()
    st.close()
    return st


def run_quiet(root, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = verify.run(root, **kw)
    return rc, buf.getvalue()


class TestVerify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_store(self.root)
        self.pq = self.root / "parquet" / "kalshi_candles" / "period=1" / "series=KXWTIW" / "event=KXWTIW-26JUN2614" / "part.parquet"

    def tearDown(self):
        self.tmp.cleanup()

    def _corrupt(self, fn):
        df = pd.read_parquet(self.pq)
        df = fn(df)
        df.to_parquet(self.pq, index=False)

    def test_healthy_store_passes(self):
        rc, out = run_quiet(self.root)
        self.assertEqual(rc, 0, out)
        self.assertIn("PASS", out.splitlines()[-1])

    def test_all_null_bid_fails(self):
        def f(df):
            df["yes_bid_close"] = np.nan
            return df
        self._corrupt(f)
        rc, out = run_quiet(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("all-null", out)

    def test_all_null_ask_fails(self):
        def f(df):
            for c in [c for c in df.columns if c.startswith("yes_ask_")]:
                df[c] = np.nan
            return df
        self._corrupt(f)
        self.assertEqual(run_quiet(self.root)[0], 1)

    def test_negative_spread_fails(self):
        def f(df):
            df["yes_ask_close"] = 1.0
            df["yes_bid_close"] = 50.0
            return df
        self._corrupt(f)
        rc, out = run_quiet(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("ask < bid", out)

    def test_out_of_range_fails(self):
        def f(df):
            df.loc[0, "yes_ask_high"] = 150.0
            return df
        self._corrupt(f)
        self.assertEqual(run_quiet(self.root)[0], 1)

    def test_row_count_mismatch_fails(self):
        def f(df):
            return df.iloc[:2]
        self._corrupt(f)
        rc, out = run_quiet(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("rows match parquet", [l for l in out.splitlines() if l.startswith("FAIL")][0])

    def test_duplicate_rows_fail(self):
        def f(df):
            return pd.concat([df, df.iloc[:1]], ignore_index=True)
        self._corrupt(f)
        self.assertEqual(run_quiet(self.root)[0], 1)

    def test_missing_manifest_fails(self):
        (self.root / "manifest.jsonl").unlink()
        self.assertEqual(run_quiet(self.root)[0], 1)

    def test_lost_expiration_value_fails(self):
        p = self.root / "parquet" / "kalshi_markets" / "series=KXWTIW" / "part.parquet"
        df = pd.read_parquet(p)
        df["expiration_value"] = ""
        df.to_parquet(p, index=False)
        rc, out = run_quiet(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("merge kept expiration_value", out)

    def test_error_entries_warn_and_strict_fails(self):
        st = kc.Store(self.root)
        st.record({"ticker": "KXWTIW-26JUN2614-T84.99", "period": 1, "series": "KXWTIW",
                   "event": "KXWTIW-26JUN2614", "status": "error", "fetch_ok": False,
                   "http_live": 0, "http_hist": 0, "source": "none", "rows": 0, "error": "HTTP 0"})
        st.close()
        # the error ticker is not in the markets table -> that is a FAIL on its own,
        # so add it to the table first
        p = self.root / "parquet" / "kalshi_markets" / "series=KXWTIW" / "part.parquet"
        df = pd.read_parquet(p)
        row = df.iloc[[0]].copy()
        row["ticker"] = "KXWTIW-26JUN2614-T84.99"
        pd.concat([df, row], ignore_index=True).to_parquet(p, index=False)
        rc, out = run_quiet(self.root)
        self.assertEqual(rc, 0)
        self.assertIn("WARN manifest: errors", out)
        self.assertEqual(run_quiet(self.root, strict=True)[0], 1)

    def test_findings(self):
        st = kc.Store(self.root)
        p = findings.write_findings(st, self.root / "FINDINGS.md")
        txt = p.read_text()
        self.assertIn("KXWTIW", txt)
        self.assertIn("ICE", txt)
        self.assertIn("2026-06", txt)
        self.assertIn("Databento shortlist", txt)
        self.assertNotIn("Tail depth", txt, "tails section is opt-in")

    def test_findings_tails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            build_store(root, n=60)                     # 60 candles: quoted; volume 512: tradeable
            st = kc.Store(root)
            f = findings.build(st)
            r = f["series"]["KXWTIW"]
            self.assertEqual(r["tradeable_months"], 1)
            findings.MIN_USABLE_MONTHS, keep = 1, findings.MIN_USABLE_MONTHS
            try:
                t = findings.tail_depth(st, f)
                p = findings.write_findings(st, root / "FINDINGS.md", tails=True)
            finally:
                findings.MIN_USABLE_MONTHS = keep
            self.assertIn("KXWTIW", t)
            self.assertEqual(len(t["KXWTIW"]["segments"]), 1)
            bands = {b["band"]: b for b in t["KXWTIW"]["segments"][0]["bands"]}
            self.assertEqual(bands["deep tail"]["brackets"], 1)       # mid = (2+4)/2 = 3c
            self.assertEqual(bands["moderate tail"]["brackets"], 0)
            self.assertEqual(bands["deep tail"]["vol_median"], 512.0)
            self.assertEqual(bands["deep tail"]["spread_median"], 2.0)
            txt = p.read_text()
            self.assertIn("Tail depth on the shortlist", txt)
            self.assertIn("| deep tail | 0-5c | 1 |", txt)

    def test_crosscheck_report(self):
        old = self.root / "old"
        d = old / "parquet" / "kalshi_candles" / "series=KXWTIW" / "event=KXWTIW-26JUN2614"
        d.mkdir(parents=True)
        df = pd.read_parquet(self.pq)
        df.to_parquet(d / "KXWTIW-26JUN2614-T83.99.parquet", index=False)
        rc, out = run_quiet(self.root, crosscheck_dir=old)
        self.assertEqual(rc, 0)
        self.assertIn("overlapping tickers: 1", out)
        self.assertIn("exact match", out)


if __name__ == "__main__":
    unittest.main()
