"""Both ticker generations parse; garbage never raises."""
import unittest
from datetime import datetime

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import kc


class TestParseTicker(unittest.TestCase):
    def test_old_format(self):
        p = kc.parse_ticker("KXWTIW-24DEC06-T74.99")
        self.assertEqual(p["series"], "KXWTIW")
        self.assertEqual(p["date"], "2024-12-06")
        self.assertIsNone(p["hour"])
        self.assertEqual(p["strike_code"], "T74.99")
        self.assertEqual(p["format"], "old")
        self.assertEqual(p["dt"], datetime(2024, 12, 6))

    def test_new_format_with_hour(self):
        p = kc.parse_ticker("KXWTIW-26JUL2414-B79.50")
        self.assertEqual(p["date"], "2026-07-24")
        self.assertEqual(p["hour"], 14)
        self.assertEqual(p["minute"], 0)
        self.assertEqual(p["strike_code"], "B79.50")
        self.assertEqual(p["format"], "new")
        self.assertEqual(p["dt"], datetime(2026, 7, 24, 14, 0))

    def test_hhmm_suffix(self):
        p = kc.parse_ticker("KXWTIDIRY-26DEC31H1430")
        self.assertEqual(p["series"], "KXWTIDIRY")
        self.assertEqual(p["date"], "2026-12-31")
        self.assertEqual((p["hour"], p["minute"]), (14, 30))
        self.assertIsNone(p["strike_code"])
        self.assertEqual(p["format"], "new")

    def test_event_tickers(self):
        self.assertEqual(kc.parse_ticker("KXWTIW-26SEP0414")["hour"], 14)
        self.assertEqual(kc.parse_ticker("KXWTI-26NOV03")["format"], "old")
        self.assertEqual(kc.parse_ticker("KXAAAGASMAXCA-26DEC31")["date"], "2026-12-31")

    def test_no_date(self):
        p = kc.parse_ticker("KXWTIWHEN-65")
        self.assertEqual(p["series"], "KXWTIWHEN")
        self.assertIsNone(p["date"])
        self.assertEqual(p["format"], "none")

    def test_garbage_never_raises(self):
        for t in ("", "garbage", None, 42, "KXWTIW-99XXX01-T1", "KXWTIW-26FEB30-T1", "-"):
            p = kc.parse_ticker(t)
            self.assertEqual(p["format"], "none", t)
            self.assertIsNone(p["dt"])

    def test_event_datetime_fallback_to_strike_date(self):
        ev = {"event_ticker": "KXWTIWHEN-65", "strike_date": "2026-07-03T18:30:00Z"}
        self.assertEqual(kc.event_datetime(ev), datetime(2026, 7, 3, 18, 30))
        self.assertIsNone(kc.event_datetime({"event_ticker": "KXWTIWHEN-65"}))


class TestTimeHelpers(unittest.TestCase):
    def test_iso_to_epoch(self):
        self.assertEqual(kc.iso_to_epoch("1970-01-01T00:00:00Z"), 0)
        self.assertEqual(kc.iso_to_epoch("2026-06-26T18:30:00Z"), 1782498600)
        self.assertIsNone(kc.iso_to_epoch(""))
        self.assertIsNone(kc.iso_to_epoch(None))
        self.assertIsNone(kc.iso_to_epoch("not a date"))

    def test_market_lifetime(self):
        m = {"open_time": "2026-06-19T14:00:00Z", "close_time": "2026-06-26T18:30:00Z"}
        t0, t1 = kc.market_lifetime(m, now=kc.iso_to_epoch("2026-06-22T00:00:00Z"))
        self.assertEqual(t0, kc.iso_to_epoch("2026-06-19T14:00:00Z"))
        self.assertEqual(t1, kc.iso_to_epoch("2026-06-22T00:00:00Z"), "clamped to now")
        self.assertEqual(kc.market_lifetime({}, now=1)[0], None)
        self.assertEqual(kc.market_lifetime({"open_time": "2026-06-19T14:00:00Z",
                                             "close_time": "2026-06-19T13:00:00Z"}, now=2_000_000_000)[1], None)


if __name__ == "__main__":
    unittest.main()
