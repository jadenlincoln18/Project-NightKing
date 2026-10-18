"""The 5,000-candle cap (silent failure #1): chunking, cap-message parsing,
and the adaptive re-chunk when the API reports a different cap."""
import unittest

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import fixture, kc, client_with, ok


def _candles(n, start_ts=1_000_000):
    return [{"end_period_ts": start_ts + 60 * i,
             "yes_bid": {"close_dollars": "0.10"}, "yes_ask": {"close_dollars": "0.12"},
             "price": {}, "volume_fp": "1.00"} for i in range(n)]


class TestWindows(unittest.TestCase):
    def test_week_of_one_minute_candles_is_three_windows(self):
        w = kc.candle_windows(0, 7 * 86400, 1, 5000)
        self.assertEqual(len(w), 3)
        self.assertEqual(w[0][0], 0)
        self.assertEqual(w[-1][1], 7 * 86400)

    def test_every_window_under_cap_and_contiguous(self):
        for period in (1, 60, 1440):
            for cap in (5000, 2000, 10):
                w = kc.candle_windows(1_700_000_000, 1_700_000_000 + 400 * 86400, period, cap)
                self.assertTrue(all((b - a) / (period * 60) <= cap for a, b in w))
                self.assertTrue(all((b - a) / (period * 60) < cap for a, b in w),
                                "inclusive end boundary must leave a margin")
                for (a, b), (c, d) in zip(w, w[1:]):
                    self.assertEqual(b, c)
                self.assertEqual(w[0][0], 1_700_000_000)
                self.assertEqual(w[-1][1], 1_700_000_000 + 400 * 86400)

    def test_empty_range(self):
        self.assertEqual(kc.candle_windows(10, 10, 1), [])
        self.assertEqual(kc.candle_windows(10, 5, 1), [])

    def test_short_range_single_window(self):
        self.assertEqual(kc.candle_windows(0, 3600, 1), [(0, 3600)])

    def test_estimate_requests(self):
        self.assertEqual(kc.estimate_requests(7 * 86400, 1), 3)
        self.assertEqual(kc.estimate_requests(3600, 1), 1)
        self.assertEqual(kc.estimate_requests(0, 1), 0)


class TestCapMessage(unittest.TestCase):
    def test_parse_from_fixture_body(self):
        import json
        body = json.dumps(fixture("cap_error.json"))
        self.assertEqual(kc.parse_cap_error(body), 5000)

    def test_variants(self):
        self.assertEqual(kc.parse_cap_error("max candlesticks: 5000"), 5000)
        self.assertEqual(kc.parse_cap_error("Max Candlesticks 2000"), 2000)
        self.assertEqual(kc.parse_cap_error("max candlestick=100"), 100)
        self.assertIsNone(kc.parse_cap_error("bad request"))
        self.assertIsNone(kc.parse_cap_error(None))


class TestAdaptiveCap(unittest.TestCase):
    def test_rechunks_when_api_reports_smaller_cap(self):
        """Client believes 5000, API says 2000: the first request 400s with the
        message, the fetcher re-chunks and completes. Zero rows would be the bug."""
        start, end = 1_000_000, 1_000_000 + 6000 * 60     # 6000 one-minute candles
        state = {"cap": 2000}

        def fetch(url):
            import urllib.parse
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
            s, e, p = int(q["start_ts"]), int(q["end_ts"]), int(q["period_interval"])
            n = (e - s) // (p * 60)
            if n > state["cap"]:
                return kc.Resp(400, None, '{"error":"max candlesticks: %d"}' % state["cap"], {}, url)
            return kc.Resp(200, {"candlesticks": _candles(n, s + 60)}, "", {}, url)

        c = kc.Client(live_base="https://live.test/v2", hist_base="https://hist.test/v2/historical",
                      pause=0.0, fetch=fetch)
        caps = kc.CapHolder(5000)
        res = kc.fetch_market_candles(c, "S", "T", start, end, 1, caps)
        self.assertEqual(res.status, "ok")
        self.assertTrue(res.fetch_ok)
        self.assertEqual(caps.cap, 2000)
        self.assertEqual(caps.observed, 2000)
        self.assertEqual(res.cap, 2000)
        self.assertEqual(res.rows, 6000)
        self.assertGreaterEqual(res.chunks, 4)

    def test_cap_holder_never_grows(self):
        caps = kc.CapHolder(5000)
        self.assertFalse(caps.learn(10000))
        self.assertEqual(caps.cap, 5000)
        self.assertTrue(caps.learn(3000))
        self.assertEqual(caps.cap, 3000)

    def test_400_without_cap_message_is_error(self):
        c, ff = client_with([(r"candlesticks", [(400, {"error": "something else"})])])
        res = kc.fetch_market_candles(c, "S", "T", 0, 3600, 1, kc.CapHolder())
        self.assertEqual(res.status, "error")
        self.assertFalse(res.fetch_ok)
        self.assertEqual(res.http_live, 400)
        self.assertEqual(res.http_hist, 400)

    def test_overlap_dedupe(self):
        rows = _candles(3, 100) + _candles(3, 100)
        df = kc.candles_to_frame(rows, "S", "E", "T", "b", "RANGE", 1, "live")
        self.assertEqual(len(df), 3)
        self.assertTrue(df["ts"].is_monotonic_increasing)


if __name__ == "__main__":
    unittest.main()
