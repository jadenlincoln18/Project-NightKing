"""End to end against the fake Kalshi server: probe -> smoke -> full -> verify,
plus the negative paths (all-null bid, outage + resume, confirm gate,
intraday exclusion, crosscheck). Runs the real CLIs in subprocesses so exit
codes and argument handling are exercised exactly as on the Mac."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

import pandas as pd

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import ROOT
sys.path.insert(0, str(ROOT / "tests"))
from fake_kalshi import FakeKalshi  # noqa: E402

PY = sys.executable


def run(*args, stdin=subprocess.DEVNULL, timeout=600, **kw):
    p = subprocess.run([PY] + [str(a) for a in args], cwd=str(ROOT), stdin=stdin,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, text=True, **kw)
    return p.returncode, p.stdout


class TestEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = FakeKalshi(port=0).start()
        cls.tmp = tempfile.mkdtemp(prefix="nightking-e2e-")
        cls.out = Path(cls.tmp) / "data"
        cls.bases = ["--live-base", cls.srv.live_base, "--hist-base", cls.srv.hist_base]

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def control(self, what):
        with urllib.request.urlopen("http://127.0.0.1:%d/__control/%s" % (self.srv.port, what), timeout=10) as r:
            return json.loads(r.read().decode())

    # ordered steps (unittest sorts by name) -----------------------------------
    def test_01_probe(self):
        rc, out = run("probe.py", "--out", self.out, "--pause", "0", "--rate-n", "10", *self.bases)
        self.assertEqual(rc, 0, out)
        P = json.loads((self.out / "probe.json").read_text())
        self.assertEqual(P["candles"]["cap"], 5000)
        self.assertIn("max candlesticks: 5000", P["candles"]["cap_evidence"])
        self.assertEqual(P["candles"]["field_style"], "dollars")
        self.assertIn("close_dollars", P["candles"]["block_keys"]["yes_bid"])
        sel = {s["ticker"]: s for s in P["series"]["selected"]}
        self.assertIn("KXFAKEWTIW", sel)
        self.assertIn("KXFAKEHEATOIL", sel, "keyword hit outside Commodities")
        self.assertNotIn("KXFAKEPOTUS", sel)
        self.assertEqual(sel["KXFAKEWTIH"]["group"], "intraday")
        self.assertEqual(sel["KXFAKEWTIW"]["cadence"], "weekly")
        self.assertEqual(sel["KXFAKEGOLDD"]["cadence"], "daily")
        hm = P["host_matrix"]
        self.assertEqual(hm["archived_market"]["live"]["http"], 404)
        self.assertEqual(hm["archived_market"]["historical"]["http"], 200)
        self.assertEqual(hm["recent_market"]["live"]["http"], 200)
        self.assertEqual(P["period_interval"]["5"]["http"], 400)
        self.assertEqual(P["period_interval"]["60"]["http"], 200)
        self.assertEqual(P["rate"]["sent"], 10)
        self.assertIs(P["markets_endpoint_complete"], False, "fake live /markets omits archived ones")
        self.assertEqual(P["events"]["KXFAKEWTIW"]["mutually_exclusive"], {"true": 12})
        self.assertIn("intraday", P["estimate"]["groups"])
        self.assertTrue(P["settled_check"]["settled_lte_unfiltered"])
        self.assertTrue(P["markets"]["KXFAKEWTIW"]["ticker_formats"].get("old"))
        self.assertTrue(P["markets"]["KXFAKEWTIW"]["ticker_formats"].get("new"))
        self.assertIn("ESTIMATE - what a full", out)
        self.assertIn("excluded by default", out)

    def test_02_smoke(self):
        rc, out = run("collect.py", "--smoke", "--out", self.out, "--pause", "0", *self.bases)
        self.assertEqual(rc, 0, out)
        smoke = Path(str(self.out) + "_smoke")
        self.assertTrue((smoke / "manifest.jsonl").exists())
        self.assertIn("PASS", out)
        entries = [json.loads(l) for l in (smoke / "manifest.jsonl").read_text().splitlines()]
        statuses = {e["status"] for e in entries}
        self.assertIn("ok", statuses)
        self.assertIn("not_found", statuses, "oldest never-traded markets 404 on both hosts")
        sources = {e["source"] for e in entries if e["status"] == "ok"}
        self.assertEqual(sources, {"live", "historical"}, "both hosts exercised")
        self.assertTrue(all("fetch_ok" in e and "http_live" in e for e in entries))

    def test_03_gate_refuses_without_tty_or_yes(self):
        rc, out = run("collect.py", "--out", self.out, "--pause", "0", *self.bases)
        self.assertEqual(rc, 3, out)
        self.assertIn("FULL RUN - estimate", out)
        self.assertIn("intraday", out)
        self.assertFalse((self.out / "manifest.jsonl").exists())

    def test_04_full_run_default_excludes_intraday(self):
        rc, out = run("collect.py", "--out", self.out, "--yes", "--pause", "0", "--workers", "3", *self.bases)
        self.assertEqual(rc, 0, out)
        st = self.out
        self.assertTrue((st / "FINDINGS.md").exists())
        self.assertTrue((st / "summary.csv").exists())
        self.assertTrue((st / "manifest.json").exists())
        series_dirs = {p.name for p in (st / "parquet" / "kalshi_candles" / "period=1").iterdir()}
        self.assertIn("series=KXFAKEWTIW", series_dirs)
        self.assertIn("series=KXFAKEGOLDD", series_dirs)
        self.assertIn("series=KXFAKEHEATOIL", series_dirs)
        self.assertNotIn("series=KXFAKEWTIH", series_dirs, "hourly excluded by default")
        rc2, out2 = run("verify.py", "--out", st)
        self.assertEqual(rc2, 0, out2)
        mk = pd.concat([pd.read_parquet(p) for p in (st / "parquet" / "kalshi_markets").rglob("part.parquet")])
        w = mk[mk["series"] == "KXFAKEWTIW"]
        self.assertEqual(len(w), 12 * 4)
        self.assertTrue((w["seen_hist"] & w["seen_live"]).any(), "overlap band merged")
        settled = w[w["status"] == "settled"]
        lagged = settled[settled["seen_hist"] & settled["seen_live"]]
        self.assertTrue(len(lagged) > 0)
        self.assertEqual(set(lagged["primary_source"]), {"historical"},
                         "hist record carries settlement fields the live one lacks -> primary")
        self.assertTrue((settled["expiration_value"] != "").all(), "settlement values kept through merge")
        self.assertTrue(settled["settlement_ts"].map(bool).all())
        self.assertTrue((w["merge_conflicts"] != "[]").sum() == 1, "the one deliberate floor_strike conflict")
        self.assertEqual(set(w["ladder_kind"]), {"RANGE"})
        self.assertIn("custom_strike.front_month_contract", mk.columns)
        self.assertIn("settlement_timer_seconds", mk.columns)
        self.assertIn("occurrence_datetime", mk.columns)
        # the archived-but-live-only market was fetched from live
        ents = {e["ticker"]: e for e in (json.loads(l) for l in (st / "manifest.jsonl").read_text().splitlines())}
        lo = self.srv.world.live_only_archived[0]
        self.assertEqual(ents[lo]["source"], "live")
        self.assertEqual(ents[lo]["http_hist"], None if ents[lo]["http_live"] == 200 else 404)
        # a weekly market spans >5000 one-minute candles -> chunked
        big = [e for e in ents.values() if e["series"] == "KXFAKEWTIW" and e["status"] == "ok"]
        self.assertTrue(any(e["chunks"] >= 3 for e in big))
        self.assertTrue(all(e["rows"] > 5000 for e in big if e["chunks"] >= 3))
        txt = (st / "FINDINGS.md").read_text()
        self.assertIn("KXFAKEWTIW", txt)
        self.assertIn("ICE", txt)
        self.assertIn("Databento shortlist", txt)
        self.assertIn("SERIES BY SETTLEMENT SOURCE", out)

    def test_05_resume_is_noop_and_intraday_optin(self):
        before = (self.out / "manifest.jsonl").read_text()
        rc, out = run("collect.py", "--out", self.out, "--yes", "--pause", "0", *self.bases)
        self.assertEqual(rc, 0, out)
        self.assertEqual((self.out / "manifest.jsonl").read_text(), before, "nothing re-fetched on resume")
        rc, out = run("collect.py", "--out", self.out, "--yes", "--pause", "0", "--include-intraday",
                      "--series", "KXFAKEWTIH", *self.bases)
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.out / "parquet" / "kalshi_candles" / "period=1" / "series=KXFAKEWTIH").exists())
        self.assertEqual(run("verify.py", "--out", self.out)[0], 0)

    def test_06_all_null_bid_is_caught(self):
        files = sorted((self.out / "parquet" / "kalshi_candles").rglob("part.parquet"))
        target = files[0]
        orig = target.read_bytes()
        try:
            df = pd.read_parquet(target)
            df["yes_bid_close"] = float("nan")
            df.to_parquet(target, index=False)
            rc, out = run("verify.py", "--out", self.out)
            self.assertEqual(rc, 1)
            self.assertIn("all-null", out)
        finally:
            target.write_bytes(orig)
        self.assertEqual(run("verify.py", "--out", self.out)[0], 0)

    def test_07_outage_then_resume_retries_only_errors(self):
        out = Path(self.tmp) / "data_outage"
        shutil.copy(self.out / "probe.json", out.mkdir(parents=True, exist_ok=True) or out / "probe.json")
        proc = subprocess.Popen([PY, "collect.py", "--out", str(out), "--yes", "--pause", "0.01",
                                 "--retries", "1", "--series", "KXFAKEGOLDD"] + self.bases,
                                cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        mf = out / "manifest.jsonl"
        deadline = time.time() + 120
        while time.time() < deadline:
            if mf.exists() and len(mf.read_text().splitlines()) >= 6:
                break
            time.sleep(0.05)
        self.control("fail/on")
        try:
            log = proc.communicate(timeout=300)[0]
        finally:
            self.control("fail/off")
        self.assertEqual(proc.returncode, 1, log)
        ents = [json.loads(l) for l in mf.read_text().splitlines()]
        errs = [e for e in ents if e["status"] == "error"]
        oks = {e["ticker"]: e for e in ents if e["status"] == "ok"}
        self.assertTrue(errs, "the outage must show up as status=error, fetch_ok=false")
        self.assertTrue(all(e["fetch_ok"] is False for e in errs))
        self.assertTrue(all(503 in (e["http_live"], e["http_hist"]) for e in errs), errs[:2])
        self.assertTrue(oks)
        self.assertIn("status=error", log)
        rc, out2 = run("collect.py", "--out", out, "--yes", "--pause", "0", "--series", "KXFAKEGOLDD", *self.bases)
        self.assertEqual(rc, 0, out2)
        ents2 = [json.loads(l) for l in mf.read_text().splitlines()]
        latest = {}
        for e in ents2:
            latest[e["key"]] = e
        self.assertFalse([e for e in latest.values() if e["status"] == "error"])
        for t, e in oks.items():
            self.assertEqual(latest[t + "@1"]["at"], e["at"], "ok entries were not re-fetched")
        retried = {e["ticker"] for e in errs}
        self.assertTrue(all(latest[t + "@1"]["status"] in ("ok", "empty", "not_found") for t in retried))
        self.assertEqual(run("verify.py", "--out", out)[0], 0)

    def test_08_crosscheck(self):
        old = Path(self.tmp) / "old_layout"
        for p in (self.out / "parquet" / "kalshi_candles").rglob("part.parquet"):
            df = pd.read_parquet(p)
            series = [x for x in p.parts if x.startswith("series=")][0]
            event = [x for x in p.parts if x.startswith("event=")][0]
            d = old / "parquet" / "kalshi_candles" / series / event
            d.mkdir(parents=True, exist_ok=True)
            for tk, sub in df.groupby("ticker"):
                sub.to_parquet(d / ("%s.parquet" % tk), index=False)
            break
        rc, out = run("verify.py", "--out", self.out, "--crosscheck", old)
        self.assertEqual(rc, 0, out)
        self.assertIn("overlapping tickers:", out)
        self.assertIn("exact match on", out)
        self.assertIn("100.00%", out)

    def test_09_findings_only_and_markets_source_flag(self):
        rc, out = run("collect.py", "--out", self.out, "--findings-only")
        self.assertEqual(rc, 0, out)
        out2 = Path(self.tmp) / "data_ms"
        out2.mkdir()
        shutil.copy(self.out / "probe.json", out2 / "probe.json")
        rc, log = run("collect.py", "--out", out2, "--yes", "--pause", "0", "--series", "KXFAKEWTIW",
                      "--markets-source", "markets", *self.bases)
        self.assertEqual(rc, 0, log)
        mk = pd.concat([pd.read_parquet(p) for p in (out2 / "parquet" / "kalshi_markets").rglob("part.parquet")])
        self.assertEqual(len(mk), 48, "live /markets + /historical/markets union still finds every market")
        self.assertTrue((mk["seen_hist"] & ~mk["seen_live"]).any(), "hist-only band visible here")
        self.assertTrue((~mk["seen_hist"] & mk["seen_live"]).any(), "live-only band visible here")
        self.assertTrue((mk["seen_hist"] & mk["seen_live"]).any(), "overlap band visible here")
        self.assertFalse(mk["seen_nested"].any())
        self.assertEqual(run("verify.py", "--out", out2)[0], 0)


if __name__ == "__main__":
    unittest.main()
