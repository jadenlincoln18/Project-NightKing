"""Databento side: symbols, Kalshi date loading, cost discipline, basis join,
density measurement, verify. Runs offline against tests/fake_databento.py."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import ROOT, kc  # noqa: E402
sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402
import db_common as dc  # noqa: E402
import db_basis  # noqa: E402
import db_pull  # noqa: E402
import db_verify  # noqa: E402
from fake_databento import FakeHistorical  # noqa: E402


class TestSymbols(unittest.TestCase):
    def test_option_symbols(self):
        p = dc.parse_option_symbol("LO1Q6 C6975")
        self.assertEqual((p["root"], p["month"], p["year"], p["right"], p["strike"], p["contract"]), ("LO1", 8, 2026, "C", 69.75, "LO1Q6"))
        p = dc.parse_option_symbol("MCOQ6 P10375")
        self.assertEqual((p["root"], p["strike"]), ("MCO", 103.75))
        self.assertEqual(dc.parse_option_symbol("LOF7 C12350")["year"], 2027)
        self.assertIsNone(dc.parse_option_symbol("UD:1N: GN 2588613"))
        self.assertIsNone(dc.parse_option_symbol("CLV6"))
        self.assertIsNone(dc.parse_option_symbol(None))

    def test_future_and_kalshi_front_month(self):
        self.assertEqual(dc.parse_future_symbol("CLV6")["month"], 10)
        self.assertEqual(dc.kalshi_front_month_to_cl("WBS 26V-ICE"), "CLV6")
        self.assertEqual(dc.kalshi_front_month_to_cl("WBS 26Z-ICE"), "CLZ6")
        self.assertIsNone(dc.kalshi_front_month_to_cl(None))
        self.assertIsNone(dc.kalshi_front_month_to_cl("garbage"))

    def test_kalshi_bar_end(self):
        t = dc.kalshi_bar_end(pd.Timestamp("2026-09-04T18:29:15Z"))
        self.assertEqual(t, pd.Timestamp("2026-09-04T18:30:00Z"))
        self.assertEqual(dc.kalshi_bar_end(pd.Timestamp("2026-09-04T18:30:00Z")), pd.Timestamp("2026-09-04T18:30:00Z"))


def kalshi_store(root: Path):
    """A tiny Kalshi markets table with KXWTI dailies and KXWTIW Fridays in 2026."""
    st = kc.Store(root)
    rows = []

    def close_utc(d):   # 14:30 America/New_York on that date, as the API serves it (Z)
        return pd.Timestamp(d.strftime("%Y-%m-%d") + " 14:30", tz="America/New_York").tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    for d in pd.bdate_range("2026-03-02", "2026-03-27"):
        et = "KXWTI-26%s" % d.strftime("%b%d").upper()
        for j in range(3):
            rows.append({"ticker": "%s-T%d" % (et, 60 + j), "event_ticker": et, "close_time": close_utc(d),
                         "expiration_value": "%.2f" % (65.0 + d.day / 10.0), "status": "settled",
                         "custom_strike": {"front_month_contract": "WBS 26K-ICE"} if d.day > 10 else None,
                         "settlement_sources": [{"name": "ICE", "url": "u"}]})
        if d.weekday() == 4:
            etw = "KXWTIW-26%s14" % d.strftime("%b%d").upper()
            rows.append({"ticker": "%s-B70.50" % etw, "event_ticker": etw, "close_time": close_utc(d),
                         "expiration_value": "%.2f" % (65.0 + d.day / 10.0), "status": "settled",
                         "custom_strike": {"front_month_contract": "WBS 26K-ICE"}})
    for series in ("KXWTI", "KXWTIW"):
        sub = [r for r in rows if r["event_ticker"].startswith(series + "-")]
        mrows = [kc.market_row(*kc.merge_market(None, m, "a", "b"), {"mutually_exclusive": True}, series) for m in sub]
        st.write_table(kc.markets_frame(mrows), "kalshi_markets", series=series)
    st.close()


class TestKalshiDates(unittest.TestCase):
    def test_loader(self):
        with tempfile.TemporaryDirectory() as d:
            kalshi_store(Path(d))
            ev = dc.kalshi_settlements(Path(d), since="2026-01-01")
            self.assertEqual(set(ev["series"]), {"KXWTI", "KXWTIW"})
            self.assertEqual(int((ev["series"] == "KXWTI").sum()), 20)
            self.assertEqual(int((ev["series"] == "KXWTIW").sum()), 4)
            self.assertTrue((ev["settle_time_et"] == "14:30").all())
            self.assertEqual(ev["contract_named"].dropna().unique().tolist(), ["CLK6"])
            self.assertTrue(ev["cl_contract"].notna().all(), "calendar fallback fills the rest")
            self.assertEqual(set(ev["front_month_source"]), {"named", "calendar"})
            self.assertEqual(dc.kalshi_calendar_contract(date(2026, 6, 15)), "CLN6")
            self.assertEqual(dc.kalshi_calendar_contract(date(2026, 6, 16)), "CLQ6")
            self.assertEqual(dc.kalshi_calendar_contract(date(2026, 12, 20)), "CLG7")
            self.assertEqual(dc.rules_contract("If the daily settlement price for WTI crude oil(September 2026 contract) on August 03"), "CLU6")
            self.assertIsNone(dc.rules_contract("If the front-month settle price for a barrel of West Texas Intermediate oil"))
            self.assertTrue(ev["expiration_value"].notna().all())


class TestCostDiscipline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "cme"

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_buys_nothing(self):
        c = dc.DBClient(self.out, max_cost=25, execute=False, client=FakeHistorical())
        df = c.pull("x", "statistics", ["CL.c.0"], "continuous", "2026-03-01", "2026-03-10")
        self.assertIsNone(df)
        self.assertEqual(len(c.plan), 1)
        self.assertFalse((self.out / "manifest.jsonl").exists())
        self.assertFalse((self.out / "raw").exists())

    def test_execute_records_cost_and_resume_is_free(self):
        c = dc.DBClient(self.out, max_cost=25, execute=True, client=FakeHistorical())
        df = c.pull("stats", "statistics", ["CL.c.0"], "continuous", "2026-03-01", "2026-03-10")
        self.assertGreater(len(df), 0)
        self.assertEqual(c.run_total, 0.01)
        self.assertTrue((self.out / "raw" / "stats.dbn.zst").exists())
        e = list(c.manifest.entries.values())[0]
        self.assertEqual((e["cost"], e["status"], e["schema"]), (0.01, "ok", "statistics"))
        c2 = dc.DBClient(self.out, max_cost=25, execute=True, client=FakeHistorical())
        df2 = c2.pull("stats", "statistics", ["CL.c.0"], "continuous", "2026-03-01", "2026-03-10")
        self.assertEqual(len(df2), len(df))
        self.assertEqual(c2.run_total, 0.0, "cached: nothing bought")
        self.assertEqual(c2.plan, [])

    def test_cap_aborts_before_buying(self):
        c = dc.DBClient(self.out, max_cost=1.0, execute=True, client=FakeHistorical())
        with self.assertRaises(dc.BudgetExceeded):
            c.pull("big", "bbo-1m", ["LO1.OPT"], "parent", "2026-03-01", "2026-09-10")
        self.assertFalse((self.out / "manifest.jsonl").exists())
        self.assertFalse((self.out / "raw").exists())

    def test_running_total_across_requests(self):
        c = dc.DBClient(self.out, max_cost=0.015, execute=True, client=FakeHistorical())
        c.pull("a", "statistics", ["CL.c.0"], "continuous", "2026-03-01", "2026-03-10")
        with self.assertRaises(dc.BudgetExceeded):
            c.pull("b", "statistics", ["CL.FUT"], "parent", "2026-03-01", "2026-03-10")
        self.assertEqual(len(c.manifest.entries), 1)

    def test_raw_without_manifest_is_rebuilt_not_rebought(self):
        fake = FakeHistorical()
        c = dc.DBClient(self.out, max_cost=25, execute=True, client=fake)
        raw = self.out / "raw" / "stats.dbn.zst"
        raw.parent.mkdir(parents=True)
        raw.write_bytes(b"paid-for download, process died before the manifest line")
        rows = fake.statistics(["CL.c.0"], "continuous", date(2026, 3, 2), date(2026, 3, 9))
        orig = dc.load_dbn
        dc.load_dbn = lambda path: pd.DataFrame(rows)
        try:
            df = c.pull("stats", "statistics", ["CL.c.0"], "continuous", "2026-03-01", "2026-03-10")
        finally:
            dc.load_dbn = orig
        self.assertEqual(len(df), len(rows))
        self.assertEqual(c.run_total, 0.0, "recovered, not bought")
        e = list(c.manifest.entries.values())[0]
        self.assertTrue(e.get("recovered_from_raw"))
        self.assertEqual(e["status"], "ok")

    def test_failed_request_is_recorded_and_run_continues(self):
        fake = FakeHistorical()
        def boom(**kw):
            raise ConnectionError("simulated outage")
        fake.timeseries.get_range = boom
        c = dc.DBClient(self.out, max_cost=25, execute=True, client=fake)
        df = c.pull("stats", "statistics", ["CL.c.0"], "continuous", "2026-03-01", "2026-03-10")
        self.assertIsNone(df)
        e = list(c.manifest.entries.values())[0]
        self.assertEqual(e["status"], "error")
        self.assertEqual(e["cost"], 0.0)
        self.assertEqual(c.run_total, 0.0)
        # the next run does not treat the error entry as cached
        c2 = dc.DBClient(self.out, max_cost=25, execute=False, client=FakeHistorical())
        self.assertIsNone(c2.pull("stats", "statistics", ["CL.c.0"], "continuous", "2026-03-01", "2026-03-10"))
        self.assertEqual(len(c2.plan), 1)

    def test_resolve_children_reads_partial(self):
        c = dc.DBClient(self.out, execute=False, client=FakeHistorical())
        kids = c.resolve_children("LO1.OPT", "2026-03-01", "2026-09-10")
        self.assertTrue(any(dc.parse_option_symbol(k) for k in kids))
        self.assertTrue(any(k.startswith("UD:") for k in kids))


class TestBasis(unittest.TestCase):
    def test_join_and_roll_check(self):
        with tempfile.TemporaryDirectory() as d:
            kalshi_store(Path(d))
            ev = dc.kalshi_settlements(Path(d))
            fake = FakeHistorical()
            c0 = pd.DataFrame(fake.statistics(["CL.c.0"], "continuous", date(2026, 2, 26), date(2026, 3, 28)))
            fut = pd.DataFrame(fake.statistics(["CL.FUT"], "parent", date(2026, 2, 26), date(2026, 3, 28)))
            j, c0t, futt = db_basis.build(ev, c0, fut)
            self.assertTrue(j["nymex_c0"].notna().all(), "every Kalshi date has a c.0 settlement")
            self.assertEqual(len(j), len(ev), "no duplicated events after the join")
            named = j[j["front_month_source"] == "named"]
            self.assertTrue(named["nymex_fm"].notna().all(), "named contract joins to CL.FUT")
            # fake: ICE == NYMEX exactly, so basis vs c.0 is 0 where contracts agree
            agree = j[~j["roll_mismatch"] & j["nymex_c0"].notna()]
            self.assertTrue(((j["expiration_value"] - j["nymex_c0"]).abs()[~j["roll_mismatch"]].fillna(0) < 20).all())
            d0 = db_basis.describe(j["basis_c0"])
            self.assertEqual(d0["n"], 24)
            self.assertIn(db_basis.verdict({"n": 30, "mean": 0.01, "sd": 0.05, "abs_p95": 0.1}), ("tight",))
            self.assertEqual(db_basis.verdict({"n": 30, "mean": 0.5, "sd": 0.5, "abs_p95": 1.0}), "too wide")
            self.assertEqual(db_basis.verdict({"n": 3}), "insufficient data")
            txt = db_basis.render(j, c0t, futt, {"3": 20, "9": 20}, {"c0": 0.01, "fut": 0.4})
            self.assertIn("## Verdict:", txt)
            self.assertIn("Roll dates", txt)

    def test_settlement_table_missing_stat_type(self):
        df = pd.DataFrame([{"ts_event": pd.Timestamp("2026-03-02T18:35Z"), "ts_ref": pd.Timestamp("2026-03-02T18:35Z"),
                            "symbol": "CLK6", "stat_type": 9, "price": float("nan")}])
        t = db_basis.settlement_table(df, "x")
        self.assertEqual(len(t), 0)


class TestDensity(unittest.TestCase):
    def _run(self, sparse):
        with tempfile.TemporaryDirectory() as d:
            kalshi_store(Path(d))
            ev = dc.kalshi_settlements(Path(d))
            fake = FakeHistorical(sparse_roots=["LO1", "LO2", "LO3", "LO4", "LO5"] if sparse else None)
            defs = pd.concat([db_pull.parse_definitions(pd.DataFrame(fake.definitions(r, date(2026, 3, 1), date(2026, 3, 31))), r)
                              for r in ("LO1", "LO2", "LO3", "LO4", "ML1", "WL1", "LO")], ignore_index=True)
            exp_tab = db_pull.expiry_table(defs)
            m, cov = db_pull.match_roots(exp_tab, ev)
            tb = {}
            for r in ("LO1", "LO2", "LO3", "LO4", "ML1", "WL1", "LO"):
                t = pd.DataFrame(fake.tbbo(r, date(2026, 3, 1), date(2026, 3, 31)))
                if len(t):
                    t["ts_event"] = pd.to_datetime(t["ts_event"], utc=True)
                    p = t["symbol"].map(dc.parse_option_symbol)
                    t["strike"] = p.map(lambda x: x["strike"])
                    t["right"] = p.map(lambda x: x["right"])
                    tb[r] = t
            dens = db_pull.measure_density(tb, defs, ev, {})
            return cov, dens

    def test_root_matching(self):
        cov, dens = self._run(sparse=False)
        w = cov["KXWTIW"]
        self.assertEqual(w["dates"], 4)
        self.assertEqual(w["dates_with_any_expiry"], 4, "every Friday has a LOn weekly")
        dly = cov["KXWTI"]
        self.assertEqual(dly["by_weekday"]["Tuesday"]["matched"], 1, "only the LO monthly on the 17th (a Tuesday in Mar 2026)")
        self.assertEqual(dly["by_weekday"]["Friday"]["matched"], 4)

    def test_density_dense_clears_sparse_does_not(self):
        _, dense = self._run(sparse=False)
        fri = dense[dense["root"].str.match(r"LO\d")]
        self.assertTrue(fri["clears"].all())
        self.assertTrue((fri["strikes_60m"] >= 8).all())
        self.assertTrue((fri["below_60m"] >= 3).all() and (fri["above_60m"] >= 3).all())
        _, sparse = self._run(sparse=True)
        fri = sparse[sparse["root"].str.match(r"LO\d")]
        self.assertFalse(fri["clears"].any(), "wings unquoted and last quote 90 min old")
        self.assertTrue((fri["strikes_60m"] == 0).all())
        self.assertTrue((sparse[sparse["root"] == "ML1"]["clears"]).all(), "non-sparse root still clears")


class TestVerifyAndCLI(unittest.TestCase):
    def test_end_to_end_fake(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            kalshi_store(d / "k")
            out = d / "cme"
            cwd = os.getcwd()
            os.chdir(d)
            try:
                Path(".gitignore").write_text(".env\n")
                Path(".env").write_text("DATABENTO_API_KEY=db-fake\n")
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = db_basis.main(["--out", str(out), "--kalshi", str(d / "k"), "--client", "fake"])
                self.assertEqual(rc, 0)
                self.assertIn("DRY RUN", buf.getvalue())
                self.assertFalse((out / "manifest.jsonl").exists())
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = db_basis.main(["--out", str(out), "--kalshi", str(d / "k"), "--client", "fake", "--execute"])
                self.assertEqual(rc, 0, buf.getvalue())
                self.assertTrue((out / "FINDINGS_BASIS.md").exists())
                self.assertIn("## Verdict:", (out / "FINDINGS_BASIS.md").read_text())
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = db_pull.main(["--out", str(out), "--kalshi", str(d / "k"), "--client", "fake",
                                       "--roots", "LO1,LO2,LO3,LO4,ML1,WL1", "--execute"])
                self.assertEqual(rc, 0, buf.getvalue())
                txt = (out / "FINDINGS_CHAIN.md").read_text()
                self.assertIn("Roots to use", txt)
                self.assertIn("TBBO is sufficient", txt)
                self.assertTrue((out / "parquet" / "options_tbbo_by_expiry").exists())
                self.assertTrue((out / "parquet" / "chain_density" / "part.parquet").exists())
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = db_verify.run(out)
                self.assertEqual(rc, 0, buf.getvalue())
                # re-run is free
                c = dc.DBClient(out, execute=True, client=FakeHistorical())
                c.pull("futures_stats_c0", "statistics", ["CL.c.0"], "continuous",
                       list(c.manifest.entries.values())[0]["start"], list(c.manifest.entries.values())[0]["end"],
                       parquet_rel="futures_stats/symbol=CL.c.0/part.parquet")
                self.assertEqual(c.run_total, 0.0)
                # all-null ask must fail verify
                p = next((out / "parquet" / "options_tbbo").rglob("part.parquet"))
                t = pd.read_parquet(p)
                t["ask_px_00"] = float("nan")
                t.to_parquet(p, index=False)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = db_verify.run(out)
                self.assertEqual(rc, 1)
                self.assertIn("entire side is null", buf.getvalue())
            finally:
                os.chdir(cwd)

    def test_env_guard(self):
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            os.chdir(d)
            try:
                Path(".env").write_text("DATABENTO_API_KEY=db-x\n")
                with self.assertRaises(SystemExit):
                    dc.assert_env_gitignored()
                Path(".gitignore").write_text(".env\n")
                dc.assert_env_gitignored()
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
