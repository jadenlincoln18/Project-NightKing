"""Cadence classification (what gets excluded by default) and the collect filters."""
import argparse
import unittest
from datetime import datetime, timedelta

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import kc, ROOT
import sys
sys.path.insert(0, str(ROOT))
import collect  # noqa: E402


def seq(start, step, n):
    return [start + step * i for i in range(n)]


class TestClassify(unittest.TestCase):
    def test_hourly(self):
        dts = seq(datetime(2026, 9, 1, 0), timedelta(hours=1), 48)
        c = kc.classify_cadence(dts, None)
        self.assertEqual(c["cadence"], "hourly")
        self.assertEqual(c["group"], "intraday")
        self.assertEqual(c["median_minutes"], 60.0)

    def test_15min(self):
        c = kc.classify_cadence(seq(datetime(2026, 9, 1), timedelta(minutes=15), 40), None)
        self.assertEqual((c["cadence"], c["group"]), ("15min", "intraday"))

    def test_daily_with_weekend_gaps(self):
        dts = [datetime(2026, 9, 1) + timedelta(days=d) for d in (0, 1, 2, 3, 4, 7, 8, 9, 10, 11, 14, 15)]
        c = kc.classify_cadence(dts, None)
        self.assertEqual((c["cadence"], c["group"]), ("daily", "daily"))

    def test_weekly_and_monthly_and_longer(self):
        self.assertEqual(kc.classify_cadence(seq(datetime(2026, 1, 2), timedelta(days=7), 30), None)["cadence"], "weekly")
        self.assertEqual(kc.classify_cadence(seq(datetime(2026, 1, 1), timedelta(days=30), 6), None)["cadence"], "monthly")
        self.assertEqual(kc.classify_cadence(seq(datetime(2020, 1, 1), timedelta(days=365), 4), None)["cadence"], "longer")

    def test_unknown_when_too_few(self):
        c = kc.classify_cadence([datetime(2026, 1, 1), datetime(2026, 1, 8)], None)
        self.assertEqual(c["cadence"], "unknown")
        c2 = kc.classify_cadence([datetime(2026, 1, 1)], "weekly")
        self.assertEqual(c2["cadence"], "weekly")
        self.assertTrue(c2.get("from_hint_only"))

    def test_hint_conflict_recorded(self):
        dts = seq(datetime(2026, 9, 1), timedelta(hours=1), 30)
        c = kc.classify_cadence(dts, "daily")
        self.assertEqual(c["cadence"], "hourly", "measurement wins")
        self.assertTrue(c["hint_conflict"])
        c2 = kc.classify_cadence(dts, "hourly")
        self.assertFalse(c2["hint_conflict"])

    def test_hints(self):
        self.assertEqual(kc.cadence_hint("KXWTIH", "WTI Hourly", None), "hourly")
        self.assertEqual(kc.cadence_hint("KXWTI15M", "WTI 15-minute", None), "15min")
        self.assertEqual(kc.cadence_hint("KXGOLDD", "Gold price today", "daily"), "daily")
        self.assertEqual(kc.cadence_hint("KXWTIW", "WTI oil weekly range", None), "weekly")
        self.assertIsNone(kc.cadence_hint("KXWTIWHEN", "When will WTI ...", None))


def _args(**kw):
    base = dict(series=None, exclude=None, cadence=None, include_intraday=False)
    base.update(kw)
    return argparse.Namespace(**base)


SERIES = [
    {"ticker": "KXWTIH", "group": "intraday", "cadence": "hourly"},
    {"ticker": "KXWTIW", "group": "weekly", "cadence": "weekly"},
    {"ticker": "KXGOLDD", "group": "daily", "cadence": "daily"},
    {"ticker": "KXAAAGASD", "group": "daily", "cadence": "daily"},
    {"ticker": "KXWTI15M", "group": "intraday", "cadence": "15min"},
]


class TestFilters(unittest.TestCase):
    def test_default_drops_intraday(self):
        kept, excl = collect.apply_filters(SERIES, _args())
        self.assertEqual({s["ticker"] for s in kept}, {"KXWTIW", "KXGOLDD", "KXAAAGASD"})
        self.assertEqual({s["ticker"] for s in excl}, {"KXWTIH", "KXWTI15M"})
        self.assertTrue(all("intraday" in s["reason"] for s in excl))

    def test_include_intraday(self):
        kept, excl = collect.apply_filters(SERIES, _args(include_intraday=True))
        self.assertEqual(len(kept), 5)
        self.assertEqual(excl, [])

    def test_cadence_list(self):
        kept, _ = collect.apply_filters(SERIES, _args(cadence="hourly,weekly"))
        self.assertEqual({s["ticker"] for s in kept}, {"KXWTIH", "KXWTIW"})

    def test_exclude_glob(self):
        kept, excl = collect.apply_filters(SERIES, _args(exclude="KXAAAGAS*"))
        self.assertNotIn("KXAAAGASD", {s["ticker"] for s in kept})

    def test_explicit_series_overrides_intraday_default(self):
        kept, _ = collect.apply_filters(SERIES, _args(series="KXWTIH,KXNEW"))
        self.assertEqual({s["ticker"] for s in kept}, {"KXWTIH", "KXNEW"})

    def test_priority_order(self):
        kept, _ = collect.apply_filters(SERIES, _args(include_intraday=True))
        self.assertEqual(kept[0]["ticker"][:5], "KXWTI")
        self.assertEqual(kept[-1]["ticker"], "KXAAAGASD")


if __name__ == "__main__":
    unittest.main()
